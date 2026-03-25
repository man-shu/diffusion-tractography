from nipype.interfaces.utility.wrappers import Function
from nipype import IdentityInterface, Node, Workflow, Merge
from nipype.interfaces.mrtrix3.utils import ComputeTDI
import os

TEMPLATE_ROOT = os.path.join(os.path.dirname(__file__), "report_template")
REPORT_TEMPLATE = os.path.join(TEMPLATE_ROOT, "report_template.html")


def plot_tdi_on_image(tdi_file, background_file, title="Track Density"):
    """Plot track density image overlaid on anatomical image.

    Parameters
    ----------
    tdi_file : str
        Path to track density image (.mif or .nii.gz)
    background_file : str
        Path to background anatomical image (NIfTI)
    title : str
        Title for the plot

    Returns
    -------
    out_file : str
        Path to output SVG file
    """
    import nibabel as nib
    import numpy as np
    from nilearn.plotting import plot_stat_map
    from nilearn.image import new_img_like
    import matplotlib.pyplot as plt
    import os

    # Load TDI image
    tdi_img = nib.load(tdi_file)

    # Load background image
    bg_img = nib.load(background_file)

    # Create plot
    display = plot_stat_map(
        stat_map_img=tdi_img,
        bg_img=bg_img,
        title=title,
        display_mode="mosaic",
        colorbar=True,
    )

    # Save as SVG
    out_file = "tdi_on_image.svg"
    display.savefig(out_file)
    plt.close()

    return os.path.abspath(out_file)


def create_html_report(
    calling_wf_name,
    report_wf_name,
    template_path,
    output_dir,
    bids_entities,
    plots,
):
    import os
    import string
    from nilearn.plotting.html_document import HTMLDocument

    def _embed_svg(to_embed, template_path=template_path):
        with open(template_path) as f:
            template_text = f.read()
        string_template = string.Template(template_text)
        string_text = string_template.safe_substitute(**to_embed)
        f.close()

        return string_text

    def _get_html_text(subject_id, *args):
        to_embed = {"subject_id": subject_id}
        plot_names = ["plot_tdi_t1w", "plot_tdi_dwi"]

        for idx, plot in enumerate(args):
            if plot is not None and idx < len(plot_names):
                with open(plot, "r", encoding="utf-8") as f:
                    svg_text = f.read()
                f.close()
                to_embed[plot_names[idx]] = svg_text

        return _embed_svg(to_embed)

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

    html_text = _get_html_text(bids_entities["subject"], *plots)
    bids_name = _build_bids(bids_entities)
    out_file = os.path.join(
        output_dir,
        calling_wf_name,
        report_wf_name,
        f"{bids_name}_report.html",
    )
    report_html = HTMLDocument(html_text).save_as_html(out_file)
    print(f"Report for {calling_wf_name} created at {out_file}")
    return out_file


def init_report_wf(calling_wf_name, output_dir, name="report"):
    """Create a workflow to generate a report for the diffusion preprocessing
    pipeline.

    Parameters
    ----------
    calling_wf_name : str
        Name of the calling workflow
    output_dir : str
        Base directory to store the reports. The workflow will create a
        subdirectory called 'report' in this directory to store the reports.
    name : str, optional, by default "report"
        Name of the workflow

    Returns
    -------
    workflow : nipype Workflow
        A nipype Workflow to generate the report for the diffusion
        preprocessing pipeline.
    """
    inputnode = Node(
        IdentityInterface(
            fields=[
                "bids_entities",
                "streamlines",
                "t1w",
                "dwi",
            ]
        ),
        name="report_inputnode",
    )
    outputnode = Node(
        IdentityInterface(fields=["out_file"]),
        name="report_outputnode",
    )

    # ===== Track Density Image (TDI) Computation =====

    # Compute TDI with T1w as template
    tdi_t1w = Node(
        interface=ComputeTDI(),
        name="tdi_t1w",
    )
    tdi_t1w.inputs.out_file = "tdi_t1w.nii.gz"

    # Compute TDI with DWI as template
    tdi_dwi = Node(
        interface=ComputeTDI(),
        name="tdi_dwi",
    )
    tdi_dwi.inputs.out_file = "tdi_dwi.nii.gz"

    # ===== Tractography Plotting Nodes =====

    # Plot TDI on T1w
    PlotTDIT1W = Function(
        input_names=["tdi_file", "background_file", "title"],
        output_names=["out_file"],
        function=plot_tdi_on_image,
    )
    plot_tdi_t1w = Node(PlotTDIT1W, name="plot_tdi_t1w")
    plot_tdi_t1w.inputs.title = "Track Density on T1w"

    # Plot TDI on DWI
    PlotTDIDWI = Function(
        input_names=["tdi_file", "background_file", "title"],
        output_names=["out_file"],
        function=plot_tdi_on_image,
    )
    plot_tdi_dwi = Node(PlotTDIDWI, name="plot_tdi_dwi")
    plot_tdi_dwi.inputs.title = "Track Density on DWI"

    # Create a Merge node to combine TDI plots
    merge_node = Node(Merge(2), name="merge_node")

    # embed plots in a html template
    CreateHTML = Function(
        input_names=[
            "calling_wf_name",
            "report_wf_name",
            "template_path",
            "output_dir",
            "bids_entities",
            "plots",
        ],
        output_names=["out_file"],
        function=create_html_report,
    )
    create_html = Node(CreateHTML, name="create_html")
    create_html.inputs.calling_wf_name = calling_wf_name
    create_html.inputs.report_wf_name = name
    create_html.inputs.template_path = REPORT_TEMPLATE
    create_html.inputs.output_dir = output_dir

    workflow = Workflow(name=name, base_dir=output_dir)
    workflow.connect(
        [
            # ===== TDI Computation Connections =====
            # Compute TDI with T1w as reference template
            (
                inputnode,
                tdi_t1w,
                [
                    ("streamlines", "in_file"),
                    ("t1w", "reference"),
                ],
            ),
            # Compute TDI with DWI as reference template
            (
                inputnode,
                tdi_dwi,
                [
                    ("streamlines", "in_file"),
                    ("dwi", "reference"),
                ],
            ),
            # ===== TDI Plotting Connections =====
            # Plot TDI on T1w
            (
                tdi_t1w,
                plot_tdi_t1w,
                [
                    ("out_file", "tdi_file"),
                ],
            ),
            (
                inputnode,
                plot_tdi_t1w,
                [
                    ("t1w", "background_file"),
                ],
            ),
            # Plot TDI on DWI
            (
                tdi_dwi,
                plot_tdi_dwi,
                [
                    ("out_file", "tdi_file"),
                ],
            ),
            (
                inputnode,
                plot_tdi_dwi,
                [
                    ("dwi", "background_file"),
                ],
            ),
            # Add TDI plots to merge node
            (plot_tdi_t1w, merge_node, [("out_file", "in1")]),
            (plot_tdi_dwi, merge_node, [("out_file", "in2")]),
            # input the bids_entities
            (inputnode, create_html, [("bids_entities", "bids_entities")]),
            # create the html report
            (merge_node, create_html, [("out", "plots")]),
            # output the html report
            (create_html, outputnode, [("out_file", "out_file")]),
        ]
    )
    return workflow
