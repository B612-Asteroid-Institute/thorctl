#!/bin/bash
set -xeuo pipefail


echo "Bringing down existing autoscaler..."
gcloud compute instances delete thor-autoscaler-production \
       --zone=us-west1-a

echo "Bringing up new one..."

# Create the autoscaler using the configuration file ('production-cloudconfig')
# in the same directory as this script.
#
# Magic one-liner to get the directory containing this script:
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# Now we can get the path of the config file:
CONFIG_FILE=${SCRIPT_DIR}/production-cloudconfig

gcloud compute instances create thor-autoscaler-production \
       --description="THOR autoscaler for the production queue" \
       --machine-type=e2-small \
       --service-account="thor-autoscaler@moeyens-thor-dev.iam.gserviceaccount.com" \
       --zone=us-west1-a \
       --scopes=cloud-platform \
       --create-disk='image-family=projects/cos-cloud/global/images/family/cos-stable,boot=yes,auto-delete=yes' \
       --metadata-from-file=user-data=${CONFIG_FILE}
