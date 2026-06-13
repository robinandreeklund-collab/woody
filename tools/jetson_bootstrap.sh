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

# ---------------------------------------------------------------- root-strategi
# Stegen apt/udev/usbfs/nvpmodel KRÄVER root (OS-design — går ej att göra utan).
# Men vi vägrar BLOCKERA på en interaktiv lösenordsprompt: går det inte att bli
# root utan prompt skjuter vi upp de stegen till ett skript du kör en gång:
#     sudo bash tools/jetson_root_steps.sh
# Allt annat (venv, pip, CuPy, Jetson.GPIO, verifierare) körs utan sudo direkt.
ROOT_SH="$REPO/tools/jetson_root_steps.sh"
ROOT_STEPS=()
if [ "$(id -u)" = 0 ]; then
  ROOT_MODE="run"          # redan root
elif have sudo && sudo -n true 2>/dev/null; then
  ROOT_MODE="sudo"         # icke-interaktiv (lösenordsfri) sudo funkar
else
  ROOT_MODE="defer"        # ingen tyst root → samla stegen i ROOT_SH
fi
asroot() {  # kör ett kommando som root, eller skjut upp det till ROOT_SH
  case "$ROOT_MODE" in
    run)   "$@" ;;
    sudo)  sudo "$@" ;;
    defer) ROOT_STEPS+=("$(printf '%q ' "$@")") ;;
  esac
}
case "$ROOT_MODE" in
  run)   log "Root-läge: kör root-steg direkt (du är root)." ;;
  sudo)  log "Root-läge: lösenordsfri sudo — kör root-steg inline." ;;
  defer) warn "Root-läge: ingen tyst sudo — root-steg skjuts upp till $ROOT_SH (kör det en gång efteråt)." ;;
esac

# ---------------------------------------------------------------- 0. sanity
if [ "$(uname -m)" != "aarch64" ]; then
  warn "Inte aarch64 — du kör inte på Jetsonen. Fortsätter ändå (dev-läge)."
fi
log "Repo: $REPO"

# ---------------------------------------------------------------- 1. apt-deps
APT_PKGS=(
  python3-venv python3-pip python3-dev build-essential pkg-config
  git curl
  aravis-tools libaravis-dev gir1.2-aravis-0.8         # GenICam GigE + USB3 Vision
  libgirepository1.0-dev python3-gi                    # gobject-introspection (Aravis py)
  v4l-utils usbutils net-tools                          # diagnostik (lsusb, ethtool)
)
if have apt-get; then
  log "Installerar apt-paket (root) ..."
  asroot apt-get update -y || warn "apt-get update flaggade — fortsätter"
  # Försök batch-installera; faller tillbaka till per-paket så ETT saknat namn
  # inte blockerar resten (apt installerar inget alls om ett glob ej hittas).
  if ! asroot apt-get install -y "${APT_PKGS[@]}"; then
    warn "batch-install föll — försöker paket för paket"
    for p in "${APT_PKGS[@]}"; do
      asroot apt-get install -y "$p" || warn "  hoppar saknat paket: $p"
    done
  fi
else
  warn "apt-get saknas — hoppar OS-paket (ej Ubuntu/Jetson?)"
fi

# ---------------------------------------------------------------- 2. python-venv
# venv kräver python3-venv (ett apt/root-paket). Om root-stegen ännu inte körts
# (defer-läge) kan venv inte skapas — då hoppar vi pip+verifiering snyggt och ber
# dig köra root-stegen först. Skriptet ska ALDRIG krascha på det.
VENV_OK=1
if [ ! -d "$VENV" ]; then
  log "Skapar venv: $VENV (--system-site-packages för Jetson.GPIO/CUDA)"
  if ! python3 -m venv --system-site-packages "$VENV" 2>&1; then
    VENV_OK=0
    rm -rf "$VENV"   # städa halvskapad venv
    warn "Kunde inte skapa venv — python3-venv saknas (installeras av root-stegen)."
  fi
fi

if [ "$VENV_OK" = 1 ]; then
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  python -m pip install --upgrade pip wheel setuptools

  log "Installerar python-paket ..."
  PY_PKGS=(
    numpy scipy opencv-python-headless
    PySide6
    harvesters            # GenICam-API (appens cameras.py)
    pyserial              # RoboClaw packet serial
    pymodbus              # 3× LR400 över RS-485 (Waveshare 4CH)
  )
  python -m pip install "${PY_PKGS[@]}" || warn "några python-paket föll bort — se ovan"

  # Jetson.GPIO endast på riktig Jetson (annars no-op)
  if [ "$(uname -m)" = "aarch64" ]; then
    python -m pip install Jetson.GPIO || warn "Jetson.GPIO kunde inte installeras"
    # CuPy för GPU-stripe-extraktion (keep-up @ 60 fps). Måste matcha JetPacks CUDA.
    log "Försöker installera CuPy (GPU-stripe). Matcha JetPacks CUDA-version vid behov."
    python -c "import cupy" 2>/dev/null && log "CuPy redan installerat" || \
      python -m pip install cupy-cuda12x || \
      warn "CuPy ej installerat — bygg mot JetPacks CUDA (se NVIDIA-forum) eller kör VPI; CPU-fallback funkar men når ej full-frame 60 fps"
  fi
