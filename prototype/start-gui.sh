#!/usr/bin/env bash
# Startar kontrollsystem-GUI:t (control.html) i din standardwebbläsare.
# Kör:  ./prototype/start-gui.sh    (eller dubbelklicka på filen)
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAGE="$DIR/control.html"

if [ ! -f "$PAGE" ]; then
  echo "Hittar inte $PAGE" >&2
  exit 1
fi

echo "Öppnar $PAGE ..."
case "$(uname -s)" in
  Darwin*)  open "$PAGE" ;;                    # macOS
  Linux*)   xdg-open "$PAGE" >/dev/null 2>&1 || sensible-browser "$PAGE" ;;
  CYGWIN*|MINGW*|MSYS*) start "" "$PAGE" ;;     # Windows (Git Bash)
  *)        echo "Öppna manuellt i webbläsaren: $PAGE" ;;
esac
