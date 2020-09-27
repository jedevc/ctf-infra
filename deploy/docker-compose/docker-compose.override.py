#!/usr/bin/env python3

import os
import pathlib
import site
import yaml

import ctftool


def main():
    local = os.path.dirname(os.path.realpath(__file__))

    services = {}
    for challenge in ctftool.Challenge.load_all():
        service = generate_service(challenge)
        if service:
            services = {**service, **services}

    with open(os.path.join(local, "docker-compose.override.yaml"), "w") as f:
        compose = {
            "version": "3",
            "services": services,
        }
        yaml.dump(compose, f)


def generate_service(challenge):
    if not challenge.deploy.docker:
        return None

    result = {
        "image": f"challenge-{challenge.name}",
        "restart": "always",
    }
    if challenge.deploy.env:
        result["environment"] = {key: f"${key}" for key in challenge.deploy.env}
    if challenge.deploy.ports:
        ports = []
        for port in challenge.deploy.ports:
            ports.append(f"{port.external}:{port.internal}/{port.protocol}")
        result["ports"] = ports

    return {
        f"challenge-{challenge.name}": result,
    }


if __name__ == "__main__":
    main()
