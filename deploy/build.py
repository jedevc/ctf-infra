#!/usr/bin/env python3

import argparse
import os
import subprocess
import yaml

import ctftool


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--push", action="store_true")
    args = parser.parse_args()

    for challenge in ctftool.Challenge.load_all():
        if challenge.deploy and challenge.deploy.docker:
            print(f"Building from {challenge.path}...")

            image_name = f"challenge-{challenge.name}"
            image_tag = os.environ.get("IMAGE_TAG")
            if (image_repo := os.environ.get("IMAGE_REPO")):
                image_name = f"{image_repo}/{image_name}"
                subprocess.run(["docker", "pull", f"{image_name}:latest"])

            subprocess.run(["docker", "build", "-t", f"{image_name}:latest", "."], cwd=os.path.dirname(challenge.path), check=True)
            if image_tag:
                subprocess.run(["docker", "tag", f"{image_name}:latest", f"{image_name}:{image_tag}"], check=True)

            if args.push:
                subprocess.run(["docker", "push", f"{image_name}:latest"], check=True)
                if image_tag:
                    subprocess.run(["docker", "push", f"{image_name}:{image_tag}"], check=True)


if __name__ == "__main__":
    main()
