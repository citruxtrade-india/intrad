#!/bin/bash
# ============================================================
# Anti-Gravity Trading Platform — AWS EC2 Deploy Script
# Run once on a fresh Ubuntu 20.04 / 22.04 EC2 instance
# Usage: chmod +x deploy.sh && sudo ./deploy.sh
# ============================================================

set -e  # Exit immediately on any error

APP_DIR="/home/ubuntu/alice_trading"
SERVICE_NAME="trading-server"
REPO_URL="https://github.com/md-anees/Algo.git"  # Update if URL changed

echo ""
echo "============================================"
echo "  Anti-Gravity Trading Platform Deployer"
echo "============================================"
echo ""

# ── 1. System update ─────────────────────────────────────────
echo "[1/8] Updating system packages..."
apt-get update -qq
apt-get install -y python3 python3-pip git curl ufw -qq

# ── 2. Clone or pull the repo ────────────────────────────────
echo "[2/8] Fetching application code..."
if [ -d "$APP_DIR/.git" ]; then
    echo "  → Repo exists, pulling latest..."
    cd "$APP_DIR" && git pull
else
    echo "  → Cloning repo..."
    git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

# ── 3. Install Python dependencies ───────────────────────────
echo "[3/8] Installing Python dependencies..."
pip3 install -r requirements.txt --quiet

# Install pya3 separately (no-deps to avoid conflicts)
echo "  → Installing pya3 (no-deps)..."
pip3 install pya3==1.0.30 --no-deps --quiet

# ── 4. Set up .env file if missing ───────────────────────────
echo "[4/8] Checking .env configuration..."
if [ ! -f "$APP_DIR/.env" ]; then
    echo ""
    echo "  ⚠️  .env file NOT FOUND!"
    echo "  Create it at: $APP_DIR/.env"
    echo ""
    echo "  Required content:"
    echo "    ALICEBLUE_USER_ID=YOUR_USER_ID"
    echo "    ALICEBLUE_API_KEY=YOUR_API_KEY"
    echo "    ALICEBLUE_TOTP_SECRET=YOUR_TOTP_SECRET"
    echo ""
    echo "  Then re-run this script."
    exit 1
else
    echo "  → .env found ✓"
    chmod 600 "$APP_DIR/.env"  # Restrict to owner only
fi

# ── 5. Install & enable systemd service ──────────────────────
echo "[5/8] Setting up systemd service..."
cp "$APP_DIR/trading-server.service" "/etc/systemd/system/$SERVICE_NAME.service"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

# ── 6. Configure firewall ────────────────────────────────────
echo "[6/8] Configuring firewall..."
ufw allow OpenSSH
ufw allow 8002/tcp comment "Anti-Gravity Dashboard"
ufw --force enable
echo "  → Firewall: SSH + port 8002 open ✓"

# ── 7. Start the service ─────────────────────────────────────
echo "[7/8] Starting trading server..."
systemctl restart "$SERVICE_NAME"
sleep 3

# ── 8. Status check ─────────────────────────────────────────
echo "[8/8] Verifying deployment..."
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo ""
    echo "  ✅ Service is RUNNING"
    echo ""
    PUBLIC_IP=$(curl -s http://checkip.amazonaws.com/ 2>/dev/null || echo "YOUR_EC2_IP")
    echo "============================================"
    echo "  Dashboard URL: http://$PUBLIC_IP:8002"
    echo "  View logs:     journalctl -u $SERVICE_NAME -f"
    echo "  Stop server:   sudo systemctl stop $SERVICE_NAME"
    echo "  Restart:       sudo systemctl restart $SERVICE_NAME"
    echo "============================================"
else
    echo ""
    echo "  ❌ Service FAILED to start!"
    echo "  Check logs: journalctl -u $SERVICE_NAME -n 50 --no-pager"
    exit 1
fi
