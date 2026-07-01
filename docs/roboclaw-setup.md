# Transportör (RoboClaw 2x7A) — idrifttagning + kalibrering

**RoboClaw 2x7A** driver båda banden i sluten slinga (quadrature-encoder per motor)
över USB packet serial (`/dev/ttyACM*`). Drivern (`app/hal/real/roboclaw_conveyor.py`)
wrappar BasicMicros **officiella** Python-bibliotek (`pip install basicmicro`,
https://github.com/basicmicro/basicmicro_python) — det sköter CRC16, retries och hela
protokollet. Encoder band A → RoboClaw EN1; encoder band B → linjekamera Line0 + 26C32→EN2.
Jetson läser **ingen** encoder direkt (allt via RoboClaw).

## API som finns (utöver HAL set_speed/position_mm)
| Metod | Vad |
|---|---|
| `firmware()` | RoboClaw-version (selftest) |
| `position_mm()` | bandposition ur encoder M1 (band A) |
| `encoder_counts()` | råa counts (M1, M2) — bandsynk-jämförelse |
| `read_speed_mm_s()` | momentan hastighet per band (PID-stegsvar) |
| `move_mm(d, v)` | kör EXAKT sträcka, sluten slinga, auto-stopp (`SpeedAccelDistanceM1M2`) |
| `main_battery_v()` / `temperature_c()` / `error_status()` | hälsa |
| `health()` | allt ovan i en dict (selftest/GUI) |

`close()` och varje kalibrering stoppar **alltid** banden (`set_speed(0)`).

## Kalibrering (GUI: Sensorer → Transportör → Kalibrering)
| Metod | AUTO | Vad |
|---|---|---|
| `speedstep` | ✅ | Stega hastighet 0→50 mm/s, sampla `read_speed` → stigtid, översläng, ripple. (Banden kör bundet, operatörsinitierat via Kör, stoppas efteråt.) |
| `beltsync` | ✅ | Kör båda banden 200 mm (`move_mm`) → jämför encoder A/B → drift mm/m + status. |
| `countsmm` | ⛔ guidat | Encoder counts/mm: kör känd sträcka (anslag→anslag via fotocell) och mät — kräver fysisk referens, helt guidat i GUI:t. |

Encoder-verifieringar (enc_a/enc_b `pulsemm`, enc_b `camtrig`) är guidade — de kräver
känd matningssträcka resp. linjekamera + rörelse.

> PID auto-justeras INTE (kan göra banden instabila). `speedstep` MÄTER och
> rapporterar; PID-trim görs guidat utifrån utfallet (`SetM1VelocityPID` finns i biblioteket).

## Idrifttagning (plug-and-play)
1. `bash tools/jetson_bootstrap.sh` installerar `basicmicro` (+ pyserial).
2. Koppla in RoboClaw via USB. udev-regeln `99-woody.rules` ger åtkomst utan sudo
   (`/dev/ttyACM*`, symlänk `/dev/roboclaw`); logga ut/in för `dialout`-gruppen.
3. `python tools/jetson_selftest.py` → sektion 3 visar firmware, **batteri**, **temp**,
   **fel-flaggor** och **encoder M1/M2**. Allt grönt = ansluten.
4. Verifiera riktning/jog (öppen slinga) innan sluten slinga om PID inte är satt.
5. GUI: Transportör → kör `countsmm` (guidat) → sätt `counts_per_mm`. Sen `speedstep`
   (auto) → trimma Velocity-PID. Sen `beltsync` (auto) → trimma M2 mot M1.
6. Spara `counts_per_mm` (i drivern / config) så positionering stämmer.

## Felsökning
- **Hittas inte:** ingen `/dev/ttyACM*` → kontrollera USB + att RoboClaw är i
  packet-serial-läge (38400 baud, adress 0x80). udev/`dialout` för åtkomst.
- **Svarar inte (version tom):** fel baud/adress, eller annan enhet på porten.
- **Band rör sig fel håll / olika fort:** kontrollera encoder-fas (A/B) + Velocity-PID;
  kör `beltsync` och trimma M2.
- **Fel-flaggor ≠ 0:** läs `error_status()` (överström/temp/spänning) — åtgärda HW.
