/* ============================================================
   sim.js — porterad från js/main.js: flerbrädskö, sidledsmatning,
   takt↔upplösning. State ligger i Zustand-storen (store.ts);
   motorn körs av React via initSim() i stället för DOMContentLoaded.
   Renderingen (Scene/Panel/Readout) och datakällan (WoodGen) är
   prototypens beprövade moduler – oförändrade.
   ============================================================ */
import { useSimStore } from "../store";
import { startPrefetch, takePatch, applyPatch } from "./source.js";

const N = 11;
const SENSOR_RATE = 758;     // sensorns radtakt (Hz), fast
const PX_LEN = 16364;        // px tvärs längden (5,4 m @ 0,33 mm)
const WU_MM = 5400 / 7;      // 1 världsenhet i mm (≈ 771)
let seed = 7, mIoUbase = 0.987, boardSeq = 0;
const boards = [];
const history = [];

// state-objektet bor i storen; vi muterar det in-place (motorn pollar varje tick)
const state = useSimStore.getState();

const makeData = () => {
  const d = window.WoodGen.makeBoard(seed++);  // alla lager (hjälpsensorer)
  d.id = ++boardSeq;
  const patch = takePatch();                   // riktig färg + segmentering om tillgänglig
  if (patch) applyPatch(d, patch);
  d.plan = window.CutPlan.plan(d.stats.features, state.lengths);

  // rundräkning (120 brädor/runda) – reaktivt för React-HUD:en
  const s = useSimStore.getState();
  let bir = s.boardInRound + 1, rnd = s.round;
  if (bir > s.perRound) { bir = 1; rnd += 1; }
  const lasers = patch && patch.laser ? ` · ${patch.laser.nLasers} lasrar` : "";

  // rundstatistik (nollställs vid ny runda)
  let rs = bir === 1 ? { n: 0, rejected: 0, valueSum: 0, defects: {} }
                     : { ...s.roundStats };
  rs.n += 1;
  if (patch && patch.lengthOk === false) rs.rejected += 1;
  rs.valueSum += d.plan ? d.plan.totalValue : 0;
  if (patch && patch.defects) for (const dd of patch.defects) rs.defects[dd.name] = (rs.defects[dd.name] || 0) + 1;

  const sensorBoard = patch && patch.colorPng ? {
    colorPng: patch.colorPng, heightPng: patch.heightPng,
    nLasers: patch.laser ? patch.laser.nLasers : 6,
    nSurfaceCams: patch.laser ? patch.laser.nSurfaceCams || 2 : 2,
    laserOverlapFrac: patch.laser ? patch.laser.laserOverlapFrac || 0.14 : 0.14,
    surfaceOverlapFrac: patch.laser ? patch.laser.surfaceOverlapFrac || 0.06 : 0.06,
  } : s.sensorBoard;

  useSimStore.setState({
    boardInRound: bir, round: rnd, roundStats: rs, sensorBoard,
    source: (patch ? patch.source : "syntetisk (lokal)") + lasers,
    lengthMm: patch && patch.lengthMm ? patch.lengthMm : 0,
    lengthDevMm: patch && patch.lengthDevMm != null ? patch.lengthDevMm : 0,
    lengthOk: patch ? patch.lengthOk !== false : true,
    defects: patch && patch.defects ? patch.defects : [],
  });
  return d;
};

const BW = () => window.Scene.getW();
const feedWorld = () => state.pitch * state.takt / 60;        // wu/s
const feedMps = () => feedWorld() * WU_MM / 1000;             // m/s bandhastighet
const alongRes = () => feedMps() * 1000 / SENSOR_RATE;        // mm/px längs matning
const coarse = () => Math.max(0, Math.min(1, (alongRes() - 0.15) / 0.7));
const ring = () => N * state.pitch;

function initBoards() {
  for (let i = 0; i < N; i++)
    boards.push({ data: makeData(), x: ((N - 1) / 2 - i) * state.pitch });
}
function respace() {
  const sorted = [...boards].sort((a, b) => b.x - a.x);
  const lead = sorted[0].x;
  sorted.forEach((b, i) => b.x = lead - i * state.pitch);
}

const developFrac = x => Math.max(0, Math.min(1, (BW() / 2 - x) / BW()));

