/* source.js — backend-datakälla med prefetch-buffert och fallback.
   Hämtar brädor (riktig färg + modellens segmentering + features + kapplan) från
   /api/next och patchar in dem i motorns brädobjekt. Om backenden är onåbar
   körs prototypens lokala generator (WoodGen) som tidigare. */

const BUF_TARGET = 4;
const buffer = [];
let seq = 1;
let backendOk = true;

function loadImage(dataUrl) {
  return new Promise((res) => {
    const im = new Image();
    im.onload = () => res(im);
    im.onerror = () => res(null);
    im.src = dataUrl;
  });
}

async function fetchOne(lengths) {
  try {
    const r = await fetch("/api/next", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seed: seq++, lengths }),
    });
    if (!r.ok) throw new Error("status " + r.status);
    const d = await r.json();
    const [colorImg, labelImg, heightImg] = await Promise.all([
      loadImage(d.color_png), loadImage(d.label_png), loadImage(d.height_png),
    ]);
    backendOk = true;
    return { colorImg, labelImg, heightImg, stats: d.stats, cutplan: d.cutplan,
             id: d.id, source: d.source, laser: d.laser,
             lengthMm: d.lengthMm, lengthDevMm: d.lengthDevMm, lengthOk: d.lengthOk,
             strength: d.strength, straightness: d.straightness,
             defects: d.defects, colorPng: d.color_png, heightPng: d.height_png };
  } catch (e) {
    backendOk = false;
    return null;
  }
}

export function startPrefetch(getLengths) {
  async function loop() {
    if (buffer.length < BUF_TARGET) {
      const item = await fetchOne(getLengths());
      if (item) buffer.push(item);
    }
    setTimeout(loop, backendOk ? 40 : 4000);
  }
  loop();
}

export function takePatch() {
  return buffer.length ? buffer.shift() : null;
}

export function backendAvailable() {
  return backendOk;
}

/* Patchar in riktig färg + segmentering + features i ett WoodGen-brädobjekt.
   Hjälplagren (höjd/tracheid/undersida) behålls från generatorn. */
export function applyPatch(d, patch) {
  const C = window.LineConfig.CLASSES;
  if (patch.colorImg) {
    d.color.getContext("2d").drawImage(patch.colorImg, 0, 0, d.W, d.H);
  }
  if (patch.labelImg) {
    const off = document.createElement("canvas");
    off.width = patch.labelImg.width; off.height = patch.labelImg.height;
    const ox = off.getContext("2d");
    ox.drawImage(patch.labelImg, 0, 0);
    const img = ox.getImageData(0, 0, off.width, off.height);
    const px = img.data;
    for (let i = 0; i < px.length; i += 4) {
      const cls = px[i];                 // klass-id ligger i R-kanalen
      const rgb = cls >= 1 && cls <= 6 ? C[cls].rgb : null;
      if (rgb) { px[i] = rgb[0]; px[i + 1] = rgb[1]; px[i + 2] = rgb[2]; px[i + 3] = 230; }
      else { px[i + 3] = 0; }
    }
    ox.putImageData(img, 0, 0);
    const lx = d.label.getContext("2d");
    lx.clearRect(0, 0, d.W, d.H);
    lx.drawImage(off, 0, 0, d.W, d.H);
  }
  if (patch.heightImg) {
    // höjdkartan kamerorna mätte (warp + laser-array) -> motorns höjdlager
    const hx = d.height.getContext("2d");
    hx.drawImage(patch.heightImg, 0, 0, d.W, d.H);
    d.heightData = hx.getImageData(0, 0, d.W, d.H).data;
  }
  d.laser = patch.laser;
  d.stats.features = patch.stats.features;
  d.stats.counts = patch.stats.counts;
  d.stats.areas = patch.stats.areas;
  if (patch.stats.crackLenMm != null) d.stats.crackLenMm = patch.stats.crackLenMm;
  if (patch.stats.defectArea != null) d.stats.defectArea = patch.stats.defectArea;
  d.source = patch.source;
}
