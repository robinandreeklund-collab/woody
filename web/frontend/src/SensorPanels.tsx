import { useEffect, useRef } from "react";
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

/* Ritar varje sensor som en separat ruta + en gemensam fusion (med överlapp). */
function drawMontage(cv: HTMLCanvasElement, url: string, n: number,
                     overlapFrac: number, colored: boolean) {
  const ctx = cv.getContext("2d")!;
  const img = new Image();
  img.onload = () => {
    const W = (cv.width = Math.max(280, cv.clientWidth || 600));
    const labelH = 14, tileH = 32, gap = 4, fuseH = 34;
    cv.height = labelH + tileH + 10 + fuseH;
    ctx.clearRect(0, 0, W, cv.height);
    const segs = tiles(n, overlapFrac);
    const tileW = (W - (n - 1) * gap) / n;
    ctx.font = "600 10px 'IBM Plex Mono', monospace";
    ctx.textAlign = "left"; ctx.fillStyle = "#9a9ea4";
    ctx.fillText(`${n} sensorer (separata)`, 0, 10);
    for (let i = 0; i < n; i++) {
      const [u0, u1] = segs[i], x = i * (tileW + gap), y = labelH;
      ctx.drawImage(img, u0 * img.width, 0, (u1 - u0) * img.width, img.height,
        x, y, tileW, tileH);
      ctx.strokeStyle = colored ? `hsl(${Math.round(i * 360 / n)},68%,46%)` : "#3f86c4";
      ctx.lineWidth = 2; ctx.strokeRect(x + 1, y + 1, tileW - 2, tileH - 2);
    }
    const fy = labelH + tileH + 10;
    ctx.fillStyle = "#9a9ea4"; ctx.fillText("fusion (hopsydd)", 0, fy - 2);
    ctx.drawImage(img, 0, 0, img.width, img.height, 0, fy, W, fuseH);
    ctx.fillStyle = "rgba(232,84,44,0.30)";          // överlappszoner
    for (let i = 0; i < n - 1; i++) {
      const a = segs[i + 1][0], b = segs[i][1];
      if (b > a) ctx.fillRect(a * W, fy, (b - a) * W, fuseH);
    }
    ctx.strokeStyle = "rgba(0,0,0,0.14)"; ctx.strokeRect(0.5, fy + 0.5, W - 1, fuseH - 1);
  };
  img.src = url;
}

export function SensorView() {
  const sb = useSimStore((s) => s.sensorBoard);
  const colorRef = useRef<HTMLCanvasElement>(null);
  const heightRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    if (!sb) return;
    if (colorRef.current)
      drawMontage(colorRef.current, sb.colorPng, sb.nSurfaceCams, sb.surfaceOverlapFrac, false);
    if (heightRef.current)
      drawMontage(heightRef.current, sb.heightPng, sb.nLasers, sb.laserOverlapFrac, true);
  }, [sb]);
  if (!sb) return null;
  return (
    <div className="sensorview">
      <div className="sv-h">SENSORVY — varje sensor separat + fusion</div>
      <div className="sv-sub">Färgkameror (yta)</div>
      <canvas ref={colorRef} className="sv-cv" />
      <div className="sv-sub">Profillasrar (höjd)</div>
      <canvas ref={heightRef} className="sv-cv" />
      <div className="sv-foot">
        {sb.nSurfaceCams} färgkameror · {sb.nLasers} laser/kamera-moduler ·{" "}
        <span style={{ color: "#e8542c" }}>rött</span> = överlapp som fusioneras
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
      <div className="stat-grid">
        <div className="stat"><b style={{ color: "#2f9e6e" }}>{approved}</b><span>godkända</span></div>
        <div className="stat"><b style={{ color: "#e8542c" }}>{rs.rejected}</b><span>kasserade (längd)</span></div>
        <div className="stat"><b>{avg} kr</b><span>snittvärde/bräda</span></div>
        <div className="stat"><b>{top ? `${top[0]} (${top[1]})` : "—"}</b><span>vanligaste fel</span></div>
      </div>
    </div>
  );
}
