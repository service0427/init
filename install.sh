#!/bin/bash

# Qewr Monitoring Agent Installer (v3.0 - Automation Focus)
# Target: Ubuntu 22.04/24.04 (Fresh Install)

set -e

echo "=========================================="
echo "   QEWR MONITORING AGENT INSTALLER        "
echo "=========================================="

# 1. Check for Sudo
if [ "$EUID" -ne 0 ]; then
  echo "Error: Please run as root (sudo bash ...)"
  exit 1
fi

# 2. Hostname Policy: Hostname must not be 'tech'
CURRENT_HOSTNAME=$(hostname)
if [ "${CURRENT_HOSTNAME,,}" = "tech" ]; then
    echo "Warning: Hostname is currently set to the default 'tech'."
    read -p "Enter new hostname (must not be 'tech'): " NEW_HOSTNAME < /dev/tty
    while [[ -z "$NEW_HOSTNAME" || "${NEW_HOSTNAME,,}" == "tech" ]]; do
        read -p "Invalid hostname. Hostname must not be empty or 'tech': " NEW_HOSTNAME < /dev/tty
    done
    hostnamectl set-hostname "$NEW_HOSTNAME"
    echo "Hostname changed to: $NEW_HOSTNAME"
    CURRENT_HOSTNAME=$NEW_HOSTNAME
fi

# 3. Setup Target Info
SERVER_URL="https://qewr.link/api/ping"
echo "Target Monitoring Server: $SERVER_URL"
echo "Registering as: $CURRENT_HOSTNAME"

# 4. Install All Dependencies
echo "Installing system dependencies (cron, tailscale, python)..."
apt update
apt install -y python3-pip python3-venv cron curl git

# Install Tailscale
if ! command -v tailscale &> /dev/null; then
    echo "Installing Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
fi

# Authenticate Tailscale
echo "Authenticating Tailscale..."
tailscale up --authkey tskey-auth-kN5PWmF1r111CNTRL-y4BpkBCqFZZwB9etTX8DZZjTv6HGb71u --accept-routes --accept-dns || echo "Tailscale up skipped or failed."

# Enable/Start Cron
systemctl enable cron
systemctl start cron

# 5. Setup Agent Directory & Venv
INSTALL_DIR="/opt/qewr-agent"
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

echo "Setting up Python virtual environment..."
python3 -m venv venv
./venv/bin/pip install psutil httpx

# 6. Pull latest agent.py
echo "Downloading agent logic..."
curl -sSL https://raw.githubusercontent.com/service0427/init/main/agent.py -o agent.py

# 7. Create Wrapper
cat <<EOF > run_agent.sh
#!/bin/bash
cd $INSTALL_DIR
./venv/bin/python agent.py
EOF
chmod +x run_agent.sh

# Inject configuration into agent.py
sed -i "s|SERVER_URL = .*|SERVER_URL = \"$SERVER_URL\"|" agent.py
sed -i "s|SERVER_NAME = .*|SERVER_NAME = \"$CURRENT_HOSTNAME\"|" agent.py

# 8. Crontab Registration (System-wide)
echo "Registering to /etc/cron.d/qewr-agent..."
echo "* * * * * root $INSTALL_DIR/run_agent.sh >> $INSTALL_DIR/agent.log 2>&1" | tee /etc/cron.d/qewr-agent > /dev/null
chmod 644 /etc/cron.d/qewr-agent

# Remove old crontab entry if exists
crontab -l 2>/dev/null | grep -v "$INSTALL_DIR/run_agent.sh" | crontab - || true

# 9. Immediate Execution
echo "Sending initial ping to monitoring server..."
$INSTALL_DIR/run_agent.sh || echo "Initial ping failed, but cron will retry."

echo "=========================================="
echo "   INSTALLATION COMPLETE!                 "
echo "   - Hostname: $(hostname)"
echo "   - Tailscale: Run 'sudo tailscale up' to connect."
echo "   - Monitoring: Active (Check $INSTALL_DIR/agent.log)"
echo "   - Next Step: git clone https://github.com/service0427/nmap_multi_v1.git"
echo "=========================================="
