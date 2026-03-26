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
    Tractography as MRTrix3Tractography,
)
from nipype.interfaces.mrtrix3.connectivity import BuildConnectome
from nipype.interfaces.mrtrix3.tracking import (
    TractographyInputSpec,
    TractographyOutputSpec,
)
from nipype.interfaces.mrtrix3.utils import (
    Generate5ttInputSpec,
    Generate5ttOutputSpec,
)
from nipype.interfaces.mrtrix3.base import MRTrix3Base
from nipype.interfaces.base import traits, File, isdefined
from .bids import init_bidsdata_wf
from .sink import init_sink_wf
from .report import init_report_wf


# Custom Generate5tt interface with proper lut_file positioning
class Generate5ttWithLUT(MRTrix3Base):
    """Generate5tt with LUT file support using explicit command line building."""

    class input_spec(Generate5ttInputSpec):
        # Add lut_file as an optional parameter
        lut_file = File(
            exists=True,
            argstr="-lut %s",
            desc="Manually provide path to the lookup table.",
        )

    output_spec = Generate5ttOutputSpec
    _cmd = "5ttgen"

    def _list_outputs(self):
        """Capture the output file from Generate5tt."""
        import os.path as op

        outputs = self.output_spec().get()
        outputs["out_file"] = op.abspath(self.inputs.out_file)
        return outputs

    @property
    def cmdline(self):
        """Manually build the command line with correct argument ordering.

        Order should be: 5ttgen algorithm [-lut lut.txt] input.mif output.mif
        """
        from nipype.utils.filemanip import fname_presuffix
        import os.path as op

        cmd_parts = [self._cmd]

        # 1. Add algorithm (mandatory positional)
        cmd_parts.append(str(self.inputs.algorithm))

        # 2. Add lut_file if provided (optional flag)
        if isdefined(self.inputs.lut_file):
            cmd_parts.append("-lut")
            cmd_parts.append(str(self.inputs.lut_file))

        # 3. Add in_file (mandatory positional)
        cmd_parts.append(str(self.inputs.in_file))

        # 4. Add out_file (mandatory positional)
        cmd_parts.append(str(self.inputs.out_file))

        cmdline = " ".join(cmd_parts)
        return cmdline


