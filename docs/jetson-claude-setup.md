# Köra Claude Code lokalt på Jetsonen — steg för steg

Mål: få Claude Code att jobba **lokalt på Jetsonen** (så den kan röra kameror,
RoboClaw, GPIO, LR400) och kunna nå den från mobilen. Förutsättning: Jetsonen är
flashad med JetPack 6.x (Ubuntu 22.04, aarch64) på NVMe och har internet.

## Snabbast: ett kommando
```bash
# 1) hämta bara setup-scriptet (om repot inte är klonat än) och kör det
curl -fsSL https://raw.githubusercontent.com/robinandreeklund-collab/woody/claude/stoic-newton-CMsDC/tools/jetson_claude_setup.sh -o /tmp/jcs.sh
bash /tmp/jcs.sh --tailscale
```
Scriptet installerar git + tmux + Claude Code (+ Tailscale med `--tailscale`),
klonar/checkar ut repot och startar en kvarlevande `tmux`-session som kör `claude`
i `~/woody`. Är repot redan klonat: `bash tools/jetson_claude_setup.sh`.

## Manuellt (samma sak, steg för steg)

### 1. Git + grundverktyg
```bash
sudo apt-get update
sudo apt-get install -y git tmux curl
```

### 2. Klona repot + rätt branch
```bash
cd ~
git clone https://github.com/robinandreeklund-collab/woody.git
cd ~/woody
git checkout claude/stoic-newton-CMsDC
```

### 3. Installera Claude Code (native installer, arm64)
```bash
curl -fsSL https://claude.ai/install.sh | bash
exec $SHELL          # nytt skal så ~/.local/bin hamnar i PATH
claude --version     # verifiera
claude doctor        # djupare hälsokoll (valfritt)
```
> Kräver Pro/Max/Team/Enterprise-konto — gratis-planen ger inte Claude Code.

### 4. Kör Claude i repot
```bash
cd ~/woody
claude               # första gången: följ /login → öppna URL i webbläsaren, klistra tillbaka koden
```
Claude läser `CLAUDE.md` automatiskt. Säkerheten är förinställd
(`.claude/settings.json` kräver bekräftelse för sudo/push; lasrarna tänds aldrig
utan ditt OK).

### 5. (Valfritt) Nå Jetson-Claude från mobilen, var som helst
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up                       # följ URL:en för att para ihop enheten

tmux new -s woody                       # kvarlevande session
cd ~/woody && claude
#  koppla loss:  Ctrl-b  d
#  återanslut (även från mobilens SSH-app via Tailscale): tmux attach -t woody
```

## Viktigt om "Claude-appen"
Claude-appen / claude.ai (Claude Code på webben) kör i en **moln-sandbox** och når
**inte** Jetsonens fysiska hårdvara. Hårdvaru-idrifttagning (probning, GPIO,
laser-enable) måste köras på **Jetsonen** (steg 4–5 ovan).

Arbetsdelning: använd appen/webben för **kod** (planera, ändra, granska) — den
pushar till `claude/stoic-newton-CMsDC`. Jetson-Claude kör `git pull`, kör skarpt
mot hårdvaran och committar tillbaka. Branchen är bryggan mellan de två.

## Idrifttagning härnäst
När Claude kör på Jetsonen, följ `docs/jetson-prep-plan.md` §5:
```
bash tools/jetson_bootstrap.sh      # apt, venv, Aravis, pymodbus, CuPy, udev ...
python -m app                       # GUI i sim → verifiera
python tools/jetson_selftest.py     # probar varje enhet tills grön
```
