#!/usr/bin/env python3

import os
import site
import yaml

base = pathlib.Path(__file__).parent.parent.parent.absolute()
site.addsitedir(base)
import ctftool


def main():
    local = os.path.dirname(os.path.realpath(__file__))
    local = os.path.join(local, "challenges")
    os.makedirs(os.path.join(local), exist_ok=True)

    challenges = list(ctftool.Challenge.load_all())
    for challenge in challenges:
        with open(os.path.join(local, challenge.name) + ".yaml", "w") as f:
            service = generate_service(challenge)
            if service:
                yaml.dump(service, f)
                print("---", file=f)

            deploy = generate_deployment(challenge)
            if deploy:
                yaml.dump(deploy, f)
                print("---", file=f)

    with open(os.path.join(local, "kustomization.yaml"), "w") as f:
        kustomization = generate_kustomization(challenges)
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
        "configMapGenerator": [
            {"namespace": "ingress", "name": "tcp-services", "literals": ports}
        ],
        "generatorOptions": {"disableNameSuffixHash": True,},
        "resources": resources,
    }


def generate_deployment(challenge):
    if not challenge.deploy.docker:
        return None

    ports = []
    for port in challenge.deploy.ports:
        ports.append({"containerPort": port.internal})

    IMAGE_REPO = os.environ.get("IMAGE_REPO", "")
    IMAGE_TAG = os.environ.get("IMAGE_TAG", "latest")

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
                    "containers": [
                        {
                            "name": f"challenge-{challenge.name}",
                            "image": f"{IMAGE_REPO}/challenge-{challenge.name}:{IMAGE_TAG}",
                            "imagePullPolicy": "Always",
                            "ports": ports,
                        },
                    ],
                },
            },
        },
    }


def generate_service(challenge):
    if not challenge.deploy.docker:
        return None

    ports = []
    for port in challenge.deploy.ports:
        ports.append(
            {
                "port": port.external,
                "targetPort": port.internal,
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
        "spec": {"ports": ports, "selector": {"challenge": challenge.name}},
    }


if __name__ == "__main__":
    main()
