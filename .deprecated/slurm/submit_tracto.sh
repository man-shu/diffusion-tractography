#!/bin/bash
#
#SBATCH --job-name=tracto
#SBATCH --partition=gpu-best,parietal
#SBATCH --error error_%A_%a.out
#SBATCH --gres=gpu:1

module load singularity

singularity exec \
--env-file /data/parietal/store3/work/haggarwa/diffusion/diffusion-tractography/singularity_env.txt \
--bind /data/parietal/store3/work/haggarwa/diffusion/diffusion-tractography/data:/home/input \
/data/parietal/store3/work/haggarwa/diffusion/diffusion-tractography/diffusion-tractography_main_singularity.sif \
/opt/miniconda3/bin/tractography \
/home/input/WAND-downsampled \
/home/input/WAND-downsampled/derivatives \
--work-dir /home/input/cache \
--participant-label sub-00395 \
--bids-filter-file /home/input/bids_filter.json \
--roi-dir /home/input/rois-downsampled \
--debug
