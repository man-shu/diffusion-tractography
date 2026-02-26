import os
import time
from tractography.workflows import init_tracto_wf

from nipype import config as nipype_config

from tractography.cli.arg_parser import get_parser


def _run_pipeline(config):
    """
    Run the pipeline based on the config file.
    """

    # Create a timestamp in YYYYMMDD_HHMMSS format
    timestamp = time.strftime("%Y%m%d-%H%M%S")

    if config.run_uuid is None:
        config.run_uuid = f"{timestamp}_{config.participant_label[0]}"

    if config.debug:
        nipype_config.enable_debug_mode()

    # create the pipeline
    wf = init_tracto_wf(
        output_dir=os.path.join(
            config.work_dir, f"{pipeline}_output_{config.run_uuid}"
        ),
        config=config,
    )
    wf.write_graph(
        graph2use="flat",
        dotfilename=os.path.join(
            config.work_dir,
            f"{pipeline}_output_{config.run_uuid}",
            "graph.dot",
        ),
        format="svg",
    )
    wf.run()


def main():
    """
    Main function to run the diffusion preprocessing pipeline.
    """
    config = get_parser().parse_args()
    _run_pipeline(config)
