# Virkesinspektion – simulering (tvärmatad rigg)

En liten, fristående simulering av den tvärmatade virkesinspektionen vi
skissat: brädan ligger tvärs över transportkedjorna, glider i sidled genom
en mätzon, och avläses av en line-scan-kamera + linjelaser.

Simuleringen gör tre saker:

1. **Räknar förvärvsparametrar** (pixlar tvärs längden, radtakt, dataflöde)
   för både en prototypsektion och full 5,4 m längd, vid olika upplösningar.
2. **Genererar syntetiska brädor** med procedurell ådring och defekter
   (levande/död kvist, spricka, blånad, vankant, märg) – plus facit-etiketter
   på pixelnivå. Användbart både som test och för att utöka träningsdata.
3. **Simulerar själva förvärvet**: visar varför en line-scan måste triggas på
   pulsgivare (encoder) och inte på klocka, samt extraherar tjocklek och
   vankant ur en laserhöjdprofil.

## Geometri som modelleras

- Brädans **längd** (3,6–5,4 m) spänner tvärs mätzonen → sätter upplösningen.
- Brädans **bredd** (100–150 mm) passerar zonen i sidled → blir skanningsaxeln.
- 60 brädor/min → ~0,25 m/s i sidled → radtakten blir låg och oproblematisk.

## Köra

```bash
pip install -r requirements.txt
python run_demo.py
```

Figurer hamnar i `outputs/`:

- `1_board_labels.png` – syntetisk bräda + facit-etiketter
- `2_encoder_vs_time.png` – encoder-trigger vs tids-trigger (distorsion)
- `3_laser_profile.png` – tjocklek och vankant ur laserprofilen

## Struktur

```
src/config.py        parametrar + härledda förvärvsmått
src/board.py         syntetisk bräda + defekter + facit + höjdkarta
src/acquisition.py   line-scan (encoder/tid) + laserprofil
src/metrics.py       utskrift av förvärvstabell
run_demo.py          kör allt och genererar figurer
```

## Nästa steg

- Byt ut den syntetiska brädgeneratorn mot riktiga bilder, eller använd den
  för att förstärka den öppna Kodytek-datamängden (samma defektklasser).
- Koppla på en faktisk detektionsmodell där `run_demo` nu bara visar facit.
- Justera `LineConfig` i `src/config.py` när de verkliga måtten (delning
  mellan brädor, tjocklek, önskad mm/px) är fastställda.

## Lägga in i ett befintligt repo

```bash
cp -r wood-inspection-sim/ <ditt-repo>/
cd <ditt-repo>
git add wood-inspection-sim
git commit -m "Lägg till simulering av tvärmatad virkesinspektion"
```
