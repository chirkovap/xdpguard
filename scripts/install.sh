#!/bin/bash

# XDPGuard Installation Script
# Supports: Ubuntu 20.04+, Debian 11+, CentOS 8+, RHEL 8+

set -e

echo ""
echo "=========================================="
echo "  XDPGuard Installation Script"
echo "  High-Performance DDoS Protection"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "Cannot detect OS"
    exit 1
fi

echo "Detected OS: $OS"
echo ""

# Install dependencies
echo "[1/6] Installing dependencies..."
if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    apt-get update
    apt-get install -y \
        python3-pip \
        clang \
        llvm \
        libelf-dev \
        gcc-multilib \
        linux-headers-$(uname -r) \
        python3-bcc \
        bpfcc-tools \
        libbpf-dev \
        make \
        git \
        curl
elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
    yum install -y \
        python3-pip \
        clang \
        llvm \
        elfutils-libelf-devel \
        kernel-devel \
        bcc-tools \
        python3-bcc \
        libbpf-devel \
        make \
        git \
        curl
else
    echo "Unsupported OS: $OS"
    exit 1
fi

echo "✓ Dependencies installed"
echo ""

# Install Python dependencies
echo "[2/6] Installing Python dependencies..."
pip3 install -r requirements.txt
echo "✓ Python dependencies installed"
echo ""

# Create directories
echo "[3/6] Creating directories..."
mkdir -p /etc/xdpguard
mkdir -p /var/lib/xdpguard
mkdir -p /var/log
mkdir -p /opt/xdpguard
echo "✓ Directories created"
echo ""

# Install files
echo "[4/6] Installing files..."
cp config.yaml /etc/xdpguard/
cp -r python /opt/xdpguard/
cp -r web /opt/xdpguard/
cp daemon.py /opt/xdpguard/
cp systemd/xdpguard.service /etc/systemd/system/
chmod +x /opt/xdpguard/daemon.py
echo "✓ Files installed"
echo ""

# Setup systemd service
echo "[5/6] Setting up systemd service..."
systemctl daemon-reload
systemctl enable xdpguard
echo "✓ Systemd service configured"
echo ""

# Create CLI symlink
echo "[6/6] Creating CLI command..."
ln -sf /opt/xdpguard/python/cli.py /usr/local/bin/xdpguard
chmod +x /opt/xdpguard/python/cli.py
echo "✓ CLI command created"
echo ""

echo "=========================================="
echo "  Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Edit config: nano /etc/xdpguard/config.yaml"
echo "  2. Set your network interface (eth0, ens3, etc.)"
echo "  3. Start service: systemctl start xdpguard"
echo "  4. Check status: systemctl status xdpguard"
echo "  5. Open web panel: http://your-ip:8080"
echo ""
echo "CLI Commands:"
echo "  xdpguard status         - Show system status"
echo "  xdpguard block <ip>     - Block an IP"
echo "  xdpguard unblock <ip>   - Unblock an IP"
echo "  xdpguard list-blocked   - List blocked IPs"
echo ""
echo "Logs: /var/log/xdpguard.log"
echo "Config: /etc/xdpguard/config.yaml"
echo ""
