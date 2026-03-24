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
    MRTransform,
    Generate5tt,
    Generate5tt2gmwmi,
    Tractography,
)
from .bids import init_bidsdata_wf
from .sink import init_sink_wf
from .report import init_report_wf


def init_tracto_wf(output_dir=".", config=None):
    wf = _tracto_wf(output_dir=output_dir, config=config)
    wf = _set_inputs_outputs(config, wf)
    return wf


def _set_inputs_outputs(config, tracto_wf):
    # bids dataset
    bidsdata_wf = init_bidsdata_wf(config=config)
    # outputs
    sink_wf = init_sink_wf(config=config)
    # report
    report_wf = init_report_wf(
        calling_wf_name="diffusion_tractography",
        output_dir=config.output_dir,
        name="report",
    )
    # create the full workflow
    tracto_wf.connect(
        [
            (
                bidsdata_wf,
                tracto_wf.get_node("input_subject"),
                [
                    (
                        "output.preprocessed_t1_mask",
                        "preprocessed_t1_mask",
                    ),
                    ("output.preprocessed_dwi", "preprocessed_dwi"),
                    ("output.bval", "bval"),
                    ("output.rotated_bvec", "rotated_bvec"),
                    ("output.t1_dseg", "t1_dseg"),
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
            (
                tracto_wf.get_node("output_subject"),
                sink_wf,
                [
                    ("streamlines", "sinkinputnode.streamlines"),
                    ("wm_fod", "sinkinputnode.wm_fod"),
                    ("gm_fod", "sinkinputnode.gm_fod"),
                    ("csf_fod", "sinkinputnode.csf_fod"),
                    ("gmwm_boundary", "sinkinputnode.gmwm_boundary"),
                    ("t1_5tt", "sinkinputnode.t1_5tt"),
                ],
            ),
            # Connect tractography outputs to report
            (
                tracto_wf.get_node("output_subject"),
                report_wf.get_node("report_inputnode"),
                [
                    ("streamlines", "streamlines"),
                    ("wm_fod", "wm_fod"),
                    ("gmwm_boundary", "gmwm_boundary"),
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
                "preprocessed_t1_mask",
                "bids_entities",
                "t1_dseg",
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

    # Generate 5-tissue segmentation from anatomical image using freesurfer-style segmentation
    # This converts the tissue segmentation (dseg from sMRIprep) to MrTrix3's 5-tissue format
    generate5tt = Node(
        interface=Generate5tt(),
        name="generate5tt",
    )
    generate5tt.inputs.algorithm = "freesurfer"
    generate5tt.inputs.out_file = "t1_5tt.mif"
    generate5tt.inputs.lut_file = "/opt/FreeSurferColorLUT.txt"

    # ===== GM/WM Boundary Generation =====
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

    # ===== Output Node =====
    output_subject = Node(
        IdentityInterface(
            fields=[
                "streamlines",
                "wm_fod",
                "gm_fod",
                "csf_fod",
                "gmwm_boundary",
                "t1_5tt",
            ],
        ),
        name="output_subject",
    )

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
                    ("rotated_bvec", "in_bvec"),
                    ("bval", "in_bval"),
                ],
            ),
            # Response function estimation from DWI
            (dwi2mif, response_wm, [("out_file", "in_file")]),
            (
                input_subject,
                response_wm,
                [
                    ("rotated_bvec", "in_bvec"),
                    ("bval", "in_bval"),
                    ("preprocessed_t1_mask", "in_mask"),
                ],
            ),
            # FOD estimation using response functions
            (dwi2mif, estimate_fod, [("out_file", "in_file")]),
            (
                input_subject,
                estimate_fod,
                [
                    ("rotated_bvec", "in_bvec"),
                    ("bval", "in_bval"),
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
            # Anatomical processing: Generate 5-tissue segmentation from dseg
            (input_subject, generate5tt, [("t1_dseg", "in_file")]),
            # Generate GM/WM boundary from 5-tissue segmentation
            (generate5tt, gmwm_boundary, [("out_file", "in_file")]),
            # Generate streamlines with anatomical constraints
            # All processing is in T1 space
            (estimate_fod, tckgen, [("wm_odf", "in_file")]),
            (generate5tt, tckgen, [("out_file", "act_file")]),
            (gmwm_boundary, tckgen, [("mask_out", "seed_gmwmi")]),
            # Collect outputs
            (tckgen, output_subject, [("out_file", "streamlines")]),
            (
                estimate_fod,
                output_subject,
                [
                    ("wm_odf", "wm_fod"),
                    ("gm_odf", "gm_fod"),
                    ("csf_odf", "csf_fod"),
                ],
            ),
            (gmwm_boundary, output_subject, [("mask_out", "gmwm_boundary")]),
            (generate5tt, output_subject, [("out_file", "t1_5tt")]),
        ]
    )

    return workflow
