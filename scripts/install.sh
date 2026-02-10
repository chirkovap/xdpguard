#!/bin/bash

# XDPGuard Installation Script
# Installs XDP/eBPF DDoS protection system
# Compatible with Ubuntu 20.04+, Debian 11+, CentOS 8+, RHEL 8+

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
    OS_VERSION=$VERSION_ID
else
    echo "ERROR: Cannot detect operating system"
    exit 1
fi

echo "[1/8] Detected OS: $OS $OS_VERSION"
echo ""

# Install dependencies
echo "[2/8] Installing system dependencies..."
if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    apt-get update
    
    # Core dependencies (without python3-bcc which may not exist)
    apt-get install -y \
        python3 \
        python3-pip \
        clang \
        llvm \
        libelf-dev \
        libbpf-dev \
        make \
        git \
        curl \
        iproute2 || true
    
    # Try to install linux headers
    apt-get install -y linux-headers-$(uname -r) || \
    apt-get install -y linux-headers-amd64 || \
    apt-get install -y linux-headers-generic || \
    echo "WARNING: Could not install kernel headers, compilation may fail"
    
elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ] || [ "$OS" = "fedora" ]; then
    yum install -y \
        python3 \
        python3-pip \
        clang \
        llvm \
        elfutils-libelf-devel \
        kernel-devel \
        libbpf-devel \
        make \
        git \
        curl \
        iproute || true
else
    echo "ERROR: Unsupported OS: $OS"
    echo "Supported: Ubuntu, Debian, CentOS, RHEL, Fedora"
    exit 1
fi

echo "✓ System dependencies installed"
echo ""

# Install Python dependencies
echo "[3/8] Installing Python dependencies..."

# Try system packages first
if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    apt-get install -y \
        python3-flask \
        python3-yaml \
        python3-click \
        python3-requests \
        python3-psutil 2>/dev/null || true
fi

# Install via pip if needed (with fallback for newer Ubuntu)
pip3 install Flask PyYAML click requests psutil --break-system-packages 2>/dev/null || \
pip3 install Flask PyYAML click requests psutil || \
echo "WARNING: Some Python packages may not be installed"

echo "✓ Python packages installed"
echo ""

# Compile XDP programs
echo "[4/8] Compiling XDP/eBPF programs..."
cd bpf

# Check dependencies
if ! which clang > /dev/null 2>&1; then
    echo "ERROR: clang not found. Install clang first."
    exit 1
fi

echo "Cleaning previous builds..."
make clean 2>/dev/null || true

echo "Compiling XDP program..."
if make; then
    echo "✓ XDP program compiled successfully"
else
    echo "ERROR: XDP compilation failed"
    echo "Check that kernel headers are installed: apt install linux-headers-\$(uname -r)"
    exit 1
fi

echo "Installing XDP program..."
if make install; then
    echo "✓ XDP program installed"
else
    echo "ERROR: XDP installation failed"
    exit 1
fi

cd ..
echo ""

# Verify XDP compilation
echo "[5/8] Verifying XDP program..."
if [ ! -f "/usr/lib/xdpguard/xdp_filter.o" ]; then
    echo "ERROR: XDP program not found at /usr/lib/xdpguard/xdp_filter.o"
    exit 1
fi

XDP_SIZE=$(stat -c%s /usr/lib/xdpguard/xdp_filter.o)
echo "✓ XDP program verified (size: $XDP_SIZE bytes)"
echo ""

# Create directories
echo "[6/8] Creating system directories..."
mkdir -p /etc/xdpguard
mkdir -p /var/lib/xdpguard
mkdir -p /var/log
mkdir -p /opt/xdpguard
echo "✓ Directories created"
echo ""

# Install files
echo "[7/8] Installing XDPGuard files..."

# Copy config if not exists
if [ ! -f "/etc/xdpguard/config.yaml" ]; then
    cp config.yaml /etc/xdpguard/
    echo "✓ Configuration file installed"
else
    echo "! Configuration file already exists, skipping"
fi

# Copy Python modules
cp -r python /opt/xdpguard/
cp -r web /opt/xdpguard/
cp daemon.py /opt/xdpguard/
cp cli.py /opt/xdpguard/
chmod +x /opt/xdpguard/daemon.py
chmod +x /opt/xdpguard/cli.py

# Install systemd service
cp systemd/xdpguard.service /etc/systemd/system/
echo "✓ Files installed"
echo ""

# Setup systemd service
echo "[8/8] Setting up systemd service..."
systemctl daemon-reload
systemctl enable xdpguard
echo "✓ Service enabled"
echo ""

echo "======================================"
echo "   Installation Complete!"
echo "======================================"
echo ""
echo "IMPORTANT: Configure before starting!"
echo ""
echo "1. Edit configuration:"
echo "   nano /etc/xdpguard/config.yaml"
echo ""
echo "2. Set your network interface:"
echo "   Find your interface: ip link show"
echo "   Edit config and change 'interface' value"
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
echo "7. Check XDP is loaded:"
echo "   ip link show <your-interface>"
echo "   bpftool prog show"
echo ""
echo "======================================"
echo "For help: https://github.com/chirkovap/xdpguard"
echo "======================================"
