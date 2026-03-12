#!/bin/bash
# wifi-watchdog.sh - Wi-Fi watchdog with fallback to known hotspot
#
# If no internet is found:
#   1. Tries to reconnect to the current saved network
#   2. If that fails, connects to the fallback hotspot:
#        SSID    : crypto-epaper
#        Password: bitcoin123
#      (User creates this hotspot on their phone)
#
# Once connected to the hotspot, the user can access:
#        http://crypto-epaper.local:8080
#   and optionally configure a new Wi-Fi network from there.
#
# Add to cron: */2 * * * * /usr/local/bin/wifi-watchdog.sh

LOG=/home/cripto/crypto-epaper/files/logs/wifi.log
CONFIG=/home/cripto/crypto-epaper/files/config.json

# Read fallback hotspot credentials from config.json if available
AP_SSID=$(python3 -c "import json; d=json.load(open('$CONFIG')); print(d.get('ap_ssid','crypto-epaper'))" 2>/dev/null || echo "crypto-epaper")
AP_PASS=$(python3 -c "import json; d=json.load(open('$CONFIG')); print(d.get('ap_pass','bitcoin123'))" 2>/dev/null || echo "bitcoin123")

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') -- $*" >> "$LOG"; }

is_connected() {
    ping -c 2 -W 3 8.8.8.8 > /dev/null 2>&1
}

connected_to_hotspot() {
    iwgetid -r 2>/dev/null | grep -qF "$AP_SSID"
}

reconnect_saved() {
    log "Trying to reconnect saved Wi-Fi..."
    nmcli radio wifi off && sleep 2 && nmcli radio wifi on
    sleep 15
}

connect_hotspot() {
    log "Connecting to fallback hotspot '$AP_SSID'..."

    # Remove old connection entry if exists
    nmcli connection delete "$AP_SSID" 2>/dev/null || true

    # Connect to hotspot
    nmcli device wifi connect "$AP_SSID" password "$AP_PASS" >> "$LOG" 2>&1
    sleep 5

    if connected_to_hotspot; then
        log "Connected to hotspot '$AP_SSID'"
        log "Access the dashboard at http://crypto-epaper.local:8080"
    else
        log "Failed to connect to hotspot '$AP_SSID' — make sure it is active"
    fi
}

# ── Main logic ────────────────────────────────────────────────────────────────

if is_connected; then
    # Online — nothing to do
    if connected_to_hotspot; then
        log "Connected via hotspot '$AP_SSID' — internet is available"
    fi
    exit 0
fi

# Offline
if connected_to_hotspot; then
    log "Connected to hotspot '$AP_SSID' but no internet — waiting for user to configure Wi-Fi"
    exit 0
fi

# Not connected at all — try saved network first
reconnect_saved

if is_connected; then
    log "Reconnected to saved Wi-Fi successfully"
    exit 0
fi

# Saved network failed — fall back to hotspot
connect_hotspot
