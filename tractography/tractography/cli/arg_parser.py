# mostly a copy of get_parser function in https://github.com/nipreps/smriprep/blob/master/src/smriprep/cli/run.py


def get_parser():
    """Build parser object."""
    from argparse import ArgumentParser, RawTextHelpFormatter
    from pathlib import Path

    from niworkflows.utils.spaces import (
        OutputReferencesAction,
        Reference,
        SpatialReferences,
    )

    import smriprep

    def _drop_ses(value):
        return value.removeprefix("ses-")

    def _drop_sub(value):
        return value.removeprefix("sub-")

    parser = ArgumentParser(
        description="tractography",
        formatter_class=RawTextHelpFormatter,
    )

    # Arguments as specified by BIDS-Apps
    # required, positional arguments
    # IMPORTANT: they must go directly with the parser object
    parser.add_argument(
        "bids_dir",
        action="store",
        type=Path,
        help="the root folder of a BIDS valid dataset (sub-XXXXX folders should "
        "be found at the top level in this folder).",
    )
    parser.add_argument(
        "output_dir",
        action="store",
        type=Path,
        help="the output path for the outcomes of preprocessing and visual reports",
    )

    # optional arguments
    g_bids = parser.add_argument_group("Options for filtering BIDS queries")
    g_bids.add_argument(
        "--participant-label",
        "--participant_label",
        action="store",
        nargs="+",
        type=_drop_sub,
        help="a space delimited list of participant identifiers or a single "
        "identifier (the sub- prefix can be removed)",
    )
    g_bids.add_argument(
        "--session-label",
        nargs="+",
        type=_drop_ses,
        help="A space delimited list of session identifiers or a single "
        "identifier (the ses- prefix can be removed)",
    )
    g_bids.add_argument(
        "-d",
        "--derivatives",
        action="store",
        metavar="PATH",
        type=Path,
        nargs="*",
        help="Search PATH(s) for pre-computed derivatives.",
    )
    g_bids.add_argument(
        "--bids-filter-file",
        action="store",
        type=Path,
        metavar="PATH",
        help="a JSON file describing custom BIDS input filters using pybids "
        "{<suffix>:{<entity>:<filter>,...},...} "
        "(https://github.com/bids-standard/pybids/blob/master/bids/layout/config/bids.json)",
    )

    g_other = parser.add_argument_group("Other options")
    g_other.add_argument(
        "--roi-dir",
        action="store",
        type=Path,
        help="path where ROI images are stored",
    )
    g_other.add_argument(
        "-w",
        "--work-dir",
        action="store",
        type=Path,
        default=Path("work"),
        help="path where intermediate results should be stored",
    )
    g_other.add_argument(
        "--run-uuid",
        action="store",
        default=None,
        help="Specify UUID of previous run, to include error logs in report. "
        "No effect without --reports-only.",
    )
    g_other.add_argument(
        "--write-graph",
        action="store_true",
        default=False,
        help="Write workflow graph.",
    )
    g_other.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Run in debug mode.",
    )

    return parser
