docker run -it \
       --env GCLOUD_PROJECT=moeyens-thor-dev \
       -v=$HOME/.config/gcloud:/root/.config/gcloud \
       --net=host \
       --env RABBIT_PASSWORD \
       --env THOR_QUEUE=production-tasks \
       thor-worker
