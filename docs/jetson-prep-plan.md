# Jetson-förberedelse — komplett analys & plan ("allt klart innan resten kommer")

**Mål:** Jetsonen är på plats. Resten av hårdvaran (kameror, RoboClaw, encodrar, lasrar)
kommer senare. Det här dokumentet beskriver hur vi gör Jetsonen **100 % mjukvaruklar
nu**, så att idrifttagningen sen bara är *koppla in → kör självtest → kalibrera*.

> Snabbstart på Jetsonen:
> ```bash
> bash tools/jetson_bootstrap.sh        # installerar allt (idempotent)
> python tools/jetson_selftest.py       # probar varje enhet, skriver anslutningsrapport
> python -m app                         # appen i sim-läge (funkar utan hårdvara)
> ```

---

## 0. TL;DR — vad kan göras NU vs NÄR hårdvaran kommer

| Kan göras NU (ingen fältmaskinvara) | Kräver inkopplad hårdvara |
|---|---|
| JetPack/OS, NVMe, swap, klockor, ström-läge | Hitta kamerorna (serienummer, live-bild) |
| Alla SDK:er & drivrutiner (MVS, Aravis, Harvester, RoboClaw, pyserial, Jetson.GPIO) | RoboClaw-kalibrering (counts/mm, hastighet) |
| Python-venv + repo + beroenden | Encoder-trigg av linjekameran (hårdvarutrigg) |
| Köra appen i **sim-läge** end-to-end | Laser-enable via GPIO (MOSFET) verifieras |
| Bygga/validera CUDA-stripe-extraktion | Geometri-/nollkalibrering mot referensbräda |
| udev-regler, usbfs-gräns, jumbo frames | Fotocell (brädstart) timing |
| Real-HAL **koden** klar (RoboClaw, linjekamera, profilkameror) | Färgbalans/exponering mot riktigt LED-ljus |
| Självtest-verktyg som rapporterar "ansluten/ej" per enhet | Bandhastighet ↔ linjetakt-synk |

Resultat av NU-kolumnen: när en enhet pluggas in säger `jetson_selftest.py` direkt
"RÖD profilkamera: ansluten (serial …)", "RoboClaw: ansluten /dev/ttyACM0", osv.

---

## 1. Maskinvaran som är LÅST (vad mjukvaran ska prata med)

| Roll | Produkt | Jetson-länk | SDK / drivrutin på aarch64 |
|---|---|---|---|
| Profilkamera RÖD (triangulering) | Hikrobot **MV-CS050-10UM** (USB3, mono 5 MP, IMX264, 60 fps) + bandpass **FS03-BP650** | USB3 #1 (egen kontroller) | **Hikrobot MVS SDK** (GenTL `.cti`) el. **Aravis** |
| Profilkamera GRÖN (triangulering) | Hikrobot **MV-CS050-10UM** + bandpass **FS03-BP525** | USB3 #2 (egen kontroller) | samma |
| Profillins ×2 | **MVL-MF1228M-8MP** (12 mm, C-mount) | — | — |
| Ytkamera (färg, 4K) | **HT-GELM44C-T2** linjekamera (GigE, 4096 px, färg) | GbE (RJ45, direkt) | **Aravis / vendor-SDK (GenICam)**, **encoder-triggad** |
| Ytlins | **ZLKC TM2004MPC** (f=20, M42) | — | — |
| Bandstyrning (2 motorer) | **RoboClaw 2x7A** (dubbelkanal, sluten slinga, quadrature) | **1× USB** (`/dev/ttyACM*`, packet serial) | **pyserial** + RoboClaw-protokoll (vår `roboclaw_conveyor.py`) |
| Encoder band A | Omron **E6B2-CWZ6C** (single-ended) → RoboClaw EN1 | (ej till Jetson) | — |
| Encoder band B | Omron **E6B2-CWZ1X** (RS-422) → linjekamera Line0 + 26C32→EN2 | (ej till Jetson) | hårdvarutrigg |
| Röd laserlinje | 650 nm, **5 V** (DC-barrel) — enable via D4184/AO3400 | GPIO (MOSFET) | Jetson.GPIO |
| Grön laserlinje | 520 nm, **24 V** (DC-barrel) — enable via AOD4184 opto-MOSFET | GPIO (MOSFET) | Jetson.GPIO |
| Vitt LED (ytbelysning) | 24 V LED-list | GPIO (MOSFET) | Jetson.GPIO |
| Anslagsfotocell (brädstart) | GTRIC **LSZ-S30N1** (NPN, diffus) | GPIO in | Jetson.GPIO |
| Lagring | NVMe SSD | M.2 Key-M | — |

