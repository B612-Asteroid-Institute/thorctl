#!/bin/bash
set -xeuo pipefail

echo "Bringing down existing autoscaler..."
gcloud compute instances delete thor-autoscaler-production

echo "Bringing up new one..."
gcloud compute instances create thor-autoscaler-production \
       --description="THOR autoscaler for the production queue" \
       --machine-type=e2-small \
       --service-account="thor-autoscaler@moeyens-thor-dev.iam.gserviceaccount.com" \
       --zone=us-west1-a \
       --scopes=cloud-platform \
       --create-disk='image-family=projects/cos-cloud/global/images/family/cos-stable,boot=yes,auto-delete=yes' \
       --metadata-from-file=user-data=production-cloudconfig
