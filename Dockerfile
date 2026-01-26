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
    $INSTALL_DIR/freesurfer \
    $INSTALL_DIR/miniconda3 \
    $INSTALL_DIR/fsl \
    $INSTALL_DIR/niflow \
    $INSTALL_DIR/Convert3D

# Install ANTS
RUN cd $INSTALL_DIR/ANTS && \
    wget https://github.com/ANTsX/ANTs/releases/download/v2.4.4/ants-2.4.4-ubuntu-22.04-X64-gcc.zip && \
    unzip ants-2.4.4-ubuntu-22.04-X64-gcc.zip && \
    rm ants-2.4.4-ubuntu-22.04-X64-gcc.zip

# Set up environment variables for ANTs
ENV ANTSPATH="$INSTALL_DIR/ANTS/ants-2.4.4/bin"
ENV PATH="$ANTSPATH:$PATH"

# Install FreeSurfer
COPY docker/files/freesurfer7.3.2-exclude.txt $INSTALL_DIR/freesurfer/freesurfer7.3.2-exclude.txt
RUN cd $INSTALL_DIR/freesurfer
RUN curl -sSL https://surfer.nmr.mgh.harvard.edu/pub/dist/freesurfer/7.3.2/freesurfer-linux-ubuntu22_amd64-7.3.2.tar.gz \
    | tar zxv --no-same-owner -C $INSTALL_DIR/freesurfer --exclude-from=$INSTALL_DIR/freesurfer/freesurfer7.3.2-exclude.txt
RUN rm $INSTALL_DIR/freesurfer/freesurfer7.3.2-exclude.txt

# Simulate SetUpFreeSurfer.sh
ENV OS="Linux" \
    FS_OVERRIDE=0 \
    FIX_VERTEX_AREA="" \
    FSF_OUTPUT_FORMAT="nii.gz" \
    FREESURFER_HOME="$INSTALL_DIR/freesurfer/freesurfer"
ENV SUBJECTS_DIR="$FREESURFER_HOME/subjects" \
    FUNCTIONALS_DIR="$FREESURFER_HOME/sessions" \
    MNI_DIR="$FREESURFER_HOME/mni" \
    LOCAL_DIR="$FREESURFER_HOME/local" \
    MINC_BIN_DIR="$FREESURFER_HOME/mni/bin" \
    MINC_LIB_DIR="$FREESURFER_HOME/mni/lib" \
    MNI_DATAPATH="$FREESURFER_HOME/mni/data"
ENV PERL5LIB="$MINC_LIB_DIR/perl5/5.8.5" \
    MNI_PERL5LIB="$MINC_LIB_DIR/perl5/5.8.5" \
    PATH="$FREESURFER_HOME/bin:$FREESURFER_HOME/tktools:$MINC_BIN_DIR:$PATH"

# Install conda
RUN cd $INSTALL_DIR/miniconda3 && \
    wget https://repo.anaconda.com/miniconda/Miniconda3-py310_25.5.1-0-Linux-x86_64.sh -O $INSTALL_DIR/miniconda3/miniconda.sh && \
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

# Install sdcflows
RUN pip install sdcflows

# Configure PPAs for libpng12 and libxp6
RUN GNUPGHOME=/tmp gpg --keyserver hkps://keyserver.ubuntu.com --no-default-keyring --keyring /usr/share/keyrings/linuxuprising.gpg --recv 0xEA8CACC073C3DB2A \
    && GNUPGHOME=/tmp gpg --keyserver hkps://keyserver.ubuntu.com --no-default-keyring --keyring /usr/share/keyrings/zeehio.gpg --recv 0xA1301338A3A48C4A \
    && echo "deb [signed-by=/usr/share/keyrings/linuxuprising.gpg] https://ppa.launchpadcontent.net/linuxuprising/libpng12/ubuntu jammy main" > /etc/apt/sources.list.d/linuxuprising.list \
    && echo "deb [signed-by=/usr/share/keyrings/zeehio.gpg] https://ppa.launchpadcontent.net/zeehio/libxp/ubuntu jammy main" > /etc/apt/sources.list.d/zeehio.list

# Dependencies for AFNI; requires a discontinued multiarch-support package from bionic (18.04)
RUN apt-get update -qq \
    && apt-get install -y -q --no-install-recommends \
    ed \
    gsl-bin \
    libglib2.0-0 \
    libglu1-mesa-dev \
    libglw1-mesa \
    libgomp1 \
    libjpeg62 \
    libpng12-0 \
    libxm4 \
    libxp6 \
    netpbm \
    tcsh \
    xfonts-base \
    xvfb \
    && curl -sSL --retry 5 -o /tmp/multiarch.deb http://archive.ubuntu.com/ubuntu/pool/main/g/glibc/multiarch-support_2.27-3ubuntu1.5_amd64.deb \
    && dpkg -i /tmp/multiarch.deb \
    && rm /tmp/multiarch.deb \
    && apt-get install -f \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && gsl2_path="$(find / -name 'libgsl.so.19' || printf '')" \
    && if [ -n "$gsl2_path" ]; then \
    ln -sfv "$gsl2_path" "$(dirname $gsl2_path)/libgsl.so.0"; \
    fi \
    && ldconfig

# AFNI
# Bump the date to current to update AFNI
RUN echo "2024.03.08"
RUN mkdir -p $INSTALL_DIR/afni-latest \
    && curl -fsSL --retry 5 https://afni.nimh.nih.gov/pub/dist/tgz/linux_openmp_64.tgz \
    | tar -xz -C $INSTALL_DIR/afni-latest --strip-components 1 \
    --exclude "linux_openmp_64/*.gz" \
    --exclude "linux_openmp_64/funstuff" \
    --exclude "linux_openmp_64/shiny" \
    --exclude "linux_openmp_64/afnipy" \
    --exclude "linux_openmp_64/lib/RetroTS" \
    --exclude "linux_openmp_64/lib_RetroTS" \
    --exclude "linux_openmp_64/meica.libs" \
    # Keep only what we use
    && find $INSTALL_DIR/afni-latest -type f -not \( \
    -name "3dTshift" -or \
    -name "3dUnifize" -or \
    -name "3dAutomask" -or \
    -name "3dvolreg" \) -delete
# AFNI config
ENV PATH="$INSTALL_DIR/afni-latest:$PATH" \
    AFNI_IMSAVE_WARNINGS="NO" \
    AFNI_PLUGINPATH="$INSTALL_DIR/afni-latest"

# Install synthstrip deps
RUN pip install torch torchvision --index-url \
    https://download.pytorch.org/whl/cpu

RUN pip install surfa

RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*


# Install dipy for MP-PCA denoising and Gibbs unringing
RUN pip install dipy

# Install tractography
COPY tractography $INSTALL_DIR/tractography
RUN cd $INSTALL_DIR/tractography && \
    pip install -e . --use-pep517

# copy FreeSurfer license
COPY docker/files/license.txt $FREESURFER_HOME/license.txt

RUN useradd -m -s /bin/bash -G users ${USER_NAME}

# Update HOME environment variable to use the proper user home
ENV HOME="/home/${USER_NAME}"

# Fetch templateflow stuff
RUN wget -O $INSTALL_DIR/fetch_templates.py https://raw.githubusercontent.com/nipreps/fmriprep/master/scripts/fetch_templates.py && \
    python $INSTALL_DIR/fetch_templates.py && \
    rm $INSTALL_DIR/fetch_templates.py

# Give full permissions to everything in the home directory
RUN chmod --recursive a+wrX ${HOME}

# Set entrypoint to tractography
ENTRYPOINT ["/opt/miniconda3/bin/tractography"]