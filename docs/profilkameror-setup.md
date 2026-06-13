# Profilkameror — idrifttagning (laser-triangulering, RÖD + GRÖN)

Två **Hikrobot MV-CS050-10UM** (mono, 2448×2048, 60 fps, USB3 Vision), en per huvud:
**RÖD** (BP650-bandpass, 650 nm laser) och **GRÖN** (BP525, 520 nm). Varje kamera ser
en mono-ROI runt sin laserstripe (rader = djup, kolumner = längs linjen) → subpixel-
centroid → triangulering → höjdkarta. Drivs via GenICam (`harvesters`), samma kod
som sim — bara HAL byts.

## ⚠️ Kritiskt: bind varje huvud till sitt serienummer
Två **identiska** kameror på USB3 → om de inte binds till serienummer kan RÖD/GRÖN
**förväxlas mellan körningar** och trianguleringen blir spegelvänd/fel. Identiteten
ligger i **`data/cameras.json`** (inte CLI). Saknas filen tas "första bästa" kamera
per roll — funkar för EN kamera men är otillförlitligt för två.

### Skapa cameras.json vid inkoppling
```bash
python tools/dump_camera_features.py --list           # se serienr på anslutna kameror
python tools/dump_camera_features.py --json > data/cameras.json   # skelett (förslag i ordning)
```
Öppna `data/cameras.json` och sätt rätt serienr på `profile_red` resp. `profile_green`.
**Vilken är vilken?** Den med BP650-filter = röd, BP525 = grön. Osäker? Tänd bara RÖD
lasern och kör `python tools/jetson_selftest.py` / grabba en ram per serienr — den som
ser stripen är den vars huvud lasern sitter på. (Lasersäkerhet: interlock + glasögon.)

```json
{
  "profile_red":   {"serial": "DA1234", "exposure_us": 800, "roi_rows": 80,
                    "roi_offset_y": null, "frame_rate_hz": 60},
  "profile_green": {"serial": "DA5678", "exposure_us": 800, "roi_rows": 80,
                    "roi_offset_y": null, "frame_rate_hz": 60},
  "surface":       {"serial": null, "divider": 1, "direction": "forward"}
}
```

## Hårdvaru-ROI = 60 fps keep-up
`open()` sätter ett **ROI-band** på kameran (full bredd 2448 × `roi_rows` höjd) i stället
för att överföra hela 2448×2048-sensorn. Det kapar USB-bandbredden och är det som gör
60 fps möjligt (se `tools/profile_stripe.py`: tight band 128–250 rader på GPU → keep-up).
Ordningen är `OffsetY=0 → Height=roi_rows → OffsetY` (offset-range beror på höjden).
`roi_offset_y=null` ⇒ bandet centreras via `HeightMax`; sätt ett kalibrerat värde när
alignment vet var stripen ligger.

## Kalibreringar (GUI: Sensorer → klick på kameran → Kalibrering)
| id | Vad | Påverkar kameran |
|---|---|---|
| `exposure` | svep exponering tills topp ≈ 200/255 | `exposure_us` i cameras.json |
| `dark` | mörkbild (laser av) → bakgrund | (mjukvara, subtraheras) |
| `intrinsics` | ChArUco → fokallängd/distorsion | (geometri) |
| `triangplane` | referenstrappa → px/mm i Z | (mm-skala) |
| `focus` | stripe-FWHM över FOV | (fysisk fokusring) |
| alignment RÖD↔GRÖN | var stripen ligger vertikalt | `roi_offset_y` (`configure_roi`) |

Efter kalibrering: spara värdena i `data/cameras.json` så de appliceras vid nästa start
(`exposure_us`, `roi_rows`, `roi_offset_y`). Körtid: `configure(ExposureTime=…)` och
`configure_roi(rows, offset_y)` på respektive kamera.

## Idrifttagning i ordning (en kamera i taget)
1. Installera Hikrobot MVS SDK (klart) + `GENICAM_GENTL64_PATH` satt. Aravis = fallback.
2. Koppla in **EN** profilkamera. `dump_camera_features.py --list` → serienr syns.
3. Fyll i serienr i `data/cameras.json` (rätt färg).
4. `python tools/jetson_selftest.py` → sektion 2 ska visa kameran ANSLUTEN.
5. `python tools/profile_stripe.py` → bekräfta GPU keep-up för vald `roi_rows`.
6. Kalibrera `exposure` → spara `exposure_us`. Sen `intrinsics`/`triangplane`/`focus`.
7. Koppla in den ANDRA kameran, upprepa 2–6. Verifiera att RÖD≠GRÖN (rätt serienr).
8. Alignment RÖD↔GRÖN → sätt `roi_offset_y` per kamera.

## Felsökning
- **RÖD/GRÖN förväxlade:** serienr fel i `cameras.json` — verifiera med en laser tänd.
- **Tappade USB3-ramar / låg fps:** usbfs-gräns (bootstrap satte 1000 MB temporärt;
  gör permanent i extlinux.conf), eller ROI för hög — minska `roi_rows`.
- **Hittas inte:** `GENICAM_GENTL64_PATH` ej satt, eller kör mot Aravis. Bägge USB3
  + 4× USB3 fulla → kontrollera att inte en hub delar bandbredd.
- **Stripen utanför bandet:** `roi_offset_y` fel — kör alignment eller sätt `null` (centrerat).
