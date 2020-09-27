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
    challenges_added = []

    for challenge in challenges:
        deploy = generate_deployment(challenge)
        service = generate_service(challenge)

        if not deploy and not service:
            continue

        with open(os.path.join(local, challenge.name) + ".yaml", "w") as f:
            if service:
                yaml.dump(service, f)
                print("---", file=f)

            if deploy:
                yaml.dump(deploy, f)
                print("---", file=f)

        challenges_added.append(challenge)

    with open(os.path.join(local, "kustomization.yaml"), "w") as f:
        kustomization = generate_kustomization(challenges_added)
        if kustomization:
            yaml.dump(kustomization, f)


def generate_kustomization(challenges):
    ports = []
    resources = []
    for challenge in challenges:
        resources.append(challenge.name + ".yaml")

        for port in challenge.deploy.ports:
            ports.append(
                f"{port.external}=default/challenge-{challenge.name}-service:{port.internal}"
            )

    return {
        "apiVersion": "kustomize.config.k8s.io/v1beta1",
        "kind": "Kustomization",
        "resources": resources,
    }


def generate_deployment(challenge):
    if not challenge.deploy.docker:
        return None

    image_name = f"challenge-{challenge.name}"
    image_tag = os.environ.get("IMAGE_TAG", "latest")
    if (image_repo := os.environ.get("IMAGE_REPO")):
        image_name = f"{image_repo}/{image_name}"
        subprocess.run(["docker", "pull", f"{image_name}:{image_tag}"])

    container = {
        "name": f"challenge-{challenge.name}",
        "image": f"{image_name}:{image_tag}",
    }

    ports = []
    for port in challenge.deploy.ports:
        ports.append({"containerPort": port.internal})
    if ports:
        container["ports"] = ports

    env = []
    for key in challenge.deploy.env:
        env.append({"name": key, "value": os.environ[key]})
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
