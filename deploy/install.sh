#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="${PROJECT_DIR:-/root/limitstarsbot}"
REPOSITORY_URL="${REPOSITORY_URL:-https://github.com/VapeStoreBro/limitStars.git}"

apt-get update
apt-get install -y git python3 python3-venv python3-pip openssl

if [[ ! -d "$PROJECT_DIR/.git" ]]; then
  git clone "$REPOSITORY_URL" "$PROJECT_DIR"
else
  git -C "$PROJECT_DIR" fetch origin main
  git -C "$PROJECT_DIR" reset --hard origin/main
fi

cd "$PROJECT_DIR"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m compileall -q bot deploy run.py

cp deploy/limitstarsbot.service /etc/systemd/system/limitstarsbot.service
cp deploy/limitstarsbot-deploy.service /etc/systemd/system/limitstarsbot-deploy.service
systemctl daemon-reload

echo "Installation completed. Next: bash deploy/configure.sh"
