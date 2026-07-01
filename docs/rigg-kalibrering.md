# Rigg-kalibrering — analys: helt automatiskt vs guidat manuellt

Rigg-kalibreringen knyter ihop hela pipelinen (triangulering → fusion → nollplan →
ankring → gradering). Den körs sist, när alla enheter är inkopplade och
per-enhet-kalibrerade. Tre metoder (GUI: Sensorer → "Riggen" → Kalibrering).

> ALLA tre kräver att **båda linjelasrarna är tända** (klass 3B) → de är **grindade**:
> rutinen tänder ALDRIG lasern själv, den mäter bara om operatören redan armat + tänt
> via interlock-kontrollen. Annars: *"tänd båda linjelasrarna via interlock-kontrollen först"*.

## Översikt — vad är auto, vad är manuellt

| Metod | Klass | Auto-del (systemet) | Manuell del (operatören, guidat) |
|---|---|---|---|
| `zeroplane` | **HELT AUTO** | Medlar 50 tomma-band-profiler → B(x), RMS, platthet → `data/zero.json` | Tömma mätzonen + arma laser |
| `align` | **AUTO + fysiskt mål** | Skannar klossen med båda huvuden → Z-offset/lutning/residual → `data/align.json` | Lägga referensklossen rätt + arma laser |
| `refboard` | **AUTO + facit** | Mäter tjocklek + bredd → jämför mot facit | Mäta brädan (facit), mata den, arma laser; längd via Y-svep |

Inget kräver mekanisk justering av vinklar — geometrin **kalibreras optiskt**
(se docs/alignment-calibration.md). Det enda fysiska är: tomt band / kloss / bräda.

---

## 1. `zeroplane` — Nollplan B(x)  [HELT AUTOMATISKT]
**Princip:** bandplanet ÄR nollan. Tjocklek(x) = topp(x) − B(x). Bandet är inte
perfekt plant → spara **hela profilen** B(x), inte ett tal (docs/zero-reference.md).

**Exakt guidning:**
1. **Töm mätzonen helt** — inga brädor, verktyg, spån eller damm på bandet i hela
   laserns bredd. (B(x) blir annars fel och allt mäts mot ett felaktigt noll.)
2. **Säkra rummet** (dörrinterlock, skyddsglasögon HM326-C) och **arma lasrarna**.
3. Tryck **Kör**. Systemet medlar 50 profiler — **rör inte riggen/bandet** under tiden.
4. Resultat: `bandprofil RMS` (profil-till-profil-brus, mål < 0,1 mm) + `platthet`
   (bandets ojämnhet). B(x) sparas i `data/zero.json`.

**Tips:** kör om periodiskt eller efter en smäll. Drift mellan körningar hanteras
dessutom av auto-omnollning i varje brädmellanrum (runtime, se zero-reference.md).

## 2. `align` — Huvud-alignment RÖD↔GRÖN  [AUTO + referenskloss]
**Princip:** RÖD och GRÖN ska se samma plan. Mät skillnaden i höjd/lutning mellan
huvudena på ett känt objekt → korrektion så de stämmer överens.

**Exakt guidning:**
1. **Lägg den maskinbearbetade referensklossen mitt i mätzonen, tvärs bandet**, så att
   **båda** huvuden ser hela dess ovansida (ingen skuggar). Klossen ska vara plan och
   stadig (rör sig inte under skanning).
2. **Säkra rummet + arma BÅDA lasrarna.**
3. Tryck **Kör**. Systemet skannar klossen med båda huvuden samtidigt.
4. Resultat: `Z-offset` (höjdskillnad), `lutning` (rotation över linjen), `residual`.
   **Godkänt: residual < 50 µm.** Korrektionen sparas i `data/align.json`.

**Om residual hög:** kontrollera att klossen är plan/ren, att båda lasrarna träffar
den, och att profilkamerornas ROI/exponering är kalibrerade (kör de stegen först).

## 3. `refboard` — Referensbräda end-to-end  [AUTO + facit]
**Princip:** systemets slutverifiering mot en bräda med **känt facit**.

**Exakt guidning:**
1. **Mät referensbrädan** med skjutmått/mikrometer och skapa `data/refboard.json`:
   ```json
   { "tjocklek": 22.05, "bredd": 75.10, "längd": 500.0 }
   ```
   (Utan facit rapporterar systemet bara uppmätta värden.)
2. **Mata brädan till mätzonen**, mot anhållet (fotocellen nollar positionen).
3. **Säkra rummet + arma lasrarna.**
4. Tryck **Kör**. Systemet mäter **tjocklek + bredd** och jämför mot facit
   (`tjocklek-fel`, `bredd-fel`). **Längd** kräver ett Y-svep med bandrörelse — kör
   det guidade steget (mata brädan genom mätzonen).
5. **Godkänn** om alla fel < tolerans (t.ex. tjocklek < 0,1 mm, längd < 0,5 mm),
   annars kalibrera om föregående steg (triangplane/zeroplane/align).

---

## Ordning vid idrifttagning (Fas D)
1. Per-enhet-kalibrering klar (profilkameror: exposure/stripe_roi/triangplane; LR400: zero_d0).
2. `zeroplane` (tomt band) → B(x).
3. `align` (kloss) → huvudkorrektion.
4. `refboard` (känd bräda + facit) → slutgodkännande.
5. `cfg.mode = "real"` → skarp drift; tona `grading_rules.py` mot SS-EN 1611-1 + referensbrädor.

## Persistensfiler
- `data/zero.json` — nollplan B(x) (lista) + antal medlade profiler.
- `data/align.json` — RÖD↔GRÖN Z-offset + lutning.
- `data/refboard.json` — facit (skapas av operatören före refboard).
