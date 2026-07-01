import { useEffect } from "react";
import { initSim } from "./engine/sim.js";
import { useSimStore } from "./store";
import { SensorView, StatsPanel, StraightnessView } from "./SensorPanels";

function RoundHud() {
  const round = useSimStore((s) => s.round);
  const bir = useSimStore((s) => s.boardInRound);
  const per = useSimStore((s) => s.perRound);
  const source = useSimStore((s) => s.source);
  const lengthMm = useSimStore((s) => s.lengthMm);
  const lengthDevMm = useSimStore((s) => s.lengthDevMm);
  const lengthOk = useSimStore((s) => s.lengthOk);
  const strength = useSimStore((s) => s.strength);
  const defects = useSimStore((s) => s.defects);
  const dev = lengthDevMm > 0 ? `+${lengthDevMm}` : `${lengthDevMm}`;
  const cColor: Record<string, string> = {
    C30: "#2f9e6e", C24: "#2f9e6e", C18: "#d6a23e", C14: "#cf6b46", Vrak: "#e8542c",
  };
  return (
    <>
      <div className="phase" style={{ marginTop: 4 }}>
        Runda {round} · bräda {bir}/{per} · {source}
      </div>
      {lengthMm > 0 && (
        <div className="phase" style={{ marginTop: 2 }}>
          <span style={{ color: lengthOk ? "#2f9e6e" : "#e8542c", fontWeight: 600 }}>
            {lengthOk ? "✓" : "✗"}
          </span>{" "}
          Uppmätt längd: {(lengthMm / 1000).toFixed(3)} m ({dev} mm)
          {strength && (
            <>
              {" · hållfasthet: "}
              <span style={{ color: cColor[strength.cclass] || "#25282c", fontWeight: 600 }}>
                {strength.cclass}
              </span>{" "}
              <span style={{ color: "#9a9ea4" }}>({strength.limiting})</span>
            </>
          )}
          {defects.length > 0 && (
            <>
              {" · fel: "}
              {defects
                .slice(0, 3)
                .map((d) => `${d.name} @${(d.posMm / 1000).toFixed(2)} m`)
                .join(", ")}
            </>
          )}
        </div>
      )}
    </>
  );
}

/* Skalet motsvarar Virkesskanner.html. Scene/Panel/Readout fyller
   #view / #panel / #readout. Motorn startas efter mount. */
export default function App() {
  useEffect(() => {
    initSim();
  }, []);

  return (
    <div id="app">
      <div id="left">
        <div id="stage">
          <canvas id="view" />
          <div className="hud hud-tl">
            <div className="eyebrow">Skanning → klassning → sågoptimering</div>
            <h1>Multisensor virkesskanner</h1>
          </div>
          <div className="hud hud-bl">
            <div className="phase">
              <span className="dot" /> Mätram aktiv ·{" "}
              <span id="hud-takt">60</span> brädor/min
            </div>
            <RoundHud />
          </div>
        </div>
        <div id="readout" />
        <StatsPanel />
        <StraightnessView />
        <SensorView />
      </div>
      <aside id="panel" />
    </div>
  );
}
