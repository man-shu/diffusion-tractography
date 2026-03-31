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


def plot_parcellation_on_t1w(parcellation_t1w, t1w_file, title="Parcellation on T1w"):
    """Plot a parcellation image overlaid on a T1w image using nilearn.

    Parameters
    ----------
    parcellation_t1w : str
        Path to the parcellation NIfTI registered to T1w space
    t1w_file : str
        Path to the T1w background image (NIfTI)
    title : str
        Title for the plot

    Returns
    -------
    out_file : str
        Path to output SVG file
    """
    from nilearn.plotting import plot_roi
    import matplotlib.pyplot as plt
    import os

    display = plot_roi(
        roi_img=parcellation_t1w,
        bg_img=t1w_file,
        title=title,
        display_mode="mosaic",
        colorbar=True,
    )

    out_file = "parcellation_on_t1w.svg"
    display.savefig(out_file)
    plt.close()

    return os.path.abspath(out_file)


def _make_connectome_html_with_surfaces(connectome_info, pial_left, pial_right):
    """Like nilearn's _make_connectome_html but uses subject-specific pial surfaces.

    Parameters
    ----------
    connectome_info : dict
        Output of nilearn's _get_connectome.
    pial_left, pial_right : str
        Paths to the left/right pial GIfTI files in T1w space.

    Returns
    -------
    ConnectomeView
    """
    import json
    from nilearn import datasets
    from nilearn.plotting.html_connectome import ConnectomeView
    from nilearn.plotting.js_plotting_utils import (
        add_js_lib,
        get_html_template,
        mesh_to_plotly,
    )

    plot_info = {"connectome": connectome_info}

    # Use subject surfaces where available, fall back to fsaverage otherwise
    fsaverage = None
    for key, surf_path in [("pial_left", pial_left), ("pial_right", pial_right)]:
        if surf_path is not None:
            plot_info[key] = mesh_to_plotly(surf_path)
        else:
            if fsaverage is None:
                fsaverage = datasets.fetch_surf_fsaverage()
            plot_info[key] = mesh_to_plotly(fsaverage[key])

    as_json = json.dumps(plot_info)
    as_html = get_html_template("connectome_plot_template.html").safe_substitute(
        {
            "INSERT_CONNECTOME_JSON_HERE": as_json,
            "INSERT_PAGE_TITLE_HERE": (
                connectome_info.get("title") or "Connectome plot"
            ),
        }
    )
    as_html = add_js_lib(as_html, embed_js=True)
    return ConnectomeView(as_html)


def plot_connectome_interactive(connectome_file, parcellation_t1w, surfaces_t1=None):
    """Generate an interactive 3D connectome visualization on the subject's
    pial surface.

    Uses nilearn's ``_get_connectome`` to prepare node/edge data and a
    custom ``_make_connectome_html_with_surfaces`` that substitutes the
    fsaverage mesh with the subject-specific pial GIfTI files from sMRIprep.
    Falls back to fsaverage for any missing hemisphere.

    Parameters
    ----------
    connectome_file : str
        Path to the connectome CSV produced by tck2connectome.
    parcellation_t1w : str
        Path to the parcellation NIfTI in T1w space.
    surfaces_t1 : list of str or None
        Paths to the left and right pial surface GIfTI files in T1w/fsnative
        space from sMRIprep derivatives.

    Returns
    -------
    html_str : str
        An ``<iframe>`` HTML string ready for embedding in a report.
    """
    import numpy as np
    import nibabel as nib
    from scipy import ndimage
    from nilearn.plotting.html_connectome import _get_connectome

    matrix = np.loadtxt(connectome_file, delimiter=",")
    matrix = matrix + matrix.T - np.diag(np.diag(matrix))

    parc_img = nib.load(parcellation_t1w)
    parc_data = parc_img.get_fdata()
    affine = parc_img.affine

    labels = np.unique(parc_data)
    labels = sorted(labels[labels > 0].astype(int))

    node_coords = []
    for label in labels:
        voxel_coords = ndimage.center_of_mass(parc_data == label)
        world_coords = nib.affines.apply_affine(affine, voxel_coords)
        node_coords.append(world_coords)

    node_coords = np.array(node_coords)

    connectome_info = _get_connectome(
        matrix,
        node_coords,
        threshold="80%",
    )
    connectome_info["line_width"] = 6.0
    connectome_info["colorbar"] = True
    connectome_info["cbar_height"] = 0.5
    connectome_info["cbar_fontsize"] = 25
    connectome_info["title"] = "Structural Connectome"
    connectome_info["title_fontsize"] = 25

    # Identify left/right surfaces from filenames
    pial_left, pial_right = None, None
    if surfaces_t1 is not None:
        surf_files = surfaces_t1 if isinstance(surfaces_t1, list) else [surfaces_t1]
        for f in surf_files:
            if "hemi-L" in f:
                pial_left = f
            elif "hemi-R" in f:
                pial_right = f

    view = _make_connectome_html_with_surfaces(connectome_info, pial_left, pial_right)
    return view.get_iframe()


