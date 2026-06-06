# VIRKE — Kontrollsystem: arkitektur & teknikförslag

> Komplett analys och förslag för det **riktiga huvudprogrammet** — ett native
> skrivbordsprogram som kör på bänk-datorn (Jetson Orin Nano Super) och är *enda*
> programmet för hela skannern: hårdvara, bildbehandling, gradering, GUI, loggning
> och kalibrering. Ersätter `prototype/control.html` (en proof-of-concept-skiss).

Datum: 2026-06-06 · Status: **förslag, inväntar beslut om teknikstack**

---

## 1. Varför vi byter spår (ärlig problembild)

`control.html` byggdes som en snabb proof-of-concept: **en** handritad canvas-loop
utan layoutmotor, utan riktiga enheter, utan riktig diagram-/bildmotor. Det räckte
för att visa idén men slår i taket direkt:

| Problem du såg | Grundorsak | Går inte att patcha bort |
|---|---|---|
| Brädans proportioner fel (500×75 ritas som hög stående planka) | Pixlar placeras "på ögat", inget riktigt koordinatsystem mm→px | Varje vy skulle behöva egen manuell skala |
| Ytkameran sitter fel mot `head-mech.svg` | Riggens geometri är inte modellerad — bara dekor | Måste härledas ur samma optikmodell som ritningen |
| "2000-tals-känsla" | Ingen layoutmotor, inget designsystem, ingen GPU-accelererad scen-graf | Webcanvas ger aldrig native-känsla på en bänkpanel |
| Risk för hack/glapp vid riktig data | Allt i en enda rAF-loop, ingen trådning, ingen backpressure | Riktiga kameror @ 60 fps + 4K-radkamera kväver en enkeltrådad loop |
| Simulering ↔ verklig hårdvara | HTML kan inte prata USB3 Vision / GigE / RS-485 / Jrk-USB | Webbläsaren har ingen åtkomst till hårdvaran |

**Slutsats:** prototypen var rätt för att *visa konceptet*, fel som *huvudprogram*.
Huvudprogrammet måste (a) prata med den fysiska hårdvaran, (b) köra tung
realtids-bildbehandling utan glapp, och (c) ha ett native, modernt, animerat GUI.
Det pekar entydigt mot ett riktigt skrivbordsprogram.

---

## 2. Krav på huvudprogrammet

### Funktionella
- **Hårdvarustyrning:** 2× Hikrobot MV-CS050-10UM (USB3 Vision, mono, 650/520-bandpass),
  1× Huateng 4K färg-radkamera (GigE Vision), 3× LR400 punktlaser (RS-485/Modbus),
  2× Pololu Jrk G2 (transportör, USB), linjelasrar (på/av/effekt), belysning.
- **Förvärv (acquisition):** strömma bilder i full takt utan tappade ramar.
- **Bildbehandling:** subpixel-laserstripe → triangulering → höjdprofil/3D · färgyta →
  defektdetektion (kvist, vankant, spricka, blånad, röta, hål) · punktlaser-fusion
  (absolut tjocklek) · gradering (klass A/B/C/Vrak enligt regelverk).
- **GUI:** översikt (live rigg/yta/tvärsnitt/3D), sensorvy (telemetri), kalibrering,
  bräd-logg/historik, inställningar. Modernt, animerat, **rätt proportioner & enheter**.
- **Drift:** simuleringsläge (utvecklas/demas nu) och verkligt läge (samma GUI) —
  väljs i config/CLI.
- **Persistens:** per bräda sparas mätdata, bilder, defekter, klass → sökbar historik + export.
- **Kalibrering:** kamera-intrinsics, trianguleringsplan, punktlaser-nollning, sparas till disk.

### Icke-funktionella
- **Realtid utan glapp:** 60 fps GUI, förvärv i egna trådar, backpressure (släpp hellre
  ram än hänger). Detta var ett uttryckligt krav.
