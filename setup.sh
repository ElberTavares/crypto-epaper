#!/bin/bash
# setup.sh - Automated installer for Crypto E-Paper
set -e

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "=== Crypto E-Paper Setup ==="
echo "Base directory: $BASE_DIR"

# System packages
echo "[1/6] Installing system packages..."
sudo apt update -q
sudo apt install -y python3 python3-venv python3-dev python3-pip \
    git wget libfreetype6-dev libopenjp2-7 libtiff-dev libjpeg-dev \
    libatlas-base-dev fonts-dejavu-core

# Waveshare driver (sparse clone — only the files we need)
echo "[2/6] Downloading Waveshare e-Paper driver..."
DRIVER_DIR="$BASE_DIR/waveshare_epd"
if [ ! -d "$DRIVER_DIR" ]; then
    git clone --depth=1 --filter=blob:none --sparse \
        https://github.com/waveshare/e-Paper.git /tmp/waveshare-epaper
    cd /tmp/waveshare-epaper
    git sparse-checkout set RaspberryPi_JetsonNano/python/lib/waveshare_epd
    cp -r RaspberryPi_JetsonNano/python/lib/waveshare_epd "$DRIVER_DIR"
    cd "$BASE_DIR"
    rm -rf /tmp/waveshare-epaper
    # Fix relative import issue in driver
    sed -i 's|from \. import epdconfig|import epdconfig|g' "$DRIVER_DIR/epd2in13_V2.py" 2>/dev/null || true
    sed -i 's|from \. import epdconfig|import epdconfig|g' "$DRIVER_DIR/epd2in13_V3.py" 2>/dev/null || true
    echo "    Driver installed at $DRIVER_DIR"
else
    echo "    Driver already present — skipping"
fi

# Fonts
echo "[3/6] Downloading fonts..."
FONTS_DIR="$BASE_DIR/fonts"
mkdir -p "$FONTS_DIR"
if [ ! -f "$FONTS_DIR/RobotoMono-Regular.ttf" ]; then
    wget -q -O "$FONTS_DIR/RobotoMono-Regular.ttf" \
        "https://github.com/google/fonts/raw/main/apache/robotomono/RobotoMono%5Bwght%5D.ttf" || \
    cp /usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf "$FONTS_DIR/RobotoMono-Regular.ttf"
    echo "    Font downloaded"
else
    echo "    Font already present — skipping"
fi

# Python virtual environment
echo "[4/6] Creating Python virtual environment..."
if [ ! -d "$BASE_DIR/venv" ]; then
    python3 -m venv "$BASE_DIR/venv" --without-pip
    curl -sS https://bootstrap.pypa.io/get-pip.py | "$BASE_DIR/venv/bin/python3"
fi

echo "[5/6] Installing Python dependencies..."
"$BASE_DIR/venv/bin/pip" install --upgrade pip -q
"$BASE_DIR/venv/bin/pip" install requests flask "pillow==10.4.0" RPi.GPIO spidev gpiozero lgpio -q

# Logs directory
mkdir -p "$BASE_DIR/logs"

# systemd services
echo "[6/6] Installing systemd services..."
CURRENT_USER=$(whoami)
sed "s|INSTALL_PATH|$BASE_DIR|g; s|INSTALL_USER|$CURRENT_USER|g" \
    "$BASE_DIR/crypto-epaper.service" | sudo tee /etc/systemd/system/crypto-epaper.service > /dev/null
sed "s|INSTALL_PATH|$BASE_DIR|g; s|INSTALL_USER|$CURRENT_USER|g" \
    "$BASE_DIR/crypto-epaper-web.service" | sudo tee /etc/systemd/system/crypto-epaper-web.service > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable crypto-epaper crypto-epaper-web
sudo systemctl start crypto-epaper crypto-epaper-web

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Display service:  sudo systemctl status crypto-epaper"
echo "Web dashboard:    http://$(hostname).local:8080"
echo "Live logs:        tail -f $BASE_DIR/logs/display.log"
