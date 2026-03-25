from nipype import IdentityInterface, Node, Workflow
from nipype.interfaces.utility import Function
from nipype.interfaces.io import DataSink


def init_sink_wf(config, name="sink_wf"):

    inputnode = Node(
        IdentityInterface(
            fields=[
                "bids_entities",
                "streamlines",
                "wm_fod",
                "gm_fod",
                "csf_fod",
                "gmwm_boundary",
                "t1_5tt",
            ]
        ),
        name="sinkinputnode",
    )

    ### build the full file name
    def build_substitutions(
        bids_entities,
        streamlines=None,
        wm_fod=None,
        gm_fod=None,
        csf_fod=None,
        gmwm_boundary=None,
        t1_5tt=None,
    ):

        import os
        from pathlib import Path

        def _build_bids(bids_entities):
            replacements = {
                "subject": "sub-",
                "session": "_ses-",
                "acquisition": "_acq-",
                "direction": "_dir-",
                "part": "_part-",
            }
            bids_name = ""
            for key, value in bids_entities.items():
                if key in replacements:
                    bids_name += f"{replacements[key]}{value}"
            return bids_name

        bids_name = _build_bids(bids_entities)

        substitutions = []

        # Add tractography outputs if provided
        if streamlines:
            substitutions.append(
                (
                    "streamlines.tck",
                    f"{bids_name}_space-T1_desc-iFOD2+ACT+10M_tractography.tck",
                )
            )
        if wm_fod:
            substitutions.append(
                (
                    "wm_fod.mif",
                    f"{bids_name}_space-T1_desc-msmt+csd_wm_fod.mif",
                )
            )
        if gm_fod:
            substitutions.append(
                (
                    "gm_fod.mif",
                    f"{bids_name}_space-T1_desc-msmt+csd_gm_fod.mif",
                )
            )
        if csf_fod:
            substitutions.append(
                (
                    "csf_fod.mif",
                    f"{bids_name}_space-T1_desc-msmt+csd_csf_fod.mif",
                )
            )
        if gmwm_boundary:
            substitutions.append(
                (
                    "gmwm_boundary.mif",
                    f"{bids_name}_space-T1_desc-gmwm+boundary_mask.mif",
                )
            )
        if t1_5tt:
            substitutions.append(
                (
                    "t1_5tt.mif",
                    f"{bids_name}_space-T1_desc-5tissue+segmentation_space.mif",
                )
            )

        # add root directory with derivatives/diffusion-tractography structure
        for i, (src, dst) in enumerate(substitutions):

            modality = dst.split("_")[-1].split(".")[0]

            if bids_entities.get("session"):
                prefix = os.path.join(
                    "sub-" + bids_entities["subject"],
                    "ses-" + bids_entities["session"],
                    modality,
                )
            else:
                prefix = os.path.join(
                    "sub-" + bids_entities["subject"],
                    modality,
                )

            substitutions[i] = (src, os.path.join(prefix, dst))

        return substitutions

    BuildSubstitutions = Function(
        input_names=[
            "bids_entities",
            "streamlines",
            "wm_fod",
            "gm_fod",
            "csf_fod",
            "gmwm_boundary",
            "t1_5tt",
        ],
        output_names=["substitutions"],
        function=build_substitutions,
    )
    build_substitutions = Node(BuildSubstitutions, name="build_substitutions")

    ### DataSink node
    sink = Node(DataSink(), name="sink")
    sink.inputs.base_directory = str(config.output_dir)

    # Create the workflow
    sink_wf = Workflow(name=name)
    sink_wf.connect(
        [
            (
                inputnode,
                build_substitutions,
                [
                    ("bids_entities", "bids_entities"),
                    ("streamlines", "streamlines"),
                    ("wm_fod", "wm_fod"),
                    ("gm_fod", "gm_fod"),
                    ("csf_fod", "csf_fod"),
                    ("gmwm_boundary", "gmwm_boundary"),
                    ("t1_5tt", "t1_5tt"),
                ],
            ),
            (build_substitutions, sink, [("substitutions", "substitutions")]),
        ]
    )
    return sink_wf
