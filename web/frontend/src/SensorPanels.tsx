import { useEffect, useRef, useState } from "react";
import { useSimStore } from "./store";

/* Delar upp [0,1] i n överlappande sensorsegment (samma logik som riggen). */
function tiles(n: number, overlapFrac: number): [number, number][] {
  const segLen = 1 / (n - (n - 1) * overlapFrac);
  const step = segLen * (1 - overlapFrac);
  const out: [number, number][] = [];
  for (let i = 0; i < n; i++) {
    const u1 = Math.min(1, i * step + segLen);
    out.push([Math.max(0, u1 - segLen), u1]);
  }
  return out;
}

/* Reservspecar (om backenden inte skickar – matchar src/hardware.py). */
const FALLBACK: any = {
  surface: { model: "MindVision MV-XGLC83BM-T4-90", n: 2, pxAcross: 8192, pixelUm: 7,
             mmPerPx: 0.33, fovMm: 2700, wdMm: 951, lensMm: 20, lineRateKHz: 27.5 },
  profile: { model: "Hikrobot MV-CS050-10UC", n: 6, pxLat: 2448, pixelUm: 3.45,
             mmPerPx: 0.449, segLenMm: 1098, overlapMm: 150, heightResMm: 0.78,
             wdMm: 1040, triAngle: 30, frameFps: 60, profileRateHz: 500,
             laser: "iadiy LM9R650H100L60" },
  boardLenMm: 5400, boardWidthMm: 150,
};

/* Ritar ett längdsegment [u0,u1] (full bredd) av en bräd-textur i en canvas. */
function drawCrop(cv: HTMLCanvasElement, url: string, u0: number, u1: number,
                 hPx: number, smooth = true, accent?: string) {
  const ctx = cv.getContext("2d")!;
  const img = new Image();
  img.onload = () => {
    const W = (cv.width = Math.max(60, cv.clientWidth || 160));
    const sw = (u1 - u0) * img.width;
    const H = (cv.height = hPx || Math.max(48, Math.round(W * img.height / sw)));
    ctx.clearRect(0, 0, W, H);
    ctx.imageSmoothingEnabled = smooth;
    ctx.drawImage(img, u0 * img.width, 0, sw, img.height, 0, 0, W, H);
    if (accent) { ctx.strokeStyle = accent; ctx.lineWidth = 2; ctx.strokeRect(1, 1, W - 2, H - 2); }
  };
  img.src = url;
}

/* En klickbar sensorruta (visar sitt utsnitt av brädan). */
function SensorTile({ url, u0, u1, label, accent, onClick }: any) {
  const ref = useRef<HTMLCanvasElement>(null);
  const sb = useSimStore((s) => s.sensorBoard);
  useEffect(() => { if (ref.current) drawCrop(ref.current, url, u0, u1, 64, true); }, [url, u0, u1, sb]);
  return (
    <button className="sv-tile" style={{ borderColor: accent }} onClick={onClick}
            title={`Öppna ${label} – se exakt vad kameran ser`}>
      <canvas ref={ref} className="sv-tile-cv" />
      <span className="sv-tile-lab" style={{ color: accent }}>{label}</span>
    </button>
  );
}

const Spec = ({ k, v }: any) => (
  <div className="sm-spec-i"><span>{k}</span><b>{v}</b></div>
);

/* Uppförstorad zoom-/panorerbar vy: hämtar SANN-upplösnings-utsnitt från
   backenden (regenererar brädan ur seed) och visar i rätt fysiska proportioner. */
