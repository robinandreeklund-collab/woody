# CLAUDE.md — woody (virkesskanner)

Orientering för en Claude-agent som kör i detta repo, särskilt **lokalt på Jetsonen**
vid idrifttagning. Läs detta först, sen `docs/jetson-prep-plan.md`.

## Vad projektet ÄR
"woody" är en **virkesinspektions- och sorteringsrigg** med en **dubbel-oblik
laser-trianguleringsskanner**. En bräda (500×75×15–50 mm) matas tvärs förbi en
laserlinje; två huvuden (RÖD 650 nm + GRÖN 520 nm), vart och ett = profilkamera +
linjelaser, mäter höjd/tjocklek från var sin sida. En färg-linjekamera tar ytan,
3× punktlaser ger absolut tjocklek, och systemet graderar brädan enligt nordisk
**A/B/C/D**-utseendesortering. Allt på en **Jetson Orin Nano Super**.

Mjukvaran: **PySide6 + QML desktop-app** med en HAL (sim/real-backends) så att
*exakt samma* behandlingskod kör mot simulering eller fysisk hårdvara.

> Allt språk i kod/GUI/commits är **svenska**. Fortsätt på svenska.

## LÅST hårdvara (sanningskälla = `prototype-wiring.svg` + `prototype-pinout.svg`)
| Enhet | Modell | Buss/pin |
|---|---|---|
| Profilkamera RÖD/GRÖN | Hikrobot MV-CS050-10UM (mono, 60 fps) + BP650/BP525 | 2× USB3 |
| Linjekamera (färg, yta) | HT-GELM44C-T2 (4096 px) | GbE, encoder-triggad |
| 3× punktlaser | LR400 (absolut tjocklek, ankrar trianguleringen) | RS-485 Modbus, Waveshare USB→4CH ch1–3 |
| Bandstyrning (2 band) | RoboClaw 2x7A (sluten slinga, quadrature) | 1× USB (`/dev/ttyACM*`) |
| Encoder band A | Omron E6B2-CWZ6C | → RoboClaw EN1 (ej till Jetson) |
| Encoder band B | Omron E6B2-CWZ1X (RS-422) | → linjekamera Line0 + 26C32→EN2 |
| Linjelaser RÖD enable | 650 nm, 5 V | GPIO **pin 16** |
| Linjelaser GRÖN enable | 520 nm, 24 V | GPIO **pin 18** |
| Vitt LED ×2 | 24 V | GPIO **pin 13 + 15** |
| Anhåll-fotocell | GTRIC LSZ-S30N1 (NPN) | GPIO **pin 7** (aktiv låg) |

Geometri (LÅST): kamera-arm 25°, laser-arm 50° (θ=25°), WD 760 mm, baslinje 329 mm,
konvergens 35 mm över bandet, täcker tjocklek 15–50 mm. **4× USB3 fulla:** RÖD-kam +
GRÖN-kam + RS-485 4CH + RoboClaw. Jetson läser **ingen encoder direkt**.

## ⚠️ SÄKERHET — läs innan du rör hårdvaran
- Lasrarna är **klass 3B**. Sätt **ALDRIG** laser-enable (GPIO pin 16/18) utan
  uttrycklig människo-bekräftelse: rummet låst, dörrinterlock, skyddsglasögon
  (HM326-C). `gpio_io.GpioEnable.close()` släcker alltid utgångarna.
- Du kan inte koppla kablar eller rikta lasrar — det gör människan.

## Kodkarta
- `app/` — appen (det som körs).
  - `app/main.py` / `python -m app` — entry point (PySide6+QML). Flaggor: `--mode sim|real`,
    `--fullscreen`, `--probe` (testa anslutningar, ingen GUI), `--no-store`.
  - `app/core/run_controller.py` — `AppController`: driver, tillståndsmaskin, QML-egenskaper.
  - `app/core/config.py`, `state.py` — config + körtillstånd.
  - `app/core/calibration.py` — **data-driven** enhetskatalog + kalibreringsmetoder + lager + körmotor.
  - `app/core/devices.py` — `DeviceManager` (status + kalibrering mot QML).
  - `app/hal/base.py` — HAL-gränssnitt. `app/hal/factory.py` väljer backend.
  - `app/hal/sim/` — simulering (board_gen.py genererar brädor + defekter).
  - `app/hal/real/` — **riktig hårdvara**: `cameras.py` (GenICam), `lr400_modbus.py`
    (RS-485), `roboclaw_conveyor.py` (USB packet serial), `gpio_io.py` (laser/LED/fotocell),
    `real_backends.py` (knyter ihop allt; `jrk_conveyor.py` är DEPRECATED).
  - `app/processing/` — pipeline: `stripe.py`→`triangulate.py`→`fusion.py`→`grade.py`.
    `stripe_gpu.py` = GPU/CPU-stripe (CuPy/numpy). `grading_rules.py` = A/B/C/D-tal (data).
    `acquisition.py` = trådad capture∥GPU → färdig Board.
  - `app/ui/qml/` — GUI. `Main.qml` (skal+footer+notisbanner), `SensorsView.qml`
    (enhetskort, klick→kalibrering), `CalibrationView.qml` (kör metoder).
  - `app/tests/` — `test_core`, `test_grading`, `test_calibration`, `test_passmode`.
