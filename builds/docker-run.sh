#!/bin/bash

CONTAINER_NAME="peyeon"

if [[ $1 == new ]]; then
    docker stop "$CONTAINER_NAME" 2>/dev/null 1>/dev/null &
    wait  # 
    sleep 1
    docker rm "$CONTAINER_NAME" 2>/dev/null
fi

# check to see if container already exists
CONTAINER_HASH=$(docker ps -a -q -f name=$CONTAINER_NAME)

if [[ "$CONTAINER_HASH" ]]; then
    # Container already exists--launch the stopped container
    docker start "$CONTAINER_NAME"
    docker exec -it -u eyeon $CONTAINER_NAME /bin/bash
else
    # Doesn't exist, creates a new container called eyeon
    docker run --name "$CONTAINER_NAME" -p8888:8888 -p8501:8501 -it -v $(pwd):/workdir:Z ghcr.io/llnl/peyeon:main /bin/bash
fi
