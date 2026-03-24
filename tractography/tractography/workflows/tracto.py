from configparser import ConfigParser
from nipype import DataGrabber, Node, Workflow, MapNode, Merge
from nipype.interfaces.utility import IdentityInterface
from nipype.interfaces.utility.wrappers import Function
import nipype.interfaces.ants as ants
import nipype.interfaces.fsl as fsl
from nipype.interfaces.mrtrix3 import (
    MRConvert,
    ResponseSD,
    EstimateFOD,
    Generate5tt,
    MRTransform,
    Generate5tt2gmwmi,
    Tractography,
    TransformFSLConvert,
)
from .bids import init_bidsdata_wf
from .sink import init_sink_wf


def init_tracto_wf(output_dir=".", config=None):
    wf = _tracto_wf(output_dir=output_dir, config=config)
    wf = _set_inputs_outputs(config, wf)
    return wf


def _set_inputs_outputs(config, tracto_wf):
    # bids dataset
    bidsdata_wf = init_bidsdata_wf(config=config)
    # outputs
    sink_wf = init_sink_wf(config=config)
    # create the full workflow
    tracto_wf.connect(
        [
            (
                bidsdata_wf,
                tracto_wf.get_node("input_subject"),
                [
                    ("output.preprocessed_t1", "preprocessed_t1"),
                    (
                        "output.preprocessed_t1_mask",
                        "preprocessed_t1_mask",
                    ),
                    (
                        "output.space2t1w_xfm",
                        "space2t1w_xfm",
                    ),
                    ("output.preprocessed_dwi", "preprocessed_dwi"),
                    ("output.bval", "bval"),
                    ("output.rotated_bvec", "rotated_bvec"),
                    ("output.surfaces_t1", "surfaces_t1"),
                    ("decode_entities.bids_entities", "bids_entities"),
                ],
            ),
            (
                bidsdata_wf,
                sink_wf,
                [
                    (
                        "decode_entities.bids_entities",
                        "sinkinputnode.bids_entities",
                    )
                ],
            ),
        ]
    )
    return tracto_wf


