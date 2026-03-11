#!/bin/bash
# sd_health.sh - SD card maintenance: rotate logs to reduce writes
# Add to cron: 0 3 * * * /path/to/sd_health.sh

LOG_DIR="$(cd "$(dirname "$0")" && pwd)/logs"
MAX_SIZE=512  # KB

for log in "$LOG_DIR"/*.log; do
    [ -f "$log" ] || continue
    size=$(du -k "$log" | cut -f1)
    if [ "$size" -gt "$MAX_SIZE" ]; then
        tail -n 200 "$log" > "$log.tmp" && mv "$log.tmp" "$log"
        echo "$(date) -- rotated $log (was ${size}KB)" >> "$LOG_DIR/health.log"
    fi
done
