#!/bin/bash
# wifi-watchdog.sh - Auto-reconnect Wi-Fi if connection drops
# Add to cron: */2 * * * * /usr/local/bin/wifi-watchdog.sh

LOG=/home/pi/crypto-epaper/files/logs/wifi.log

if ! ping -c 2 -W 3 8.8.8.8 > /dev/null 2>&1; then
    echo "$(date) -- offline, reconnecting..." >> "$LOG"
    ip link set wlan0 down
    sleep 3
    ip link set wlan0 up
    sleep 15
    dhclient wlan0 2>> "$LOG"
    echo "$(date) -- $(iwgetid -r || echo 'still offline')" >> "$LOG"
fi
