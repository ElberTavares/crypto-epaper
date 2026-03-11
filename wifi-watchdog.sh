#!/bin/bash
# wifi-watchdog.sh - Auto-reconnect Wi-Fi or fall back to Access Point
# When no Wi-Fi is found, starts AP "crypto-epaper" / password "bitcoin123"
# User connects to the AP and accesses http://192.168.4.1:8080 to configure Wi-Fi
# Add to cron: */2 * * * * /usr/local/bin/wifi-watchdog.sh

LOG=/home/cripto/crypto-epaper/files/logs/wifi.log
AP_SSID="crypto-epaper"
AP_PASS="bitcoin123"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') -- $*" >> "$LOG"; }

is_connected() {
    ping -c 2 -W 3 8.8.8.8 > /dev/null 2>&1
}

ap_is_active() {
    nmcli -t -f NAME,TYPE con show --active 2>/dev/null | grep -q "wifi-ap\|$AP_SSID"
}

start_ap() {
    log "Starting Access Point '$AP_SSID'..."
    # Remove any stale AP connection first
    nmcli connection delete "$AP_SSID" 2>/dev/null || true
    nmcli connection add type wifi ifname wlan0 con-name "$AP_SSID" autoconnect no \
        ssid "$AP_SSID" \
        -- wifi-sec.key-mgmt wpa-psk \
           wifi-sec.psk "$AP_PASS" \
           ipv4.method shared \
           ipv4.addresses 192.168.4.1/24 \
           802-11-wireless.mode ap \
           802-11-wireless.band bg 2>/dev/null
    nmcli connection up "$AP_SSID" >> "$LOG" 2>&1
    log "Access Point started — connect to '$AP_SSID' and open http://192.168.4.1:8080"
}

stop_ap() {
    log "Stopping Access Point..."
    nmcli connection down "$AP_SSID" 2>/dev/null || true
    nmcli connection delete "$AP_SSID" 2>/dev/null || true
}

reconnect_wifi() {
    log "Attempting Wi-Fi reconnect..."
    nmcli radio wifi off && sleep 2 && nmcli radio wifi on
    sleep 15
}

# ── Main logic ────────────────────────────────────────────────────────────────

if is_connected; then
    # Online — if AP was running, stop it
    if ap_is_active; then
        log "Wi-Fi restored — stopping Access Point"
        stop_ap
    fi
else
    # Offline
    if ap_is_active; then
        log "Still offline — Access Point already running, waiting for user config"
    else
        log "Offline — trying Wi-Fi reconnect first..."
        reconnect_wifi
        sleep 10
        if is_connected; then
            log "Reconnected to Wi-Fi successfully"
        else
            log "Reconnect failed — starting Access Point"
            start_ap
        fi
    fi
fi
