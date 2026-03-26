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
            config.work_dir, f"tractography_output_{config.run_uuid}"
        ),
        config=config,
    )
    wf.write_graph(
        graph2use="flat",
        dotfilename=os.path.join(
            config.work_dir,
            f"tractography_output_{config.run_uuid}",
            "graph.dot",
        ),
        format="svg",
    )

    # Run with MultiProc plugin using n_threads for parallelization
    n_procs = config.n_threads if hasattr(config, "n_threads") else 1
    if n_procs > 1:
        print(f"Running pipeline with {n_procs} thread(s).")
        wf.run(plugin="MultiProc", plugin_args={"n_procs": n_procs})
    else:
        print("Running pipeline with a single thread.")
        wf.run()


def main():
    """
    Main function to run the diffusion tractography pipeline.
    """
    config = get_parser().parse_args()
    _run_pipeline(config)
