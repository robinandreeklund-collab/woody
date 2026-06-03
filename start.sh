#!/usr/bin/env bash
# ============================================================================
# Woody – ett kommando: miljö + beroenden + bygg + (valfritt Kodytek) + GUI.
#
#   ./start.sh                      # fungerar direkt (syntetisk data)
#   ./start.sh --with-kodytek       # ladda ner + rastrera Kodytek, kör på riktig data
#   ./start.sh --with-kodytek --train   # + träna modellen lokalt (GPU via device=auto)
#   ./start.sh --port 8080
#
# Öppna sedan webbgränssnittet på den URL som skrivs ut (default http://localhost:8000).
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")"

PORT=8000
WITH_KODYTEK=0
TRAIN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --with-kodytek) WITH_KODYTEK=1 ;;
    --train) TRAIN=1 ;;
    --port) PORT="$2"; shift ;;
    *) echo "Okänt argument: $1"; exit 1 ;;
  esac
  shift
done

echo "==> 1/5  Python-miljö"
command -v python3 >/dev/null || { echo "python3 saknas"; exit 1; }
[ -d .venv ] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -q --upgrade pip
echo "    installerar Python-beroenden ..."
pip install -q -r requirements.txt -r web/backend/requirements.txt

echo "==> 2/5  Frontend (Vite-bygge)"
command -v npm >/dev/null || { echo "npm/node saknas – installera Node 18+"; exit 1; }
( cd web/frontend && npm install --no-audit --no-fund --silent && npm run build --silent )

export WOODY_KODYTEK_ROOT=""
export WOODY_CKPT="seg_unet.pt"

if [ "$WITH_KODYTEK" = "1" ]; then
  echo "==> 3/5  Kodytek-dataset (laddar ner + rastrerar – kan ta lång tid, flera GB)"
  if [ ! -d data/kodytek/images ]; then
    python tools/download_kodytek.py --out data/kodytek_raw
    python -m src.kodytek --auto data/kodytek_raw --out data/kodytek
  else
    echo "    data/kodytek finns redan – hoppar över nedladdning"
  fi
  export WOODY_KODYTEK_ROOT="data/kodytek"
else
  echo "==> 3/5  Kodytek hoppas över (kör syntetisk data). Lägg till --with-kodytek för riktig data."
fi

if [ "$TRAIN" = "1" ]; then
  echo "==> 4/5  Tränar modellen på Kodytek (device=auto plockar GPU)"
  python -c "from src.config import SegConfig; from src.train import fit; fit(SegConfig.gpu_kodytek('data/kodytek'))"
  export WOODY_CKPT="seg_kodytek.pt"
else
  echo "==> 4/5  Träning hoppas över. Lägg till --train för att träna på Kodytek."
fi

echo "==> 5/5  Startar server"
echo ""
echo "    ▶ Webbgränssnitt:  http://localhost:${PORT}"
echo "      datakälla: ${WOODY_KODYTEK_ROOT:-syntetisk}  |  modell: ${WOODY_CKPT}"
echo "      (Ctrl+C för att stoppa)"
echo ""
exec uvicorn web.backend.app:app --host 0.0.0.0 --port "$PORT"
