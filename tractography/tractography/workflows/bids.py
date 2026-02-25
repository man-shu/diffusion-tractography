from bids.layout import BIDSLayout, parse_file_entities, Query
from bids.utils import listify
from nipype import Node, Workflow, IdentityInterface
from nipype.interfaces.utility import Function
from nipype.interfaces.io import SelectFiles
from niworkflows.interfaces.bids import BIDSDataGrabber
import os
from pathlib import Path
import json
import copy

DEFAULT_BIDS_QUERIES = {
    "preprocessed_dwi": {
        "datatype": "dwi",
        "extension": [".nii", ".nii.gz"],
    },
    "bval": {
        "datatype": "dwi",
        "extension": [".bval"],
    },
    "preprocessed_t1_mask": {
        "datatype": "anat",
        "suffix": "mask",
        "desc": "brain",
        "space": None,
        "extension": [".nii", ".nii.gz"],
    },
    "rotated_bvec": {
        "datatype": "dwi",
        "extension": [".bvec"],
    },
    "preprocessed_t1": {
        "datatype": "anat",
        "suffix": "T1w",
        "desc": "preproc",
        "space": None,
        "extension": [".nii", ".nii.gz"],
    },
    "space2t1w_xfm": {
        "datatype": "anat",
        "suffix": "xfm",
        "to": "T1w",
        "extension": [".h5"],
    },
    "surfaces_t1": {
        "datatype": "anat",
        "extension": [".surf.gii"],
    },
}


def collect_data(config, bids_validate=False, bids_filters=None):
    if isinstance(config.bids_dir, BIDSLayout):
        layout = config.bids_dir
    else:
        print(
            f"Initializing BIDSLayout with root: {config.bids_dir}",
            type(config.bids_dir),
            type(str(config.bids_dir)),
        )
        layout = BIDSLayout(
            root=str(config.bids_dir),
            validate=bids_validate,
            derivatives=str(config.output_dir),
        )

    queries = copy.deepcopy(DEFAULT_BIDS_QUERIES)

    session_id = config.session_label or Query.OPTIONAL
    layout_get_kwargs = {
        "return_type": "file",
        "subject": config.participant_label,
        "session": session_id,
    }

    reserved_entities = [
        ("subject", config.participant_label),
        ("session", session_id),
    ]

    bids_filters = bids_filters or {}
    for acq, entities in bids_filters.items():
        # BIDS filters will not be able to override subject / session entities
        for entity, param in reserved_entities:
            if param == Query.OPTIONAL:
                continue
            if entity in entities and listify(param) != listify(
                entities[entity]
            ):
                raise ValueError(
                    f'Conflicting entities for "{entity}" found:'
                    f" {entities[entity]} // {param}"
                )

        queries[acq].update(entities)

    subj_data = {
        dtype: sorted(
            layout.get(
                **layout_get_kwargs,
                **query,
                invalid_filters="allow",
            )
        )
        for dtype, query in queries.items()
    }
    # Filter out unwanted files
    # DWI: specified derivatives via bids_filters, and the source bval
    # ideally the dwi should be the preprocessed one, which can be filtered
    # via with the proper desc in the bids_filters
    # the bvec file should be the one with rotated gradients, in case the dwi
    # was transformed. This could also be filtered via the proper desc in the
    # bids_filters
    # T1w, brain_mask, ribbon mask, fsnative2t1w_xfm: only derivatives
    for dtype, files in subj_data.items():
        selected = []
        for f in files:
            if dtype == "bval" and "derivative" not in f:
                selected.append(f)
            elif "derivative" in f:
                selected.append(f)
            else:
                continue
        if len(selected) == 1:
            subj_data[dtype] = selected[0]
        elif dtype == "surfaces_t1" and len(selected) == 2:
            subj_data[dtype] = selected
        else:
            raise RuntimeError(
                f"Found none or multiple {dtype} files for participant "
                f"{config.participant_label}: {selected}"
            )

    return subj_data, layout


def init_bidsdata_wf(config, name="bidsdata_wf"):

    bids_filters = (
        json.loads(config.bids_filter_file.read_text())
        if config.bids_filter_file
        else None
    )

    subject_data, layout = collect_data(
        config=config, bids_filters=bids_filters
    )
    bids_datasource = Node(
        IdentityInterface(fields=list(subject_data.keys())),
        name="bids_datasource",
    )
    bids_datasource.inputs.trait_set(**subject_data)

    ### Node to decode entities
    def decode_entities(file_name):
        from bids.layout import parse_file_entities

        print(f"Decoding entities from {file_name}")
        return parse_file_entities(file_name)

    DecodeEntities = Function(
        input_names=["file_name"],
        output_names=["bids_entities"],
        function=decode_entities,
    )

    decode_entities = Node(DecodeEntities, name="decode_entities")

    output = Node(
        IdentityInterface(
            fields=[
                "preprocessed_t1",
                "MNI2t1w_xfm",
                "preprocessed_dwi",
                "bval",
                "rotated_bvec",
            ]
        ),
        name="output",
    )

    bidsdata_wf = Workflow(name=name)
    bidsdata_wf.connect(
        [
            (
                bids_datasource,
                decode_entities,
                [("preprocessed_dwi", "file_name")],
            ),
            (
                bids_datasource,
                output,
                [("preprocessed_dwi", "preprocessed_dwi")],
            ),
            (bids_datasource, output, [("bval", "bval")]),
            (
                bids_datasource,
                output,
                [("preprocessed_t1_mask", "preprocessed_t1_mask")],
            ),
            (bids_datasource, output, [("rotated_bvec", "rotated_bvec")]),
            (
                bids_datasource,
                output,
                [("preprocessed_t1", "preprocessed_t1")],
            ),
            (
                bids_datasource,
                output,
                [("MNI2t1w_xfm", "MNI2t1w_xfm")],
            ),
        ]
    )

    return bidsdata_wf
