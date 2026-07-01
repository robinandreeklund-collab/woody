# Driftsättning på Jetson Orin Nano Super (Fas 5)

Kör VIRKE-kontrollsystemet som ett **kiosk-program** på bänkpanelen, autostartat.

## 1. Installera
```bash
sudo mkdir -p /opt/woody && sudo chown $USER /opt/woody
git clone <repo> /opt/woody && cd /opt/woody
python3 -m venv .venv && .venv/bin/pip install -r app/requirements.txt
# hårdvara (verkligt läge):
.venv/bin/pip install -r app/requirements-hw.txt
```
Se **[`../../docs/jetson-setup.md`](../../docs/jetson-setup.md)** för kamera-drivrutiner
(MVS/Aravis), USB3/GigE-inställningar (usbfs_memory_mb, jumbo frames) och GenICam-CTI.

## 2. Testa hårdvaran (bring-up)
```bash
.venv/bin/python -m app.main --mode real --probe
```
Skriver en anslutningsrapport per enhet (profilkameror, ytkamera, 3× LR400, transportör).

## 3. Kalibrera
Kör kalibreringsflödena (se fliken **Kalibrering**): kamera-intrinsics,
trianguleringsplan, punktlaser-nollning, ytkamera-vitbalans, matnings-encoder.
Värdena lagras i config och används av behandlingspipelinen.

## 4. Autostart (systemd)
```bash
sudo cp app/deploy/woody-kontrollsystem.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now woody-kontrollsystem
journalctl -u woody-kontrollsystem -f      # loggar
```
Servicefilen kör helskärm via `QT_QPA_PLATFORM=eglfs` (direkt på GPU, ingen
fönsterhanterare). Avkommentera `GENICAM_CTI` så den pekar på din CTI-fil.

## Lägen / felsökning
- **Simulering på vilken dator som helst:** `python -m app.main` (fönster).
- **Kiosk på bänken:** servicen ovan, eller `python -m app.main --mode real --fullscreen`.
- **Loggdata:** `data/woody.db` (SQLite) + CSV-export från Logg-vyn.
- "Hänger den?" — förvärv körs drop-safe; se `tools/verify_jetson_io.py` för I/O-budget.
