# VIRKE Kontrollsystem — huvudprogram (PySide6 + QML)

Det riktiga, native skrivbordsprogrammet för skannern. Ett program för allt:
hårdvara, bildbehandling, gradering, GUI. Kör på bänk-datorn (Jetson Orin Nano
Super) och i simuleringsläge på vilken dator som helst.

> Arkitektur, faser och beslut: se [`../docs/control-app-design.md`](../docs/control-app-design.md).
> Driftsättning på Jetson (kiosk/systemd): se [`deploy/README.md`](deploy/README.md).

**Status:** M0–M5 byggda. Simuleringsläget är komplett och verifierat; verkligt
hårdvaruläge har drivrutiner + probe klara (full radackumulering = sista bring-up).

## Kör

```bash
pip install -r app/requirements.txt
python -m app.main                 # simulering (standard)
python -m app.main --feed 40 --rate 600
python -m app.main --fullscreen    # kiosk på bänken
python -m app.main --mode real --probe   # testa hårdvaruanslutning
python -m app.main --mode real     # fysisk hårdvara (kräver SDK + kalibrering)
python -m app.tests.test_core      # kör testsviten
```

På Linux/Jetson krävs Qt:s GL-bibliotek (finns i JetPack; på en bar Ubuntu:
`sudo apt-get install libegl1 libgl1 libxkbcommon0 libfontconfig1`).
Hårdvaruberoenden (verkligt läge): `pip install -r app/requirements-hw.txt`.

## Vyer
- **Översikt** — ytkamera + höjdkarta (rätt proportion, reveal), tvärsnitt Z(x),
  profilkameror rå-stripe (röd/grön m. ocklusion), **rigg ovanifrån** (laserlinjen
  längs 500 mm-långsidan), LR400-tjocklek, gradering, defekter.
- **Sensorer** — live-telemetri per sensor mot databladsspec.
- **Logg** — bräd-historik (SQLite) + CSV-export.
- **Kalibrering** — riggens geometri + kalibreringsflöden (Fas 3).

## Vad finns i M0
- **`geometry/rig.py`** — EN sanningskälla för riggens geometri (WD 710, kamera-arm
  20°, laser-arm 40°, θ 30°, ytkamera i centrum 400 mm, bräda 500×75×20). Samma tal
  som `head-mech.svg` → GUI och ritning kan inte säga emot varandra. Fixar
  proportions- och ytkamera-buggarna på rätt nivå.
- **HAL** (`hal/`) — gränssnitt per enhet med **sim**-backend (numpy-fysik,
  databladstakter) och plats för **real**-backend (MVS/Aravis/Modbus/Jrk i Fas 4).
- **Behandling** (`processing/grade.py`) — gradering till klass A/B/C/Vrak.
- **GUI** (`ui/qml/Main.qml`) — modern, animerad Qt Quick-yta: ytkamera i rätt
  proportion med skann-reveal, live-tvärsnitt Z(x), 3× LR400-tjocklek, gradering,
  defektlista, matnings-/profiltakts-reglage.

## Struktur
```
app/
  main.py            entry (--mode sim|real, --fullscreen)
  core/              config, körtidstillstånd, AppController (QObject, 60 Hz)
  geometry/rig.py    riggens geometri (sanningskälla)
  hal/               base (ABC) · sim/ (numpy) · real/ (Fas 4) · factory
  processing/        gradering (mät/tri/yta-pipeline byggs i M2)
  ui/                QML + numpy→QImage-leverantör
```

## Nästa steg (ur designdokumentet)
M1 full dashboard-paritet · M2 mät-/graderingspipeline · M3 kalibrering ·
M4 verklig hårdvara på Jetson · M5 driftsättning.
