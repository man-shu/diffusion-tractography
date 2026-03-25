from nipype.interfaces.utility.wrappers import Function
from nipype import IdentityInterface, Node, Workflow, Merge
import os

TEMPLATE_ROOT = os.path.join(os.path.dirname(__file__), "report_template")
REPORT_TEMPLATE = os.path.join(TEMPLATE_ROOT, "report_template.html")


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
    import tempfile
    import os

    try:
        # Try to import MRtrix3 module for loading .tck files
        import mrtrix3

        streamlines_list = mrtrix3.read_mrtrix(streamlines_file)[0]
    except:
        # Fallback: create empty streamlines for visualization
        print(f"Warning: Could not load streamlines from {streamlines_file}")
        streamlines_list = []

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


def plot_fod_peaks(wm_fod_file, background_file, title="WM FOD"):
    """Plot WM fiber orientation distributions as overlay.

    Parameters
    ----------
    wm_fod_file : str
        Path to WM FOD .mif file
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

    try:
        # Try to load FOD as MIF
        import mrtrix3

        fod_data, fod_affine = mrtrix3.read_mrtrix(wm_fod_file)[:2]
    except:
        # Fallback: try loading as NIfTI if converted
        try:
            fod_img = nib.load(wm_fod_file.replace(".mif", ".nii.gz"))
            fod_data = fod_img.get_fdata()
            fod_affine = fod_img.affine
        except:
            print(f"Warning: Could not load FOD from {wm_fod_file}")
            # Create dummy output
            out_file = "fod_peaks.svg"
            return os.path.abspath(out_file)

    # Load background
    bg_img = nib.load(background_file)

    # Extract magnitude from FOD (sum across spherical harmonics)
    if len(fod_data.shape) == 4:
        fod_mag = np.sqrt(np.sum(fod_data**2, axis=3))
    else:
        fod_mag = fod_data

    # Normalize
    fod_mag = fod_mag / fod_mag.max() if fod_mag.max() > 0 else fod_mag

    # Create image with FOD magnitude
    fod_img = new_img_like(bg_img, fod_mag)

    # Create plot
    display = plot_anat(bg_img, title=title, display_mode="ortho")
    display.add_contours(
        fod_img, levels=[0.3, 0.6, 0.9], colors=["red", "orange", "yellow"]
    )

    out_file = "fod_peaks.svg"
    display.savefig(out_file, format="svg")
    plt.close()

    return os.path.abspath(out_file)


def plot_gmwm_boundary(gmwm_file, background_file, title="GM/WM Boundary"):
    """Plot GM/WM boundary mask overlay.

    Parameters
    ----------
    gmwm_file : str
        Path to GM/WM boundary .mif file
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

    try:
        # Load GM/WM boundary
        import mrtrix3

        gmwm_data, gmwm_affine = mrtrix3.read_mrtrix(gmwm_file)[:2]
    except:
        try:
            gmwm_img = nib.load(gmwm_file.replace(".mif", ".nii.gz"))
            gmwm_data = gmwm_img.get_fdata()
        except:
            print(f"Warning: Could not load GM/WM boundary from {gmwm_file}")
            out_file = "gmwm_boundary.svg"
            return os.path.abspath(out_file)

    # Load background
    bg_img = nib.load(background_file)

    # Binarize
    gmwm_mask = (gmwm_data > 0).astype(float)

    # Create image
    gmwm_img = new_img_like(bg_img, gmwm_mask)

    # Create plot
    display = plot_anat(bg_img, title=title, display_mode="ortho")
    display.add_contours(
        gmwm_img, levels=[0.5], colors=["green"], linewidths=1.5
    )

    out_file = "gmwm_boundary.svg"
    display.savefig(out_file, format="svg")
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
    import base64

    def _embed_svg(to_embed, template_path=template_path):
        with open(template_path) as f:
            template_text = f.read()
        string_template = string.Template(template_text)
        string_text = string_template.safe_substitute(**to_embed)
        f.close()

        return string_text

    def _get_html_text(subject_id, *args):
        to_embed = {"subject_id": subject_id}
        recon_plots = {
            "T1w.svg": "plot_recon_surface_on_t1",
            "dseg.svg": "plot_recon_segmentations_on_t1",
        }
        for plot in args:
            if plot is not None:
                with open(plot, "r", encoding="utf-8") as f:
                    svg_text = f.read()
                f.close()
                # get the plot name from the path
                if "smriprep" in plot:
                    suffix = plot.split(os.path.sep)[-1].split("_")[-1]
                    plot_name = recon_plots[suffix]
                else:
                    plot_name = plot.split(os.path.sep)[-2]
                to_embed[plot_name] = svg_text
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
    name : str, optional, by default "report"
        Name of the workflow
    output_dir : str, optional, by default "."
        Base directory to store the reports. The workflow will create a
        subdirectory called 'report' in this directory to store the reports.

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
                "wm_fod",
                "gmwm_boundary",
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
    plot_streamlines_t1.inputs.title = "Streamlines on T1 (iFOD2+ACT)"

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

    # Plot WM FOD
    PlotFOD = Function(
        input_names=["wm_fod_file", "background_file", "title"],
        output_names=["out_file"],
        function=plot_fod_peaks,
    )
    plot_fod = Node(PlotFOD, name="plot_fod")
    plot_fod.inputs.title = "White Matter FOD (msmt-csd)"

    # Plot GM/WM boundary
    PlotGMWM = Function(
        input_names=["gmwm_file", "background_file", "title"],
        output_names=["out_file"],
        function=plot_gmwm_boundary,
    )
    plot_gmwm = Node(PlotGMWM, name="plot_gmwm")
    plot_gmwm.inputs.title = "GM/WM Boundary (Seed Region)"

    # Create a Merge node to combine tractography plots
    merge_node = Node(Merge(4), name="merge_node")

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
            # ===== Tractography Plotting Connections =====
            # Plot streamlines on T1
            (
                inputnode,
                plot_streamlines_t1,
                [
                    ("streamlines", "streamlines_file"),
                    ("wm_fod", "background_file"),
                ],
            ),
            # Plot streamlines on DWI
            (
                inputnode,
                plot_streamlines_dwi,
                [
                    ("streamlines", "streamlines_file"),
                    ("wm_fod", "background_file"),
                ],
            ),
            # Plot WM FOD
            (
                inputnode,
                plot_fod,
                [
                    ("wm_fod", "wm_fod_file"),
                    ("wm_fod", "background_file"),
                ],
            ),
            # Plot GM/WM boundary
            (
                inputnode,
                plot_gmwm,
                [
                    ("gmwm_boundary", "gmwm_file"),
                    ("wm_fod", "background_file"),
                ],
            ),
            # Add tractography plots to merge node
            (plot_streamlines_t1, merge_node, [("out_file", "in1")]),
            (plot_streamlines_dwi, merge_node, [("out_file", "in2")]),
            (plot_fod, merge_node, [("out_file", "in3")]),
            (plot_gmwm, merge_node, [("out_file", "in4")]),
            # input the bids_entities
            (inputnode, create_html, [("bids_entities", "bids_entities")]),
            # create the html report
            (merge_node, create_html, [("out", "plots")]),
            # output the html report
            (create_html, outputnode, [("out_file", "out_file")]),
        ]
    )
    return workflow
