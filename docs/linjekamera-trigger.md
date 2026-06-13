# Linjekamera — encoder-triggad line-scan (idrifttagning)

Linjekameran **HuaTeng HT-GELM44C-T2** (färg, 4096 px, GigE Vision) tar ytbilden.
Den triggas av **band B-encodern** (Omron E6B2-CWZ1X, RS-422) som matas in på
kamerans **Line0** (via 26C32, se `prototype-wiring.svg`) — en bildrad per
encoderpuls medan brädan matas förbi. Jetson läser **ingen** encoder direkt.

> Allt styrs från koden via GenICam (vendor-neutralt) — Huatengs proprietära
> `libMVSDK` används **inte** i drift, bara som referens (`~/huateng/…`).

## Trigger-modellen (Huatengs SDK → vad vi konfigurerar)
Huatengs `CameraDefine.h` definierar sensorns snap-lägen:

| Värde | Läge | Användning |
|---|---|---|
| 0 | `CONTINUATION` | fri ström (fokus/justering) |
| 1 | `SOFT_TRIGGER` | mjukvarutrigg |
| 2 | `EXTERNAL_TRIGGER` | extern signal (areakamera) |
| **3** | **`ROTARYENC_TRIGGER`** | **encoder-trigg (linjekamera) ← vår** |
| 4 | `ROTARYENC_COND_TRIGGER` | encoder villkorlig |

Encoder-parametrar (`CameraApi.h`):
- `CameraSetRotaryEncDir(dir)` — **0**=båda riktn., **1**=medurs (A före B), **2**=moturs.
  Vi använder en riktning så att **bara framåtmatning** triggar (annars dubbel-räknas
  brädan när den backar till anhållet i pass-läget).
- `CameraSetRotaryEncFreq(mul, div)` — radtakt = puls × `mul` / `div`. **`div` = "divider"**
  i kalibreringssteget *linesync* (rader/mm) → kvadratiska pixlar.

## Hur appen sätter det (vendor-neutralt)
`app/hal/real/cameras.py` → `GenICamSurfaceCamera`:
- Default: encoder-line-trigg **PÅ** (`_line_trigger`), färg `RGB8`, auto-WB/exp/gain av.
- `configure_encoder_line_trigger(divider=…, multiplier=…, direction=…, line_rate_hz=…)`
  appliceras direkt om ansluten, annars vid nästa `open()`.
- `disable_line_trigger()` → fri ström (fokus/MTF-kalibrering utan matning).

GenICam-nodnamnen följer SFNC men **varierar per modell**, så koden provar
prioriterade **kandidatlistor** (`set_first_available`) och använder första som funkar:

| Logiskt | GenICam-kandidater | Värde |
|---|---|---|
| trigg-selektor | `TriggerSelector` | `LineStart` |
| trigg på/av | `TriggerMode` | `On` |
| trigg-källa | `TriggerSource`, `LineSource` × `Encoder0`/`RotaryEncoder`/`FrequencyConverter`/`Line0` | — |
| flank | `TriggerActivation` | `RisingEdge` |
| encoder-val | `EncoderSelector` | `Encoder0` |
| encoder A/B | `EncoderSourceA/B`, `RotaryEncoderSourceA/B` | `Line0`/`Line1` |
| riktning | `EncoderDirection`, `RotaryEncoderDirection`, `RotaryEncDir` | forward→1 |
| divider | `EncoderDivider`, `RotaryEncoderDivider`, `RotaryEncDiv` | från *linesync* |
| multiplikator | `EncoderMultiplier`, … | 1 |
| line-rate | `AcquisitionLineRate`, `LineRate` | valfri tak |

Fel/okänt nodnamn loggas (kraschar aldrig) — så samma kod funkar mot olika firmware.

## Idrifttagning när kameran kopplas in (gör i ordning)
1. **Ström + GigE-länk.** Anslut kameran. Sätt jumbo frames + rätt subnät på Jetsons
   GbE. GigE-kameran behöver en IP i samma subnät — tilldela med Huatengs verktyg:
   `~/huateng/linuxSDK_V2.1.0.49(202511141513)/tools/GeConfigCmd` (eller `QGeConfigTools`).
2. **Hitta kameran:** `python tools/jetson_selftest.py` → sektion 2 ska visa kameran,
   och `python tools/dump_camera_features.py --list` ska lista serienr.
3. **Mappa de EXAKTA nodnamnen:** `python tools/dump_camera_features.py --trigger`
   — visar alla trigger/encoder/line-noder **med tillåtna enum-värden**. Jämför mot
   kandidatlistan ovan; om kameran använder andra namn/värden, lägg till dem i
   `_TRIG_CANDS` / `_TRIG_SOURCE_CANDS` i `cameras.py`.
4. **Verifiera trigg:** kör band ~60 mm/s, kalibrera `enc_b → camtrig` (rader vs pulser,
   jitter) i GUI:t. 0 missade pulser = OK.
5. **Synka radavstånd:** kalibrera `surface → linesync` (mata 200 mm, räkna rader) →
   få rader/mm → `surface.configure_encoder_line_trigger(divider=N)` för kvadratiska
   pixlar (mål 1 rad ≈ 0,122 mm vid 4096 px / 500 mm).
6. **Färg/exponering:** `whitebalance` + `flatfield`-kalibreringarna under LED-ljuset.

## Felsökning
- **Inga rader fångas:** trigg-källa fel — kör `--trigger` och kontrollera att
  `TriggerSource`/`LineSource` matchar en nod som finns; verifiera encoderpulser på Line0.
- **Brädan dubbel-skannas vid backning:** sätt `direction="forward"` (inte `"both"`).
- **Streckiga/skeva pixlar:** fel `divider` — kör om `linesync`.
- **Ingen GenTL-producent:** `GENICAM_GENTL64_PATH` ej satt, eller använd Aravis-fallback.
  Se `docs/jetson-prep-plan.md` + MVS-installationen.
