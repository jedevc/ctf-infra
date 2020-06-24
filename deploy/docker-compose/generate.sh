#!/bin/bash

BASE=$(dirname $0)

$BASE/challenges.py > $BASE/docker-compose.yaml