**Viktigt om encodrar:** Jetsonen läser **ingen encoder direkt**. Encoder A → RoboClaw
(closed-loop), Encoder B → linjekamerans hårdvarutrigg + RoboClaw EN2. Jetsonen får
matningsposition från **RoboClaw över USB**. Profilkamerorna är USB3 och triggas/
fri-körs av appen med positionsstämpel — ingen encoderkabel till Jetson.

**Jetsonens enda fysiska länkar:** 2× USB3 (profilkameror, skilda kontroller),
1× GbE (linjekamera), 1× USB (RoboClaw), GPIO 40-pin (2 laser-enable + LED + fotocell),
M.2 (SSD). Inget annat.

---

## 2. Mjukvarustacken

### 2.1 OS / plattform
- **NVIDIA Jetson Orin Nano (Super) Dev Kit**, aarch64.
- **JetPack 6.x** (L4T r36.x, Ubuntu 22.04, CUDA 12.x, cuDNN, TensorRT, VPI).
- Boota OS + appdata från **NVMe** (snabbare än SD; SD bara för första flash).
- Sätt **MAXN/Super** ström-läge + `jetson_clocks` för full prestanda.

### 2.2 Kamerabibliotek (GenICam — vendor-neutralt)
- **Hikrobot MVS SDK** (aarch64 `.deb`) → ger GenTL-producent `.cti` för USB3 (profilkameror).
- **Aravis 0.8** (open source) → driver **både** USB3 Vision och GigE Vision; reserv +
  bekväm för linjekameran. `arv-tool-0.8`/`arv-viewer` för snabbtest.
- **Harvester** (python `harvesters`) → GenICam-API i Python; appens `cameras.py`
  pratar redan mot detta (pekas ut av `GENICAM_GENTL64_PATH` / vår `GENICAM_CTI`).

### 2.3 Styr-/IO-bibliotek
- **pyserial** → RoboClaw packet serial (`/dev/ttyACM*`).
- **Jetson.GPIO** → laser-enable, LED, fotocell-in (40-pin header).
- (LR400/Modbus och Jrk G2 är **utgångna** ur designen — se §4.)

### 2.4 Beräkning
- **numpy/scipy/opencv** (CPU-referens), **PySide6/Qt** (GUI).
- **CUDA/CuPy eller NVIDIA VPI** för laserstripe-extraktion på GPU (kravet för keep-up,
  se `docs/jetson-setup.md §4`).
- **PyTorch + TensorRT** för defekt-/U-Net-inferens (Kodytek-tränad modell).

---

## 3. Vad finns redan i repot (och vad är klart att köra)

**Klart och kör i sim nu:**
- Hela GUI:t + behandlingspipeline (`app/processing/*`): stripe → triangulering →
  fusion → yta → **A/B/C/D-gradering** (nyss färdigställd, `grade.py`+`grading_rules.py`).
- HAL-abstraktionen (`app/hal/base.py`) + **sim-backend** (full fysiksim).
- GenICam-kameror via Harvester (`app/hal/real/cameras.py`) — profilkamera + linjekamera.
- Verktyg: `verify_jetson_io.py`, `verify_optics.py`, `verify_geometry.py`.