# Custom Tractography interface with nthreads support
class TractographyWithNThreads(MRTrix3Base):
    """Tractography with nthreads parameter for controlling parallelization."""

    class input_spec(TractographyInputSpec):
        # Add nthreads parameter
        nthreads = traits.Int(
            argstr="-nthreads %d",
            desc="Number of threads to use for tractography",
        )

    output_spec = TractographyOutputSpec
    _cmd = "tckgen"

    def _format_arg(self, name, trait_spec, value):
        """Format arguments like the parent class."""
        if "roi_" in name and isinstance(value, tuple):
            value = ["%f" % v for v in value]
            return trait_spec.argstr % ",".join(value)
        return super()._format_arg(name, trait_spec, value)

    def _list_outputs(self):
        """Capture output files."""
        import os.path as op

        outputs = self.output_spec().get()
        outputs["out_file"] = op.abspath(self.inputs.out_file)
        if isdefined(self.inputs.out_seeds):
            outputs["out_seeds"] = op.abspath(self.inputs.out_seeds)
        return outputs


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
    if config and getattr(config, "parcellation_file", None):
        tracto_wf.get_node("input_subject").inputs.parcellation_file = str(
            config.parcellation_file
        )

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
                    ("output.preprocessed_t1", "preprocessed_t1"),
                    ("output.bval", "bval"),
                    ("output.rotated_bvec", "rotated_bvec"),
                    ("output.t1_dseg", "t1_dseg"),
                    ("output.space2t1w_xfm", "space2t1w_xfm"),
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
                sink_wf.get_node("sink"),
                [
                    ("streamlines", "diffusion_tractography.@streamlines"),
                    ("wm_fod", "diffusion_tractography.@wm_fod"),
                    ("gm_fod", "diffusion_tractography.@gm_fod"),
                    ("csf_fod", "diffusion_tractography.@csf_fod"),
                    ("gmwm_boundary", "diffusion_tractography.@gmwm_boundary"),
                    ("t1_5tt", "diffusion_tractography.@t1_5tt"),
                ],
            ),
            *(
                [
                    (
                        tracto_wf.get_node("output_subject"),
                        sink_wf.get_node("sink"),
                        [("connectome", "diffusion_tractography.@connectome")],
                    )
                ]
                if config and getattr(config, "parcellation_file", None)
                else []
            ),
            (
                tracto_wf.get_node("report"),
                sink_wf.get_node("sink"),
                [
                    (
                        "report_outputnode.out_file",
                        "diffusion_tractography.@report",
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
                "preprocessed_t1_mask",
                "preprocessed_t1",
                "bids_entities",
                "t1_dseg",
                "space2t1w_xfm",
                "parcellation_file",
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
    estimate_fod.inputs.max_sh = [8, 8, 8]  # lmax for WM, GM, CSF tissues
    estimate_fod.inputs.wm_odf = "wm_fod.mif"
    estimate_fod.inputs.gm_odf = "gm_fod.mif"
    estimate_fod.inputs.csf_odf = "csf_fod.mif"

    # ===== Anatomical Processing =====

    # Generate 5-tissue segmentation from anatomical image using freesurfer-style segmentation
    # This converts the tissue segmentation (dseg from sMRIprep) to MrTrix3's 5-tissue format
    # Uses custom interface with proper LUT file argument positioning
    generate5tt = Node(
        interface=Generate5ttWithLUT(),
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
        interface=TractographyWithNThreads(),
        name="tckgen",
    )
    tckgen.inputs.algorithm = "iFOD2"  # Improved Fiber ODFs
    tckgen.inputs.select = nstreamlines  # Number of streamlines to generate
    tckgen.inputs.max_length = max_len  # Maximum length in mm
    tckgen.inputs.min_length = 10  # Minimum length in mm
    tckgen.inputs.cutoff = cutoff  # FOD amplitude cutoff
    tckgen.inputs.backtrack = True  # Allow backtracking
    tckgen.inputs.out_file = "streamlines.tck"

    # Set nthreads if config provides it
    if (
        config
        and hasattr(config, "n_threads")
        and config.n_threads is not None
    ):
        tckgen.inputs.nthreads = 30

    # ===== Connectome Nodes (optional — only when parcellation_file is provided) =====

    has_parcellation = config and getattr(config, "parcellation_file", None)

    if has_parcellation:
        # Register parcellation from standard space to T1w space
        # NearestNeighbor interpolation preserves integer label values
        apply_transform_parc = Node(
            interface=ants.ApplyTransforms(),
            name="apply_transform_parc",
        )
        apply_transform_parc.inputs.interpolation = "NearestNeighbor"
        apply_transform_parc.inputs.output_image = "parcellation_t1w.nii.gz"
        apply_transform_parc.inputs.input_image_type = 0  # scalar / label image

        # Compute structural connectome from streamlines and parcellation
        tck2connectome = Node(
            interface=BuildConnectome(),
            name="tck2connectome",
        )
        tck2connectome.inputs.out_file = "connectome.csv"

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
                *(["connectome"] if has_parcellation else []),
            ],
        ),
        name="output_subject",
    )

    report = init_report_wf(
        name="report",
        calling_wf_name=name,
        output_dir=output_dir,
        has_connectome=bool(has_parcellation),
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
            # Connect tractography outputs to report
            (
                input_subject,
                report,
                [("bids_entities", "report_inputnode.bids_entities")],
            ),
        ]
    )

    if has_parcellation:
        workflow.connect(
            [
                # Transform parcellation from standard space to T1w space
                (
                    input_subject,
                    apply_transform_parc,
                    [
                        ("parcellation_file", "input_image"),
                        ("preprocessed_t1", "reference_image"),
                        ("space2t1w_xfm", "transforms"),
                    ],
                ),
                # Compute connectome from streamlines and T1w-space parcellation
                (tckgen, tck2connectome, [("out_file", "in_file")]),
                (
                    apply_transform_parc,
                    tck2connectome,
                    [("output_image", "in_parc")],
                ),
                # Collect connectome output
                (
                    tck2connectome,
                    output_subject,
                    [("out_file", "connectome")],
                ),
                # Forward connectome to report
                (
                    tck2connectome,
                    report,
                    [("out_file", "report_inputnode.connectome")],
                ),
            ]
        )

    workflow.connect(
        [
            (
                output_subject,
                report,
                [
                    ("streamlines", "report_inputnode.streamlines"),
                ],
            ),
            (
                input_subject,
                report,
                [
                    ("preprocessed_t1", "report_inputnode.t1w"),
                ],
            ),
        ]
    )

    return workflow
