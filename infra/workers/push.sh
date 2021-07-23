docker tag thor-worker gcr.io/moeyens-thor-dev/thor-worker
gcloud auth configure-docker
docker push gcr.io/moeyens-thor-dev/thor-worker