function SensorDetail({ sb, specs, sel, tilesS, tilesP, onClose }: any) {
  const cvRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const dragRef = useRef<any>(null);
  const isSurf = sel.kind === "surface";
  const sp = isSurf ? specs.surface : specs.profile;
  const t = (isSurf ? tilesS : tilesP)[sel.idx];
  const accent = isSurf ? "#2f6fb0" : "#2f9e6e";
  const name = isSurf ? `YTKAMERA ${sel.idx + 1}` : `PROFILMODUL ${sel.idx + 1}`;
  const boardLen = specs.boardLenMm || 5400;
  const boardW = specs.boardWidthMm || 150;
  const pxAcross = isSurf ? sp.pxAcross : sp.pxLat;
  const seed = sb.id;
  const [win, setWin] = useState({ u0: t[0], u1: t[1], v0: 0, v1: 1 });
  const [crop, setCrop] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // hämta utsnitt när fönstret ändras (debouncat) — sann upplösning ur backenden
  useEffect(() => {
    if (seed == null) return;
    let cancel = false;
    setLoading(true);
    const tm = setTimeout(() => {
      fetch("/api/crop", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ seed, u0: win.u0, u1: win.u1, v0: win.v0, v1: win.v1, maxPx: 2000 }),
      }).then((r) => r.json()).then((d) => {
        if (cancel) return;
        const im = new Image();
        im.onload = () => { imgRef.current = im; setCrop(d); setLoading(false); };
        im.src = d.png;
      }).catch(() => { if (!cancel) setLoading(false); });
    }, 110);
    return () => { cancel = true; clearTimeout(tm); };
  }, [seed, win]);

  // rita utsnittet i fysiska proportioner + skalstock
  useEffect(() => {
    const cv = cvRef.current, im = imgRef.current; if (!cv || !im || !crop) return;
    const W = (cv.width = Math.min(1080, Math.max(320, cv.clientWidth || 900)));
    const spanLen = (win.u1 - win.u0) * boardLen, spanW = (win.v1 - win.v0) * boardW;
    const H = (cv.height = Math.max(60, Math.min(560, Math.round(W * spanW / Math.max(1, spanLen)))));
    const ctx = cv.getContext("2d")!;
    ctx.clearRect(0, 0, W, H);
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(im, 0, 0, W, H);
    const px100 = (100 / spanLen) * W;
    ctx.fillStyle = "rgba(20,22,26,0.78)"; ctx.fillRect(10, H - 26, px100 + 12, 18);
    ctx.fillStyle = "#fff"; ctx.font = "600 11px 'IBM Plex Mono', monospace";
    ctx.fillText("100 mm", 16, H - 13); ctx.fillRect(16, H - 9, px100, 2);
    ctx.strokeStyle = accent; ctx.lineWidth = 3; ctx.strokeRect(1.5, 1.5, W - 3, H - 3);
  }, [crop, win, accent, boardLen, boardW]);

  const zoomAt = (factor: number, fx: number, fy: number) => setWin((w) => {
    const du = w.u1 - w.u0, dv = w.v1 - w.v0;
    const cu = w.u0 + fx * du, cv2 = w.v0 + fy * dv;
    const nu = Math.min(1, Math.max(0.01, du * factor));
    const nv = Math.min(1, Math.max(0.02, dv * factor));
    const u0 = Math.min(Math.max(0, cu - fx * nu), 1 - nu);
    const v0 = Math.min(Math.max(0, cv2 - fy * nv), 1 - nv);
    return { u0, u1: u0 + nu, v0, v1: v0 + nv };
  });
  const onWheel = (e: any) => {
    e.preventDefault();
    const r = cvRef.current!.getBoundingClientRect();
    zoomAt(e.deltaY > 0 ? 1.25 : 0.8, (e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height);
  };
  const onDown = (e: any) => { dragRef.current = { x: e.clientX, y: e.clientY, win }; };
  const onMove = (e: any) => {
    if (!dragRef.current) return;
    const r = cvRef.current!.getBoundingClientRect();
    const g = dragRef.current.win, du = g.u1 - g.u0, dv = g.v1 - g.v0;
    const u0 = Math.min(Math.max(0, g.u0 - (e.clientX - dragRef.current.x) / r.width * du), 1 - du);
    const v0 = Math.min(Math.max(0, g.v0 - (e.clientY - dragRef.current.y) / r.height * dv), 1 - dv);
    setWin({ u0, u1: u0 + du, v0, v1: v0 + dv });
  };
  const onUp = () => { dragRef.current = null; };
  const reset = () => setWin({ u0: t[0], u1: t[1], v0: 0, v1: 1 });

  return (
    <div className="sm-backdrop" onClick={onClose}>
      <div className="sm-panel" onClick={(e) => e.stopPropagation()}>
        <div className="sm-head" style={{ borderColor: accent }}>
          <b style={{ color: accent }}>{name}</b> — {sp.model}
          <button className="sm-close" onClick={onClose}>✕</button>
        </div>
        <div className="sm-spec">
          {isSurf ? (<>
            <Spec k="Sensor" v={`${pxAcross} px tvärs · ${sp.pixelUm} µm`} />
            <Spec k="Riggens skala" v={`${sp.mmPerPx} mm/px · FOV ${sp.fovMm} mm`} />
            <Spec k="Radtakt / WD" v={`${sp.lineRateKHz} kHz · ${sp.wdMm} mm`} />
          </>) : (<>
            <Spec k="Sensor" v={`${pxAcross} px · ${sp.pixelUm} µm`} />
            <Spec k="Riggens skala" v={`${sp.mmPerPx} mm/px · seg ${sp.segLenMm} mm`} />
            <Spec k="Höjd / takt" v={`${sp.heightResMm} mm · ${sp.profileRateHz} prof/s`} />
          </>)}
          <Spec k="Utsnitt" v={crop ? `${crop.spanLenMm} × ${crop.spanWidthMm} mm` : "…"} />
          <Spec k="Källans uppl." v={crop ? `${crop.mmPerPx} mm/px (${crop.wPx}×${crop.hPx})` : "…"} />
          <Spec k="Zoom" v={`${(boardLen * (t[1] - t[0]) / (boardLen * (win.u1 - win.u0))).toFixed(1)}×`} />
        </div>
        <canvas ref={cvRef} className="sm-cv" style={{ cursor: "grab" }}
          onWheel={onWheel} onMouseDown={onDown} onMouseMove={onMove}
          onMouseUp={onUp} onMouseLeave={onUp} />
        <div className="sv-foot">
          {loading ? "hämtar utsnitt …" : "scrolla = zoom · dra = panorera · "}
          <b style={{ cursor: "pointer", color: accent }} onClick={reset}>återställ</b>
          {" · "}visas vid riggens skala (~{sp.mmPerPx} mm/px). Kodytek = hopsydda
          {" "}154 mm-sektioner (källa 0,06×0,15 mm/px).
        </div>
      </div>
    </div>
  );
}

