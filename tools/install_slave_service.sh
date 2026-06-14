#!/usr/bin/env bash
# Installera + aktivera woody-slave som systemd-tjänst (startar vid boot).
# Genererar unit med RÄTT sökvägar (repo + venv) och nodnamn = hostname (%H).
#
#   bash tools/install_slave_service.sh [port] [mode]
#       port  default 8765
#       mode  default real   (sim för test utan hårdvara)
#
# Avinstallera:  sudo systemctl disable --now woody-slave && sudo rm /etc/systemd/system/woody-slave.service
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO/.venv"
PY="$VENV/bin/python"
USER_NAME="$(whoami)"
PORT="${1:-8765}"
MODE="${2:-real}"
UNIT="/etc/systemd/system/woody-slave.service"

[ -x "$PY" ] || { echo "Saknar venv ($PY) — kör tools/jetson_bootstrap.sh först."; exit 1; }

TMP="$(mktemp)"
cat > "$TMP" <<EOF
[Unit]
Description=woody slave (lashuvud) - master/slave-nod
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$REPO
Environment=GENICAM_GENTL64_PATH=/opt/MVS/lib/aarch64
Environment=LD_LIBRARY_PATH=/opt/MVS/lib/aarch64
Environment=PYTHONUNBUFFERED=1
ExecStart=$PY -m app.net.slave --mode $MODE --name %H --port $PORT
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

echo "Installerar $UNIT  (hostname=$(hostname), läge=$MODE, port=$PORT)"
sudo install -m 0644 "$TMP" "$UNIT"
rm -f "$TMP"
sudo systemctl daemon-reload
sudo systemctl enable --now woody-slave.service
echo
echo "KLART — slaven startar nu + vid varje boot, auto-annonserar på LAN."
echo "Status:"; systemctl --no-pager --lines=0 status woody-slave.service | head -6 || true
echo
echo "Följ loggen:   journalctl -u woody-slave -f"
echo "Stoppa/av:     sudo systemctl disable --now woody-slave"
