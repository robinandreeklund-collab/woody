/* ============================================================
   textures.js — procedurell virkesbräda, alla sensorkanaler
   Genererar per bräda: färg, facit (U-Net-mål), höjdkarta,
   fiberfält (tracheid), undersida + statistik.
   Axel X = längd, Y = bredd.  (jfr src/board.py)
   ============================================================ */
(function () {
  const W = 1400, H = 176;                 // px (längd × bredd) ~8:1
  const RES = 0.33;                        // nominell mm/px för areaberäkning
  const C = window.LineConfig.CLASSES;

  /* ---- seedad RNG ---- */
  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function cls(id, a = 1) {
    const r = C[id].rgb;
    return `rgba(${r[0]},${r[1]},${r[2]},${a})`;
  }

  /* ---- grundträ: pall spruce/furu med årsringar + ådring ---- */
  function paintBase(ctx, rng, hueShift) {
    const baseR = 224 + (rng() - 0.5) * 14;
    const baseG = 198 + (rng() - 0.5) * 12;
    const baseB = 152 + hueShift;
    ctx.fillStyle = `rgb(${baseR},${baseG},${baseB})`;
    ctx.fillRect(0, 0, W, H);

    // mjuk längsgradient (sågat virke ljusnar/mörknar)
    const g = ctx.createLinearGradient(0, 0, W, 0);
    g.addColorStop(0, "rgba(255,245,225,0.12)");
    g.addColorStop(0.5, "rgba(150,110,60,0.05)");
    g.addColorStop(1, "rgba(255,245,225,0.10)");
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);

    // ådring: många längsgående vågiga streck (grain)
    const lines = 150;
    for (let i = 0; i < lines; i++) {
      const y0 = (i / lines) * H + (rng() - 0.5) * 3;
      const amp = 1.5 + rng() * 4;
      const freq = 0.004 + rng() * 0.01;
      const phase = rng() * Math.PI * 2;
      const dark = rng() * 0.18 + 0.04;
      ctx.beginPath();
      ctx.moveTo(0, y0);
      for (let x = 0; x <= W; x += 6) {
        const y = y0 + Math.sin(x * freq + phase) * amp
          + Math.sin(x * freq * 3.1 + phase) * amp * 0.3;
        ctx.lineTo(x, y);
      }
      ctx.strokeStyle = `rgba(120,86,48,${dark})`;
      ctx.lineWidth = 0.6 + rng() * 1.2;
      ctx.stroke();
    }
    // breda katedralband
    for (let i = 0; i < 5; i++) {
      const cy = rng() * H, w = 30 + rng() * 60;
      const gg = ctx.createLinearGradient(0, cy - w, 0, cy + w);
      gg.addColorStop(0, "rgba(150,110,60,0)");
      gg.addColorStop(0.5, `rgba(150,110,60,${0.05 + rng() * 0.05})`);
      gg.addColorStop(1, "rgba(150,110,60,0)");
      ctx.fillStyle = gg; ctx.fillRect(0, cy - w, W, w * 2);
    }
  }

  /* ---- features ---- */
  function drawKnot(col, lab, hgt, rng, kx, ky, r, knots) {
    knots.push({ x: kx, y: ky, r });
    // ådring böjer runt kvisten (på färgkartan)
    for (let i = 0; i < 14; i++) {
      const off = (i - 7) * (r * 0.35);
      col.beginPath();
      for (let t = -1; t <= 1.001; t += 0.05) {
        const x = kx + t * r * 3.2;
        const bend = Math.exp(-((x - kx) * (x - kx)) / (r * r * 2)) * off * 1.4;
        const y = ky + off + bend * Math.sign(off || 1);
        if (t === -1) col.moveTo(x, y); else col.lineTo(x, y);
      }
      col.strokeStyle = `rgba(110,74,40,${0.10 + rng() * 0.08})`;
      col.lineWidth = 0.8; col.stroke();
    }
    // själva kvistkroppen
    const grd = col.createRadialGradient(kx, ky, 1, kx, ky, r);
    grd.addColorStop(0, "#3a2412");
    grd.addColorStop(0.45, "#5a3a1d");
    grd.addColorStop(0.8, "#7a5328");
    grd.addColorStop(1, "rgba(150,100,50,0)");
    col.fillStyle = grd;
    col.save(); col.translate(kx, ky); col.scale(1, 0.78);
    col.beginPath(); col.arc(0, 0, r, 0, 7); col.fill();
    // inre ringar
    for (let i = 0; i < 4; i++) {
      col.beginPath(); col.arc(0, 0, r * (0.3 + i * 0.18), 0, 7);
      col.strokeStyle = `rgba(30,18,8,${0.4 - i * 0.08})`;
      col.lineWidth = 0.8; col.stroke();
    }
    col.restore();
    // facit
    lab.fillStyle = cls(1);
    lab.save(); lab.translate(kx, ky); lab.scale(1, 0.78);
    lab.beginPath(); lab.arc(0, 0, r * 0.92, 0, 7); lab.fill(); lab.restore();
    // höjd: liten upphöjning (hårdare)
    const hg = hgt.createRadialGradient(kx, ky, 1, kx, ky, r * 1.1);
    hg.addColorStop(0, "rgba(200,200,200,0.7)");
    hg.addColorStop(1, "rgba(128,128,128,0)");
    hgt.fillStyle = hg; hgt.beginPath(); hgt.arc(kx, ky, r * 1.1, 0, 7); hgt.fill();
  }

  function drawCrack(col, lab, hgt, rng, x0, y0, len, dir) {
    let x = x0, y = y0; const pts = [[x, y]];
    const steps = Math.floor(len / 6);
    for (let i = 0; i < steps; i++) {
      x += 6 * dir + (rng() - 0.5) * 2;
      y += (rng() - 0.5) * 5;
      pts.push([x, y]);
    }
    const stroke = (c, w) => {
      col.beginPath(); col.moveTo(pts[0][0], pts[0][1]);
      for (const p of pts) col.lineTo(p[0], p[1]);
      col.strokeStyle = c; col.lineWidth = w; col.lineCap = "round"; col.stroke();
    };
    stroke("rgba(60,40,28,0.55)", 3.2);
    stroke("rgba(25,15,10,0.85)", 1.3);
    // facit
    lab.beginPath(); lab.moveTo(pts[0][0], pts[0][1]);
    for (const p of pts) lab.lineTo(p[0], p[1]);
    lab.strokeStyle = cls(2); lab.lineWidth = 5; lab.lineCap = "round"; lab.stroke();
    // höjd: spricka = grop
    hgt.beginPath(); hgt.moveTo(pts[0][0], pts[0][1]);
    for (const p of pts) hgt.lineTo(p[0], p[1]);
    hgt.strokeStyle = "rgba(40,40,40,0.8)"; hgt.lineWidth = 3.5; hgt.lineCap = "round"; hgt.stroke();
    return len * RES; // mm
  }

  function drawStain(col, lab, rng, cx, cy) {
    for (let i = 0; i < 8; i++) {
      const x = cx + (rng() - 0.5) * 160, y = cy + (rng() - 0.5) * 90;
      const r = 30 + rng() * 60;
      const g = col.createRadialGradient(x, y, 1, x, y, r);
      g.addColorStop(0, "rgba(70,90,130,0.30)");
      g.addColorStop(1, "rgba(70,90,130,0)");
      col.fillStyle = g; col.beginPath(); col.arc(x, y, r, 0, 7); col.fill();
      lab.fillStyle = cls(3, 0.95); lab.beginPath(); lab.arc(x, y, r * 0.55, 0, 7); lab.fill();
    }
  }

  function drawRot(col, lab, rng, cx, cy) {
    for (let i = 0; i < 7; i++) {
      const x = cx + (rng() - 0.5) * 140, y = cy + (rng() - 0.5) * 80;
      const r = 25 + rng() * 45;
      const g = col.createRadialGradient(x, y, 1, x, y, r);
      g.addColorStop(0, "rgba(120,110,70,0.40)");
      g.addColorStop(1, "rgba(120,110,70,0)");
      col.fillStyle = g; col.beginPath(); col.arc(x, y, r, 0, 7); col.fill();
      lab.fillStyle = cls(5, 0.95); lab.beginPath(); lab.arc(x, y, r * 0.5, 0, 7); lab.fill();
    }
  }

  function drawWane(col, lab, hgt, rng, x0, x1, top) {
    const band = 26 + rng() * 18;             // bredd på vankantbandet
    const yEdge = top ? 0 : H;
    const yIn = top ? band : H - band;
    // färg: rått/rundat virke + bark
    const g = col.createLinearGradient(0, yEdge, 0, yIn);
    g.addColorStop(0, "rgba(95,68,40,0.9)");
    g.addColorStop(0.5, "rgba(160,120,70,0.5)");
    g.addColorStop(1, "rgba(200,170,120,0)");
    col.fillStyle = g; col.fillRect(x0, Math.min(yEdge, yIn), x1 - x0, band);
    // barkfläckar
    for (let i = 0; i < 40; i++) {
      const x = x0 + rng() * (x1 - x0);
      const y = top ? rng() * band : H - rng() * band;
      col.fillStyle = `rgba(70,48,28,${0.2 + rng() * 0.3})`;
      col.fillRect(x, y, 2 + rng() * 4, 1 + rng() * 3);
    }
    // facit
    lab.fillStyle = cls(4, 0.9);
    lab.fillRect(x0, Math.min(yEdge, yIn), x1 - x0, band);
    // höjd: ramp ner mot kanten
    const hg = hgt.createLinearGradient(0, yEdge, 0, yIn);
    hg.addColorStop(0, "rgba(30,30,30,1)");
    hg.addColorStop(1, "rgba(128,128,128,0)");
    hgt.fillStyle = hg; hgt.fillRect(x0, Math.min(yEdge, yIn), x1 - x0, band);
    return (x1 - x0) * band * RES * RES; // mm²
  }

  function drawHole(col, lab, hgt, rng, cx, cy, r) {
    const g = col.createRadialGradient(cx - r * 0.2, cy - r * 0.2, 1, cx, cy, r);
    g.addColorStop(0, "#15100a");
    g.addColorStop(0.7, "#241810");
    g.addColorStop(1, "rgba(120,90,55,0.6)");
    col.fillStyle = g; col.beginPath(); col.arc(cx, cy, r, 0, 7); col.fill();
    col.strokeStyle = "rgba(90,65,40,0.6)"; col.lineWidth = 1.5; col.stroke();
    lab.fillStyle = cls(6); lab.beginPath(); lab.arc(cx, cy, r * 0.9, 0, 7); lab.fill();
    const hg = hgt.createRadialGradient(cx, cy, 1, cx, cy, r);
    hg.addColorStop(0, "rgba(20,20,20,1)");
    hg.addColorStop(1, "rgba(128,128,128,0)");
    hgt.fillStyle = hg; hgt.beginPath(); hgt.arc(cx, cy, r, 0, 7); hgt.fill();
  }

  /* ---- fiberfält (tracheid): flöde längs X, böjt runt kvistar ---- */
  function fiberAngle(x, y, knots) {
    let fx = 1, fy = 0;
    for (const k of knots) {
      const dx = x - k.x, dy = y - k.y;
      const d = Math.sqrt(dx * dx + dy * dy) + 1e-3;
      const infl = (k.r * 2.4) * Math.exp(-d / (k.r * 3.0));
      fx += (dx / d) * infl;
      fy += (dy / d) * infl;
    }
    return Math.atan2(fy, fx);
  }

  function renderTracheid(rng, knots) {
    const cv = document.createElement("canvas"); cv.width = W; cv.height = H;
    const ctx = cv.getContext("2d");
    ctx.fillStyle = "#0e1320"; ctx.fillRect(0, 0, W, H);
    let maxDev = 0;
    const step = 13;
    for (let y = step / 2; y < H; y += step) {
      for (let x = step / 2; x < W; x += step) {
        const a = fiberAngle(x, y, knots);
        const dev = Math.abs(a) * 180 / Math.PI;       // graders avvikelse
        if (dev > maxDev) maxDev = dev;
        const t = Math.min(dev / 35, 1);                // 0 frisk → 1 farlig
        // teal → amber → röd
        const r = Math.round(60 + t * 195);
        const g = Math.round(190 - t * 120);
        const b = Math.round(150 - t * 110);
        const len = 9 + t * 4;
        ctx.save(); ctx.translate(x, y); ctx.rotate(a);
        ctx.strokeStyle = `rgba(${r},${g},${b},${0.55 + t * 0.4})`;
        ctx.lineWidth = 1.6 + t;
        ctx.beginPath(); ctx.moveTo(-len / 2, 0); ctx.lineTo(len / 2, 0); ctx.stroke();
        ctx.restore();
      }
    }
    return { canvas: cv, maxDev };
  }

  /* ---- undersida: egen, enklare defektkarta ---- */
  function renderUnderside(rng, seed) {
    const r2 = mulberry32(seed * 7 + 13);
    const col = document.createElement("canvas"); col.width = W; col.height = H;
    const lab = document.createElement("canvas"); lab.width = W; lab.height = H;
    const cx = col.getContext("2d"), lx = lab.getContext("2d");
    lx.clearRect(0, 0, W, H);
    paintBase(cx, r2, -8);
    const knots = [];
    const nk = 1 + Math.floor(r2() * 3);
    for (let i = 0; i < nk; i++)
      drawKnot(cx, lx, cx, r2, 100 + r2() * (W - 200), 25 + r2() * (H - 50), 10 + r2() * 14, knots);
    if (r2() > 0.4) drawCrack(cx, lx, cx, r2, 150 + r2() * 600, 40 + r2() * 90, 120 + r2() * 220, 1);
    if (r2() > 0.6) drawStain(cx, lx, r2, 300 + r2() * 700, H / 2);
    return { color: col, label: lab };
  }

  /* ============================================================ */
  function makeBoard(seed) {
    const rng = mulberry32(seed * 2654435761 >>> 0);
    const color = document.createElement("canvas"); color.width = W; color.height = H;
    const label = document.createElement("canvas"); label.width = W; label.height = H;
    const height = document.createElement("canvas"); height.width = W; height.height = H;
    const col = color.getContext("2d"), lab = label.getContext("2d"), hgt = height.getContext("2d");

    lab.clearRect(0, 0, W, H);
    hgt.fillStyle = "rgb(128,128,128)"; hgt.fillRect(0, 0, W, H);
    paintBase(col, rng, (rng() - 0.5) * 16);

    const knots = [];
    const features = [];
    const counts = [0, 0, 0, 0, 0, 0, 0];
    const areas = [0, 0, 0, 0, 0, 0, 0];
    let crackLenMm = 0;

    const add = (clsId, u, area, fv) => { counts[clsId]++; areas[clsId] += area || 0; features.push({ cls: clsId, u, area: area || 0, fv: fv == null ? 0.5 : fv }); };

    // kvistar (2–5)
    const nk = 2 + Math.floor(rng() * 4);
    for (let i = 0; i < nk; i++) {
      const kx = 120 + rng() * (W - 240), ky = 30 + rng() * (H - 60), r = 11 + rng() * 17;
      drawKnot(col, lab, hgt, rng, kx, ky, r, knots);
      add(1, kx / W, Math.PI * r * r * 0.72 * RES * RES, ky / H);
    }
    // sprickor (0–3)
    const ncr = Math.floor(rng() * 4);
    for (let i = 0; i < ncr; i++) {
      const x0 = 80 + rng() * (W - 400), y0 = 25 + rng() * (H - 50), len = 90 + rng() * 300;
      const mm = drawCrack(col, lab, hgt, rng, x0, y0, len, rng() > 0.5 ? 1 : -1);
      crackLenMm += mm; add(2, x0 / W, len * 5 * RES * RES, y0 / H);
    }
    // blånad
    if (rng() > 0.45) { const cx = 250 + rng() * (W - 500); drawStain(col, lab, rng, cx, H / 2); add(3, cx / W, 4000, 0.5); }
    // vankant (stor area)
    if (rng() > 0.4) {
      const x0 = rng() * W * 0.5, x1 = x0 + 250 + rng() * 500, top = rng() > 0.5;
      const a = drawWane(col, lab, hgt, rng, x0, Math.min(x1, W), top);
      add(4, (x0 + x1) / 2 / W, a, top ? 0.12 : 0.88);
    }
    // röta
    if (rng() > 0.7) { const cx = 300 + rng() * (W - 600); drawRot(col, lab, rng, cx, H / 2); add(5, cx / W, 5000, 0.5); }
    // hål (0–2)
    const nh = Math.floor(rng() * 3);
    for (let i = 0; i < nh; i++) {
      const cx = 100 + rng() * (W - 200), cy = 30 + rng() * (H - 60), r = 5 + rng() * 7;
      drawHole(col, lab, hgt, rng, cx, cy, r); add(6, cx / W, Math.PI * r * r * RES * RES, cy / H);
    }

    const trach = renderTracheid(rng, knots);
    const under = renderUnderside(rng, seed);

    // höjddata för laserprofil-insticket
    const hData = hgt.getImageData(0, 0, W, H);

    return {
      W, H, RES,
      color, label, height,
      tracheid: trach.canvas,
      underColor: under.color, underLabel: under.label,
      heightData: hData.data,
      stats: {
        counts, areas, features,
        crackLenMm: Math.round(crackLenMm),
        maxFiberDev: Math.round(trach.maxDev),
        defectArea: areas.reduce((a, b) => a + b, 0),
      },
    };
  }

  window.WoodGen = { makeBoard, W, H };
})();
