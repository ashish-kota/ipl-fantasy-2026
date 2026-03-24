#!/bin/bash
# =============================================================================
# IPL Fantasy 2026 — Lightsail Deployment Script
# Run this ONCE on a fresh Ubuntu 22.04 Lightsail instance as the default user
# Usage: bash deploy.sh
# =============================================================================

set -e  # Exit on any error

APP_DIR="/home/ubuntu/ipl-fantasy-2026"
REPO_URL="https://github.com/ashish-kota/ipl-fantasy-2026.git"
SERVICE_NAME="ipl-fantasy"
APP_PORT=8501

echo "============================================"
echo " IPL Fantasy 2026 — Server Setup"
echo "============================================"

# 1. System updates
echo "[1/8] Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

# 2. Install Python, pip, git, nginx
echo "[2/8] Installing Python, pip, git, nginx..."
sudo apt-get install -y python3 python3-pip python3-venv git nginx

# 3. Clone the repo
echo "[3/8] Cloning repository..."
if [ -d "$APP_DIR" ]; then
    echo "  Directory exists — pulling latest..."
    cd "$APP_DIR" && git pull origin main
else
    git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

# 4. Create virtual environment and install dependencies
echo "[4/8] Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Create data directory (SQLite DB lives here)
echo "[5/8] Creating data directory..."
mkdir -p "$APP_DIR/data"

# 6. Create systemd service
echo "[6/8] Creating systemd service..."
sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=IPL Fantasy 2026 Streamlit App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/venv/bin/streamlit run app.py --server.port=${APP_PORT} --server.address=0.0.0.0 --server.headless=true
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl start ${SERVICE_NAME}

# 7. Configure nginx as reverse proxy (port 80 → 8501)
echo "[7/8] Configuring nginx reverse proxy..."
sudo tee /etc/nginx/sites-available/${SERVICE_NAME} > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:${APP_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 86400;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/${SERVICE_NAME} /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

# 8. Done
echo ""
echo "[8/8] ✅ Deployment complete!"
echo ""
echo "  App running at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
echo "  Service status: sudo systemctl status ${SERVICE_NAME}"
echo "  App logs:       sudo journalctl -u ${SERVICE_NAME} -f"
echo ""
echo "  Admin login:    admin@iplf.com / admin123"
echo "  ⚠️  Change the admin password after first login!"
echo ""
