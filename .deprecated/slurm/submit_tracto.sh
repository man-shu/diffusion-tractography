#!/bin/bash
#
#SBATCH --job-name=diffusion_pipelines
#SBATCH --output=log_slurm/jobid_%A_%a.out 
#SBATCH --error=log_slurm/jobid_%A_%a.err
#SBATCH --partition=normal,parietal
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=10
#SBATCH --time=48:00:00
#SBATCH --array=0-95

dirs=(/data/parietal/store3/work/haggarwa/diffusion/data/stanford-bids/sub-*)
echo ${dirs[${SLURM_ARRAY_TASK_ID}]:69}

srun singularity exec \
--env-file /data/parietal/store3/work/haggarwa/diffusion/diffusion-tractography/singularity_env.txt \
--bind /data/parietal/store3/work/haggarwa/diffusion/diffusion-tractography/data:/home/input \
/data/parietal/store3/work/haggarwa/diffusion/diffusion-tractography/diffusion-tractography_main_singularity.sif \
/opt/miniconda3/bin/tractography \
/home/input/stanford-bids \
/home/input/stanford-bids/derivatives \
--work-dir /home/input/cache \
--participant-label ${dirs[${SLURM_ARRAY_TASK_ID}]:69} \
--session-label ses-01 \
--roi-dir /home/input/rois-selected \
--bids-filter /home/input/bids_filter.json \
--debug
