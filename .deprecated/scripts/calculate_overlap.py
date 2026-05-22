import os
import nibabel as nib
import numpy as np
from nilearn.image import math_img


def calculate_roi_overlaps(roi_files):
    """Calculate pairwise ROI overlaps and return percentage overlaps."""
    # Load all ROI files
    roi_images = [nib.load(f) for f in roi_files]
    roi_data = [img.get_fdata() > 0 for img in roi_images]  # Binarize
    roi_names = [os.path.basename(f) for f in roi_files]

    overlaps = []

    # Calculate pairwise overlaps
    for i in range(len(roi_data)):
        for j in range(i + 1, len(roi_data)):
            # Calculate intersection volume
            intersection = np.sum(roi_data[i] & roi_data[j])

            if intersection == 0:
                continue

            # Calculate overlap percentages
            pct_i = (intersection / np.sum(roi_data[i])) * 100
            pct_j = (intersection / np.sum(roi_data[j])) * 100

            overlaps.append(
                (roi_names[i], roi_names[j], intersection, pct_i, pct_j)
            )

    return overlaps


# Example usage with your ROI files
roi_directory = (
    "/home/himanshu/Desktop/diffusion/diffusion-tractography/data/rois-fullres"
)
roi_files = [
    os.path.join(roi_directory, f)
    for f in os.listdir(roi_directory)
    if f.endswith(".nii.gz") or f.endswith(".nii")
]

overlaps = calculate_roi_overlaps(roi_files)

if overlaps:
    print("Overlapping ROI pairs:")
    for a, b, count, pct_a, pct_b in overlaps:
        print(
            f"{a} <-> {b}: {count} voxels ({pct_a:.1f}% of {a}, {pct_b:.1f}% of {b})"
        )
else:
    print("No significant ROI overlaps found (>30% coverage)")
