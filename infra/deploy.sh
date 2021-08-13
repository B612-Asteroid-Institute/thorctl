#!/bin/bash

set -xeuo pipefail

docker tag thorctl:production-tasks-latest gcr.io/moeyens-thor-dev/thorctl:production-tasks-latest
docker push gcr.io/moeyens-thor-dev/thorctl:production-tasks-latest

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

cd $SCRIPT_DIR/autoscaler
./update.sh
cd -