- **Kör på Jetson Orin Nano Super** (ARM64, Ubuntu/JetPack, Ampere-GPU/CUDA).
- **Robust:** watchdog, felhantering, återanslutning av enheter, tydliga larm.
- **En kodbas, ett språk** — vi har redan all fysik/sim i Python (`src/`), och alla
  hårdvaru-SDK:er är Python-vänliga.

---

## 3. Teknikval — analys

| Stack | Modernt GUI | Hårdvara på Jetson | Realtid/perf | Dev-fart (vår kodbas) | Native bänk-känsla | Omdöme |
|---|---|---|---|---|---|---|
| **PySide6 + QML (Qt Quick)** | ★★★★★ GPU scen-graf, shaders, animationer | ★★★★★ Qt + Python-SDK:er | ★★★★ trådar + numpy/CUDA | ★★★★★ Python end-to-end | ★★★★★ | **Rekommenderas** |
| PySide6 Widgets + PyQtGraph | ★★★☆ funktionellt, mindre "wow" | ★★★★★ | ★★★★★ bäst på täta plottar | ★★★★★ | ★★★★ | Pragmatiskt alt. |
| C++ / Qt | ★★★★★ | ★★★★★ | ★★★★★ | ★★ (skriv om sim/CV) | ★★★★★ | Överkill nu |
| Electron (web-UI) | ★★★★★ | ★★ awkward bridge | ★★ tungt på 8 GB | ★★★ | ★★ "en webbsida igen" | Avråds |
| Tauri (Rust + webview) | ★★★★★ | ★★ bridge till Python | ★★★ | ★★ Rust + bridge | ★★★ | Avråds (hårdvarutung app) |

### Rekommendation: **PySide6 (Qt for Python) med QML/Qt Quick**
- **Modernt & animerat på riktigt:** Qt Quick renderar via en GPU scen-graf →
  äkta 60 fps, mjuka övergångar, gradient/shader-effekter. Det är så här proffsiga
  industri-HMI:er byggs. Dödar "2000-tals-känslan".
- **Native bänk-program:** eget fönster, kan köras helskärm/kiosk på pekskärm. Ingen webbläsare.
- **Hårdvara utan krångel:** Python pratar direkt med Hikrobot MVS-SDK (aarch64),
  Aravis (GigE/USB3 Vision via PyGObject), `pyserial`/`pymodbus` (LR400), Jrk G2 (USB).
- **Återanvänder allt vi har:** `src/board`, `src/hardware`, `src/laser` blir
  simuleringsbackenden rakt av. En kodbas, ett språk.
- **Realtid:** förvärv i `QThread`/processer, numpy/OpenCV (släpper GIL), CUDA/TensorRT
  på Jetson för defektmodell. Live-bilder = numpy → `QImage` (mycket snabbt).
- För extremt täta vetenskapliga plottar kan vi bädda in **PyQtGraph** i QML där det behövs
  (bästa av två världar).

---

## 4. Arkitektur (lager)

```
┌───────────────────────────────────────────────────────────────┐
│  GUI (QML / Qt Quick)  — Översikt · Sensorer · Kalibrering ·    │
│                          Logg · Inställningar                   │
├───────────────────────────────────────────────────────────────┤
│  UI-bryggor (QObject)  — exponerar state/strömmar till QML,     │
│                          numpy→QImage-providers                 │
├───────────────────────────────────────────────────────────────┤
│  App-kärna  — AppState, RunController (bräd-livscykel),         │
│               config, event-buss, larm/watchdog                 │
├───────────────────────────────────────────────────────────────┤
│  Behandling  — stripe → triangulering → höjd · yta → defekter · │
│                punktlaser-fusion · gradering   (trådar/process) │
├───────────────────────────────────────────────────────────────┤
│  Förvärv  — trådade grabbers per enhet → ringbuffrar (drop-safe)│
├───────────────────────────────────────────────────────────────┤
│  HAL (hårdvaruabstraktion) — gränssnitt per enhet               │
│     ├── sim/   (fysik ur src/, databladstakter + brus)          │
│     └── real/  (MVS · Aravis · Modbus · Jrk)                    │
└───────────────────────────────────────────────────────────────┘
        ▲ samma gränssnitt → GUI/behandling bryr sig inte om läge
```