**Stale / behöver uppdateras till låst hårdvara (åtgärdas i denna runda, §4):**
- `app/hal/real/lr400_modbus.py` — punktlasrar (utgångna).
- `app/hal/real/jrk_conveyor.py` — Jrk G2 (ersatt av RoboClaw).
- `app/hal/real/real_backends.py` — bygger fortfarande LR400 + Jrk.
- `docs/jetson-setup.md §3` enhetskarta — listar LR400/Jrk.

---

## 4. Real-HAL anpassad till låst hårdvara (görs nu)

1. **`roboclaw_conveyor.py` (ny):** RoboClaw 2x7A över packet serial (adress 0x80).
   - `set_speed(mm/s)` → DutyM1/M1M2 eller SpeedM1M2 (closed-loop).
   - `position_mm()` ← `ReadEncM1` × counts/mm (kalibreras).
   - Två kanaler (synkade band) via M1M2-kommandon.
2. **`real_backends.py`:** byter `JrkConveyor` → `RoboClawConveyor`; `point_lasers = []`
   (tjocklek kommer nu ur profilkamerornas triangulering, inte LR400).
3. **`cameras.py` linjekamera:** behåll GenICam, lägg encoder-/linjetrigg-noter +
   rätt modellnamn (HT-GELM44C-T2).
4. **Behåll interface i `base.py`** (sim använder `point_lasers` för att sampla
   tjocklek; real lämnar listan tom). Inget i sim-vägen ändras → inga regressioner.
5. `lr400_modbus.py`/`jrk_conveyor.py` markeras **DEPRECATED** (lämnas kvar för ev.
   referens men byggs inte längre av RealScanner).

---

## 5. Faser — gör i den här ordningen

### Fas A — Jetson grundsetup (NU, ingen fältmaskinvara)
1. Flasha JetPack 6.x, boota från NVMe, sätt MAXN + `jetson_clocks`.
2. `bash tools/jetson_bootstrap.sh` → apt-deps, venv, python-paket, Aravis,
   Harvester, pyserial, Jetson.GPIO, usbfs-gräns, udev-regler, repo-beroenden.
3. Installera **Hikrobot MVS SDK** (`.deb`) manuellt (kräver nedladdning från Hikrobot)
   — bootstrap skriver ut exakt länk/steg och sätter `GENICAM_GENTL64_PATH`.
4. `python -m app` → kör appen i **sim-läge** end-to-end (verifierar GUI + pipeline + gradering).
5. `python tools/verify_jetson_io.py` + `verify_optics.py` → sanity på portar/optik/keep-up.

### Fas B — CUDA-pipeline (NU) — KLAR att köra
- **GPU-stripe-extraktion** finns: `app/processing/stripe_gpu.py` kör EXAKT samma
  subpixel-centroid-algoritm på GPU (CuPy/CUDA) eller CPU (numpy) — väljs automatiskt,
  tvinga med `WOODY_STRIPE_BACKEND=cpu|gpu`. Real-profilkameran (`cameras.py`) använder
  den redan. Verifierad bit-för-bit mot CPU-referensen (`test_stripe_gpu_matches_cpu`).
- **Profilera keep-up mot syntetiska ramar** (utan kameror):
  ```bash
  python tools/profile_stripe.py                 # auto-backend, flera ROI-höjder
  WOODY_STRIPE_BACKEND=cpu python tools/profile_stripe.py
  ```
  Rapporterar fps/ram + ms-latens + keep-up-marginal mot 60 fps (×2 kameror).
  Tolkning: med tight ROI-band (128–250 rader runt stripen) räcker även CPU nära
  60 fps; full sensor (2048 rader) kräver **GPU (CuPy/VPI)** — installera CuPy
  matchande JetPacks CUDA på Jetson, kör om profilern och bekräfta GPU-marginalen
  **innan** kamerorna kopplas in.

