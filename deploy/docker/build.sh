#!/bin/bash

set -e

ROOT=$PWD
SOURCE=$(dirname $0)

for source in $($SOURCE/deployable.py); do
    cd $(dirname $source)

    if [ -z "$IMAGE_TAG" ]; then
        IMAGE_TAG="latest"
    fi

    IMAGE_NAME="challenge-$(basename $(dirname $source))"
    if [ -n "$IMAGE_REPO" ]; then
        IMAGE_NAME="$IMAGE_REPO/$IMAGE_NAME"
    fi

    if [ -n "$IMAGE_REPO" ]; then
        docker pull "$IMAGE_NAME:$IMAGE_TAG" || true
    fi
    docker build --cache-from "$IMAGE_NAME:$IMAGE_TAG" -t "$IMAGE_NAME:$IMAGE_TAG" .

    cd $ROOT
done
