# CTF Infrastructure

This is my template infrastructure for Capture the Flag competitions.

## Challenges

The challenges are managed using [ctftool](https://github.com/jedevc/mini-ctf-tool/),
a home-grown tool for managing challenge metadata and information. See the
GitHub page for more documentation on the exact formats allowed.

Essentially, all challenges are placed into the `challenges/` directory, and
should contain either a `challenge.yaml` or `challenge.json` file.

Useful ctftool commands used in development include:

- Listing:
  ```
  $ ./ctftool.py list
  ```
- Validation:
  ```
  $ ./ctftool.py validate
  ```

## Deployment

### Docker

The docker build steps contain basic primitives for building challenge images
and containers. They probably shouldn't be used on their own, and are
intended to be used in conjunction with either docker-compose or kubernetes.

Set optional environment variables:

    $ export IMAGE_TAG=...
    $ export IMAGE_PREFIX=example/

Build the challenge images:

    $ ./deploy/docker/build.sh

Push them to a private registry:

    $ ./deploy/docker/build.sh

The next steps assume that you have configured your machines to automatically
pull from this private registry.

If you don't happen to have a private registry, just leave `IMAGE_PREFIX`
unset and everything should be fine.

### Docker Compose

Deploying using docker-compose is a more lightweight alternative to building
and maintaining an entire cluster. However, it will definitely be less
flexible, so keep that in mind when making a decision.

Copy the infrastructure code to a build directory:

    $ mkdir -p build
    $ cp -R deploy/docker-compose/ build/

Build the build step for the infrastructure:

    $ ./build/docker-compose/generate.sh

Launch it!

    $ cd build/docker-compose
    $ docker-compose up

### Kubernetes

To deploy using Kubernetes, you first need a cluster. Then, once you've
installed the dependencies (listed below), you can install the entire infra.

Export required environment variables:

    $ export CTFD_MYSQL_DB=ctfd
    $ export CTFD_MYSQL_USER=ctfd
    $ export CTFD_MYSQL_PASSWORD=ctfd
    $ export CTFD_REDIS_PASSWORD=ctfd
    $ export CTFD_SECRET=ctfd
    $ export DOMAIN=ctfd.example.com

Copy the infrastructure code to a build directory:

    $ mkdir -p build
    $ cp -R deploy/kube/ build/

Build the build step for the infrastructure:

    $ ./build/kube/generate.sh

Apply the infrastructure to the cluster:
  
    $ kubectl apply -k build/kube/

#### Ingress

You need to install [Nginx Ingress](https://kubernetes.github.io/ingress-nginx/).
We set up without an external LoadBalancer, as this causes problems for the
challenges that listen on ports.

    $ helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    $ helm repo update
    $ kubectl create namespace ingress-nginx
    $ helm install ingress ingress-nginx/ingress-nginx \
        --namespace ingress \
        --set controller.hostNetwork=true \
        --set controller.kind=DaemonSet \
        --set controller.hostPort.enabled=true \
        --set controller.service.enabled=false \
        --set controller.publishService.enabled=false \
        --set controller.extraArgs.tcp-services-configmap=ingress/tcp-services

#### Cert Manager

To handle TLS certificates, we use [Cert Manager](https://cert-manager.io).

**NOTE**: Make sure that your DNS records are pointing to the right place!

First we install it:

    $ helm repo add jetstack https://charts.jetstack.io
    $ helm repo update
    $ kubectl create namespace cert-manager
    $ helm install cert-manager jetstack/cert-manager \
        --namespace cert-manager \
        --version v0.15.1 \
        --set installCRDs=true

Then we need to setup a couple LetsEncrypt issuers (one for staging, one for
production):

```yaml
apiVersion: cert-manager.io/v1alpha2
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: letsencrypt@jedevc.com
    privateKeySecretRef:
      name: letsencrypt-staging
    solvers:
    - http01:
        ingress:
          class: nginx
---
apiVersion: cert-manager.io/v1alpha2
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: letsencrypt@jedevc.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

When you setup the ClusterIssuers, the CTFd instance should automatically be
given a TLS certificate.
