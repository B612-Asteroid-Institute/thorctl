#!/bin/bash
set -xeuo pipefail

environment=$1

case $environment in

    staging)
        instance_name=thor-autoscaler-staging
        config_name=staging-cloudconfig
        queue_name=production-tasks
        ;;

    production)
        instance_name=thor-autoscaler-production
        config_name=production-cloudconfig
        queue_name=staging-tasks
        ;;

    *)
        echo "Invalid environment $environment (valid options are 'staging' or 'production')"
        exit 1
        ;;
esac

echo "Checking for existing $environment autoscaler..."
if gcloud compute instances list --zones=us-west1-a | grep -q $instance_name; then
    echo "Bringing down existing autoscaler..."
    gcloud compute instances delete $instance_name --zone=us-west1-a
fi

echo "Bringing up new $environment autoscaler..."

# Create the autoscaler using the configuration file ('production-cloudconfig')
# in the same directory as this script.
#
# Magic one-liner to get the directory containing this script:
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# Now we can get the path of the config file:
CONFIG_FILE=${SCRIPT_DIR}/${config_name}

gcloud compute instances create $instance_name \
       --description="THOR autoscaler for the $queue_name queue" \
       --machine-type=e2-small \
       --service-account="thor-autoscaler@moeyens-thor-dev.iam.gserviceaccount.com" \
       --zone=us-west1-a \
       --scopes=cloud-platform \
       --create-disk='image-family=projects/cos-cloud/global/images/family/cos-stable,boot=yes,auto-delete=yes' \
       --metadata-from-file=user-data=${CONFIG_FILE}
