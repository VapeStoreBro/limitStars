# Limit Stars

Telegram Stars shop for `@LimitStarsBot`.

## Current functionality

- User first chooses who receives Stars: self or friend.
- Friend purchase requires a valid `@username`.
- Presets: 50, 100, 250, 500, 1000, 2500, 5000, 10000 Stars.
- Custom amount from 50 to 10000 Stars.
- Default sale price: 1.40 RUB per Star.
- Sale price and internal cost price are editable from the hidden admin panel.
- Special per-user prices: at cost, fixed RUB/Star, or cost + percent.
- Order history and shop statistics.
- Hidden admin panel restricted to configured admin IDs and private chat only.
- SQLite WAL database.
- Separate provider interfaces for SBP payments and Stars fulfillment.
- Separate systemd services for the bot and GitHub auto-deploy webhook.

## Production integrations still to plug in

The repository deliberately does not fake successful payments or Stars delivery. The next production modules are:

1. Concrete SBP acquiring/provider API and signed webhook.
2. Dedicated TON hot wallet with balance monitoring.
3. Tested Stars fulfillment implementation using the selected Telegram/Fragment flow.
4. Automated treasury refill route.

## Server

The deployment files target the existing VPS layout:

- project: `/root/limitstarsbot`
- bot service: `limitstarsbot.service`
- deploy service: `limitstarsbot-deploy.service`
- deploy webhook port: `9103`

Initial server setup:

```bash
git clone https://github.com/VapeStoreBro/limitStars.git /root/limitstarsbot
cd /root/limitstarsbot
bash deploy/install.sh
bash deploy/configure.sh
```

Do not commit `.env`, wallet seed phrases, private keys, payment API secrets, or webhook secrets.
