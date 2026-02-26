# How to run

## Using Docker

- Pull the docker image

  ```bash
  docker pull ghcr.io/man-shu/diffusion-tractography:main
  ```

- **Optionally**, you can also build the docker image

  - Clone this repository and navigate to the directory

    ```bash
    git clone git@github.com:man-shu/diffusion-tractography.git
    cd diffusion-tractography
    ```

  - If you're using a machine with x86_64 architecture (check with `uname -m`):

    ```bash
    docker image build --tag ghcr.io/man-shu/diffusion-tractography:main .
    ```

  - If you're using a machine with ARM architecture (for example, Apple M1):

    ```bash
    docker image build --platform linux/x86_64 --tag ghcr.io/man-shu/diffusion-tractography:main .
    ```

- Run the container

  - To run the full pipeline, with surface reconstruction (smriprep workflow) and diffusion tractography:

    ```bash
    docker container run --rm --interactive \
    --user "$(id -u):$(id -g)" \
    --mount type=bind,source=/data/parietal/store3/work/haggarwa/diffusion/diffusion-tractography/data,target=/home/input \
    ghcr.io/man-shu/diffusion-tractography:main /home/input/WAND-downsampled \
    /home/input/WAND-downsampled/derivatives \
    --work-dir /home/input/cache \
    --participant-label sub-00395 \
    --bids-filter-file /home/input/bids_filter.json \
    --roi-dir /home/input/rois-downsampled
    ```

  - If you're using a machine with ARM architecture (for example, Apple M1), you may need to specify the platform explicitly
    with the `--platform` flag:

    ```bash
    docker container run --rm --interactive \
    --platform linux/x86_64 \
    --user "$(id -u):$(id -g)" \
    --mount type=bind,source=/data/parietal/store3/work/haggarwa/diffusion/diffusion-tractography/data,target=/home/input \
    ghcr.io/man-shu/diffusion-tractography:main /home/input/WAND-downsampled \
    /home/input/WAND-downsampled/derivatives \
    --work-dir /home/input/cache \
    --participant-label sub-00395 \
    --bids-filter-file /home/input/bids_filter.json \
    --roi-dir /home/input/rois-downsampled
    ```

- In the command above, we are filtering certain files from the BIDS dataset, using the `--bids-filter-file` flag to specify a JSON file with the filtering criteria.
For example, to include only the preprocessed diffusion-weighted images (DWIs) with the acquisition label `CHARMED`, only pial surfaces from smriprep outputs and , create a file named `bids_filter.json` with the following content:

  ```json
  {
      "preprocessed_dwi": {
          "acquisition": "CHARMED",
          "desc": "mppcadenoised+gibbsunringed+eddycorrected+bbreg"
      },
      "bval": {
          "acquisition": "CHARMED"
      },
      "rotated_bvec": {
          "acquisition": "CHARMED",
          "desc": "rotated"
      },
      "surfaces_t1": {
          "suffix": "pial",
          "den": None
      },
      "space2t1w_xfm": {
          "from": "MNI152NLin6Asym"
      }
  }
  ```

- See here for details about `--bids-filter-file`: <https://fmriprep.org/en/25.1.4/faq.html#how-do-i-select-only-certain-files-to-be-input-to-fmriprep>

## Using Singularity

- Pull the singularity image

  ```bash
  singularity pull oras://ghcr.io/man-shu/diffusion-tractography:main_singularity
  ```

- Run the singularity image

  ```bash
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
  --roi-dir /home/input/rois
  ```

- Alternatively, you can run the singularity image in an interactive shell

  ```bash
  singularity shell --env-file singularity_env.txt \
  --bind ./data:/home/input diffusion-tractography_main_singularity.sif
  ```
