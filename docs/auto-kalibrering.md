# Automatisk kamerakalibrering

Kalibreringsmotorn (`app/core/calibration.py`) kör i real-läge **riktiga mätningar**
mot kamerorna via `app/core/autocalib.py` — inte längre bara simulerade värden.
Metoder som mäter helt automatiskt visas med **AUTO**-bricka i GUI:t (Sensorer →
klick på kamera → Kalibrering). Övriga (kräver fysiska mål) är guidade.

## Vad som mäts automatiskt

### Profilkameror (RÖD/GRÖN, mono laserstripe)
| Metod | AUTO | Vad den mäter / gör | Kräver |
|---|---|---|---|
| `exposure` | ✅ | Svep exponering → topp ≈ 200/255 (mättnadsfritt) + SNR. Skriver `ExposureTime`. | laser PÅ |
| `dark` | ✅ | Släcker lasern → medlar bakgrund → nivå + hotspots. | — |
| `stripe_roi` | ✅ | Hittar stripe-raden → sätter kamerans hårdvaru-ROI-offset (band centreras → 60 fps). | laser PÅ |
| `focus` | ✅ | Mäter stripe-FWHM (operatören justerar fokusringen mot utfallet). | laser PÅ |
| `intrinsics` | ⛔ | ChArUco i 15 poser → linsmodell. | fysiskt schackbräde |
| `triangplane` | ⛔ | Referenstrappa → px/mm i Z. | fysisk trappa |

### Ytkamera (linjekamera, färg)
| Metod | AUTO | Vad den mäter / gör | Kräver |
|---|---|---|---|
| `whitebal` | ✅ | Vitreferens → R/G/B-gain (grön=1,00). Skriver `BalanceRatio`. | vit yta i FOV |
| `flatfield` | ✅ | Jämn vit → per-kolumn-gain, ojämnhet före/efter. | jämn vit yta |
| `linesync` | ⛔ | Mata känd sträcka → rader/mm → divider. | rörelse + känt mått |
| `focusmtf` | ⛔ | Slanted-edge → MTF. | testmönster |

## ⚠️ Laser-säkerhet (klass 3B)
Auto-rutinerna **tänder ALDRIG** lasern. De släcker bara (alltid säkert, t.ex. `dark`)
eller förutsätter att operatören tänt lasern enligt metodens steg (rum låst,
dörrinterlock, glasögon HM326-C). Saknas stripen returnerar rutinen
`"ingen laserstripe sedd — tänd lasern (interlock!) och kör om"` i stället för att mäta.

## Så funkar det tekniskt
- **Rena mätfunktioner** i `autocalib.py` (numpy in → värden ut) — testade helt utan
  hårdvara (`app/tests/test_autocalib.py`).
- **`CalibrationContext`** ger rutinerna kameraåtkomst via HAL-scannern (grab-ramar,
  sätt exponering/ROI/vitbalans, släck laser).
- **`CalibrationRunner`** kör auto-rutinen i en **bakgrundstråd** i real-läge (GUI
  fryser inte); progress-stapeln håller ~97 % tills mätningen är klar, sen slutförs
  den med de uppmätta värdena (eller `fel` → röd status). I sim-läge: trovärdiga
  jittrade värden som förut.
- Resultat persisteras i `data/calibration.json`. Värden som ska tillämpas vid start
  (exponering, ROI-offset, vitbalans) bör även skrivas till `data/cameras.json`
  (se `docs/profilkameror-setup.md`).

## Idrifttagning
1. Anslut kameran, kör `python tools/jetson_selftest.py` → ANSLUTEN.
2. GUI: Sensorer → kamera → Kalibrering. Kör AUTO-metoderna i ordning:
   `stripe_roi` → (tänd laser, interlock) → `exposure` → `dark` → `focus`.
   Ytkamera: `whitebal` → `flatfield` med vit referens i FOV.
3. Spara tillämpningsvärden i `data/cameras.json` så de gäller vid nästa start.
