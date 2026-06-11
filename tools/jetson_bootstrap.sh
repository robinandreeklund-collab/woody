#!/usr/bin/env bash
# Jetson-bootstrap — gör Jetsonen mjukvaruklar för woody-riggen (idempotent).
#
# Kör på den FYSISKA Jetsonen (aarch64 / JetPack 6.x):
#     bash tools/jetson_bootstrap.sh
#
# Installerar allt som går att förbereda UTAN att fältmaskinvaran är inkopplad:
# OS-deps, Python-venv + paket, Aravis (GenICam GigE+USB3), udev-regler,
# usbfs-minnesgräns. Hikrobot MVS SDK kräver manuell nedladdning — vi skriver ut steg.
#
# Säker att köra om: hoppar över det som redan finns. Inget fältberoende krävs.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO/.venv"
log()  { printf '\033[1;36m[bootstrap]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[bootstrap]\033[0m %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

# ---------------------------------------------------------------- 0. sanity
if [ "$(uname -m)" != "aarch64" ]; then
  warn "Inte aarch64 — du kör inte på Jetsonen. Fortsätter ändå (dev-läge)."
fi
log "Repo: $REPO"

# ---------------------------------------------------------------- 1. apt-deps
APT_PKGS=(
  python3-venv python3-pip python3-dev build-essential pkg-config
  git curl
  aravis-tools libaravis-0.8-dev gir1.2-aravis-0.8     # GenICam GigE + USB3 Vision
  libgirepository1.0-dev python3-gi                    # gobject-introspection (Aravis py)
  v4l-utils usbutils net-tools                          # diagnostik (lsusb, ethtool)
)
if have apt-get; then
  log "Installerar apt-paket (sudo) ..."
  sudo apt-get update -y
  sudo apt-get install -y "${APT_PKGS[@]}" || warn "några apt-paket saknades — fortsätter"
else
  warn "apt-get saknas — hoppar OS-paket (ej Ubuntu/Jetson?)"
fi

# ---------------------------------------------------------------- 2. python-venv
if [ ! -d "$VENV" ]; then
  log "Skapar venv: $VENV (--system-site-packages för Jetson.GPIO/CUDA)"
  python3 -m venv --system-site-packages "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -m pip install --upgrade pip wheel setuptools

log "Installerar python-paket ..."
PY_PKGS=(
  numpy scipy opencv-python-headless
  PySide6
  harvesters            # GenICam-API (appens cameras.py)
  pyserial              # RoboClaw packet serial
)
python -m pip install "${PY_PKGS[@]}" || warn "några python-paket föll bort — se ovan"

# Jetson.GPIO endast på riktig Jetson (annars no-op)
if [ "$(uname -m)" = "aarch64" ]; then
  python -m pip install Jetson.GPIO || warn "Jetson.GPIO kunde inte installeras"
fi

# Repo-beroenden om requirements finns
if [ -f "$REPO/requirements.txt" ]; then
  python -m pip install -r "$REPO/requirements.txt" || warn "requirements.txt delvis"
fi

# ---------------------------------------------------------------- 3. usbfs-gräns (USB3-kameror)
USBFS_LINE="usbcore.usbfs_memory_mb=1000"
log "Sätter usbfs_memory_mb=1000 temporärt (mot tappade USB3-ramar)"
sudo sh -c 'echo 1000 > /sys/module/usbcore/parameters/usbfs_memory_mb' 2>/dev/null \
  || warn "kunde inte sätta usbfs temporärt (kör som sudo på Jetson)"
warn "PERMANENT: lägg till '$USBFS_LINE' i extlinux.conf APPEND-raden och boota om."

# ---------------------------------------------------------------- 4. udev-regler (stabila enhetsnamn + rättigheter)
UDEV=/etc/udev/rules.d/99-woody.rules
if have udevadm; then
  log "Skriver udev-regler: $UDEV"
  sudo tee "$UDEV" >/dev/null <<'RULES'
# RoboClaw 2x7A (USB ACM) — läs/skriv utan sudo + stabil symlänk /dev/roboclaw
SUBSYSTEM=="tty", ATTRS{idVendor}=="03eb", MODE="0666", SYMLINK+="roboclaw"
# Generisk: ge dialout åtkomst till alla ACM/USB-serieportar
KERNEL=="ttyACM[0-9]*", MODE="0666", GROUP="dialout"
KERNEL=="ttyUSB[0-9]*", MODE="0666", GROUP="dialout"
RULES
  sudo udevadm control --reload-rules && sudo udevadm trigger || warn "udev reload misslyckades"
  sudo usermod -aG dialout "$USER" || true
  warn "Logga ut/in för att få dialout-gruppen (åtkomst till /dev/ttyACM*)."
else
  warn "udevadm saknas — hoppar udev-regler"
fi

# ---------------------------------------------------------------- 5. prestanda-läge
if have nvpmodel; then
  log "Sätter MAXN ström-läge + jetson_clocks"
  sudo nvpmodel -m 0 || warn "nvpmodel: kunde inte sätta MAXN"
  sudo jetson_clocks || warn "jetson_clocks misslyckades"
fi

# ---------------------------------------------------------------- 6. MVS SDK (manuellt steg)
cat <<EOF

$(printf '\033[1;36m[bootstrap]\033[0m') Hikrobot MVS SDK (profilkameror) — MANUELLT:
  1) Ladda ned aarch64 .deb: https://www.hikrobotics.com/en/machinevision/service/download/
  2) sudo dpkg -i MVS-*aarch64.deb
  3) Lägg i ~/.bashrc:  export GENICAM_GENTL64_PATH=/opt/MVS/lib/aarch64
     (eller peka vår app:  export GENICAM_CTI=/opt/MVS/lib/aarch64/MvProducerU3V.cti)
  Aravis funkar som reserv för BÅDE profil- (USB3) och linjekameran (GigE) utan MVS.

EOF

# ---------------------------------------------------------------- 7. verifiering
log "Kör appens egna verifierare ..."
( cd "$REPO" && python tools/verify_jetson_io.py ) || warn "verify_jetson_io flaggade (ok utan hw)"

log "KLART. Nästa steg:"
echo "    source $VENV/bin/activate"
echo "    python tools/jetson_selftest.py   # probar varje enhet"
echo "    python -m app                      # appen i sim-läge"