### Nyckelidé: **HAL med två backends**
Varje enhet definieras som ett abstrakt gränssnitt (`ProfileCameraIF`,
`SurfaceCameraIF`, `PointLaserIF`, `ConveyorIF`, `LineLaserIF`). Två
implementationer:

- **`sim`** — driven av `src/`-fysiken, med **riktiga databladsvärden** (upplösning,
  bildtakt, mm/px, brus, latens) så datatakter/beteende är representativa.
- **`real`** — MVS-SDK / Aravis / Modbus / Jrk.

En `factory` bygger HAL ur config + läge (`--mode sim|real`). **GUI och behandling
är identiska i båda lägena.** Det är så "allt i ett program" blir sant: vi utvecklar
och demar i sim nu, och slår om till hårdvara senare utan att röra GUI:t.

---

## 5. Föreslagen mappstruktur

```
woody/
  app/                         # HUVUDPROGRAMMET
    main.py                    # entry: --mode sim|real, Qt-bootstrap, helskärm
    core/
      state.py                 # AppState + signaler
      run_controller.py        # start/stopp, bräd-livscykel, auto-mata
      config.py                # YAML-config + validering (enheter, kalibrering, regler)
      alarms.py                # larm + watchdog ("hänger inte")
    hal/
      base.py                  # ABC:er per enhet
      factory.py               # bygg HAL ur config + läge
      sim/                     # simulerade backends (återanvänder src/)
      real/                    # mvs_profile.py, aravis_surface.py, lr400_modbus.py, jrk_conveyor.py
    acquire/
      grabber.py               # trådad grabber → ringbuffert (drop-safe)
      pipeline.py              # orkestrering förvärv→behandling
    processing/
      stripe.py                # subpixel-stripe-extraktion
      triangulate.py           # stripe→Z via kalibreringsmodell
      surface.py               # färg/defekt-analys
      fusion.py                # punktlaser → absolut tjocklek
      grade.py                 # regelverk → klass A/B/C/Vrak
    geometry/
      rig.py                   # EN sanning för riggens geometri (WD, vinklar,
                               #   kamera/laser/ytkamera-placering) — matchar head-mech.svg
    ui/
      qml/                     # Dashboard.qml, Sensors.qml, Calibration.qml, Log.qml, ...
      bridge.py                # QObject-bryggor
      image_provider.py        # numpy→QImage (live-vyer)
      theme/                   # designsystem (färg, typografi, komponenter)
    persistence/
      store.py                 # SQLite + bildarkiv per bräda + export
    calibration/               # rutiner + sparade modeller
  src/                         # befintlig fysik/sim (återanvänds av hal/sim)
  tools/                       # ritningar/verifiering (befintligt)
  docs/                        # denna fil m.fl.
```

`geometry/rig.py` blir **en** källa för riggens mått (WD 710, kamera-arm 20°,
laser-arm 40°, θ 30°, ytkamera i centrum @ 400 mm) — samma som `head-mech.svg`,
så GUI:t och ritningen aldrig kan säga emot varandra. Det fixar både
proportions- och ytkamera-buggen på rätt nivå.

---

## 6. Realtid & prestanda (så det inte hänger)

- **Förvärv i egna trådar** per enhet → ringbuffrar. Aldrig blockera kameran.
- **Backpressure:** om behandlingen halkar efter, släpp äldsta ram (räkna & visa
  "dropped frames"), häng aldrig GUI:t.
- **Behandling** i trådpool/process-pool (numpy/OpenCV släpper GIL; tunga CV-steg kan
  läggas i egen process). **GPU** via OpenCV-CUDA/CuPy, defektmodell via TensorRT/ONNX.
- **GUI-tråden gör bara UI** — drar senaste klart-behandlade resultat, throttlat till skärmtakt.
- **Mät & visa** verklig pipeline-latens och Jetson-last (det vi redan verifierat i
  `tools/verify_jetson_io.py` blir live-siffror).

