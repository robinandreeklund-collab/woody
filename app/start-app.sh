#!/usr/bin/env bash
# Startar VIRKE-huvudprogrammet (PySide6 + QML) i simuleringsläge.
# Kör:  ./app/start-app.sh        (lägg till --fullscreen för kiosk)
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"
python3 -m pip install -q -r app/requirements.txt
exec python3 -m app.main "$@"
