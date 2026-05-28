#!/bin/bash

# Qewr Monitoring Agent Installer
# Target: Ubuntu 22.04/24.04 (Blank PC)

set -e

echo "=========================================="
echo "   QEWR MONITORING AGENT INSTALLER        "
echo "=========================================="

# 1. Check for Sudo
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo)"
  exit 1
fi

# 2. Get User Input
read -p "Enter Monitoring Server URL [http://13.125.105.188:8000/api/ping]: " SERVER_URL
SERVER_URL=${SERVER_URL:-"http://13.125.105.188:8000/api/ping"}

DEFAULT_HOSTNAME=$(hostname)
read -p "Enter Server Nickname [$DEFAULT_HOSTNAME]: " SERVER_NICKNAME
SERVER_NICKNAME=${SERVER_NICKNAME:-$DEFAULT_HOSTNAME}

# 3. Install Dependencies
echo "Installing system dependencies..."
apt update
apt install -y python3-pip python3-venv curl

# 4. Setup Agent Directory
INSTALL_DIR="/opt/qewr-agent"
echo "Setting up agent in $INSTALL_DIR..."
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# 5. Create Virtual Environment
python3 -m venv venv
./venv/bin/pip install psutil httpx

# 6. Download Agent Script
echo "Downloading agent script..."
curl -sSL https://raw.githubusercontent.com/service0427/init/master/agent.py -o agent.py

# 7. Create Config/Wrapper
cat <<EOF > run_agent.sh
#!/bin/bash
cd $INSTALL_DIR
./venv/bin/python agent.py
EOF
chmod +x run_agent.sh

# Update agent.py with config
sed -i "s|SERVER_URL = .*|SERVER_URL = \"$SERVER_URL\"|" agent.py
sed -i "s|SERVER_NAME = .*|SERVER_NAME = \"$SERVER_NICKNAME\"|" agent.py

# 8. Setup Cron (Every minute)
CRON_JOB="* * * * * $INSTALL_DIR/run_agent.sh >> $INSTALL_DIR/agent.log 2>&1"
(crontab -l 2>/dev/null | grep -v "$INSTALL_DIR/run_agent.sh"; echo "$CRON_JOB") | crontab -

echo "=========================================="
echo "   INSTALLATION COMPLETE!                 "
echo "   Your server is now being monitored.    "
echo "   Check logs at: $INSTALL_DIR/agent.log  "
echo "=========================================="
