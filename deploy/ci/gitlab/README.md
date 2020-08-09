# GitLab CI

This gitlab-ci.yml file provides a template for what automated Continuous
Integration for a CTF *might* look like.

## Setup

- Create a kubernetes cluster
    - Follow the generic instructions for kubernetes
    - Add the cluster to a GitLab project
- Define the following CI variables:
    - `DOMAIN`
        - Make sure your DNS records are pointing to your cluster!
    - `CTFD_MYSQL_DB`
    - `CTFD_MYSQL_USER`
    - `CTFD_MYSQL_PASSWORD`
    - `CTFD_REDIS_PASSWORD`
    - `CTFD_SECRET`
- Create a commit containing the basic setup.
- Trigger a CTFd deploy.
- Setup your CTFd instance and create a token, setting the following
  environment variables:
    - `CTFD_TOKEN`
- Trigger a challenge deploy and challenge upload.
