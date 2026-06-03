import { createRoot } from "react-dom/client";
import "./styles.css";

// Motorn (prototypens beprövade moduler) i samma laddningsordning som
// Virkesskanner.html. De fäster sina API:er på window.* (LineConfig, WoodGen,
// CutPlan, Scene, Panel, Readout) och måste laddas före sim.initSim().
import "./engine/config.js";
import "./engine/textures.js";
import "./engine/cutplan.js";
import "./engine/scene.js";
import "./engine/panel.js";
import "./engine/readout.js";

import App from "./App";

createRoot(document.getElementById("root")!).render(<App />);
