import { useEffect } from "react";
import { initSim } from "./engine/sim.js";
import { useSimStore } from "./store";

function RoundHud() {
  const round = useSimStore((s) => s.round);
  const bir = useSimStore((s) => s.boardInRound);
  const per = useSimStore((s) => s.perRound);
  const source = useSimStore((s) => s.source);
  return (
    <div className="phase" style={{ marginTop: 4 }}>
      Runda {round} · bräda {bir}/{per} · {source}
    </div>
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
      </div>
      <aside id="panel" />
    </div>
  );
}
