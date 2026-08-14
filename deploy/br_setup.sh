#!/usr/bin/env bash
# Deploy the Caspar lead app on this droplet as br.investorguruji.com.
# Idempotent; adds its own nginx vhost and systemd service; DOES NOT touch
# any existing site config. Run as root:  bash br_setup.sh
set -euo pipefail

APP_DIR=/opt/caspar
DOMAIN=br.investorguruji.com

echo "== packages =="
apt-get update -qq
apt-get install -y -qq python3-venv nginx certbot python3-certbot-nginx

echo "== app dir =="
mkdir -p $APP_DIR
# expects app/, db/leads.db and app/requirements.txt already copied here (see runbook)
test -f $APP_DIR/app/server.py || { echo "!! copy the app first (see runbook)"; exit 1; }

python3 -m venv $APP_DIR/venv
$APP_DIR/venv/bin/pip install -q -r $APP_DIR/app/requirements.txt

echo "== systemd service =="
cat > /etc/systemd/system/caspar-leads.service <<EOF
[Unit]
Description=Caspar lead app
After=network.target

[Service]
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/app/server.py
Restart=always
User=www-data
# app binds 0.0.0.0:8765; nginx proxies to it; firewall must NOT open 8765

[Install]
WantedBy=multi-user.target
EOF
chown -R www-data:www-data $APP_DIR
systemctl daemon-reload
systemctl enable --now caspar-leads
sleep 2 && systemctl --no-pager -l status caspar-leads | head -5

echo "== nginx vhost (separate file; existing sites untouched) =="
cat > /etc/nginx/sites-available/$DOMAIN <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    location / {
        proxy_pass http://127.0.0.1:8765;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$remote_addr;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
    }
}
EOF
ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/$DOMAIN
nginx -t && systemctl reload nginx

echo "== HTTPS (Let's Encrypt) =="
certbot --nginx -d $DOMAIN --non-interactive --agree-tos --register-unsafely-without-email --redirect || \
  echo "!! certbot failed — check that the DNS A record for $DOMAIN points here first"

echo "== firewall: keep 8765 closed externally =="
if command -v ufw >/dev/null; then ufw deny 8765/tcp || true; fi

echo "DONE -> https://$DOMAIN"
