from nipype import IdentityInterface, Node, Workflow
from nipype.interfaces.utility import Function
from nipype.interfaces.io import DataSink


def init_sink_wf(config, name="sink_wf", parcellation_file=None):

    inputnode = Node(
        IdentityInterface(fields=["bids_entities"]),
        name="sinkinputnode",
    )

    # Derive a BIDS-compatible atlas label from the parcellation filename stem
    # e.g. schaefer2018_100parcels_7networks_5mm.nii.gz -> schaefer2018+100parcels+7networks+5mm
    atlas_name = ""
    if parcellation_file is not None:
        from pathlib import Path as _Path
        stem = _Path(parcellation_file).name.split(".")[0]
        atlas_name = stem.replace("_", "+")

    ### build the full file name
    def build_substitutions(bids_entities, atlas_name=""):

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

        substitutions = [
            (
                "streamlines.tck",
                f"{bids_name}_space-T1_desc-iFOD2+ACT+10M_tractography.tck",
            ),
            (
                "wm_fod.mif",
                f"{bids_name}_space-T1_desc-msmt+csd_wm_fod.mif",
            ),
            (
                "gm_fod.mif",
                f"{bids_name}_space-T1_desc-msmt+csd_gm_fod.mif",
            ),
            (
                "csf_fod.mif",
                f"{bids_name}_space-T1_desc-msmt+csd_csf_fod.mif",
            ),
            (
                "gmwm_boundary.mif",
                f"{bids_name}_space-T1_desc-gmwm+boundary_mask.mif",
            ),
            (
                "t1_5tt.mif",
                f"{bids_name}_space-T1_desc-5tissuetype_segmentation.mif",
            ),
            (
                f"{bids_name}_report.html",
                f"{bids_name}_report.html",
            ),
        ]

        if atlas_name:
            substitutions.append(
                (
                    "connectome.csv",
                    f"{bids_name}_atlas-{atlas_name}_desc-iFOD2+ACT+10M_connectome.csv",
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
        input_names=["bids_entities", "atlas_name"],
        output_names=["substitutions"],
        function=build_substitutions,
    )
    build_substitutions = Node(BuildSubstitutions, name="build_substitutions")
    build_substitutions.inputs.atlas_name = atlas_name

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
                [("bids_entities", "bids_entities")],
            ),
            (build_substitutions, sink, [("substitutions", "substitutions")]),
        ]
    )
    return sink_wf