---

## 7. Vad rebuilden konkret fixar

- ✅ **Rätt proportioner/enheter:** alla vyer i mm via `geometry/rig.py` → 500×75×20
  ritas korrekt (bred kort yta, inte hög planka), skalor med riktiga axlar.
- ✅ **Rätt rigg:** ovanifrån-/tvärsnittsvy härleds ur samma optikmodell som
  `head-mech.svg` (oblika huvuden + ytkamera rakt ned i centrum + punktlaser uppströms).
- ✅ **Modernt utseende:** Qt Quick designsystem (tema, typografi, mjuka animationer, shaders).
- ✅ **Riktig data:** samma program kör mot fysiska sensorer genom att byta HAL-läge.
- ✅ **Ingen genväg:** lagrad arkitektur, trådning, persistens, kalibrering, tester.

---

## 8. Leveransplan (faser)

| Fas | Innehåll | Resultat |
|---|---|---|
| **M0** | App-skelett (PySide6+QML), config, state-maskin, `geometry/rig.py`, sim-HAL som matar brädor, **en** korrekt live-vy | Native fönster ersätter control.html, rätt geometri |
| **M1** | Full dashboard-paritet (alla paneler, rätt proportioner, animerat) + sensor-telemetrivy, allt ur sim-HAL | Komplett GUI i simläge |
| **M2** | Riktig behandlingspipeline (stripe/triangulering/yta/gradering) på sim-ramar + persistens & per-bräda-logg/export | Funktionell mät- & graderingskedja |
| **M3** | Kalibreringsflöden (intrinsics, trianguleringsplan, punktlaser-noll) + inställnings-UI | Kalibrerbart system |
| **M4** | Verkliga HAL-backends (MVS, Aravis, Modbus, Jrk) + uppstart på Jetson + sim↔verklig-paritetstester | Kör mot fysisk hårdvara |
| **M5** | Defektmodell (ML, valfritt), trimning, kiosk/helskärm + autostart-tjänst på Jetson | Driftsatt bänk-program |

---

## 9. Beroenden

**Bas:** `PySide6`, `numpy`, `opencv-python` (på Jetson: system-cv2 med CUDA ur JetPack),
`PyYAML`, `pydantic` (config-validering).
**Hårdvara (Fas 4):** `pyserial` + `pymodbus`/`minimalmodbus` (LR400), `harvesters`
(GenICam) eller `aravis`/PyGObject (GigE/USB3 Vision), Hikrobot **MVS-SDK** (aarch64,
leverantör), Jrk G2 via USB (pyusb eller seriell).
**Valfritt:** `pyqtgraph` (täta plottar), `onnxruntime`/TensorRT (defektmodell på GPU).

---

## 10. Risker & motåtgärder

| Risk | Motåtgärd |
|---|---|
| Hikrobot MVS-SDK strul på ARM64 | Aravis/Harvesters som fallback (samma GenICam-standard) — redan dokumenterat i `docs/jetson-setup.md` |
| GIL/perf vid full takt | numpy/OpenCV släpper GIL; tunga steg i egen process; GPU på Jetson |
| QML inlärningskurva | Börja med litet designsystem; PyQtGraph-inbäddning för det svåra |
| Scope (stort) | Fasindelat — M0/M1 ger körbart, snyggt simläge tidigt |

---

## 11. Beslut som behövs

1. **Teknikstack:** PySide6 + QML (rekommenderat) — eller PySide6 Widgets + PyQtGraph
   (snabbare till "korrekt", mindre "wow")?
2. **Var börjar vi:** ska jag scaffolda **M0** (app-skelett + `geometry/rig.py` + sim-HAL
   + en korrekt live-vy) så du tidigt ser native-fönstret med rätt geometri?

> När stacken är vald scaffoldar jag M0 och vi itererar därifrån — inga fler
> engångsskisser, utan det riktiga programmet steg för steg.
