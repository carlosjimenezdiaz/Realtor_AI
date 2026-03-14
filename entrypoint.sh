#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────────────────────────
# Export all env vars to /etc/environment so that cron jobs can read them.
# (cron does NOT inherit the Docker runtime environment by default)
# ─────────────────────────────────────────────────────────────────────────────
printenv | grep -v "^_=" > /etc/environment

# ─────────────────────────────────────────────────────────────────────────────
# Build and install the crontab from the CRON_SCHEDULE env var.
# Default: Mon–Fri 13:00 UTC (8:00 AM EST / 9:00 AM EDT).
# ─────────────────────────────────────────────────────────────────────────────
CRON_SCHEDULE="${CRON_SCHEDULE:-0 13 * * 1-5}"

echo "Installing cron schedule: $CRON_SCHEDULE"

# Source /etc/environment so all env vars are available, then run the pipeline.
# Logs go to /app/logs/cron.log (in the mounted volume).
cat <<EOF | crontab -
SHELL=/bin/bash
$CRON_SCHEDULE . /etc/environment && cd /app && python main.py >> /app/logs/cron.log 2>&1
EOF

echo "Crontab installed:"
crontab -l

# ─────────────────────────────────────────────────────────────────────────────
# Start cron in foreground (keeps the container alive).
# ─────────────────────────────────────────────────────────────────────────────
exec cron -f
