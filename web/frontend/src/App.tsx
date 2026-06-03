import { useEffect } from "react";
import { initSim } from "./engine/sim.js";

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
          </div>
        </div>
        <div id="readout" />
      </div>
      <aside id="panel" />
    </div>
  );
}
