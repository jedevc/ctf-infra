#!/usr/bin/env python3

import os
import pathlib
import site
import yaml

base = pathlib.Path(__file__).parent.parent.parent.absolute()
site.addsitedir(base)
import ctftool


def main():
    for challenge in ctftool.Challenge.load_all():
        if challenge.deploy and challenge.deploy.docker:
            print(challenge.path)


if __name__ == "__main__":
    main()
