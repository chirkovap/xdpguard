#!/bin/bash

# XDPGuard Installation Script
# Installs XDP/eBPF DDoS protection system

set -e

echo ""
echo "======================================"
echo "   XDPGuard Installation Script"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run as root (use sudo)"
    exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "ERROR: Cannot detect operating system"
    exit 1
fi

echo "[1/7] Detected OS: $OS"
echo ""

# Install dependencies
echo "[2/7] Installing system dependencies..."
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
elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ] || [ "$OS" = "fedora" ]; then
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
    echo "ERROR: Unsupported OS: $OS"
    echo "Supported: Ubuntu, Debian, CentOS, RHEL, Fedora"
    exit 1
fi

echo "✓ Dependencies installed"
echo ""

# Install Python dependencies
echo "[3/7] Installing Python dependencies..."
pip3 install -r requirements.txt
echo "✓ Python packages installed"
echo ""

# Compile XDP programs
echo "[4/7] Compiling XDP/eBPF programs..."
cd bpf
make clean
make
sudo make install
cd ..
echo "✓ XDP programs compiled and installed"
echo ""

# Create directories
echo "[5/7] Creating system directories..."
mkdir -p /etc/xdpguard
mkdir -p /var/lib/xdpguard
mkdir -p /var/log
mkdir -p /opt/xdpguard
echo "✓ Directories created"
echo ""

# Install files
echo "[6/7] Installing XDPGuard files..."
cp config.yaml /etc/xdpguard/
cp -r python /opt/xdpguard/
cp -r web /opt/xdpguard/
cp daemon.py /opt/xdpguard/
chmod +x /opt/xdpguard/daemon.py

# Install systemd service
cp systemd/xdpguard.service /etc/systemd/system/
echo "✓ Files installed"
echo ""

# Setup systemd service
echo "[7/7] Setting up systemd service..."
systemctl daemon-reload
systemctl enable xdpguard
echo "✓ Service enabled"
echo ""

echo "======================================"
echo "   Installation Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Edit configuration:"
echo "   nano /etc/xdpguard/config.yaml"
echo ""
echo "2. Set your network interface (eth0, ens3, etc.)"
echo ""
echo "3. Start the service:"
echo "   systemctl start xdpguard"
echo ""
echo "4. Check status:"
echo "   systemctl status xdpguard"
echo ""
echo "5. View logs:"
echo "   journalctl -u xdpguard -f"
echo ""
echo "6. Open web panel:"
echo "   http://your-server-ip:8080"
echo ""
echo "======================================"
