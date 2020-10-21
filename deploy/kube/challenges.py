#!/usr/bin/env python3

import os
import site
import yaml

import ctftool


def main():
    local = os.path.dirname(os.path.realpath(__file__))
    local = os.path.join(local, "challenges")
    os.makedirs(os.path.join(local), exist_ok=True)

    challenges = list(ctftool.Challenge.load_all())
    for challenge in challenges:
        if not challenge.deploy.docker:
            continue

        deploy = generate_deployment(challenge)
        service = generate_service(challenge)

        with open(os.path.join(local, challenge.name) + ".yaml", "w") as f:
            if service:
                yaml.dump(service, f)
                print("---", file=f)

            if deploy:
                yaml.dump(deploy, f)
                print("---", file=f)

    with open(os.path.join(local, "kustomization.yaml"), "w") as f:
        kustomization = generate_kustomization(challenges)
        if kustomization:
            yaml.dump(kustomization, f)


def generate_kustomization(challenges):
    resources = []
    secrets = []
    for challenge in challenges:
        if not challenge.deploy.docker:
            continue

        resources.append(challenge.name + ".yaml")

        if challenge.deploy.env:
            secrets.append(
                {
                    "name": f"challenge-{challenge.name}-secret",
                    "type": "Opaque",
                    "literals": [f"{key}=${key}" for key in challenge.deploy.env],
                }
            )

    return {
        "apiVersion": "kustomize.config.k8s.io/v1beta1",
        "kind": "Kustomization",
        "resources": resources,
        "secretGenerator": secrets,
    }


def generate_deployment(challenge):
    if not challenge.deploy.docker:
        return None

    image_name = f"challenge-{challenge.name}"
    if (image_repo := os.environ.get("IMAGE_REPO")):
        image_name = f"{image_repo}/{image_name}"

    container = {
        "name": f"challenge-{challenge.name}",
        "image": f"{image_name}:{challenge.githash}",
    }

    ports = []
    for port in challenge.deploy.ports:
        ports.append({"containerPort": port.internal})
    if ports:
        container["ports"] = ports

    env = []
    for key in challenge.deploy.env:
        env.append(
            {
                "name": key,
                "valueFrom": {
                    "secretKeyRef": {
                        "name": f"challenge-{challenge.name}-secret",
                        "key": key,
                    }
                },
            }
        )
    if env:
        container["env"] = env

    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": f"challenge-{challenge.name}-deployment",
            "labels": {"app": "challenge", "challenge": challenge.name},
        },
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"challenge": challenge.name}},
            "template": {
                "metadata": {
                    "name": f"challenge-{challenge.name}",
                    "labels": {"app": "challenge", "challenge": challenge.name},
                },
                "spec": {
                    "automountServiceAccountToken": False,
                    "containers": [container],
                },
            },
        },
    }


def generate_service(challenge):
    if not challenge.deploy.docker or not challenge.deploy.ports:
        return None

    ports = []
    for port in challenge.deploy.ports:
        ports.append(
            {
                "name": f"port-{port.external}-{port.protocol.lower()}",
                "port": port.external,
                "targetPort": port.internal,
                "nodePort": port.external,
                "protocol": port.protocol.upper(),
            }
        )

    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": f"challenge-{challenge.name}-service",
            "labels": {"challenge": challenge.name},
        },
        "spec": {
            "type": "NodePort",
            "ports": ports,
            "selector": {"challenge": challenge.name},
        },
    }


if __name__ == "__main__":
    main()
