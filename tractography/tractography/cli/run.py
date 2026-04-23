import os
import time
from tractography.workflows import init_tracto_wf

from nipype import config as nipype_config

from tractography.cli.arg_parser import get_parser


def _find_existing_outputs(config):
    """Search output_dir for pre-existing FOD and tractography files for the subject.

    Returns a dict with keys 'wm_fod', 'gm_fod', 'csf_fod', 'tractography'
    (each a path string) for outputs that already exist and can be reused.
    """
    from pathlib import Path

    output_dir = Path(config.output_dir)
    subject = config.participant_label[0]
    sub_dir = output_dir / f"sub-{subject}"

    if not sub_dir.exists():
        return {}

    def _find_file(pattern):
        matches = sorted(sub_dir.rglob(pattern))
        return str(matches[0]) if matches else None

    n = getattr(config, "n_streamlines", None) or 10_000_000
    if n >= 1_000_000 and n % 1_000_000 == 0:
        n_label = f"{n // 1_000_000}M"
    elif n >= 1_000 and n % 1_000 == 0:
        n_label = f"{n // 1_000}K"
    else:
        n_label = str(n)

    existing = {}

    wm_fod = _find_file("*_wm_fod.mif")
    gm_fod = _find_file("*_gm_fod.mif")
    csf_fod = _find_file("*_csf_fod.mif")
    if wm_fod and gm_fod and csf_fod:
        existing["wm_fod"] = wm_fod
        existing["gm_fod"] = gm_fod
        existing["csf_fod"] = csf_fod
        print(f"Reusing existing FOD files — skipping FOD computation.")
        print(f"  WM:  {wm_fod}")
        print(f"  GM:  {gm_fod}")
        print(f"  CSF: {csf_fod}")

    tractography = _find_file(f"*_desc-iFOD2+ACT+{n_label}_tractography.tck")
    if tractography:
        existing["tractography"] = tractography
        print(f"Reusing existing tractography file — skipping streamline generation.")
        print(f"  {tractography}")

    return existing


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

    config._existing_outputs = _find_existing_outputs(config)

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
