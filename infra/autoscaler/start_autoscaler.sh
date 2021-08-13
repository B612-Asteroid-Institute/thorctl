#!/bin/bash

set -euo pipefail

source /opt/miniconda3/etc/profile.d/conda.sh
conda activate thor_py38

thorctl autoscale --rabbit-password-from-secret-manager ${THOR_AUTOSCALED_QUEUES}