export function SensorView() {
  const sb = useSimStore((s) => s.sensorBoard);
  const [sel, setSel] = useState<{ kind: "surface" | "profile"; idx: number } | null>(null);
  if (!sb) return null;
  const specs = sb.specs || FALLBACK;
  const tilesS = tiles(sb.nSurfaceCams, sb.surfaceOverlapFrac);
  const tilesP = tiles(sb.nLasers, sb.laserOverlapFrac);
  return (
    <div className="sensorview">
      <div className="sv-h">SENSORVY — klicka en sensor för att se exakt vad den ser</div>
      <div className="sv-sub">Färgkameror (yta) · {specs.surface.model} · {specs.surface.mmPerPx} mm/px</div>
      <div className="sv-tiles">
        {tilesS.map((t, i) => (
          <SensorTile key={"s" + i} url={sb.colorPng} u0={t[0]} u1={t[1]}
            label={`YTA ${i + 1}`} accent="#2f6fb0"
            onClick={() => setSel({ kind: "surface", idx: i })} />
        ))}
      </div>
      <div className="sv-sub">Profillasrar (höjd) · {specs.profile.model} · {specs.profile.mmPerPx} mm/px</div>
      <div className="sv-tiles">
        {tilesP.map((t, i) => (
          <SensorTile key={"p" + i} url={sb.heightPng} u0={t[0]} u1={t[1]}
            label={`M${i + 1}`} accent="#2f9e6e"
            onClick={() => setSel({ kind: "profile", idx: i })} />
        ))}
      </div>
      <div className="sv-foot">
        {sb.nSurfaceCams} färgkameror · {sb.nLasers} laser/kamera-moduler · klicka för
        uppförstorad vy med exakt upplösning och skalstock.
      </div>
      {sel && (
        <SensorDetail sb={sb} specs={specs} sel={sel}
          tilesS={tilesS} tilesP={tilesP} onClose={() => setSel(null)} />
      )}
    </div>
  );
}

