# Nollplan & laserdrift — analys

Hur sätter och håller man **nollpunkten/nollplanet** för triangulering när lasrarna
lyser hela tiden och även träffar rullbanden mellan brädor? Sammanfattning först,
detaljer under.

> **Kort svar:** Låt lasrarna lysa **kontinuerligt** (CW). Tänd/släck dem INTE mellan
> brädor — det skadar stabilitet och livslängd. Att lasern träffar bandet är inget
> problem: **bandplanet ÄR nollan**. Sätt nollplanet med (1) en statisk kalibrering,
> (2) **auto-omnollning i varje brädmellanrum**, och helst (3) **fasta referensskenor**
> vid linjens ändar som ger absolut noll i varje bild — även mitt under en bräda.

---

## 1. Ska lasrarna tändas/släckas mellan brädor?

**Nej — håll dem på (CW).** Skäl:
- Våra linjelasrar är **CW-moduler** (ingen sluten/trigger). De har ingen nytta av
  att blinkas och är inte byggda för snabb cykling.
- **Termisk stabilitet:** en laserdiod driftar i **intensitet och våglängd** tills den
  nått jämvikt (sekunder–minuter). Tänd/släck → ständig uppvärmning → driftande
  stripe-intensitet och våglängd → sämre subpixel + filter-matchning. Håll dem
  varma och stabila.
- **Livslängd:** termisk cykling sliter på dioden.
- Profilkamerorna gör jobbet med **trigger/free-run + bandpassfilter** — vi *gatar
  databehandlingen* på brädnärvaro, vi behöver inte släcka ljuset.

**Enda legitima skälet att "släcka": SÄKERHET.** 100 mW synliga linjelasrar +
punktlasrarna är **klass 3B** (farliga för ögat). Mätzonen ska vara **inkapslad med
förreglat lucklås (interlock)** som bryter laser/slutare när skyddet öppnas. Det är
en skydds­funktion — inte en mätfunktion.

---

## 2. Nollplanet = transportplanet (bandet)

I triangulering mäter du **höjd relativt en referens**. Naturlig referens =
**bandets/transportens plan**. Tjocklek(x) = topp(x) − band(x).

Att lasern "skjuter nedanför nollplan och på rullbanden" är alltså **förväntat och
nyttigt** — den tomma-band-avläsningen *definierar* nollan. Tre nivåer:

### (a) Statisk kalibrering (en gång / vid behov)
Kör tomt band. Spela in laserlinjens läge **per X-position per kamera** → en
**band-baslinje B(x)** (bandet är inte perfekt plant/vågrätt → spara hela profilen,
inte ett enda tal). All mätning: `tjocklek(x) = topp(x) − B(x)`.
Punktlasrarna (LR400): tomt-band-avstånd `D0` → `tjocklek = D0 − avläst`.

### (b) Auto-omnollning i varje brädmellanrum (rekommenderas)
Mellan brädor faller linjen på bandet igen. Uppdatera B(x) löpande med ett
**långsamt glidande medel** av tomma-band-avläsningarna → kompenserar **drift,
bandslitage, temperatur, damm** automatiskt. Systemet **självkalibrerar** i varje
gap. Samma för LR400 (de sitter uppströms → ser bandet i gapet och omnollas).

### (c) Fasta referensskenor vid linjens ändar (bäst)
Montera **maskinbearbetade datum-skenor** i mätzonen, strax utanför brädans bredd,
så att laserlinjens **ändar alltid korsar en fast, känd yta** — även med en bräda i
mätfältet. Då får du **absolut noll + lutnings-/nivåkorrigering i VARJE bild**, utan
att vänta på ett gap. Det är så proffsskannrar gör. Kombinera med (b) som backup.

---

## 3. Brädnärvaro & segmentering
Lasern lyser jämt → vi avgör *när det finns en bräda* och klipper mätningen därefter:
- **Kantdetektion:** linjen "hoppar upp" från bandnivå till brädnivå (ledande kant)
  och tillbaka (bakkant). Trösklar på höjd över B(x).
- **Uppströms-signal:** LR400 (eller en **ljusbom/fotocell** vid inmatningen) ger
  brädnärvaro innan mätzonen → starta/stoppa loggning per bräda.
- I gapet: ingen bräda → använd avläsningen till **omnollning (b)**, inte till mätdata.

---

## 4. Praktiskt
- **Bandyta:** välj **matt, mörk, icke-speglande** yta (eller en matt referenslist) så
  linjen syns rent på bandet för nollan, utan spegelglans/överstyrning.
- **Bandpassfilter** gör att kamerorna i princip bara ser laserlinjen — omgivningsljus
  och bandets färg spelar liten roll; det är linjens *läge* som ger nollan.
- **Driftkällor att kompensera:** diod-temp (våglängd/intensitet), bandslitage/-spänning,
  vibration, termisk expansion i riggen. (b)+(c) täcker dessa kontinuerligt.
- **LR400-ankaret** (uppströms, utanför FOV) ger dessutom **absolut** tjocklek som
  låser trianguleringens globala offset/tilt — oberoende av bandplanets exakthet.

---

## 5. Koppling till programmet
- **Kalibrering-fliken:** "Trianguleringsplan" = sätt/lagra B(x) (statisk, (a)).
  "Punktlaser-nollning" = D0 för LR400. Lägg till **auto-omnollning** (b) som
  bakgrundsprocess + **referensskene-status** (c).
- **Behandling:** `fusion.anchor()` använder redan LR400 som absolut ankare; lägg till
  att dra bort band-baslinjen B(x) (relativt nollplan) före ankringen.
- **Telemetri:** visa **band-baslinje** + senaste omnollning + drift sedan kalibrering,
  och ett larm om driften överskrider en gräns (då behövs ny statisk kalibrering).
- **Säkerhet:** interlock-status i GUI; lasrar markeras "PÅ (CW)" och blockeras av
  förregling — aldrig cyklade per bräda.
