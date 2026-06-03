/* ============================================================
   panel.js — instrumentpanel: mätare, kanalväljare, defektlegend,
   laser-höjdprofil, sido-PiP (undersida), reglage.
   ============================================================ */
(function () {
  const C = window.LineConfig.CLASSES;
  const CHANNELS = ["Färg", "Relief", "Tracheid", "Segmentering", "Höjd"];
  const refs = {};

  function el(tag, cls, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }

  function section(title, hint) {
    const s = el("section", "sec");
    const h = el("div", "sec-h");
    h.appendChild(el("span", "sec-t", title));
    if (hint) h.appendChild(el("span", "sec-hint", hint));
    s.appendChild(h);
    return s;
  }

  function init(ctrl) {
    const root = document.getElementById("panel");
    refs.hudTakt = document.getElementById("hud-takt");

    /* header */
    const head = el("header", "p-head");
    head.appendChild(el("div", "logo", "◧"));
    const ht = el("div", "");
    ht.appendChild(el("div", "p-title", "VIRKESSKANNER"));
    ht.appendChild(el("div", "p-sub", "Line-scan · multisensor · U-Net"));
    head.appendChild(ht);
    refs.status = el("div", "status live", "● LIVE");
    head.appendChild(refs.status);
    root.appendChild(head);

    /* genomflöde */
    const flow = section("Genomflöde");
    const grid = el("div", "stat-grid");
    refs.lineRate = stat(grid, "rad/s", "—");
    refs.dataRate = stat(grid, "MB/s", "—");
    refs.bpm = stat(grid, "brädor/min", "—");
    flow.appendChild(grid);
    root.appendChild(flow);

    /* huvudvy / kanalväljare */
    const ch = section("Huvudvy", "sensor­kanal");
    refs.chan = el("div", "seg");
    CHANNELS.forEach((name, i) => {
      const b = el("button", "seg-b" + (i === 0 ? " on" : ""), name);
      b.onclick = () => { ctrl.setChannel(i); setChannel(i); };
      refs.chan.appendChild(b);
    });
    ch.appendChild(refs.chan);
    refs.chanCap = el("div", "chan-cap", "");
    ch.appendChild(refs.chanCap);
    root.appendChild(ch);

    /* laserprofil */
    const prof = section("Laser-höjdprofil", "tvärsnitt @ skannlinje");
    refs.profCv = el("canvas", "prof");
    refs.profCv.width = 320; refs.profCv.height = 96;
    prof.appendChild(refs.profCv);
    const pr = el("div", "prof-read");
    refs.thick = mini(pr, "Tjocklek", "— mm");
    refs.wane = mini(pr, "Vankant", "— mm");
    prof.appendChild(pr);
    root.appendChild(prof);

    /* sidosensorer (undersida) */
    const sens = section("Sidosensorer");
    const pips = el("div", "pip-row");
    refs.under = pip(pips, "Undersida", "via kedjespringor", ctrl.toggleUnder, true);
    sens.appendChild(pips);
    root.appendChild(sens);

    /* defekter */
    const def = section("Defekter", "U-Net · per klass");
    refs.legend = el("div", "legend");
    for (let i = 1; i <= 6; i++) {
      const row = el("div", "leg-row");
      const chip = el("span", "chip"); chip.style.background = C[i].hex;
      row.appendChild(chip);
      row.appendChild(el("span", "leg-n", C[i].namn));
      const cnt = el("span", "leg-c", "0");
      const ar = el("span", "leg-a", "0 cm²");
      row.appendChild(cnt); row.appendChild(ar);
      refs.legend.appendChild(row);
      refs["leg" + i] = { cnt, ar };
    }
    def.appendChild(refs.legend);
    const miou = el("div", "miou");
    miou.appendChild(el("span", "miou-l", "mIoU (osedd bräda)"));
    refs.miou = el("span", "miou-v", "0.987");
    miou.appendChild(refs.miou);
    def.appendChild(miou);
    root.appendChild(def);

    /* sågoptimering */
    const saw = section("Sågoptimering", "max värde / bräda");
    refs.sawCv = el("canvas", "saw-bar");
    refs.sawCv.width = 322; refs.sawCv.height = 56;
    saw.appendChild(refs.sawCv);
    const sg = el("div", "stat-grid");
    refs.sawVal = stat(sg, "kr / bräda", "—");
    refs.sawYield = stat(sg, "utbyte", "—");
    refs.sawPieces = stat(sg, "bitar", "—");
    saw.appendChild(sg);
    saw.appendChild(label("Tillåtna kaplängder"));
    const ll = el("div", "len-row"); refs.lenInputs = [];
    [3.0, 2.7, 2.4].forEach(v => {
      const f = el("div", "len-f");
      const inp = el("input", "len-i"); inp.type = "number"; inp.step = "0.1"; inp.min = "1"; inp.max = "6"; inp.value = v.toFixed(1);
      inp.onchange = () => ctrl.setLengths(refs.lenInputs.map(i => parseFloat(i.value) || 2.4));
      f.appendChild(inp); f.appendChild(el("span", "len-u", "m"));
      ll.appendChild(f); refs.lenInputs.push(inp);
    });
    saw.appendChild(ll);
    const sf = el("div", "saw-foot");
    refs.cutBtn = el("button", "btn on", "Sågplan PÅ");
    refs.cutBtn.onclick = () => ctrl.toggleCutPlan();
    sf.appendChild(refs.cutBtn);
    const gl = el("div", "grade-leg");
    [["C30", "#2f9e6e"], ["C24", "#5fae6a"], ["C18", "#d6a23e"], ["C14", "#cf6b46"], ["Vrak", "#8a8f96"]].forEach(([n, c]) => {
      const x = el("span", "gleg"); x.innerHTML = '<i style="background:' + c + '"></i>' + n; gl.appendChild(x);
    });
    sf.appendChild(gl);
    saw.appendChild(sf);
    root.appendChild(saw);

    /* reglage */
    const ctr = section("Reglage");
    // trigg
    refs.trig = el("div", "seg trig");
    ["Encoder", "Tid (jitter)"].forEach((t, i) => {
      const b = el("button", "seg-b" + (i === 0 ? " on" : ""), t);
      b.onclick = () => { ctrl.setTrigger(i); setTrigger(i); };
      refs.trig.appendChild(b);
    });
    ctr.appendChild(label("Triggning"));
    ctr.appendChild(refs.trig);
    refs.warn = el("div", "warn hidden", "⚠ Geometrisk distorsion — hastighetsjitter mot tids-trigg");
    ctr.appendChild(refs.warn);
    // sliders
    // takt -> upplösning
    ctr.appendChild(slider("Takt (brädor/min)", 20, 120, 5, 60, v => ctrl.setTakt(v),
      v => Math.round(v) + " /min", null));
    refs.resBox = el("div", "res-box");
    ctr.appendChild(refs.resBox);
    ctr.appendChild(slider("Bräddbredd", 70, 150, 5, 125, v => ctrl.setWidth(v),
      v => Math.round(v) + " mm", null));
    ctr.appendChild(slider("Medbringaravstånd", 0.25, 0.7, 0.02, 0.35, v => ctrl.setSpacing(v),
      v => Math.round(v * 714) + " mm", null));
    // overlay + transport
    const tog = el("div", "tog-row");
    refs.ovBtn = el("button", "btn on", "Segmentering PÅ");
    refs.ovBtn.onclick = () => ctrl.toggleOverlay();
    tog.appendChild(refs.ovBtn);
    refs.playBtn = el("button", "btn", "❚❚ Paus");
    refs.playBtn.onclick = () => ctrl.togglePlay();
    tog.appendChild(refs.playBtn);
    refs.stepBtn = el("button", "btn ghost", "Steg ▸");
    refs.stepBtn.onclick = () => ctrl.step();
    tog.appendChild(refs.stepBtn);
    ctr.appendChild(tog);
    root.appendChild(ctr);

    setChannel(0);
  }

  /* ---- byggblock ---- */
  function stat(parent, unit, val) {
    const t = el("div", "stat");
    const v = el("div", "stat-v", val);
    t.appendChild(v);
    t.appendChild(el("div", "stat-u", unit));
    parent.appendChild(t);
    return v;
  }
  function mini(parent, lab, val) {
    const m = el("div", "mini");
    m.appendChild(el("span", "mini-l", lab));
    const v = el("span", "mini-v", val);
    m.appendChild(v); parent.appendChild(m); return v;
  }
  function label(t) { return el("div", "ctl-l", t); }
  function slider(lab, min, max, step, def, onIn, fmt, store) {
    const w = el("div", "sld");
    const top = el("div", "sld-top");
    top.appendChild(el("span", "", lab));
    const val = el("span", "sld-v", fmt(def));
    top.appendChild(val); w.appendChild(top);
    const inp = el("input", "range"); inp.type = "range";
    inp.min = min; inp.max = max; inp.step = step; inp.value = def;
    inp.oninput = () => { val.textContent = fmt(parseFloat(inp.value)); onIn(parseFloat(inp.value)); };
    w.appendChild(inp); if (store) store(val); return w;
  }
  function pip(parent, title, sub, onToggle, on) {
    const card = el("div", "pip" + (on ? "" : " off"));
    const cv = el("canvas", "pip-cv"); cv.width = 180; cv.height = 40;
    card.appendChild(cv);
    const bar = el("div", "pip-bar");
    const tt = el("div", "");
    tt.appendChild(el("div", "pip-t", title));
    tt.appendChild(el("div", "pip-s", sub));
    bar.appendChild(tt);
    const sw = el("button", "sw on", "PÅ");
    sw.onclick = () => { const v = sw.classList.toggle("on"); sw.textContent = v ? "PÅ" : "AV"; card.classList.toggle("off", !v); onToggle(v); };
    bar.appendChild(sw);
    card.appendChild(bar); parent.appendChild(card);
    return { cv, card };
  }

  /* ---- tillståndssättning ---- */
  function setChannel(i) {
    [...refs.chan.children].forEach((b, k) => b.classList.toggle("on", k === i));
    const caps = [
      "RGB linjekamera — färg per pixel",
      "Fotometrisk stereo — riktade LED, sprickor & relief",
      "Tracheid-effekten — laserspridning visar fiberriktning",
      "U-Net per-pixel-segmentering",
      "Laserprofil — tjocklek & vankant via triangulering",
    ];
    refs.chanCap.textContent = caps[i];
  }
  function setTrigger(i) {
    [...refs.trig.children].forEach((b, k) => b.classList.toggle("on", k === i));
    refs.warn.classList.toggle("hidden", i === 0);
  }

  /* ---- per-frame uppdatering ---- */
  function update(d) {
    refs.lineRate.textContent = Math.round(d.live.lineRate).toLocaleString("sv-SE");
    refs.dataRate.textContent = d.live.dataRate.toFixed(1);
    refs.bpm.textContent = d.live.bpm;
    refs.thick.textContent = d.live.thicknessMm.toFixed(1) + " mm";
    refs.wane.textContent = d.live.waneMm.toFixed(1) + " mm";
    refs.miou.textContent = d.live.miou.toFixed(3);

    // kanal-caption metrik
    const ch = d.channelIdx;
    if (ch === 2) refs.chanCap.textContent = "Tracheid — max fiberavvikelse " + d.metrics.fiberDev + "°";
    else if (ch === 4) refs.chanCap.textContent = "Laserprofil — tjocklek " + d.live.thicknessMm.toFixed(1) + " mm";

    // defektlegend (löpande)
    for (let i = 1; i <= 6; i++) {
      refs["leg" + i].cnt.textContent = d.counts[i];
      refs["leg" + i].ar.textContent = (d.areas[i] / 100).toFixed(0) + " cm²";
    }
    drawProfile(d.profile);
    if (refs.resBox) {
      const ar = d.live.alongRes, sharp = Math.round((1 - d.metrics.coarse) * 5);
      refs.resBox.innerHTML = '<span class="res-l">Längsupplösning</span>' +
        '<span class="res-v">' + ar.toFixed(2) + ' mm/px</span>' +
        '<span class="res-d">' + '●'.repeat(sharp) + '<i>' + '○'.repeat(5 - sharp) + '</i></span>';
    }
    drawPiP(refs.under.cv, d.board.underColor, d.frac, "#cdbf9f", d.underOn);

    if (d.plan) {
      refs.sawVal.textContent = d.plan.totalValue;
      refs.sawYield.textContent = Math.round(d.plan.yield * 100) + "%";
      refs.sawPieces.textContent = d.plan.pieces.length;
      drawSawBar(d.plan);
    }
    refs.cutBtn.textContent = d.cutOverlay > 0.5 ? "Sågplan PÅ" : "Sågplan AV";
    refs.cutBtn.classList.toggle("on", d.cutOverlay > 0.5);

    refs.playBtn.textContent = d.playing ? "❚❚ Paus" : "▶ Spela";
    refs.ovBtn.textContent = d.overlay > 0.5 ? "Segmentering PÅ" : "Segmentering AV";
    refs.ovBtn.classList.toggle("on", d.overlay > 0.5);
    refs.status.className = "status " + (d.playing ? "live" : "paused");
    refs.status.textContent = d.playing ? "● LIVE" : "❚❚ PAUS";
    if (refs.hudTakt) refs.hudTakt.textContent = d.live.bpm;
  }

  function drawSawBar(plan) {
    const cv = refs.sawCv, ctx = cv.getContext("2d"), W = cv.width, H = cv.height;
    ctx.clearRect(0, 0, W, H);
    // brädbas (spill-ton)
    ctx.fillStyle = "#e7ddc8"; ctx.fillRect(0, 0, W, H);
    // spill-zoner (gap) med hatch
    const segs = [...plan.pieces].sort((a, b) => a.aU - b.aU);
    const gaps = []; let c = 0;
    for (const p of segs) { if (p.aU > c + 0.002) gaps.push([c, p.aU]); c = p.bU; }
    if (c < 0.998) gaps.push([c, 1]);
    ctx.strokeStyle = "rgba(110,110,110,0.4)"; ctx.lineWidth = 1;
    for (const [a, b] of gaps) {
      const x0 = a * W, x1 = b * W;
      ctx.save(); ctx.beginPath(); ctx.rect(x0, 0, x1 - x0, H); ctx.clip();
      ctx.fillStyle = "#ddd3bf"; ctx.fillRect(x0, 0, x1 - x0, H);
      ctx.strokeStyle = "rgba(120,120,120,0.45)";
      for (let x = x0 - H; x < x1; x += 6) { ctx.beginPath(); ctx.moveTo(x, H); ctx.lineTo(x + H, 0); ctx.stroke(); }
      ctx.restore();
      if (x1 - x0 > 16) { ctx.fillStyle = "#8a8f96"; ctx.font = "600 9px 'IBM Plex Mono', monospace"; ctx.textAlign = "center"; ctx.fillText("spill", (x0 + x1) / 2, H / 2 + 3); }
    }
    // bitar
    for (const p of plan.pieces) {
      const x0 = p.aU * W, x1 = p.bU * W;
      ctx.fillStyle = p.color; ctx.fillRect(x0, 0, x1 - x0, H);
      ctx.strokeStyle = "rgba(0,0,0,0.45)"; ctx.lineWidth = 1.5; ctx.strokeRect(x0 + 0.75, 0.75, x1 - x0 - 1.5, H - 1.5);
      ctx.fillStyle = "#fff"; ctx.textAlign = "center";
      ctx.font = "600 11px 'IBM Plex Mono', monospace"; ctx.fillText(p.lenM.toFixed(1) + " m", (x0 + x1) / 2, H / 2 - 3);
      ctx.font = "700 10px 'IBM Plex Sans', sans-serif"; ctx.fillText(p.grade + " · " + p.value + " kr", (x0 + x1) / 2, H / 2 + 12);
    }
    // metermarkeringar
    ctx.strokeStyle = "rgba(0,0,0,0.18)"; ctx.lineWidth = 1;
    for (let m = 1; m < plan.L; m++) { const x = m / plan.L * W; ctx.beginPath(); ctx.moveTo(x, H - 5); ctx.lineTo(x, H); ctx.stroke(); }
  }

  function drawProfile(prof) {
    const cv = refs.profCv, ctx = cv.getContext("2d");
    const W = cv.width, H = cv.height;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = "#fbfaf7"; ctx.fillRect(0, 0, W, H);
    // rutnät
    ctx.strokeStyle = "rgba(0,0,0,0.06)"; ctx.lineWidth = 1;
    for (let i = 1; i < 4; i++) { ctx.beginPath(); ctx.moveTo(0, H * i / 4); ctx.lineTo(W, H * i / 4); ctx.stroke(); }
    if (!prof || !prof.length) return;
    // nominell 22 mm linje
    const toY = mm => H - ((mm - 8) / (28 - 8)) * H;
    ctx.strokeStyle = "rgba(63,134,196,0.45)"; ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.moveTo(0, toY(22)); ctx.lineTo(W, toY(22)); ctx.stroke();
    ctx.setLineDash([]);
    // fyll under profil
    ctx.beginPath(); ctx.moveTo(0, H);
    for (let i = 0; i < prof.length; i++) ctx.lineTo(i / (prof.length - 1) * W, toY(prof[i]));
    ctx.lineTo(W, H); ctx.closePath();
    ctx.fillStyle = "rgba(232,84,44,0.10)"; ctx.fill();
    // profil-linje
    ctx.beginPath();
    for (let i = 0; i < prof.length; i++) {
      const x = i / (prof.length - 1) * W, y = toY(prof[i]);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.strokeStyle = "#e8542c"; ctx.lineWidth = 2; ctx.stroke();
  }

  function drawPiP(cv, src, frac, blank, on) {
    const ctx = cv.getContext("2d"), W = cv.width, H = cv.height;
    ctx.fillStyle = blank; ctx.fillRect(0, 0, W, H);
    const f = Math.max(0, Math.min(1, frac));
    if (src && f > 0) ctx.drawImage(src, 0, 0, src.width, f * src.height, 0, 0, W, f * H);
    // skannlinje sveper tvärs bredden
    if (f < 1 && f > 0) { ctx.fillStyle = "#e8542c"; ctx.fillRect(0, f * H - 1, W, 2); }
    if (!on) { ctx.fillStyle = "rgba(241,240,234,0.72)"; ctx.fillRect(0, 0, W, H); }
  }

  window.Panel = { init, update };
})();
