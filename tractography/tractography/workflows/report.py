from niworkflows.interfaces.reportlets.masks import SimpleShowMaskRPT
from niworkflows.interfaces.reportlets.registration import (
    SimpleBeforeAfterRPT as SimpleBeforeAfter,
)
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
    from nilearn.plotting.js_plotting_utils import get_colorbar
    from nilearn.plotting import plot_anat
    from nilearn.image import new_img_like
    import matplotlib.pyplot as plt
    from matplotlib import cm
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
                "dwi_initial",
                "dwi_masked",
                "bval",
                "eddy_corrected",
                "mask",
                "bet_mask",
                "dwi_rigid_registered",
                "t1_initial",
                "t1_masked",
                "bids_entities",
                "plot_recon_surface_on_t1",
                "plot_recon_segmentations_on_t1",
                "initial_mean_bzero",
                "eddy_mean_bzero",
                "registered_mean_bzero",
                "ribbon_mask",
                "mppca_denoised",
                "gibbs_unringed_denoised",
                # Tractography outputs
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
    # MPPCA
    plot_before_after_mppca = Node(
        SimpleBeforeAfter(), name="plot_before_after_mppca"
    )
    plot_before_after_mppca.inputs.before_label = "Before MP-PCA (Initial DWI)"
    plot_before_after_mppca.inputs.after_label = "After MP-PCA"

    # Gibbs Unringing
    plot_before_after_gibbs = Node(
        SimpleBeforeAfter(), name="plot_before_after_gibbs"
    )
    plot_before_after_gibbs.inputs.before_label = (
        "Before Gibbs Unringing (MP-PCA Denoised)"
    )
    plot_before_after_gibbs.inputs.after_label = "After Gibbs Unringing"

    # this node plots the before and after images of the eddy correction
    plot_before_after_eddy = Node(
        SimpleBeforeAfter(), name="plot_before_after_eddy"
    )
    # set labels for the before and after images
    plot_before_after_eddy.inputs.before_label = (
        "Before Eddy Correction (Gibbs Unringed + MP-PCA Denoised)"
    )
    plot_before_after_eddy.inputs.after_label = "Eddy Corrected DWI"
    # this node plots before and after images of masking T1 template
    plot_before_after_mask_t1 = Node(
        SimpleBeforeAfter(), name="plot_before_after_mask_t1"
    )
    # set labels for the before and after images
    plot_before_after_mask_t1.inputs.before_label = "Subject T1"
    plot_before_after_mask_t1.inputs.after_label = "Masked Subject T1"
    # this node plots the masked subject T1 as before and the dwi registered
    # to it as after
    plot_before_after_t1_dwi = Node(
        SimpleBeforeAfter(), name="plot_before_after_t1_dwi"
    )
    # set labels for the before and after images
    plot_before_after_t1_dwi.inputs.before_label = "Masked Subject T1"
    plot_before_after_t1_dwi.inputs.after_label = "Registered DWI"
    # this node plots the extracted brain mask as outline on the initial dwi
    # image
    plot_bet = Node(SimpleShowMaskRPT(), name="plot_bet")
    # this node plots the transformed mask as an outline on transformed dwi
    # image
    plot_transformed = Node(SimpleShowMaskRPT(), name="plot_transformed")

    def ribbon_on_dwi(dwi_file, ribbon_mask):
        import nibabel as nib
        from niworkflows.viz.utils import (
            compose_view,
            cuts_from_bbox,
            plot_registration,
        )

        dwi_img = nib.load(dwi_file)
        ribbon_img = nib.load(ribbon_mask)
        svg = plot_registration(
            dwi_img,
            "Ribbon mask on DWI",
            estimate_brightness=True,
            cuts=cuts_from_bbox(ribbon_img, cuts=7),
            contour=ribbon_img,
        )
        out_file = compose_view(svg, [], out_file="ribbon_on_dwi.svg")

        return out_file

    RibbonOnDWI = Function(
        input_names=["dwi_file", "ribbon_mask"],
        output_names=["out_file"],
        function=ribbon_on_dwi,
    )
    plot_ribbon_on_dwi = Node(RibbonOnDWI, name="plot_ribbon_on_dwi")

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

    # Create a Merge node to combine the outputs of plot_bet,
    # plot_before_after_eddy, and plot_transformed
    merge_node = Node(Merge(14), name="merge_node")

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
            # plot the extracted brain mask as outline on the initial dwi image
            (
                inputnode,
                plot_bet,
                [
                    ("bet_mask", "mask_file"),
                    ("dwi_initial", "background_file"),
                ],
            ),
            (
                inputnode,
                plot_before_after_mppca,
                [("initial_mean_bzero", "before")],
            ),
            (
                inputnode,
                plot_before_after_mppca,
                [("mppca_denoised", "after")],
            ),
            (
                inputnode,
                plot_before_after_gibbs,
                [("mppca_denoised", "before")],
            ),
            (
                inputnode,
                plot_before_after_gibbs,
                [("gibbs_unringed_denoised", "after")],
            ),
            # plot the initial dwi as before
            (
                inputnode,
                plot_before_after_eddy,
                [("gibbs_unringed_denoised", "before")],
            ),
            # plot the eddy corrected dwi as after
            (
                inputnode,
                plot_before_after_eddy,
                [("eddy_mean_bzero", "after")],
            ),
            # plot the initial subject T1 as before
            (inputnode, plot_before_after_mask_t1, [("t1_initial", "before")]),
            # plot the masked subject T1 as after
            (inputnode, plot_before_after_mask_t1, [("t1_masked", "after")]),
            # plot the masked subject T1 as before and transformed dwi as
            # after
            (inputnode, plot_before_after_t1_dwi, [("t1_masked", "before")]),
            (
                inputnode,
                plot_before_after_t1_dwi,
                [("registered_mean_bzero", "after")],
            ),
            # plot the transformed mask as an outline on transformed dwi image
            (
                inputnode,
                plot_transformed,
                [
                    ("dwi_rigid_registered", "background_file"),
                    ("mask", "mask_file"),
                ],
            ),
            (
                inputnode,
                plot_ribbon_on_dwi,
                [
                    ("registered_mean_bzero", "dwi_file"),
                    ("ribbon_mask", "ribbon_mask"),
                ],
            ),
            # ===== Tractography Plotting Connections =====
            # Plot streamlines on T1
            (
                inputnode,
                plot_streamlines_t1,
                [
                    ("streamlines", "streamlines_file"),
                    ("t1_masked", "background_file"),
                ],
            ),
            # Plot streamlines on DWI
            (
                inputnode,
                plot_streamlines_dwi,
                [
                    ("streamlines", "streamlines_file"),
                    ("registered_mean_bzero", "background_file"),
                ],
            ),
            # Plot WM FOD
            (
                inputnode,
                plot_fod,
                [
                    ("wm_fod", "wm_fod_file"),
                    ("t1_masked", "background_file"),
                ],
            ),
            # Plot GM/WM boundary
            (
                inputnode,
                plot_gmwm,
                [
                    ("gmwm_boundary", "gmwm_file"),
                    ("t1_masked", "background_file"),
                ],
            ),
            # merge the outputs of plot_bet, plot_before_after_eddy,
            # plot_before_after_mask_t1, plot_transformed
            (plot_bet, merge_node, [("out_report", "in1")]),
            (plot_before_after_eddy, merge_node, [("out_report", "in2")]),
            (plot_before_after_mask_t1, merge_node, [("out_report", "in3")]),
            (plot_before_after_t1_dwi, merge_node, [("out_report", "in4")]),
            (plot_transformed, merge_node, [("out_report", "in5")]),
            (
                inputnode,
                merge_node,
                [("plot_recon_surface_on_t1", "in6")],
            ),
            (
                inputnode,
                merge_node,
                [("plot_recon_segmentations_on_t1", "in7")],
            ),
            (plot_ribbon_on_dwi, merge_node, [("out_file", "in8")]),
            (plot_before_after_mppca, merge_node, [("out_report", "in9")]),
            (plot_before_after_gibbs, merge_node, [("out_report", "in10")]),
            # Add tractography plots to merge node
            (plot_streamlines_t1, merge_node, [("out_file", "in11")]),
            (plot_streamlines_dwi, merge_node, [("out_file", "in12")]),
            (plot_fod, merge_node, [("out_file", "in13")]),
            (plot_gmwm, merge_node, [("out_file", "in14")]),
            # input the bids_entities
            (inputnode, create_html, [("bids_entities", "bids_entities")]),
            # create the html report
            (merge_node, create_html, [("out", "plots")]),
            # output the html report
            (create_html, outputnode, [("out_file", "out_file")]),
        ]
    )
    return workflow
