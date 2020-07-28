#!/bin/bash

set -e

ROOT=$PWD
SOURCE=$(dirname $0)

for source in $($SOURCE/deployable.py); do
    IMAGE_NAME="challenge-$(basename $(dirname $source))"
    if [ -n "$IMAGE_REPO" ]; then
        IMAGE_NAME="$IMAGE_REPO/$IMAGE_NAME"
    fi

    if [ -n "$IMAGE_TAG" ]; then
        docker push "${IMAGE_NAME}:${IMAGE_TAG}"
    else
        docker push "${IMAGE_NAME}:latest"
    fi
done
