# workers #

This directory contains a Dockerfile for building the THOR task queue worker.

Build a new image like this:

```
docker build --tag thor-worker --build-arg THOR_GIT_REF=fork/release/1.2-rc2
```

Push it like this:
```
docker tag thor-worker gcr.io/moeyens-thor-dev/thor-worker
gcloud auth configure-docker
docker push gcr.io/moeyens-thor-dev/thor-worker
```

The workers fetch the latest container when they start up, so new workers will
take in your update.
