/* Zustand-store — porterad från js/main.js `state`.
   Motorn (sim.js) läser/skriver denna; React-komponenter kan läsa den. */
import { create } from "zustand";

export interface SimState {
  channel: number;       // 0..4 huvudkanal
  overlay: number;       // 0/1 segmenteringsoverlay
  distort: number;       // 0/1 geometrisk distorsion (tids-trigg)
  trigger: number;       // 0 encoder / 1 tid
  takt: number;          // brädor/min
  pitch: number;         // medbringaravstånd (wu)
  widthWu: number;       // brädbredd (wu)
  lengths: number[];     // tillåtna kaplängder (m)
  cutOverlay: number;    // 0/1 sågplan-overlay
  time: number;
  playing: boolean;
  showUnder: boolean;
  dispScale: number;
  // rundor (uppdateras reaktivt av motorn)
  round: number;
  boardInRound: number;
  perRound: number;
  source: string;
  lengthMm: number;       // uppmätt brädlängd (laser)
  lengthDevMm: number;    // avvikelse mot nominell
  lengthOk: boolean;      // inom tolerans?
  strength: { cclass: string; limiting: string } | null;  // hållfasthetsklass
  defects: { name: string; posMm: number }[];
  // sensorvy (aktuell bräda) + rundstatistik
  sensorBoard: {
    id?: number;
    colorPng: string; heightPng: string;
    nLasers: number; nSurfaceCams: number;
    laserOverlapFrac: number; surfaceOverlapFrac: number;
    specs?: any; segments?: number[][] | null;
  } | null;
  roundStats: { n: number; rejected: number; valueSum: number; defects: Record<string, number> };
  straightness: {
    springCenterMm: number[]; bowCenterMm: number[]; win2mFrac: number;
    worstSpring: { a: number; b: number; sag: number };
    worstBow: { a: number; b: number; sag: number };
    springMm2m: number; bowMm2m: number; twistMm2m: number;
  } | null;
}

export const useSimStore = create<SimState>(() => ({
  channel: 0,
  overlay: 1,
  distort: 0,
  trigger: 0,
  takt: 60,
  pitch: 0.35,
  widthWu: 125 / (5400 / 7),
  lengths: [3.0, 2.7, 2.4],
  cutOverlay: 1,
  time: 0,
  playing: true,
  showUnder: true,
  dispScale: 1,
  round: 1,
  boardInRound: 0,
  perRound: 120,
  source: "startar …",
  lengthMm: 0,
  lengthDevMm: 0,
  lengthOk: true,
  strength: null,
  defects: [],
  sensorBoard: null,
  roundStats: { n: 0, rejected: 0, valueSum: 0, defects: {} },
  straightness: null,
}));