- `tools/` — `jetson_bootstrap.sh` (installerar allt), `jetson_selftest.py` (probar enheter),
  `profile_stripe.py` / `profile_acquisition.py` (keep-up @ 60 fps), `verify_*.py`, `draw_*.py` (SVG).
- `docs/` — `jetson-prep-plan.md` (HUVUDPLAN), `jetson-setup.md`, `grading-nordic.md`,
  `alignment-calibration.md`, `zero-reference.md`.
- `src/` — fristående forsknings-/träningskod (U-Net, Kodytek) — separat från `app/`.
- `*.svg` i roten — wiring/pinout/geometri (sanningskälla för hårdvaran).

## Arbetssätt / körkommandon
```bash
python -m app                       # GUI, sim-läge (funkar utan hårdvara)
python -m app.main --mode real      # mot riktig hårdvara
python -m app.main --mode real --probe   # anslutningsrapport, ingen GUI
python -m app.tests.test_core       # testsviter (även .test_grading/.test_calibration/.test_passmode)
python tools/jetson_selftest.py     # probar varje enhet (RS-485, RoboClaw, GPIO, kameror)
bash tools/jetson_bootstrap.sh      # ENGÅNGS-setup på Jetsonen (sudo — fråga först)
```
Tester körs utan pytest (`python -m app.tests.<modul>`). Kör relevanta tester efter ändring.

## Idrifttagning på Jetsonen (gör i ordning — se docs/jetson-prep-plan.md §5)
1. `bash tools/jetson_bootstrap.sh` (apt, venv, Aravis, pymodbus, pyserial, Jetson.GPIO, CuPy, udev).
2. Installera Hikrobot MVS SDK (`.deb`, manuell nedladdning) + sätt `GENICAM_GENTL64_PATH`.
3. `python -m app` i sim → verifiera GUI + gradering.
4. `python tools/profile_stripe.py` → bekräfta GPU-keep-up @ 60 fps.
5. Koppla in en enhet i taget → `python tools/jetson_selftest.py` tills grön.
6. Kalibrera i GUI:t (Sensorer → klick på enhet → Kalibrering): nollplan B(x),
   huvud-alignment RÖD↔GRÖN, LR400-nollning (D0), counts/mm, vitbalans, referensbräda.

## Pass-lägen (liten rigg, ingen separat in-/utmatning)
Brädan skannas **framåt → backar till anhåll-fotocellen (nollar) → ev. igen**.
- **single**: 1 pass → analys + notis "Ladda ny bräda" → vänta (knapp / fotocell).
- **multi (N)**: skanna samma bräda N ggr (medel) → analys. Sämsta klassen styr.

## Gradering A/B/C/D
Data-driven motor (`grade.py` + `grading_rules.py`), princip "worst governs" enligt
EN 1611-1 / Nordic Timber. Talen i `grading_rules.py` är **representativa** — tona dem
mot köpt standard (SS-EN 1611-1) + referensbrädor för certifierad sortering.

## Git
- Utvecklingsbranch: **`claude/stoic-newton-CMsDC`**. Utveckla, committa, pusha dit.
- Pusha bara när användaren ber om det. Skapa **inte** PR utan att bli ombedd.
- Behörigheter är förinställda i `.claude/settings.json` (sudo/push/rm kräver bekräftelse).

## Konventioner
- Svenska i kod, kommentarer, GUI, commits.
- Lazy-importera hårdvaru-SDK:er (pyserial/pymodbus/Jetson.GPIO/harvesters) så appen
  startar på dev-maskiner utan dem.
- HAL-principen: GUI/behandling pratar BARA mot `app/hal/base.py`-gränssnitten.
- Ändra inte den låsta geometrin/hårdvaran utan att användaren ber om det; SVG-filerna
  är sanningskälla.
