#!/bin/bash
set -euo pipefail
dnf install -y docker git python3-pip
systemctl enable --now docker
mkdir -p /usr/local/lib/docker/cli-plugins
curl --fail --location https://github.com/docker/compose/releases/download/v2.35.1/docker-compose-linux-x86_64 --output /usr/local/lib/docker/cli-plugins/docker-compose
chmod 755 /usr/local/lib/docker/cli-plugins/docker-compose
usermod -aG docker ec2-user
install -d -m 0755 -o ec2-user -g ec2-user /opt/hydra-practice
