FROM ubuntu:20.04

# Install system dependencies
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update -y && \
    apt-get install -y git curl systemd
RUN curl -L https://github.com/stedolan/jq/releases/download/jq-1.5/jq-linux64 > /usr/bin/jq
RUN chmod +x /usr/bin/jq

# Install conda
RUN curl -L https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh > /tmp/miniconda_install.sh && \
    bash /tmp/miniconda_install.sh -b -p /opt/miniconda3

# Install mamba
RUN /opt/miniconda3/bin/conda install mamba -n base -c conda-forge

## Create THOR conda environment
RUN /opt/miniconda3/bin/conda create \
      --yes \
      --name thor_py38 \
      --channel defaults \
      --channel astropy \
      --channel moeyensj \
    --channel conda-forge \
    numpy numba pandas openorb astropy python=3.8

# Clone THOR
ARG THOR_GIT_REF

RUN git clone https://github.com/moeyensj/thor /opt/thor
WORKDIR /opt/thor

##### FIXME: Temporary while unmerged
RUN git remote add fork https://github.com/spenczar/thor
RUN git fetch fork
##### FIXME: End

RUN git checkout $THOR_GIT_REF

RUN /opt/miniconda3/bin/mamba install \
      --yes \
      --name thor_py38 \
      --channel defaults \
      --channel astropy \
      --channel moeyensj \
      --channel conda-forge \
      --file requirements.txt

RUN /bin/bash -c "source /opt/miniconda3/bin/activate thor_py38 && pip install --editable ."
# Install start script
COPY start_worker.sh /etc/thor/start_worker.sh
RUN chmod +x /etc/thor/start_worker.sh

ARG THOR_QUEUE
CMD /etc/thor/start_worker.sh
