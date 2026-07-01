#!/usr/bin/env bash
# jetson_claude_setup.sh — gör Jetsonen redo att köra Claude Code lokalt mot woody.
#
# Installerar git + tmux + Claude Code, klonar/checkar ut repot och startar en
# KVARLEVANDE tmux-session som kör `claude --remote-control` i repot — sessionen
# kör LOKALT på Jetsonen (rör hårdvaran) men går att styra från Claude-appen
# (iOS/Android) och claude.ai/code. Idempotent: kör om utan att förstöra något.
#
# Kör på den FYSISKA Jetsonen (aarch64 / JetPack 6.x, Ubuntu 22.04):
#     bash tools/jetson_claude_setup.sh
#
# Flaggor:
#   --tailscale     installera Tailscale (extra: rå SSH-terminal var som helst —
#                   behövs INTE för app-styrning, Remote Control räcker)
#   --no-launch     gör allt UTOM att starta tmux-sessionen (skriv bara ut nästa steg)
#   --name=NAMN     sessionsnamn i appen/claude.ai/code (default: woody-jetson)
#   --branch=NAMN   branch att checka ut (default: claude/stoic-newton-CMsDC)
set -euo pipefail

REPO_URL="https://github.com/robinandreeklund-collab/woody.git"
BRANCH="claude/stoic-newton-CMsDC"
REPO_DIR="$HOME/woody"
RC_NAME="woody-jetson"
DO_TAILSCALE=0
DO_LAUNCH=1

log()  { printf '\033[1;36m[claude-setup]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[claude-setup]\033[0m %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

for a in "$@"; do
  case "$a" in
    --tailscale) DO_TAILSCALE=1 ;;
    --no-launch) DO_LAUNCH=0 ;;
    --name=*)    RC_NAME="${a#*=}" ;;
    --branch=*)  BRANCH="${a#*=}" ;;
    *) echo "okänd flagga: $a (se kommentarshuvudet)"; exit 2 ;;
  esac
done

# ---------------------------------------------------------------- 1. apt-deps
if have apt-get; then
  log "Installerar git + tmux + curl (sudo) ..."
  sudo apt-get update -y
  sudo apt-get install -y git tmux curl
else
  warn "apt-get saknas — installera git/tmux/curl manuellt (ej Ubuntu/Jetson?)"
fi

# ---------------------------------------------------------------- 2. Claude Code
if have claude; then
  log "Claude Code redan installerat ($(claude --version 2>/dev/null || echo okänd version))"
else
  log "Installerar Claude Code (native installer) ..."
  curl -fsSL https://claude.ai/install.sh | bash
fi
# se till att claude hittas nu OCH i framtida skal
export PATH="$HOME/.local/bin:$PATH"
if ! grep -q '/.local/bin' "$HOME/.bashrc" 2>/dev/null; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
fi
have claude && log "claude: $(claude --version 2>/dev/null || echo installerat) (Remote Control kräver ≥ v2.1.51)" \
            || warn "claude hittades inte i PATH — öppna nytt skal och kör 'claude --version'"

# ---------------------------------------------------------------- 3. Tailscale (valfritt, ej nödvändigt)
if [ "$DO_TAILSCALE" = 1 ]; then
  if have tailscale; then
    log "Tailscale redan installerat"
  else
    log "Installerar Tailscale (extra — Remote Control behöver det INTE) ..."
    curl -fsSL https://tailscale.com/install.sh | sh
  fi
  warn "Kör sedan:  sudo tailscale up   (följ URL:en för att para ihop Jetsonen)"
fi

# ---------------------------------------------------------------- 4. klona/checka ut repot
if [ -d "$REPO_DIR/.git" ]; then
  log "Repo finns: $REPO_DIR"
else
  log "Klonar repot → $REPO_DIR"
  git clone "$REPO_URL" "$REPO_DIR"
fi
cd "$REPO_DIR"
log "Hämtar + checkar ut branch: $BRANCH"
git fetch origin "$BRANCH" 2>/dev/null || warn "kunde inte hämta $BRANCH (offline?) — fortsätter"
git checkout "$BRANCH" 2>/dev/null \
  || git checkout -b "$BRANCH" --track "origin/$BRANCH" 2>/dev/null \
  || warn "kunde inte checka ut $BRANCH — gör det manuellt"

# ---------------------------------------------------------------- 5. starta Remote Control-session
log "KLART. Repo: $REPO_DIR  ·  branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
warn "Första gången: inne i sessionen, kör /login (claude.ai — EJ API-nyckel) om du inte loggat in."
warn "Öppna sessionen i appen: scanna QR (välj indikatorn → Enter) eller hitta '$RC_NAME' under Code på claude.ai/code."
if [ "$DO_LAUNCH" = 1 ] && [ -t 1 ] && have tmux && have claude; then
  log "Startar kvarlevande tmux-session 'woody' med Remote Control (Ctrl-b d = koppla loss) ..."
  if tmux has-session -t woody 2>/dev/null; then
    exec tmux attach -t woody
  fi
  exec tmux new -s woody "cd '$REPO_DIR' && claude --remote-control --name '$RC_NAME'; exec bash"
else
  echo
  echo "Nästa steg (kör manuellt):"
  echo "    tmux new -s woody                                  # kvarlevande session"
  echo "    cd $REPO_DIR && claude --remote-control --name '$RC_NAME'"
  echo "    # koppla loss: Ctrl-b d   ·   återanslut: tmux attach -t woody"
  echo "    # styr sedan från Claude-appen (Code) eller claude.ai/code"
fi
