#!/bin/bash

source /opt/miniconda3/etc/profile.d/conda.sh
conda activate thor_py38

exec run-thor-worker --idle-shutdown-timeout=60 ${THOR_QUEUE}
