# Virkesinspektion – simulering + segmentering (tvärmatad rigg)

En fristående simulering av den tvärmatade virkesinspektionen: brädan ligger
tvärs över transportkedjorna, glider i sidled genom en mätzon och avläses av en
line-scan-kamera + linjelaser. Ovanpå förvärvssimuleringen ligger en komplett
segmenteringspipeline (U-Net) som lär sig hitta defekterna pixelvis.

Allt kör och verifieras på CPU mot den syntetiska generatorn (inga
nedladdningar), och är förberett för att pekas mot Kodytek-datamängden och
tränas skarpt på GPU.

## Vad som ingår

1. **Förvärvsparametrar** (pixlar tvärs längden, radtakt, dataflöde) för
   prototypsektion och full 5,4 m längd vid olika upplösningar.
2. **Syntetiska brädor** med procedurell ådring och sex defektklasser
   (levande/död kvist, spricka, blånad, vankant, märg) + facit på pixelnivå.
3. **Förvärvssimulering**: encoder- kontra tidstriggning (geometrisk
   distorsion) och tjocklek/vankant ur en laserhöjdprofil.
4. **Segmenteringsmodell**: kompakt U-Net, träningsloop med CE + Dice och
   per-klass-IoU, samt inferens som kaklar och syr ihop en hel bräda.
5. **Kompletterande sensorkanaler**: fotometrisk stereo (riktade LED →
   relief/sprickor), tracheid-effekten (laserspridning → fiberriktning och
   snedfibrighet) och undersidesavbildning genom springorna mellan kedjorna.

## Geometri som modelleras

- Brädans **längd** (3,6–5,4 m) spänner tvärs mätzonen → sätter upplösningen.
- Brädans **bredd** (100–150 mm) passerar zonen i sidled → blir skanningsaxeln.
- 60 brädor/min → ~0,25 m/s i sidled → radtakten blir låg och oproblematisk.

## Köra

```bash
pip install -r requirements.txt

python run_demo.py        # bara förvärvssimuleringen (numpy + matplotlib)
python run_sensors.py     # fotometrisk stereo, tracheid, undersida (figur 5–7)
python run_pipeline.py    # hela flödet: förvärv -> data -> träning -> inferens
python run_pipeline.py --smoke   # minimal rökverifiering på sekunder

python -m src.train             # träna bara modellen (full config)
python -m src.train --smoke     # snabb rökverifiering av träningen
```

Figurer hamnar i `outputs/`:

- `1_board_labels.png` – syntetisk bräda + facit-etiketter
- `2_encoder_vs_time.png` – encoder-trigger vs tids-trigger (distorsion)
- `3_laser_profile.png` – tjocklek och vankant ur laserprofilen
- `4_segmentation.png` – facit vs modellens prediktion på en osedd bräda
- `5_photometric.png` – fotometrisk stereo: riktade LED → relief/sprickor
- `6_tracheid.png` – tracheid: fiberriktning + snedfibrighet (kvistindikator)
- `7_underside.png` – undersida synlig genom kedjespringorna

## Struktur

```
src/config.py        parametrar, förvärvsmått (LineConfig) + SegConfig
src/board.py         syntetisk bräda + defekter + facit + höjdkarta
src/acquisition.py   line-scan (encoder/tid) + laserprofil
src/metrics.py       utskrift av förvärvstabell
src/model.py         kompakt U-Net för segmentering
src/dataset.py       syntetiskt dataset (+ Kodytek-redo loader)
src/losses.py        CE + Dice, klassvikter, IoU-metrik
src/train.py         träningsloop med checkpointing
src/infer.py         kakla + sy ihop prediktion över en hel bräda
src/photometric.py   fotometrisk stereo: normaler + relief ur höjdkartan
src/tracheid.py      fiberriktning + snedfibrighet ur fiberfältet
src/underside.py     undersida + ocklusion från kedjespringorna
run_demo.py          kör förvärvssimuleringen och genererar figur 1–3
run_sensors.py       genererar sensorfigurerna 5–7
run_pipeline.py      hela flödet end-to-end och genererar figur 4
```

## Träna skarpt mot Kodytek på GPU

Modell- och träningskoden är ramverksidentisk på CPU och GPU. För skarp körning:

1. Installera ett GPU-bygge av torch (se `requirements.txt`).
2. Rastrera Kodyteks annoteringar till klass-id-masker (0..6, samma klasser som
   `config.CLASSES`) i layouten `root/images/*.png` + `root/masks/*.png`.
3. Byt loader i `src/dataset.py:make_loaders` från `SyntheticBoardDataset` till
   `KodytekDataset(cfg, root=...)`.
4. Höj `SegConfig` (fler brädor/epoker, större `base_channels`) och kör
   `python -m src.train` – `device="auto"` plockar upp GPU:n automatiskt.

## Nästa steg (konceptuellt, ej i koden ännu)

- Stacka sensorkanalerna (relief, fiberavvikelse) som extra ingångar till
  segmenteringsnätet utöver färg.
- Röntgen för inre defekter (märgspricka, inre kvist).
- Webbgränssnitt som visar hela flödet i 3D – se `web/DESIGN.md`.
