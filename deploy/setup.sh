#!/usr/bin/env bash
# Setup script for running booking-alert as a systemd service on Ubuntu.
# Run on the VM as a user with sudo privileges:
#   bash deploy/setup.sh
set -euo pipefail

APP_DIR="/opt/booking-alert"
SERVICE_SRC="$(dirname "$0")/booking-alert.service"
SERVICE_DEST="/etc/systemd/system/booking-alert.service"
RUN_USER="$(logname 2>/dev/null || echo "$USER")"

echo "==> Installing system packages"
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip

echo "==> Creating app directory at $APP_DIR"
sudo mkdir -p "$APP_DIR"
sudo chown -R "$RUN_USER":"$RUN_USER" "$APP_DIR"

echo "==> Copying project files to $APP_DIR"
# Copy everything except .venv, __pycache__, .git, deploy/
rsync -a --exclude='.venv' --exclude='__pycache__' --exclude='.git' \
      --exclude='deploy' --exclude='*.pyc' \
      ./ "$APP_DIR/"

echo "==> Creating Python virtualenv"
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "==> Ensuring config.yaml and .env exist"
if [ ! -f "$APP_DIR/.env" ]; then
  echo "WARNING: $APP_DIR/.env not found. Copy .env.example and fill in secrets:"
  echo "  cp $APP_DIR/.env.example $APP_DIR/.env"
  echo "  nano $APP_DIR/.env"
fi

if [ ! -f "$APP_DIR/config.yaml" ]; then
  echo "ERROR: $APP_DIR/config.yaml missing. Copy it from your local repo." >&2
  exit 1
fi

echo "==> Installing systemd service"
sudo sed "s|__USER__|$RUN_USER|g" "$SERVICE_SRC" > /tmp/booking-alert.service
sudo mv /tmp/booking-alert.service "$SERVICE_DEST"
sudo chown root:root "$SERVICE_DEST"
sudo chmod 644 "$SERVICE_DEST"

sudo systemctl daemon-reload
sudo systemctl enable booking-alert

echo "==> Done."
echo ""
echo "Next steps:"
echo "  1. Set your timezone (so alert timestamps are correct):"
echo "     sudo timedatectl set-timezone Asia/Kolkata"
echo "  2. Fill in .env on the VM:"
echo "     nano $APP_DIR/.env"
echo "  3. Edit config.yaml on the VM (film IDs, dates):"
echo "     nano $APP_DIR/config.yaml"
echo "  4. Send a message to your Telegram bot so it can discover chat IDs."
echo "  5. Start the service:"
echo "     sudo systemctl start booking-alert"
echo "  6. Check logs:"
echo "     journalctl -u booking-alert -f"
echo "  7. Check status:"
echo "     systemctl status booking-alert"
