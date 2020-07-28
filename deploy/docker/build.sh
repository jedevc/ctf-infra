#!/bin/bash

set -e
shopt -s globstar

ROOT=$PWD

for source in challenges/**/challenge.yaml; do
    cd $(dirname $source)

    if [ -z "$IMAGE_TAG" ]; then
        IMAGE_TAG="latest"
    fi
    IMAGE_NAME="${IMAGE_REPO}/challenge-$(basename $(dirname $source))"

    if [ -n "$IMAGE_REPO" ]; then
        docker pull "$IMAGE_NAME:$IMAGE_TAG" || true
    fi
    docker build --cache-from "$IMAGE_NAME:$IMAGE_TAG" -t "$IMAGE_NAME:$IMAGE_TAG" .

    cd $ROOT
done
