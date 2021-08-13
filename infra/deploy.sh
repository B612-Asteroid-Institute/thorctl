#!/bin/bash

set -xeuo pipefail

docker tag thorctl:production-tasks-latest gcr.io/moeyens-thor-dev/thorctl:production-tasks-latest
docker push gcr.io/moeyens-thor-dev/thorctl:production-tasks-latest

cd autoscaler
./update.sh
cd -
