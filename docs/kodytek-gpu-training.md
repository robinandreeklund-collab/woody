# Träna segmenteringsmodellen på Kodytek (GPU)

Steg-för-steg för att träna på den riktiga datan lokalt (t.ex. RTX 5090).
`device="auto"` plockar upp GPU:n automatiskt.

## 1. Hämta datasetet

Kodytek et al., *A large-scale image dataset of wood surface defects*
(Zenodo **10.5281/zenodo.4694695**, CC-BY 4.0). Produktionsbilderna är 2800×1024
(≈500×15 cm = en hel bräda) med färgkodade **semantiska kartor** (BMP) och
**bounding-box**-textfiler. 10 defektklasser.

Ladda ner och packa upp så att du har kataloger med bilder, semantiska kartor och
(valfritt) bounding boxes.

## 2. Rastrera annoteringar → klass-id-masker (GUI:ts 7 klasser)

```bash
# Semantiska kartor (pixelnoggrant). Färg→klass auto-härleds ur bbox+semantik:
python -m src.kodytek \
  --images "Kodytek/Images" \
  --semantic "Kodytek/Semantic Maps" \
  --bboxes  "Kodytek/Bounding Boxes" \
  --out data/kodytek

# Alternativ utan semantiska kartor (grövre, fyller boxarna):
python -m src.kodytek --images "Kodytek/Images" --bboxes "Kodytek/Bounding Boxes" \
  --out data/kodytek
```

Det skapar `data/kodytek/images/*.png` + `data/kodytek/masks/*.png` (pixelvärde =
klass-id 0..6).

### Klassmappning (Kodytek 10 → GUI 7)

Redigera `KODYTEK_TO_GUI` i `src/kodytek.py` vid behov. Standard:

| GUI-klass | Kodytek |
|---|---|
| 1 Kvist | live_knot, dead_knot, knot_with_crack |
| 2 Spricka | crack |
| 3 Blånad | blue_stain |
| 4 Vankant | overgrown |
| 5 Röta | resin, marrow, quartzity |
| 6 Hål | knot_missing |

## 3. Träna

```bash
python -c "
from src.config import SegConfig
from src.train import fit
fit(SegConfig.gpu_kodytek('data/kodytek'))
"
```

`SegConfig.gpu_kodytek` sätter en skarp GPU-konfig (tile 320, base 48, depth 4,
40 epoker, batch 16, `device='auto'`). Justera fritt – t.ex. höj `batch_size`
och `base_channels` för att utnyttja 5090:ans VRAM. Bästa checkpoint sparas till
`outputs/seg_kodytek.pt`.

## 4. Använd modellen

Backenden (`web/backend`) och `run_pipeline.py` laddar checkpointen automatiskt
via `find_checkpoint`. Peka `SegConfig.ckpt_name` på `seg_kodytek.pt` så kör
segmenteringen i GUI:t på den Kodytek-tränade modellen.
