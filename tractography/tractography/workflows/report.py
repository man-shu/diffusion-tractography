from nipype.interfaces.utility.wrappers import Function
from nipype import IdentityInterface, Node, Workflow, Merge
import os

TEMPLATE_ROOT = os.path.join(os.path.dirname(__file__), "report_template")
REPORT_TEMPLATE = os.path.join(TEMPLATE_ROOT, "report_template.html")


def read_tck_file(tck_file):
    """Read streamlines from MRTrix3 TCK file format.

    TCK format consists of a text header followed by binary track data.
    Tracks are separated by NaN triplets and file ends with Inf triplet.

    Parameters
    ----------
    tck_file : str
        Path to .tck file

    Returns
    -------
    streamlines_list : list of ndarray
        List of streamlines, each as an Nx3 array of coordinates
    """
    import numpy as np
    import struct
    import os

    streamlines_list = []

    with open(tck_file, "rb") as f:
        # Read header
        header_lines = []
        offset = None
        datatype = "Float32LE"  # Default

        while True:
            line = f.readline().decode("utf-8").strip()
            header_lines.append(line)

            if line.startswith("file:"):
                # Extract file offset
                parts = line.split()
                offset = int(parts[-1])

            if line.startswith("datatype:"):
                datatype = line.split()[-1]

            if line == "END":
                break

        if offset is None:
            raise ValueError("No 'file:' offset found in TCK header")

        # Determine float format
        if "Float32" in datatype:
            fmt = "f"  # 32-bit float
            float_size = 4
        elif "Float64" in datatype:
            fmt = "d"  # 64-bit float
            float_size = 8
        else:
            raise ValueError(f"Unsupported datatype: {datatype}")

        # Determine byte order
        if "BE" in datatype:
            byte_order = ">"  # Big endian
        else:
            byte_order = "<"  # Little endian (default)

        # Move to binary data
        f.seek(offset)

        # Read binary track data
        current_streamline = []

        while True:
            # Read triplet of floats
            data = f.read(3 * float_size)
            if len(data) < 3 * float_size:
                break  # End of file

            # Unpack triplet
            fmt_str = byte_order + "3" + fmt
            triplet = struct.unpack(fmt_str, data)

            # Check for end of file marker (all Inf)
            if all(np.isinf(v) for v in triplet):
                if current_streamline:
                    streamlines_list.append(np.array(current_streamline))
                    current_streamline = []
                break

            # Check for track separator (all NaN)
            if all(np.isnan(v) for v in triplet):
                if current_streamline:
                    streamlines_list.append(np.array(current_streamline))
                    current_streamline = []
            else:
                current_streamline.append(triplet)

    return streamlines_list


def plot_streamlines_on_image(
    streamlines_file, background_file, title="Streamlines"
):
    """Plot streamlines as density map overlaid on anatomical image.

    Parameters
    ----------
    streamlines_file : str
        Path to .tck streamlines file
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
    from nilearn.plotting import plot_anat
    from nilearn.image import new_img_like
    import matplotlib.pyplot as plt
    import os

    # Read TCK file
    streamlines_list = read_tck_file(streamlines_file)

    # Load background image
    bg_img = nib.load(background_file)
    bg_data = bg_img.get_fdata()

    # Create streamline density map
    density = np.zeros(bg_img.shape[:3])

    if streamlines_list:
        # Get affine for coordinate transformation
        affine = bg_img.affine
        affine_inv = np.linalg.inv(affine)

        for streamline in streamlines_list:
            # Transform streamline to voxel coordinates
            voxel_coords = np.dot(
                affine_inv,
                np.column_stack([streamline, np.ones(len(streamline))]).T,
            )[:3].T
            voxel_coords = np.round(voxel_coords).astype(int)

            # Filter valid coordinates
            valid = np.all(
                (voxel_coords >= 0) & (voxel_coords < bg_img.shape[:3]), axis=1
            )
            voxel_coords = voxel_coords[valid]

            # Add to density
            for coord in voxel_coords:
                density[tuple(coord)] += 1

    # Normalize density
    if density.max() > 0:
        density = density / density.max()

    # Create density image
    density_img = new_img_like(bg_img, density)

    # Create plot
    display = plot_anat(bg_img, title=title, display_mode="ortho")
    display.add_contours(
        density_img, levels=[0.3, 0.6, 0.9], colors=["blue", "cyan", "yellow"]
    )

    # Save as SVG
    out_file = "streamlines_on_image.svg"
    display.savefig(out_file, format="svg")
    plt.close()

    return os.path.abspath(out_file)


# FOD and GMWM plotting functions have been removed as they require MIF format images.
# The report now focuses on streamline visualizations with T1 and DWI background images.


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
        plot_names = ["plot_streamlines_t1w", "plot_streamlines_dwi"]

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

    # ===== Tractography Plotting Nodes =====

    # Plot streamlines on T1
    PlotStreamlinesT1 = Function(
        input_names=["streamlines_file", "background_file", "title"],
        output_names=["out_file"],
        function=plot_streamlines_on_image,
    )
    plot_streamlines_t1 = Node(PlotStreamlinesT1, name="plot_streamlines_t1")
    plot_streamlines_t1.inputs.title = "Streamlines on T1w"

    # Plot streamlines on DWI
    PlotStreamlinesDWI = Function(
        input_names=["streamlines_file", "background_file", "title"],
        output_names=["out_file"],
        function=plot_streamlines_on_image,
    )
    plot_streamlines_dwi = Node(
        PlotStreamlinesDWI, name="plot_streamlines_dwi"
    )
    plot_streamlines_dwi.inputs.title = "Streamlines on DWI"

    # Create a Merge node to combine streamline plots
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
            # ===== Streamline Plotting Connections =====
            # Plot streamlines on T1
            (
                inputnode,
                plot_streamlines_t1,
                [
                    ("streamlines", "streamlines_file"),
                    ("t1w", "background_file"),
                ],
            ),
            # Plot streamlines on DWI
            (
                inputnode,
                plot_streamlines_dwi,
                [
                    ("streamlines", "streamlines_file"),
                    ("dwi", "background_file"),
                ],
            ),
            # Add streamline plots to merge node
            (plot_streamlines_t1, merge_node, [("out_file", "in1")]),
            (plot_streamlines_dwi, merge_node, [("out_file", "in2")]),
            # input the bids_entities
            (inputnode, create_html, [("bids_entities", "bids_entities")]),
            # create the html report
            (merge_node, create_html, [("out", "plots")]),
            # output the html report
            (create_html, outputnode, [("out_file", "out_file")]),
        ]
    )
    return workflow
