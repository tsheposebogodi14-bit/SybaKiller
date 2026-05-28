#!/usr/bin/env bash
# System packages for SybaKiller / HFT dev (requires sudo once).
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Re-run with sudo: sudo bash scripts/install-system.sh"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
  build-essential \
  curl \
  wget \
  git \
  jq \
  ripgrep \
  fd-find \
  htop \
  pkg-config \
  libssl-dev \
  ca-certificates \
  gnupg \
  python3-venv \
  python3-pip \
  python3-dev \
  redis-tools \
  postgresql-client

# Docker (optional — for redis/postgres/grafana compose stack)
if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "${VERSION_CODENAME:-$VERSION}") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
  usermod -aG docker "${SUDO_USER:-$USER}" 2>/dev/null || true
fi

echo "System packages installed. Log out/in if docker group was added."
