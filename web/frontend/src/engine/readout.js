/* ============================================================
   readout.js — "Mätresultat": varje bräda utrullad platt medan
   den passerar mätramen. Aktuell bräda stor (vald kanal + facit
   + sågplan + tjockleksprofil längs brädan) + historik.
   ============================================================ */
(function () {
  const refs = {};

  function el(t, c, h) { const e = document.createElement(t); if (c) e.className = c; if (h != null) e.innerHTML = h; return e; }

  function card(isCur) {
    const wrap = el("div", "ro-card" + (isCur ? " cur" : " mini"));
    const head = el("div", "ro-head");
    const id = el("span", "ro-id", "");
    const st = el("span", "ro-st", "");
    const grade = el("span", "ro-grade", "");
    const val = el("span", "ro-val", "");
    head.appendChild(id); head.appendChild(st); head.appendChild(grade); head.appendChild(val);
    const strip = el("canvas", "ro-strip");
    wrap.appendChild(head); wrap.appendChild(strip);
    let prof = null;
    if (isCur) { prof = el("canvas", "ro-prof"); wrap.appendChild(prof); }
    return { wrap, id, st, grade, val, strip, prof };
  }

  function init() {
    const root = document.getElementById("readout");
    root.innerHTML = "";
    const t = el("div", "ro-title");
    t.appendChild(el("span", "ro-t", "MÄTRESULTAT"));
    t.appendChild(el("span", "ro-tsub", "skannas tvärs bredden medan den matas genom mätramen"));
    root.appendChild(t);
    refs.cur = card(true); root.appendChild(refs.cur.wrap);
    refs.histTitle = el("div", "ro-htitle", "Klassade brädor →");
    root.appendChild(refs.histTitle);
    const hl = el("div", "ro-hist"); root.appendChild(hl);
    refs.hist = []; for (let i = 0; i < 4; i++) { const c = card(false); hl.appendChild(c.wrap); refs.hist.push(c); }
  }

  function srcFor(data, ch) {
    if (ch === 2) return data.tracheid;
    if (ch === 1 || ch === 4) return data.height;
    return data.color;
  }

  function fit(cv, h) {
    const w = Math.max(80, cv.clientWidth || cv.parentElement.clientWidth || 600);
    if (cv.width !== w) cv.width = w;
    if (cv.height !== h) cv.height = h;
    return [cv.width, cv.height];
  }

  function drawStrip(cv, data, o) {
    const [W, H] = fit(cv, o.h); const ctx = cv.getContext("2d");
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = "#d9cdb2"; ctx.fillRect(0, 0, W, H);   // oskannad/blank
    // utveckling sker TVÄRS BREDDEN (kortsidan) — skannlinjen täcker hela längden
    const rev = Math.max(0, Math.min(1, o.frac)), rh = rev * H;
    const src = srcFor(data, o.channel);
    if (rev > 0) ctx.drawImage(src, 0, 0, src.width, rev * src.height, 0, 0, W, rh);
    // segmentering
    if ((o.channel === 3 || o.overlay) && rev > 0) {
      ctx.globalAlpha = 0.5;
      ctx.drawImage(data.label, 0, 0, data.label.width, rev * data.label.height, 0, 0, W, rh);
      ctx.globalAlpha = 1;
    }
    // sågplan (kaplinjer längs längden = vertikala; klipps till utvecklad bredd)
    if (o.cutOverlay && data.plan) {
      for (const p of data.plan.pieces) {
        const x0 = p.aU * W, x1 = p.bU * W;
        ctx.fillStyle = p.color; ctx.globalAlpha = 0.34; ctx.fillRect(x0, 0, x1 - x0, rh); ctx.globalAlpha = 1;
        ctx.strokeStyle = "rgba(12,12,12,0.7)"; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.moveTo(x0, 0); ctx.lineTo(x0, rh); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(x1, 0); ctx.lineTo(x1, rh); ctx.stroke();
        if (o.labels && rev > 0.55 && x1 - x0 > 46) {
          ctx.fillStyle = "#fff"; ctx.textAlign = "center";
          ctx.font = "600 12px 'IBM Plex Mono', monospace"; ctx.fillText(p.lenM.toFixed(1) + " m · " + p.grade, (x0 + x1) / 2, H / 2 - 1);
          ctx.font = "700 11px 'IBM Plex Sans', sans-serif"; ctx.fillText(p.value + " kr", (x0 + x1) / 2, H / 2 + 14);
        }
      }
    }
    // metermarkeringar (längd, horisontellt)
    const L = data.plan ? data.plan.L : 5.4;
    ctx.strokeStyle = "rgba(0,0,0,0.22)"; ctx.lineWidth = 1;
    for (let m = 1; m < L; m++) { const x = m / L * W; ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, o.labels ? 6 : 4); ctx.stroke(); }
    // skannlinje sveper tvärs bredden (horisontell, hela längden)
    if (rev < 1 && rev > 0) { ctx.fillStyle = "#e8542c"; ctx.fillRect(0, rh - 1.5, W, 3); }
    ctx.strokeStyle = "rgba(0,0,0,0.14)"; ctx.strokeRect(0.5, 0.5, W - 1, H - 1);
  }

  function drawProf(cv, data, frac) {
    const [W, H] = fit(cv, 62); const ctx = cv.getContext("2d");
    ctx.clearRect(0, 0, W, H); ctx.fillStyle = "#fbfaf7"; ctx.fillRect(0, 0, W, H);
    const hd = data.heightData, DW = data.W, DH = data.H, cy = Math.floor(DH / 2);
    const toY = mm => H - ((mm - 14) / 14) * (H - 10) - 5;
    // nominell 22 mm
    ctx.strokeStyle = "rgba(63,134,196,0.45)"; ctx.setLineDash([4, 3]);
    ctx.beginPath(); ctx.moveTo(0, toY(22)); ctx.lineTo(W, toY(22)); ctx.stroke(); ctx.setLineDash([]);
    if (frac <= 0) return;
    // hela längden på en gång (varje skannlinje täcker hela längden)
    ctx.beginPath();
    for (let px = 0; px < W; px++) {
      const col = Math.min(DW - 1, Math.floor(px / W * DW));
      let s = 0; for (let dy = -3; dy <= 3; dy++) s += hd[((cy + dy) * DW + col) * 4];
      const t = 22 + (s / 7 / 255 - 0.5) * 12;
      const y = toY(t); px === 0 ? ctx.moveTo(0, y) : ctx.lineTo(px, y);
    }
    ctx.strokeStyle = "#e8542c"; ctx.lineWidth = 1.6; ctx.stroke();
  }

  function gradeStr(plan) { return plan ? plan.pieces.map(p => p.grade + "·" + p.lenM.toFixed(1)).join(" + ") : ""; }

  function update(d) {
    const cd = d.active; if (!cd) return;
    drawStrip(refs.cur.strip, cd, { h: 104, frac: d.frac, channel: d.channel, overlay: d.overlay > 0.5, cutOverlay: d.cutOverlay > 0.5, labels: true });
    drawProf(refs.cur.prof, cd, d.frac);
    refs.cur.id.textContent = "Bräda #" + (cd.id || "—");
    const done = d.frac >= 0.999;
    refs.cur.st.textContent = done ? "✓ Klassad" : "Skannar " + Math.round(d.frac * 100) + "%";
    refs.cur.st.className = "ro-st " + (done ? "done" : "scan");
    refs.cur.grade.textContent = gradeStr(cd.plan);
    refs.cur.val.textContent = cd.plan ? cd.plan.totalValue + " kr" : "";

    for (let i = 0; i < 4; i++) {
      const h = refs.hist[i], hd = d.history[i];
      if (hd) {
        h.wrap.style.display = "";
        drawStrip(h.strip, hd, { h: 38, frac: 1, channel: d.channel, overlay: d.overlay > 0.5, cutOverlay: d.cutOverlay > 0.5, labels: false });
        h.id.textContent = "#" + (hd.id || "");
        h.st.textContent = "";
        h.grade.textContent = hd.plan ? hd.plan.pieces.map(p => p.grade).join("+") : "";
        h.val.textContent = hd.plan ? hd.plan.totalValue + " kr" : "";
      } else h.wrap.style.display = "none";
    }
  }

  window.Readout = { init, update };
})();
