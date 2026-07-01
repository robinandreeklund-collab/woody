# Köra Claude Code lokalt på Jetsonen — steg för steg

Mål: få Claude Code att jobba **lokalt på Jetsonen** (så den kan röra kameror,
RoboClaw, GPIO, LR400) **och** kunna styra den från Claude-appen (iOS/Android)
eller claude.ai/code. Det går via **Remote Control** — sessionen kör hela tiden
lokalt på Jetsonen, appen/webben är bara ett fönster in i den. Förutsättning:
Jetsonen är flashad med JetPack 6.x (Ubuntu 22.04, aarch64) på NVMe och har internet.

## Snabbast: ett kommando
```bash
# hämta setup-scriptet (om repot inte är klonat än) och kör det
curl -fsSL https://raw.githubusercontent.com/robinandreeklund-collab/woody/claude/stoic-newton-CMsDC/tools/jetson_claude_setup.sh -o /tmp/jcs.sh
bash /tmp/jcs.sh
```
Scriptet installerar git + tmux + Claude Code, klonar/checkar ut repot och startar
en kvarlevande `tmux`-session som kör `claude --remote-control --name woody-jetson`
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
claude --version     # verifiera — Remote Control kräver ≥ v2.1.51
claude doctor        # djupare hälsokoll (valfritt)
```
> Kräver Pro/Max/Team/Enterprise-konto via **claude.ai-inloggning** (ej API-nyckel) —
> gratis-planen ger inte Claude Code. På Team/Enterprise måste admin slå på
> Remote Control-toggeln i claude.ai/admin-settings/claude-code.

### 4. Kör Claude i repot med Remote Control
```bash
cd ~/woody
tmux new -s woody                                   # kvarlevande (överlever SSH-frånkoppling)
claude --remote-control --name woody-jetson         # = claude --rc
#  första gången: följ /login (claude.ai), acceptera workspace-trust
#  koppla loss tmux: Ctrl-b d   ·   återanslut: tmux attach -t woody
```
Sessionen kör **lokalt på Jetsonen** (rör hårdvaran) och registrerar sig hos
Anthropic API. Claude läser `CLAUDE.md` automatiskt; säkerheten är förinställd
(`.claude/settings.json` kräver bekräftelse för sudo/push; lasrarna tänds aldrig
utan ditt OK).

> Tre sätt att starta: `claude --remote-control` (interaktivt + fjärr, kan skriva
> både lokalt och i appen), `claude remote-control` (serverläge, väntar bara på
> fjärranslutning), eller `/remote-control` (`/rc`) inifrån en pågående session.

### 5. Öppna sessionen i Claude-appen / claude.ai/code
- **Scanna QR-koden**: markera Remote Control-indikatorn i terminalen (pil ned →
  Enter) för att visa URL + QR, eller i serverläge tryck **mellanslag**.
- **Eller** öppna appen → fliken **Code** → välj `woody-jetson` (dator-ikon, grön
  prick = online). Samma på claude.ai/code.
- Konversationen synkar åt båda håll — skriv från Jetson-terminalen, mobilen eller
  webben om vartannat.

### 6. (Valfritt) Push-notiser till mobilen
```bash
# i sessionen:  /config  → slå på "Push when Claude decides"
```
Då pingar Claude din telefon när en lång körning är klar eller den behöver ett
beslut. Du kan be om det i prompten: "notify me when the tests finish". Kräver
appen installerad + inloggad med samma konto (v2.1.110+).

## Remote Control vs Claude Code på webben
Båda använder samma gränssnitt (claude.ai/code + appen), men **var** sessionen kör
skiljer dem åt:

| | Var Claude kör | Når Jetson-hårdvaran? |
|---|---|---|
| **Remote Control** (`claude --rc` på Jetsonen) | **lokalt på Jetsonen** | **Ja** — appen är ett fönster in i den lokala sessionen |
| **Claude Code på webben** (starta i appen) | Anthropic moln-sandbox | Nej — klonar bara repot i molnet |

Så: **Remote Control = rätt verktyg för idrifttagning** (du styr den hårdvaru-
rörande Jetson-sessionen från mobilen). Webb-sessioner (som denna) är bra för
**ren kod** — de pushar till `claude/stoic-newton-CMsDC`, och Jetson-sessionen
drar ner och kör skarpt.

### Bra att veta
- **Inga inkommande portar** öppnas — bara utgående HTTPS till Anthropic API. Därför
  behövs *ingen* Tailscale/portforward för app-styrning (`--tailscale` i scriptet är
  bara extra för rå SSH-terminal).
- **Processen måste leva** — stänger du `claude`-processen dör sessionen. Därför tmux.
- Nätbortfall > ~10 min → sessionen timeout:ar; kör `claude --remote-control` igen.

## Idrifttagning härnäst
När Claude kör på Jetsonen, följ `docs/jetson-prep-plan.md` §5:
```
bash tools/jetson_bootstrap.sh      # apt, venv, Aravis, pymodbus, CuPy, udev ...
python -m app                       # GUI i sim → verifiera
python tools/jetson_selftest.py     # probar varje enhet tills grön
```