### Real-lägets körtidsmotor — KLAR att köra (testas mot sim nu)
`app/processing/acquisition.py` är den trådade förvärvspipelinen (encoder-triggad
radackumulering → färdig bräda): en **capture-tråd** läser laserstripe-rader (röd +
grön) + färgrad medan brädan matas, en **process-konsument** kör GPU-stripe →
triangulering → fusion per rad och bygger höjdkartan. Stegen överlappar (kamera ∥ GPU).
Samma kod kör mot sim och real — bara HAL byts. Profilera/verifiera utan hårdvara:
```bash
python tools/profile_acquisition.py            # rader/s, brädor/min, överlapp, grad
```
Mätt på CPU-host: ~450 rader/s, **1.00× överlapp** (GPU helt gömd bakom capture),
brädor assembleras + graderas. På Jetson-GPU lyfter rad-takten ytterligare.

### Fas C — Plug-in en enhet i taget (NÄR den kommer)
För varje enhet: koppla in → `python tools/jetson_selftest.py` → ska visa "ansluten".
1. **RoboClaw** (USB): självtest hittar `/dev/ttyACM*`, läser firmware/version, jog ±.
   Kalibrera `counts_per_mm` + hastighetsskala.
2. **Profilkameror** (USB3, var för sig): MVS/Aravis hittar serienr, live-bild, sätt
   exponering, kontrollera bandpass (bara laserlinjen syns).
3. **Linjekamera** (GbE): jumbo frames + subnät, live, sen **encoder-triggad** radskanning.
4. **Lasrar + LED** (GPIO): enable on/off, **laser-säkerhet** (rum låst, dörrinterlock,
   glasögon HM326-C) innan ström på.
5. **Fotocell** (GPIO in): bräda bryter stråle → brädstart-event.

### Fas D — Kalibrering & skarp drift (NÄR allt är inkopplat)
- Geometri-/nollkalibrering mot referensbräda (`docs/zero-reference.md`,
  `docs/alignment-calibration.md`).
- Synka bandhastighet ↔ profiltakt ↔ linjekamerans linjetakt.
- Färg/exponering mot riktigt LED-ljus.
- `cfg.mode = "real"` → kör skarpt; jämför grad mot facit/referensbrädor och tona
  `grading_rules.py` mot köpt standard (SS-EN 1611-1 / Nordic Timber).

---

## 6. Checklista — "Jetson mjukvaruklar"
- [ ] JetPack 6.x på NVMe, MAXN + jetson_clocks
- [ ] `jetson_bootstrap.sh` kört utan fel
- [ ] MVS SDK installerat, `GENICAM_GENTL64_PATH` satt
- [ ] Aravis: `arv-tool-0.8` svarar (även utan kamera: listar tomt utan fel)
- [ ] `python -m app` kör i sim end-to-end (gradering A/B/C/D syns)
- [ ] `verify_jetson_io.py` + `verify_optics.py` gröna
- [ ] CUDA-stripe-extraktion profilerad @ ≥60 fps på syntetiska ramar
- [ ] udev-regler + usbfs_memory_mb=1000 permanent
- [ ] Real-HAL bygger RoboClaw + profilkameror + linjekamera (inga LR400/Jrk)
- [ ] `jetson_selftest.py` kör (rapporterar "ej ansluten" snyggt utan hårdvara)

När alla rutor är i: **inkoppling = plug-in + självtest + kalibrera.**

---

## Referenser
- `docs/jetson-setup.md` — drivrutiner, OS-inställningar, enhetskarta (uppdateras till låst hw)
- `docs/alignment-calibration.md`, `docs/zero-reference.md` — kalibrering
- `docs/grading-nordic.md` — A/B/C/D-gradering (tona talen mot köpt standard)
- Hikrobot MVS SDK (aarch64): <https://www.hikrobotics.com/en/machinevision/service/download/>
- Aravis: <https://github.com/AravisProject/aravis>
- RoboClaw user manual (packet serial-protokoll): BasicMicro