def _tracto_wf(
    config,
    name="diffusion_tractography",
    max_len=250,
    cutoff=0.06,
    nstreamlines=10000000,
    output_dir=".",
):
    """
    MrTrix3-based tractography workflow.

    Parameters
    ----------
    config : object
        Configuration object containing roi_dir, gpu settings, etc.
    name : str
        Name of the workflow
    max_len : int
        Maximum length of streamlines in mm
    cutoff : float
        FA cutoff for streamline generation
    nstreamlines : int
        Number of streamlines to generate
    output_dir : str
        Base output directory
    """

    input_subject = Node(
        IdentityInterface(
            fields=[
                "preprocessed_dwi",
                "bval",
                "rotated_bvec",
                "preprocessed_t1",
                "preprocessed_t1_mask",
                "bids_entities",
                "space2t1w_xfm",
                "surfaces_t1",
            ],
        ),
        name="input_subject",
    )

    # ===== DWI Processing with MrTrix3 =====

    # Convert preprocessed DWI to MIF format
    # Uses bvec/bval files in FSL format
    dwi2mif = Node(
        interface=MRConvert(),
        name="dwi2mif",
    )
    dwi2mif.inputs.grad_fsl = True
    dwi2mif.inputs.out_file = "dwi.mif"

    # Derive response functions using Dhollander algorithm
    # This estimates WM, GM, and CSF response functions
    response_wm = Node(
        interface=ResponseSD(),
        name="response_wm",
    )
    response_wm.inputs.algorithm = "dhollander"
    response_wm.inputs.wm_file = "wm_response.txt"
    response_wm.inputs.gm_file = "gm_response.txt"
    response_wm.inputs.csf_file = "csf_response.txt"

    # Estimate fiber orientation distributions (FOD) using multi-shell multi-tissue CSD
    estimate_fod = Node(
        interface=EstimateFOD(),
        name="estimate_fod",
    )
    estimate_fod.inputs.algorithm = "msmt_csd"
    estimate_fod.inputs.wm_odf = "wm_fod.mif"
    estimate_fod.inputs.gm_odf = "gm_fod.mif"
    estimate_fod.inputs.csf_odf = "csf_fod.mif"

    # ===== Anatomical Processing =====

    # Remove NaNs from T1
    remove_nans = Node(
        interface=fsl.ImageMaths(),
        name="remove_nans",
    )
    remove_nans.inputs.op_string = "-nan"
    remove_nans.inputs.out_file = "t1_nonan.nii.gz"

    # Convert T1 to MIF format
    t12mif = Node(
        interface=MRConvert(),
        name="t12mif",
    )
    t12mif.inputs.out_file = "t1.mif"

    # Generate 5TT segmentation (5-tissue-type) from T1
    # Uses FSL's tissue classification tools
    generate_5tt = Node(
        interface=Generate5tt(),
        name="generate_5tt",
    )
    generate_5tt.inputs.algorithm = "fsl"
    generate_5tt.inputs.out_file = "t1_5tt.mif"

    # ===== Registration and Transformation =====

    # Extract first volume (b=0) from DWI for registration
    extract_b0 = Node(
        interface=MRConvert(),
        name="extract_b0",
    )
    extract_b0.inputs.coord = [
        3,
        0,
    ]  # Extract volume at index 0 along dimension 3
    extract_b0.inputs.out_file = "mean_b0.nii.gz"

    # Register b0 to T1 using FLIRT
    reg_b0_to_t1 = Node(
        interface=fsl.FLIRT(),
        name="reg_b0_to_t1",
    )
    reg_b0_to_t1.inputs.out_file = "b0_to_t1.nii.gz"
    reg_b0_to_t1.inputs.out_matrix_file = "b0_to_t1.mat"

    # Convert FSL transformation to MrTrix3 format
    convert_xfm = Node(
        interface=TransformFSLConvert(),
        name="convert_xfm",
    )
    convert_xfm.inputs.flirt_import = True
    convert_xfm.inputs.out_transform = "b0_to_t1.txt"

    # Apply transformation to 5TT segmentation to align it to DWI space
    # Use inverse transform to go from T1 space to DWI space
    transform_5tt = Node(
        interface=MRTransform(),
        name="transform_5tt",
    )
    transform_5tt.inputs.linear_transform = True
    transform_5tt.inputs.invert = True
    transform_5tt.inputs.out_file = "t1_5tt_aligned.mif"

    # Generate GM/WM boundary for seeding
    gmwm_boundary = Node(
        interface=Generate5tt2gmwmi(),
        name="gmwm_boundary",
    )
    gmwm_boundary.inputs.mask_out = "gmwm_boundary.mif"

    # ===== Streamline Generation =====

    # Generate streamlines using ACT (Anatomically Constrained Tractography)
    tckgen = Node(
        interface=Tractography(),
        name="tckgen",
    )
    tckgen.inputs.algorithm = "iFOD2"  # Improved Fiber ODFs
    tckgen.inputs.select = nstreamlines  # Number of streamlines to generate
    tckgen.inputs.max_length = max_len  # Maximum length in mm
    tckgen.inputs.min_length = 10  # Minimum length in mm
    tckgen.inputs.cutoff = cutoff  # FOD amplitude cutoff
    tckgen.inputs.use_rk4 = True  # Use 4th order Runge-Kutta integration
    tckgen.inputs.backtrack = True  # Allow backtracking
    tckgen.inputs.out_file = "streamlines.tck"

    # Build workflow
    workflow = Workflow(name=name, base_dir=output_dir)
    workflow.connect(
        [
            # DWI to MIF conversion with bvec/bval
            (
                input_subject,
                dwi2mif,
                [
                    ("preprocessed_dwi", "in_file"),
                    ("rotated_bvec", "bvec_file"),
                    ("bval", "bval_file"),
                ],
            ),
            # Response function estimation from DWI
            (dwi2mif, response_wm, [("out_file", "in_file")]),
            (
                input_subject,
                response_wm,
                [
                    ("rotated_bvec", "bvec_file"),
                    ("bval", "bval_file"),
                    ("preprocessed_t1_mask", "mask_file"),
                ],
            ),
            # FOD estimation using response functions
            (dwi2mif, estimate_fod, [("out_file", "in_file")]),
            (
                input_subject,
                estimate_fod,
                [
                    ("rotated_bvec", "bvec_file"),
                    ("bval", "bval_file"),
                    ("preprocessed_t1_mask", "mask_file"),
                ],
            ),
            (
                response_wm,
                estimate_fod,
                [
                    ("wm_file", "wm_txt"),
                    ("gm_file", "gm_txt"),
                    ("csf_file", "csf_txt"),
                ],
            ),
            # T1 processing
            (input_subject, remove_nans, [("preprocessed_t1", "in_file")]),
            (remove_nans, t12mif, [("out_file", "in_file")]),
            (t12mif, generate_5tt, [("out_file", "in_file")]),
            # Extract b0 for registration
            (dwi2mif, extract_b0, [("out_file", "in_file")]),
            # Register b0 to T1
            (extract_b0, reg_b0_to_t1, [("out_file", "in_file")]),
            (remove_nans, reg_b0_to_t1, [("out_file", "reference")]),
            # Convert transformation matrix to MrTrix format
            (reg_b0_to_t1, convert_xfm, [("out_matrix_file", "in_transform")]),
            (extract_b0, convert_xfm, [("out_file", "in_file")]),
            (remove_nans, convert_xfm, [("out_file", "reference")]),
            # Transform 5TT to DWI space
            (generate_5tt, transform_5tt, [("out_file", "in_files")]),
            (
                convert_xfm,
                transform_5tt,
                [("out_transform", "linear_transform")],
            ),
            # Generate GM/WM boundary
            (transform_5tt, gmwm_boundary, [("out_file", "in_file")]),
            # Generate streamlines with anatomical constraints
            (estimate_fod, tckgen, [("wm_odf", "in_file")]),
            (transform_5tt, tckgen, [("out_file", "act_file")]),
            (gmwm_boundary, tckgen, [("mask_out", "seed_gmwmi")]),
        ]
    )

    return workflow