/* En "bana": centerlinjen (vertikalt överdriven) + värsta 2 m-fönstret + korda. */
function drawLane(ctx: CanvasRenderingContext2D, arr: number[],
                 worst: { a: number; b: number; sag: number }, y0: number,
                 h: number, W: number, color: string, label: string) {
  const n = arr.length, mid = y0 + h / 2;
  const maxAbs = Math.max(2, worst.sag, ...arr.map((v) => Math.abs(v)));
  const scale = (h / 2 - 8) / maxAbs;
  // värsta 2 m-fönstret
  ctx.fillStyle = "rgba(47,158,110,0.16)";
  ctx.fillRect(worst.a * W, y0, (worst.b - worst.a) * W, h);
  // nollinje
  ctx.strokeStyle = "rgba(0,0,0,0.18)"; ctx.setLineDash([4, 3]);
  ctx.beginPath(); ctx.moveTo(0, mid); ctx.lineTo(W, mid); ctx.stroke(); ctx.setLineDash([]);
  // korda över värsta fönstret
  const ia = Math.round(worst.a * (n - 1)), ib = Math.round(worst.b * (n - 1));
  ctx.strokeStyle = "rgba(47,158,110,0.9)"; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(worst.a * W, mid - arr[ia] * scale);
  ctx.lineTo(worst.b * W, mid - arr[ib] * scale); ctx.stroke();
  // centerlinjen
  ctx.strokeStyle = color; ctx.lineWidth = 1.8; ctx.beginPath();
  for (let i = 0; i < n; i++) {
    const x = (i / (n - 1)) * W, y = mid - arr[i] * scale;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.stroke();
  ctx.fillStyle = "#6a6e74"; ctx.font = "600 10px 'IBM Plex Mono', monospace";
  ctx.textAlign = "left"; ctx.fillText(label, 4, y0 + 11);
}

function drawStraight(cv: HTMLCanvasElement, st: any) {
  const ctx = cv.getContext("2d")!;
  const W = (cv.width = Math.max(280, cv.clientWidth || 600));
  const laneH = 56, gap = 10;
  cv.height = laneH * 2 + gap;
  ctx.clearRect(0, 0, W, cv.height);
  drawLane(ctx, st.springCenterMm, st.worstSpring, 0, laneH, W, "#3f86c4",
    `kantkrok ${st.springMm2m} mm/2 m`);
  drawLane(ctx, st.bowCenterMm, st.worstBow, laneH + gap, laneH, W, "#e8542c",
    `planböj ${st.bowMm2m} mm/2 m`);
}

export function StraightnessView() {
  const st = useSimStore((s) => s.straightness);
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => { if (st && ref.current) drawStraight(ref.current, st); }, [st]);
  if (!st) return null;
  return (
    <div className="sensorview">
      <div className="sv-h">RAKHET — silhuettens centerlinje + värsta 2 m-fönstret</div>
      <canvas ref={ref} className="sv-cv" />
      <div className="sv-foot">
        kantkrok (lateral, ur silhuetten) · planböj (höjd, ur lasern) · skevhet{" "}
        {st.twistMm2m} mm/2 m ·{" "}
        <span style={{ color: "#2f9e6e" }}>grönt</span> = värsta 2 m-fönstret (sagitta)
      </div>
    </div>
  );
}

export function StatsPanel() {
  const rs = useSimStore((s) => s.roundStats);
  const round = useSimStore((s) => s.round);
  const per = useSimStore((s) => s.perRound);
  const avg = rs.n ? Math.round(rs.valueSum / rs.n) : 0;
  const entries = Object.entries(rs.defects).sort((a, b) => b[1] - a[1]);
  const top = entries[0];
  const approved = rs.n - rs.rejected;
  return (
    <div className="statspanel">
      <div className="sv-h">RUNDA {round} — STATISTIK ({rs.n}/{per})</div>
      <div className="rstat-grid">
        <div className="rstat"><b style={{ color: "#2f9e6e" }}>{approved}</b><span>godkända</span></div>
        <div className="rstat"><b style={{ color: "#e8542c" }}>{rs.rejected}</b><span>kasserade (längd)</span></div>
        <div className="rstat"><b>{avg} kr</b><span>snittvärde/bräda</span></div>
        <div className="rstat"><b>{top ? `${top[0]} (${top[1]})` : "—"}</b><span>vanligaste fel</span></div>
      </div>
    </div>
  );
}
