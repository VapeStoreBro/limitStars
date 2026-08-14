#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="${PROJECT_DIR:-/root/limitstarsbot}"
cd "$PROJECT_DIR"

if [[ -f .env ]]; then
  echo "$PROJECT_DIR/.env already exists; refusing to overwrite it."
  exit 1
fi

read -rsp "Telegram bot token: " BOT_TOKEN
echo
if [[ ! "$BOT_TOKEN" =~ ^[0-9]+:[A-Za-z0-9_-]+$ ]]; then
  echo "Telegram token format looks invalid." >&2
  exit 1
fi

GITHUB_WEBHOOK_SECRET="$(openssl rand -hex 32)"
DEPLOY_PATH_SECRET="$(openssl rand -hex 24)"

cat > .env <<ENV
BOT_TOKEN=$BOT_TOKEN
ADMIN_IDS=[6577441312]
DATABASE_PATH=data/limitstars.sqlite3
DEFAULT_STAR_PRICE_RUB=1.40
DEFAULT_COST_PRICE_RUB=1.25
MIN_STARS=50
MAX_STARS=10000
PAYMENT_PROVIDER=stub
FULFILLMENT_PROVIDER=stub
TON_WALLET_ADDRESS=
TONCENTER_API_KEY=
TON_LOW_BALANCE=2.0
TON_CRITICAL_BALANCE=0.7
GITHUB_REPOSITORY=VapeStoreBro/limitStars
GITHUB_WEBHOOK_SECRET=$GITHUB_WEBHOOK_SECRET
DEPLOY_PATH_SECRET=$DEPLOY_PATH_SECRET
DEPLOY_HOST=0.0.0.0
DEPLOY_PORT=9103
PROJECT_DIR=/root/limitstarsbot
SYSTEMD_SERVICE=limitstarsbot.service
ENV
chmod 600 .env

cp deploy/limitstarsbot.service /etc/systemd/system/limitstarsbot.service
cp deploy/limitstarsbot-deploy.service /etc/systemd/system/limitstarsbot-deploy.service
systemctl daemon-reload
systemctl enable --now limitstarsbot.service limitstarsbot-deploy.service

if command -v ufw >/dev/null 2>&1 && ufw status | grep -q '^Status: active'; then
  ufw allow 9103/tcp >/dev/null
fi

sleep 2

echo
echo "========== GitHub webhook settings =========="
echo "Payload URL: http://195.133.9.214:9103/deploy/$DEPLOY_PATH_SECRET"
echo "Content type: application/json"
echo "Secret: $GITHUB_WEBHOOK_SECRET"
echo "Events: Just the push event"
echo "============================================="
systemctl --no-pager --full status limitstarsbot.service limitstarsbot-deploy.service || true
