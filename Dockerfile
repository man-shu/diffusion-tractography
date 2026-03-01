# Use Ubuntu 22.04 as the base image
FROM ubuntu:22.04

ARG USER_NAME=diffusion_pipelines

# Set environment variables to prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Update and install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    git \
    build-essential \
    ca-certificates \
    libglib2.0-0 \
    libxext6 \
    libsm6 \
    libxrender1 \
    bc \
    python3 \
    python3-pip \
    unzip \
    libgomp1 \
    cmake \
    graphviz \
    tcsh \
    gnupg \
    lsb-release \
    netbase \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set HOME explicitly
ENV INSTALL_DIR="/opt"

# Create directories and set permissions
RUN mkdir -p $INSTALL_DIR/ANTS \
    $INSTALL_DIR/miniconda3 \
    $INSTALL_DIR/fsl \
    $INSTALL_DIR/niflow \
    $INSTALL_DIR/Convert3D

# Install conda
RUN cd $INSTALL_DIR/miniconda3 && \
    wget https://repo.anaconda.com/miniconda/Miniconda3-py313_25.5.1-0-Linux-x86_64.sh -O $INSTALL_DIR/miniconda3/miniconda.sh && \
    bash $INSTALL_DIR/miniconda3/miniconda.sh -b -u -p $INSTALL_DIR/miniconda3 && \
    rm $INSTALL_DIR/miniconda3/miniconda.sh

# Set CPATH for packages relying on compiled libs (e.g. indexed_gzip)
ENV PATH="$INSTALL_DIR/miniconda3/bin:$PATH" \
    LANG="C.UTF-8" \
    LC_ALL="C.UTF-8" \
    PYTHONNOUSERSITE=1

# remove channels that need TOS agreement
RUN conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main && \
    conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r


# Install selected FSL conda packages
COPY docker/files/fsl_deps.txt $INSTALL_DIR/fsl/fsl_deps.txt
RUN conda install --yes --file $INSTALL_DIR/fsl/fsl_deps.txt -c https://fsl.fmrib.ox.ac.uk/fsldownloads/fslconda/public/ -c conda-forge

# Set up environment variables for FSL
ENV LANG="C.UTF-8" \
    LC_ALL="C.UTF-8" \
    PYTHONNOUSERSITE=1 \
    FSLDIR="$INSTALL_DIR/miniconda3" \
    FSLOUTPUTTYPE="NIFTI_GZ" \
    FSLMULTIFILEQUIT="TRUE" \
    FSLLOCKDIR="" \
    FSLMACHINELIST="" \
    FSLREMOTECALL="" \
    FSLGECUDAQ="cuda.q"

# Install niflow
RUN cd $INSTALL_DIR/niflow && \
    git clone https://github.com/niflows/nipype1-workflows.git && \
    cd nipype1-workflows/package && \
    pip install .

# Download and install Convert3D
RUN cd $INSTALL_DIR/Convert3D && \
    wget https://sourceforge.net/projects/c3d/files/c3d/1.0.0/c3d-1.0.0-Linux-x86_64.tar.gz && \
    tar -xzf c3d-1.0.0-Linux-x86_64.tar.gz && \
    rm c3d-1.0.0-Linux-x86_64.tar.gz
ENV PATH="$INSTALL_DIR/Convert3D/c3d-1.0.0-Linux-x86_64/bin:$PATH"

# Install workbench
RUN conda install --yes conda-forge::connectome-workbench-cli=2.0

# Install ANTS
RUN cd $INSTALL_DIR/ANTS && \
    wget https://github.com/ANTsX/ANTs/releases/download/v2.4.4/ants-2.4.4-ubuntu-22.04-X64-gcc.zip && \
    unzip ants-2.4.4-ubuntu-22.04-X64-gcc.zip && \
    rm ants-2.4.4-ubuntu-22.04-X64-gcc.zip

# Set up environment variables for ANTs
ENV ANTSPATH="$INSTALL_DIR/ANTS/ants-2.4.4/bin"
ENV PATH="$ANTSPATH:$PATH"

# Install tractography
COPY tractography $INSTALL_DIR/tractography
RUN cd $INSTALL_DIR/tractography && \
    pip install -e . --use-pep517

RUN useradd -m -s /bin/bash -G users ${USER_NAME}

# Update HOME environment variable to use the proper user home
ENV HOME="/home/${USER_NAME}"

# Give full permissions to everything in the home directory
RUN chmod --recursive a+wrX ${HOME}

# Set entrypoint to tractography
ENTRYPOINT ["/opt/miniconda3/bin/tractography"]