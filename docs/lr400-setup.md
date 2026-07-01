# Punktlaser LR400 (RS-485 Modbus) — idrifttagning + kalibrering

3× **LR400** punktlaser ger ABSOLUT tjocklek i tre punkter och ankrar
trianguleringens globala offset/tilt (`fusion.anchor`). De läses över RS-485 Modbus
RTU via **Waveshare USB TO 4CH RS485** (industriell, FT4232-baserad).

## Buss-topologi (VIKTIGT)
Waveshare 4CH ger **4 separata serieportar** (`/dev/ttyUSB0..3`), en RS485-buss per
port. Varje LR400 sitter **ensam på sin port** → samma slav-adress (`unit=1`) men
olika `port`. Standard-mappning (`data/lr400.json`):

| Kanal | Laser | Port | unit |
|---|---|---|---|
| ch1 | LR-V | /dev/ttyUSB0 | 1 |
| ch2 | LR-C | /dev/ttyUSB1 | 1 |
| ch3 | LR-H | /dev/ttyUSB2 | 1 |

(ch4 på adaptern = reserv.) **Verifiera port↔kanal-ordningen** vid inkoppling — FT4232
ger stabila men inte garanterat 1:1-numrerade portar. Drivern delar dessutom en
Modbus-klient per port, så en delad-buss-topologi (en port, flera adresser) funkar
också om man hellre kedjar dem.

## Register-karta (verifiera mot databladet)
Vilket Modbus-register som håller avståndet + skalan är sensor-specifikt. Default:
`reg_addr=0`, `reg_kind=holding`, `scale=0.01` (register × 0,01 = mm). **Verifiera
vid inkoppling:**
```bash
python tools/lr400_scan.py --port /dev/ttyUSB0 --unit 1 --kind both --count 32
```
Ställ ett känt mål (t.ex. 100,0 mm) framför LR400:n → leta registret vars skalade
värde matchar → skriv `reg_addr`/`reg_kind`/`scale` i `data/lr400.json`.

## Kalibrering (GUI: Sensorer → Punktlaser → Kalibrering)
| Metod | AUTO | Vad |
|---|---|---|
| `zero_d0` | ✅ | TÖM bandet → medla 100 avläsningar/kanal → sätt **D0** (tjocklek = D0 − avstånd). Skrivs till `data/lr400.json`. |
| `linearity` | ⛔ guidat | Mät referenstrappa (5/10/15/20 mm) → verifiera linjäritet/skala. Kräver fysisk trappa. |
| `anchor` | ⛔ guidat | Jämför LR400 absolut tjocklek mot profilfusion → offset/tilt. Kräver referensbräda + kameror. |

## Idrifttagning (plug-and-play)
1. `bash tools/jetson_bootstrap.sh` (pymodbus + udev `ttyUSB*` → dialout-åtkomst).
2. Koppla in Waveshare 4CH + de 3 LR400 (A+/B− per RS485-port). Logga ut/in för `dialout`.
3. `python tools/lr400_scan.py --port … --unit 1` per port → hitta avstånds-registret,
   skriv `data/lr400.json` (port↔kanal, reg, skala).
4. `python tools/jetson_selftest.py` → sektion 4 visar per kanal: avstånd, D0,
   härledd tjocklek, brus. Töm bandet och kör `zero_d0` (GUI) → D0 sätts automatiskt.
5. `linearity` + `anchor` (guidat) för certifierad absolut-skala.

## Felsökning
- **Inget svar:** fel port/unit/register — kör `lr400_scan.py`; kontrollera A+/B−,
  termineringsmotstånd och 9600 baud.
- **Tjocklek orimlig:** fel `scale` eller `d0_mm` ej nollad — kör `zero_d0` på tomt band.
- **Fel laser på fel kanal:** port↔kanal-mappningen i `lr400.json` — byt port-strängarna.
- **Brus högt:** kontrollera RS-485-jord/skärm och att målet är inom LR400:s mätområde.
