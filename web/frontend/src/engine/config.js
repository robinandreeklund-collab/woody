/* ============================================================
   config.js — LineConfig + härledda mått (jfr src/config.py)
   ============================================================ */
(function () {
  // Defektklasser 0..6 (klass 0 = frisk, ingen overlay)
  const CLASSES = [
    { id: 0, namn: "Frisk",   hex: "#00000000", rgb: [0, 0, 0],       overlay: false },
    { id: 1, namn: "Kvist",   hex: "#d4953f",    rgb: [212, 149, 63],  overlay: true },
    { id: 2, namn: "Spricka", hex: "#d2533f",    rgb: [210, 83, 63],   overlay: true },
    { id: 3, namn: "Blånad",  hex: "#5577bd",    rgb: [85, 119, 189],  overlay: true },
    { id: 4, namn: "Vankant", hex: "#a072c4",    rgb: [160, 114, 196], overlay: true },
    { id: 5, namn: "Röta",    hex: "#6fa15c",    rgb: [111, 161, 92],  overlay: true },
    { id: 6, namn: "Hål",     hex: "#cf6f9e",    rgb: [207, 111, 158], overlay: true },
  ];

  const BASE = {
    lengthM: 5.4,        // brädans längd
    widthMm: 125,        // bredd
    thickMm: 22,         // tjocklek (nominell)
    boardsPerMin: 60,    // takt
    feedMps: 0.25,       // matningshastighet (sidled)
    mmPerPx: 0.33,       // upplösning
  };

  // Härleder geometri/datatakt (samma siffror som spec)
  function derive(mmPerPx, feedMps) {
    const res = mmPerPx;                          // mm/px
    const mPerPx = res / 1000;
    const pxLen = Math.round((BASE.lengthM * 1000) / res); // px tvärs längden
    const pxWid = Math.round(BASE.widthMm / res);          // px tvärs bredden
    const lineRate = feedMps / mPerPx;            // rad/s
    const dataRate = (lineRate * pxLen * 3) / 1e6; // MB/s (RGB, 8-bit)
    return { res, pxLen, pxWid, lineRate, dataRate };
  }

  window.LineConfig = { CLASSES, BASE, derive };
})();
