FROM ubuntu:20.04

# This is the dockerfile that install thorctl and thor
# Must be run from the repository root!

# Install system dependencies
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update -y && \
    apt-get install -y git curl systemd binutils gcc
RUN curl -L https://github.com/stedolan/jq/releases/download/jq-1.5/jq-linux64 > /usr/bin/jq
RUN chmod +x /usr/bin/jq

# Install conda
RUN curl -L https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh > /tmp/miniconda_install.sh && \
    bash /tmp/miniconda_install.sh -b -p /opt/miniconda3

# Install mamba
RUN /opt/miniconda3/bin/conda install mamba -n base -c conda-forge

## Create THOR conda environment, and install Python 3.8 and OpenOrb
RUN /opt/miniconda3/bin/conda create \
      --yes \
      --name thor_py38 \
      --channel defaults \
      --channel astropy \
      --channel moeyensj \
    --channel conda-forge \
    python=3.8 openorb

COPY infra/with_conda_env.sh /usr/bin/with_conda

RUN with_conda pip install pip --upgrade

# Install dependencies.
COPY requirements.txt /tmp/requirements.txt
RUN with_conda pip install -r /tmp/requirements.txt

# Install thorctl.
COPY . /opt/thorctl
WORKDIR /opt/thorctl
RUN with_conda pip install .

ENTRYPOINT ["/usr/bin/with_conda"]