def plot_connectome_heatmap(connectome_file, title="Structural Connectome", labels_file=None):
    """Plot the lower-triangular connectome matrix as a seaborn heatmap.

    Parameters
    ----------
    connectome_file : str
        Path to the connectome CSV produced by tck2connectome
    title : str
        Title for the plot
    labels_file : str or None
        Path to a region labels file (e.g. Schaefer LUT .txt).
        Expected format: tab-separated with index in column 0 and
        region name in column 1. When provided, region names are used
        as tick labels on the heatmap axes.

    Returns
    -------
    out_file : str
        Path to output SVG file
    """
    import numpy as np
    import matplotlib.pyplot as plt
    import seaborn as sns
    import os

    matrix = np.loadtxt(connectome_file, delimiter=",")

    # tck2connectome outputs an upper-triangular matrix; reflect it to lower
    # by symmetrising (avoid doubling the diagonal values)
    matrix = matrix + matrix.T - np.diag(np.diag(matrix))

    # Log-scale for better dynamic range visualisation (zeros stay zero)
    matrix_log = np.log1p(matrix)

    # Parse region labels when a labels file is provided
    labels = None
    if labels_file is not None:
        labels = []
        with open(labels_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                # LUT format: index name [R G B alpha]
                labels.append(parts[1] if len(parts) >= 2 else parts[0])

    # Mask the strictly upper triangle so only the lower triangle + diagonal
    # are filled, matching the style of a standard connectome visualisation
    mask = np.zeros_like(matrix_log, dtype=bool)
    mask[np.triu_indices_from(mask, k=1)] = True

    n = matrix_log.shape[0]
    # Scale figure size with number of regions to avoid label crowding
    fig_size = max(11, n * 0.18)
    fontsize = max(6, min(10, 120 // n))

    fig, ax = plt.subplots(figsize=(fig_size, fig_size * 0.9))

    sns.heatmap(
        matrix_log,
        mask=mask,
        cmap="viridis",
        square=True,
        linewidths=0,
        cbar_kws={"shrink": 0.5, "label": "log(1 + streamline count)"},
        ax=ax,
        xticklabels=labels if labels is not None else False,
        yticklabels=labels if labels is not None else False,
    )

    if labels is not None:
        ax.set_xticklabels(
            ax.get_xticklabels(), rotation=40, ha="right", fontsize=fontsize
        )
        ax.set_yticklabels(
            ax.get_yticklabels(), rotation=0, fontsize=fontsize
        )

    ax.set_title(title, fontsize=fontsize + 2)

    out_file = "connectome_heatmap.svg"
    fig.savefig(out_file, format="svg", bbox_inches="tight")
    plt.close(fig)

    return os.path.abspath(out_file)


def create_html_report(
    calling_wf_name,
    report_wf_name,
    template_path,
    output_dir,
    bids_entities,
    plots,
    n_streamlines=10000000,
    plot_connectome_interactive=None,
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
        _not_available = (
            "<p style='color:#999;font-style:italic;'>"
            "Not available &mdash; no parcellation provided.</p>"
        )
        to_embed = {
            "subject_id": subject_id,
            "plot_connectome": _not_available,
            "plot_parc_t1w": _not_available,
            "n_streamlines": f"{n_streamlines:,}",
            "plot_connectome_interactive": plot_connectome_interactive or _not_available,
        }
        plot_names = ["plot_tdi_t1w", "plot_connectome", "plot_parc_t1w"]

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


def init_report_wf(calling_wf_name, output_dir, name="report", has_connectome=False, n_streamlines=10000000):
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
                *(["connectome", "labels_file", "parcellation_t1w", "surfaces_t1"] if has_connectome else []),
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

    # ===== Tractography Plotting Nodes =====

    # Plot TDI on T1w
    PlotTDIT1W = Function(
        input_names=["tdi_file", "background_file", "title"],
        output_names=["out_file"],
        function=plot_tdi_on_image,
    )
    plot_tdi_t1w = Node(PlotTDIT1W, name="plot_tdi_t1w")
    plot_tdi_t1w.inputs.title = "Track Density on T1w"

    if has_connectome:
        # Plot connectome as a heatmap
        PlotConnectome = Function(
            input_names=["connectome_file", "title", "labels_file"],
            output_names=["out_file"],
            function=plot_connectome_heatmap,
        )
        plot_connectome = Node(PlotConnectome, name="plot_connectome")
        plot_connectome.inputs.title = "Structural Connectome"

        # Interactive 3D connectome visualisation on subject pial surface
        PlotConnectomeInteractive = Function(
            input_names=["connectome_file", "parcellation_t1w", "surfaces_t1"],
            output_names=["html_str"],
            function=plot_connectome_interactive,
        )
        plot_connectome_interactive_node = Node(
            PlotConnectomeInteractive, name="plot_connectome_interactive"
        )

        # Plot parcellation overlaid on T1w for registration QC
        PlotParcT1W = Function(
            input_names=["parcellation_t1w", "t1w_file", "title"],
            output_names=["out_file"],
            function=plot_parcellation_on_t1w,
        )
        plot_parc_t1w = Node(PlotParcT1W, name="plot_parc_t1w")
        plot_parc_t1w.inputs.title = "Parcellation Registration QC"

    # Create a Merge node to collect all plots
    merge_node = Node(Merge(3 if has_connectome else 1), name="merge_node")

    # embed plots in a html template
    CreateHTML = Function(
        input_names=[
            "calling_wf_name",
            "report_wf_name",
            "template_path",
            "output_dir",
            "bids_entities",
            "plots",
            "n_streamlines",
            "plot_connectome_interactive",
        ],
        output_names=["out_file"],
        function=create_html_report,
    )
    create_html = Node(CreateHTML, name="create_html")
    create_html.inputs.calling_wf_name = calling_wf_name
    create_html.inputs.report_wf_name = name
    create_html.inputs.template_path = REPORT_TEMPLATE
    create_html.inputs.output_dir = output_dir
    create_html.inputs.n_streamlines = n_streamlines

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
            # Add TDI plot to merge node
            (plot_tdi_t1w, merge_node, [("out_file", "in1")]),
        ]
    )

    if has_connectome:
        workflow.connect(
            [
                (
                    inputnode,
                    plot_connectome,
                    [
                        ("connectome", "connectome_file"),
                        ("labels_file", "labels_file"),
                    ],
                ),
                (plot_connectome, merge_node, [("out_file", "in2")]),
                (
                    inputnode,
                    plot_connectome_interactive_node,
                    [
                        ("connectome", "connectome_file"),
                        ("parcellation_t1w", "parcellation_t1w"),
                        ("surfaces_t1", "surfaces_t1"),
                    ],
                ),
                (
                    plot_connectome_interactive_node,
                    create_html,
                    [("html_str", "plot_connectome_interactive")],
                ),
                (
                    inputnode,
                    plot_parc_t1w,
                    [
                        ("parcellation_t1w", "parcellation_t1w"),
                        ("t1w", "t1w_file"),
                    ],
                ),
                (plot_parc_t1w, merge_node, [("out_file", "in3")]),
            ]
        )

    workflow.connect(
        [
            # input the bids_entities
            (inputnode, create_html, [("bids_entities", "bids_entities")]),
            # create the html report
            (merge_node, create_html, [("out", "plots")]),
            # output the html report
            (create_html, outputnode, [("out_file", "out_file")]),
        ]
    )
    return workflow
