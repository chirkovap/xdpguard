#!/bin/bash
# XDPGuard Installation Script
# Automated installation with dependency management and config sync

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================"
echo "   XDPGuard Installation Script"
echo "============================================"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root (sudo)${NC}"
   exit 1
fi

# Detect network interface
echo -e "${YELLOW}[1/7]${NC} Detecting network interface..."
INTERFACE=$(ip route | grep default | awk '{print $5}' | head -n 1)
if [ -z "$INTERFACE" ]; then
    INTERFACE="ens33"
fi
echo -e "${GREEN}✓${NC} Network interface: $INTERFACE"

# Install dependencies
echo -e "${YELLOW}[2/7]${NC} Installing dependencies..."
apt-get update -qq
apt-get install -y -qq \
    python3 python3-pip \
    clang llvm \
    gcc make \
    libbpf-dev \
    linux-headers-$(uname -r) \
    bpftool \
    iproute2 \
    > /dev/null 2>&1

echo -e "${GREEN}✓${NC} Dependencies installed"

# Install Python packages
echo -e "${YELLOW}[3/7]${NC} Installing Python packages..."
pip3 install -q flask pyyaml scapy
echo -e "${GREEN}✓${NC} Python packages installed"

# Compile XDP program
echo -e "${YELLOW}[4/7]${NC} Compiling XDP program..."
if [ -f "Makefile" ]; then
    make clean > /dev/null 2>&1 || true
    make
    make install
    echo -e "${GREEN}✓${NC} XDP program compiled and installed"
else
    echo -e "${RED}✗${NC} Makefile not found"
    exit 1
fi

# Install Python files
echo -e "${YELLOW}[5/7]${NC} Installing XDPGuard files..."
mkdir -p /opt/xdpguard
cp -r python web *.py /opt/xdpguard/ 2>/dev/null || true
chmod +x /opt/xdpguard/daemon.py
echo -e "${GREEN}✓${NC} Files installed to /opt/xdpguard"

# Install and configure config
echo -e "${YELLOW}[6/7]${NC} Setting up configuration..."
mkdir -p /etc/xdpguard

if [ ! -f "/etc/xdpguard/config.yaml" ]; then
    if [ -f "config/config.yaml" ]; then
        cp config/config.yaml /etc/xdpguard/config.yaml
        # Update interface in config
        sed -i "s/interface: ens33/interface: $INTERFACE/g" /etc/xdpguard/config.yaml
        echo -e "${GREEN}✓${NC} Config installed and updated for $INTERFACE"
    else
        echo -e "${YELLOW}⚠${NC} Config file not found, using defaults"
    fi
else
    echo -e "${GREEN}✓${NC} Config already exists, keeping current settings"
fi

# Install systemd service
echo -e "${YELLOW}[7/7]${NC} Setting up systemd service..."

cat > /etc/systemd/system/xdpguard.service << 'EOF'
[Unit]
Description=XDPGuard DDoS Protection Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/xdpguard
ExecStart=/usr/bin/python3 /opt/xdpguard/daemon.py
Restart=on-failure
RestartSec=5

# Logging
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
echo -e "${GREEN}✓${NC} Systemd service installed"

echo ""
echo "============================================"
echo -e "${GREEN}   Installation Complete!${NC}"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Edit config (optional):    sudo nano /etc/xdpguard/config.yaml"
echo "  2. Start service:             sudo systemctl start xdpguard"
echo "  3. Enable on boot:            sudo systemctl enable xdpguard"
echo "  4. Check status:              sudo systemctl status xdpguard"
echo "  5. View logs:                 sudo journalctl -u xdpguard -f"
echo "  6. Access web UI:             http://$(hostname -I | awk '{print $1}'):8080"
echo ""
echo "Configuration will be automatically synced to XDP on service start!"
echo ""
