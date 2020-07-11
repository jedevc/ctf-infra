#!/bin/bash

shopt -s globstar

BASE=$(dirname $0)

$BASE/challenges.py
for filename in $BASE/**/*.yaml; do
    envsubst < $filename > $filename.tmp
    mv $filename.tmp $filename
done