else
  warn "Hoppar pip-installation (ingen venv) — kör root-stegen och kör om bootstrap."
fi

# Repo-beroenden om requirements finns
if [ "$VENV_OK" = 1 ] && [ -f "$REPO/requirements.txt" ]; then
  python -m pip install -r "$REPO/requirements.txt" || warn "requirements.txt delvis"
fi

# ---------------------------------------------------------------- 3. usbfs-gräns (USB3-kameror)
USBFS_LINE="usbcore.usbfs_memory_mb=1000"
log "Sätter usbfs_memory_mb=1000 temporärt (mot tappade USB3-ramar)"
asroot sh -c 'echo 1000 > /sys/module/usbcore/parameters/usbfs_memory_mb' \
  || warn "kunde inte sätta usbfs temporärt"
warn "PERMANENT: lägg till '$USBFS_LINE' i extlinux.conf APPEND-raden och boota om."

# ---------------------------------------------------------------- 4. udev-regler (stabila enhetsnamn + rättigheter)
UDEV=/etc/udev/rules.d/99-woody.rules
if have udevadm; then
  log "Förbereder udev-regler: $UDEV"
  # Skriv regelinnehållet till en repo-fil UTAN root; installera den sen som root.
  RULES_SRC="$REPO/tools/99-woody.rules"
  cat > "$RULES_SRC" <<'RULES'
# RoboClaw 2x7A (USB ACM) — läs/skriv utan sudo + stabil symlänk /dev/roboclaw
SUBSYSTEM=="tty", ATTRS{idVendor}=="03eb", MODE="0666", SYMLINK+="roboclaw"
# Generisk: ge dialout åtkomst till alla ACM/USB-serieportar
KERNEL=="ttyACM[0-9]*", MODE="0666", GROUP="dialout"
KERNEL=="ttyUSB[0-9]*", MODE="0666", GROUP="dialout"
RULES
  asroot cp "$RULES_SRC" "$UDEV"
  asroot udevadm control --reload-rules
  asroot udevadm trigger
  asroot usermod -aG dialout "$USER"
  warn "Logga ut/in för att få dialout-gruppen (åtkomst till /dev/ttyACM*)."
else
  warn "udevadm saknas — hoppar udev-regler"
fi

# ---------------------------------------------------------------- 5. prestanda-läge
if have nvpmodel; then
  log "Sätter MAXN ström-läge + jetson_clocks"
  asroot nvpmodel -m 0 || warn "nvpmodel: kunde inte sätta MAXN"
  asroot jetson_clocks || warn "jetson_clocks misslyckades"
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

# ---------------------------------------------------------------- 6b. uppskjutna root-steg
if [ "$ROOT_MODE" = "defer" ] && [ "${#ROOT_STEPS[@]}" -gt 0 ]; then
  {
    echo '#!/usr/bin/env bash'
    echo '# Auto-genererad av jetson_bootstrap.sh — root-steg som krävde sudo.'
    echo '# Kör EN gång:  sudo bash tools/jetson_root_steps.sh'
    echo 'set -e'
    for step in "${ROOT_STEPS[@]}"; do echo "$step"; done
  } > "$ROOT_SH"
  chmod +x "$ROOT_SH"
  warn "──────────────────────────────────────────────────────────────"
  warn "Root-steg uppskjutna (kräver sudo). Kör EN gång:"
  warn "    sudo bash $ROOT_SH"
  warn "──────────────────────────────────────────────────────────────"
fi

# ---------------------------------------------------------------- 7. verifiering
if [ "$VENV_OK" = 1 ]; then
  log "Kör appens egna verifierare ..."
  ( cd "$REPO" && python tools/verify_jetson_io.py ) || warn "verify_jetson_io flaggade (ok utan hw)"
  log "Profilerar stripe-extraktion (keep-up @ 60 fps) ..."
  ( cd "$REPO" && python tools/profile_stripe.py ) || warn "profile_stripe flaggade"
fi

if [ "$VENV_OK" != 1 ]; then
  log "DELVIS KLART — venv saknas (root-steg ej körda än). Gör så här:"
  echo "    sudo bash $ROOT_SH      # installerar apt-deps (python3-venv m.m.) + udev/usbfs/MAXN"
  echo "    bash tools/jetson_bootstrap.sh   # kör om — nu skapas venv + pip-paket"
else
  log "KLART. Nästa steg:"
  [ "$ROOT_MODE" = "defer" ] && echo "    sudo bash $ROOT_SH                 # (om ej kört) udev/usbfs/MAXN"
  echo "    source $VENV/bin/activate"
  echo "    python tools/jetson_selftest.py   # probar varje enhet"
  echo "    python -m app                      # appen i sim-läge"
fi