function profileOf(data) {
  const { heightData, W, H } = data;
  const cx = Math.round(0.5 * W);
  const prof = []; let minT = 99, sum = 0, n = 0;
  for (let y = 0; y < H; y++) {
    const r = heightData[(y * W + cx) * 4];
    const t = 22 + (r / 255 - 0.5) * 12;
    prof.push(t);
    if (y > 6 && y < H - 6) { sum += t; n++; }
    if (t < minT) minT = t;
  }
  return { prof, thickness: sum / n, wane: Math.max(0, 22 - minT) };
}

function tick(dt) {
  if (state.playing) for (const b of boards) b.x -= feedWorld() * dt;
  state.time += dt;
  const lim = ring() / 2;
  for (const b of boards) if (b.x < -lim) { history.unshift(b.data); if (history.length > 4) history.pop(); b.x += ring(); b.data = makeData(); }

  window.Scene.syncBoards(boards);

  let act = boards[0];
  for (const b of boards) if (Math.abs(b.x) < Math.abs(act.x)) act = b;
  const frac = developFrac(act.x);

  const counts = [0, 0, 0, 0, 0, 0, 0], areas = [0, 0, 0, 0, 0, 0, 0];
  for (const f of act.data.stats.features) if (f.fv <= frac) { counts[f.cls]++; areas[f.cls] += f.area; }

  const dataRate = SENSOR_RATE * PX_LEN * 3 / 1e6;
  const p = profileOf(act.data);

  window.Scene.update({
    channel: state.channel, overlay: state.overlay, distort: state.distort,
    time: state.time, dispScale: state.dispScale, feed: feedWorld(),
    coarse: coarse(), cutOverlay: state.cutOverlay,
    showUnder: state.showUnder,
  });

  window.Panel.update({
    live: {
      lineRate: SENSOR_RATE, dataRate, bpm: Math.round(state.takt),
      thicknessMm: p.thickness, waneMm: p.wane, alongRes: alongRes(),
      miou: mIoUbase + Math.sin(state.time * 3) * 0.0008,
    },
    counts, areas, frac, board: act.data, channelIdx: state.channel,
    metrics: { fiberDev: act.data.stats.maxFiberDev, coarse: coarse() },
    plan: act.data.plan, cutOverlay: state.cutOverlay,
    underOn: state.showUnder,
    playing: state.playing, overlay: state.overlay, profile: p.prof,
  });

  window.Readout.update({
    active: act.data, frac, channel: state.channel,
    overlay: state.overlay, cutOverlay: state.cutOverlay, history,
  });
}

const ctrl = {
  setChannel: i => { state.channel = i; if (i === 3) state.overlay = 1; },
  setTrigger: i => { state.trigger = i; state.distort = i === 1 ? 1 : 0; },
  setTakt: v => state.takt = v,
  setSpacing: v => { state.pitch = v; respace(); },
  setWidth: mm => { state.widthWu = mm / WU_MM; window.Scene.setWidth(state.widthWu); },
  setLengths: arr => { state.lengths = arr; for (const b of boards) b.data.plan = window.CutPlan.plan(b.data.stats.features, state.lengths); },
  toggleCutPlan: () => state.cutOverlay = state.cutOverlay > 0.5 ? 0 : 1,
  toggleOverlay: () => state.overlay = state.overlay > 0.5 ? 0 : 1,
  togglePlay: () => state.playing = !state.playing,
  step: () => { for (const b of boards) { b.x -= 0.18; if (b.x < -ring() / 2) { history.unshift(b.data); if (history.length > 4) history.pop(); b.x += ring(); b.data = makeData(); } } },
  toggleUnder: v => state.showUnder = v,
};
window.__sim = state;

let started = false;
export function initSim() {
  if (started) return;            // skydd mot React StrictMode-dubbelkörning
  started = true;
  const canvas = document.getElementById("view");
  const stage = document.getElementById("stage");
  window.Scene.init(canvas);
  window.Panel.init(ctrl);
  window.Readout.init();
  window.Scene.setWidth(state.widthWu);
  startPrefetch(() => state.lengths);   // börja hämta riktiga brädor från backenden
  initBoards();

  const fit = () => { const r = stage.getBoundingClientRect(); window.Scene.resize(r.width, r.height); };
  new ResizeObserver(fit).observe(stage); fit();

  let last = performance.now();
  function loop(now) {
    let dt = (now - last) / 1000; last = now;
    if (dt > 0.1) dt = 0.1;
    tick(dt);
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
}
