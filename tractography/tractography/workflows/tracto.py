from configparser import ConfigParser
from nipype import DataGrabber, Node, Workflow, MapNode, Merge
from nipype.interfaces.utility import IdentityInterface
from nipype.interfaces.utility.wrappers import Function
from nipype.interfaces.fsl import ProbTrackX2, BEDPOSTX5
import nipype.interfaces.ants as ants
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
                        "output.MNI2t1w_xfm",
                        "MNI2t1w_xfm",
                    ),
                    ("output.preprocessed_dwi", "dwi"),
                    ("output.bval", "bval"),
                    ("output.rotated_bvec", "bvec"),
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
    n_fibres=3,
    fudge=1,
    burn_in=1000,
    n_jumps=1250,
    sample_every=25,
    output_dir=".",
):

    def shrink_surface_fun(surface, image, distance):
        from os.path import join, basename
        from os import getcwd
        import subprocess

        output_file = str(join(getcwd(), basename(surface)))
        output_file = output_file.replace(".surf.gii", "_shrunk.surf.gii")

        subprocess.check_call(
            f"shrink_surface -surface {surface} -reference {image} "
            f"-mm {distance} -out {output_file}",
            shell=True,
        )

        if "lh" in output_file:
            structure_name = "CORTEX_LEFT"
        elif "rh" in output_file:
            structure_name = "CORTEX_RIGHT"

        if "inflated" in output_file:
            surface_type = "INFLATED"
        elif "sphere" in output_file:
            surface_type = "SPHERICAL"
        else:
            surface_type = "ANATOMICAL"

        if "pial" in output_file:
            secondary_type = "PIAL"
        if "white" in output_file:
            secondary_type = "GRAY_WHITE"

        subprocess.check_call(
            f"wb_command -set-structure {output_file} {structure_name} "
            f"-surface-type {surface_type} -surface-secondary-type "
            f"{secondary_type}",
            shell=True,
        )

        return output_file

    shrink_surface_node = MapNode(
        interface=Function(
            input_names=["surface", "image", "distance"],
            output_names=["out_file"],
            function=shrink_surface_fun,
        ),
        name="surface_shrink_surface",
        iterfield=["surface"],
    )
    shrink_surface_node.inputs.distance = 3

    roi_source = Node(DataGrabber(infields=[]), name="rois")
    roi_source.inputs.sort_filelist = True
    roi_source.inputs.base_directory = config.roi_dir
    roi_source.inputs.template = "*.nii.gz"

    input_subject = Node(
        IdentityInterface(
            fields=[
                "preprocessed_dwi",
                "bval",
                "rotated_bvec",
                "preprocessed_t1",
                "preprocessed_t1_mask",
                "bids_entities",
            ],
        ),
        name="input_subject",
    )

    # node for applying registration from recon to ROIs
    apply_registration = MapNode(
        interface=ants.ApplyTransforms(),
        name="apply_registration",
        iterfield=["input_image"],
    )
    apply_registration.inputs.dimension = 3
    apply_registration.inputs.input_image_type = 3
    apply_registration.inputs.interpolation = "NearestNeighbor"

    # node for joining seeds
    join_seeds = Node(
        interface=Merge(2),
        name="join_seeds",
    )

    # bedpost_gpu
    bedpost_gpu = Node(interface=BEDPOSTX5(), name="bedpost_gpu")
    bedpost_gpu.inputs.n_fibres = n_fibres
    bedpost_gpu.inputs.fudge = fudge
    bedpost_gpu.inputs.burn_in = burn_in
    bedpost_gpu.inputs.n_jumps = n_jumps
    bedpost_gpu.inputs.sample_every = sample_every
    bedpost_gpu.inputs.use_gpu = True

    # setup probtrackx2 node
    pbx2 = Node(
        interface=ProbTrackX2(),
        name="probtrackx2",
    )
    pbx2.inputs.n_samples = 5000
    pbx2.inputs.n_steps = 2000
    pbx2.inputs.step_length = 0.5
    pbx2.inputs.omatrix1 = True
    pbx2.inputs.distthresh1 = 5
    pbx2.inputs.args = " --ompl --fibthresh=0.01 "

    workflow = Workflow(name=name, base_dir=output_dir)
    workflow.connect(
        [
            (roi_source, apply_registration, [("outfiles", "input_image")]),
            (
                input_subject,
                apply_registration,
                [
                    ("output.MNI2t1w_xfm", "transforms"),
                    ("output.preprocessed_t1", "reference_image"),
                ],
            ),
            (
                input_subject,
                shrink_surface_node,
                [("output.surfaces_t1", "surface")],
            ),
            (
                input_subject,
                shrink_surface_node,
                [("output.preprocessed_t1", "image")],
            ),
            (
                shrink_surface_node,
                join_seeds,
                [("output.shrunk_surface", "in1")],
            ),
            (apply_registration, join_seeds, [("output_image", "in2")]),
            (
                join_seeds,
                pbx2,
                [
                    ("out", "seed"),
                ],
            ),
            (
                input_subject,
                bedpost_gpu,
                [
                    ("output.bval", "bvals"),
                    ("output.rotated_bvec", "bvecs"),
                    ("output.preprocessed_dwi", "dwi"),
                    ("output.preprocessed_t1_mask", "mask"),
                ],
            ),
            (
                input_subject,
                pbx2,
                [
                    ("output.preprocessed_t1_mask", "mask"),
                ],
            ),
            (
                bedpost_gpu,
                pbx2,
                [
                    ("merged_thsamples", "thsamples"),
                    ("merged_fsamples", "fsamples"),
                    ("merged_phsamples", "phsamples"),
                ],
            ),
        ]
    )
    return workflow
