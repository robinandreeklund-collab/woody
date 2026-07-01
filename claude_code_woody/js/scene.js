/* ============================================================
   scene.js — Three.js: brädor ligger TVÄRS flera parallella
   kedjor och matas i SIDLED genom en mätbrygga vars skannlinje
   löper längs hela brädans längd (5 m).  Flerbrädskö.
   ============================================================ */
(function () {
  const T = window.THREE;

  // världsgeometri:  X = matning (sidled),  Z = brädans längd
  const BOARD_LEN = 7.0;     // längs Z (≙ 5 m)  ⇒ 1 wu ≈ 714 mm
  const REF_W = 1.0;         // referensbredd för geometri (skalas per bräda)
  let curW = 0.175;          // aktuell brädbredd (wu) ≙ 125 mm, ställbar
  const BOARD_THICK = 0.13;
  const SCAN_X = 0.0;
  const SAW_X = -2.4;        // kapstation – längre nedströms från mätramen
  const CHAIN_Z = [-3.0, -1.5, 0.0, 1.5, 3.0];

  const COL = {
    bg: 0xf1f0ea, floor: 0xe7e5df, grid: 0xcfccc4,
    metal: 0xc3c6ca, metalDark: 0x33373d, housing: 0x2b3036,
    frame: 0xc2a43e, dog: 0x5b616a,
    laser: 0xe8542c, tracheid: 0x33c98c, blue: 0x3f86c4,
    led: 0xfff4e0, blank: 0xd9cdb2,
  };

  let renderer, scene, camera;
  let laserStripes = [], laserFans = [], tracheidBeam, underBeam, ledRing = [];
  let labelSprites = [], lastActiveId = -1;   // flytande defektetiketter i 3D
  const NLAS = 6;                 // laser-/kameramoduler i array längs längden
  let sawBlades = [], pusherA, pusherB;
  let bladeStations = [];           // FASTA klingpositioner (wu) – ändras bara av kaplängderna
  const MWU = BOARD_LEN / 5.4;      // wu per meter
  const NOMINAL_M = 5.4;            // nominell brädlängd
  let chains = [];
  const slots = [];

  /* ---------- shader (oförändrad logik, distorsion längs matningsled = uv.y) ---------- */
  const VERT = `
    uniform sampler2D uHeightTex;
    uniform float uDisp;
    varying vec2 vUv;
    varying float vWorldX;
    void main(){
      vUv = uv;
      float h = texture2D(uHeightTex, uv).r;
      vec3 transformed = position + normal * (h - 0.5) * uDisp;
      vec4 wp = modelMatrix * vec4(transformed, 1.0);
      vWorldX = wp.x;
      gl_Position = projectionMatrix * viewMatrix * wp;
    }`;

  const FRAG = `
    precision highp float;
    uniform sampler2D uColorTex, uLabelTex, uHeightTex, uTrachTex;
    uniform float uChannel, uOverlay, uDistort, uTime, uLeadX, uCoarse;
    uniform float uCutOverlay, uPieceN, uPieceA[5], uPieceB[5];
    uniform vec3 uPieceCol[5];
    uniform vec3 uScanColor, uBlank, uLightDir;
    varying vec2 vUv;
    varying float vWorldX;

    vec3 colormap(float t){
      t = clamp(t,0.0,1.0);
      vec3 a=vec3(0.18,0.32,0.75), b=vec3(0.20,0.72,0.74),
           c=vec3(0.45,0.78,0.36), d=vec3(0.92,0.80,0.25), e=vec3(0.86,0.32,0.24);
      if(t<0.25) return mix(a,b,t/0.25);
      if(t<0.5)  return mix(b,c,(t-0.25)/0.25);
      if(t<0.75) return mix(c,d,(t-0.5)/0.25);
      return mix(d,e,(t-0.75)/0.25);
    }

    void main(){
      vec2 uv = vUv;
      if(uDistort > 0.001){
        float j = sin(uv.y*42.0 + uTime*2.2)*0.55 + sin(uv.y*131.0)*0.45;
        uv.y += j * 0.012 * uDistort;
      }
      // line-scan upplösning: kvantisera bygg-upp-axeln (matningsled = uv.y)
      // hög takt -> få rader -> grov bild;  låg takt -> många rader -> skarpt
      float lines = mix(200.0, 22.0, clamp(uCoarse,0.0,1.0));
      uv.y = (floor(uv.y * lines) + 0.5) / lines;

      bool scanned = vWorldX < uLeadX;      // matning -X: passerad = vänster om linjen
      float distBehind = uLeadX - vWorldX;

      float hv = texture2D(uHeightTex, uv).r;
      float e = 0.0026;
      float hL=texture2D(uHeightTex,uv-vec2(e,0.)).r;
      float hR=texture2D(uHeightTex,uv+vec2(e,0.)).r;
      float hD=texture2D(uHeightTex,uv-vec2(0.,e)).r;
      float hU=texture2D(uHeightTex,uv+vec2(0.,e)).r;
      vec3 nrm = normalize(vec3((hL-hR)*5.0,(hD-hU)*5.0,1.0));
      float diff = max(dot(nrm, normalize(uLightDir)), 0.0);

      vec3 wood = texture2D(uColorTex, uv).rgb;
      vec3 layer;
      if(uChannel < 0.5){ layer = wood * (0.78 + 0.30*diff); }
      else if(uChannel < 1.5){
        float sh = 0.45 + 0.62*diff;
        float edge = clamp(1.0 - hv*1.0, 0.0, 1.0);
        layer = vec3(sh) * vec3(0.90,0.93,1.0);
        layer = mix(layer, vec3(0.95,0.55,0.40), edge*edge*0.6);
      } else if(uChannel < 2.5){ layer = texture2D(uTrachTex, uv).rgb * (0.85+0.2*diff); }
      else if(uChannel < 3.5){ layer = wood * (0.80 + 0.25*diff); }
      else { layer = colormap((hv-0.35)/0.5) * (0.7 + 0.4*diff); }

      vec3 base = scanned ? layer : uBlank * (0.82 + 0.30*diff);

      vec4 lab = texture2D(uLabelTex, uv);
      float ovEff = (uChannel > 2.5 && uChannel < 3.5) ? max(uOverlay,0.85) : uOverlay;
      float band = clamp(distBehind/0.4, 0.0, 1.0);
      float ov = lab.a * ovEff * band * (scanned ? 1.0 : 0.0);
      base = mix(base, lab.rgb, ov*0.55);

      // sågplan: kvalitetsfärg per bit + kaplinjer (tvärs brädan)
      if(uCutOverlay > 0.5 && scanned){
        for(int k=0;k<5;k++){
          if(float(k) >= uPieceN) break;
          if(vUv.x >= uPieceA[k] && vUv.x < uPieceB[k]) base = mix(base, uPieceCol[k], 0.34);
          float dl = min(abs(vUv.x - uPieceA[k]), abs(vUv.x - uPieceB[k]));
          base = mix(base, vec3(0.05), smoothstep(0.005, 0.0, dl));
        }
      }

      float g = smoothstep(0.10, 0.0, abs(vWorldX - uLeadX));
      base = mix(base, uScanColor, g*0.9);
      float fresh = smoothstep(0.22,0.0,distBehind) * step(0.0,distBehind);
      base += uScanColor * fresh * 0.18;

      gl_FragColor = vec4(base, 1.0);
    }`;

  function box(w, h, d, color, o) {
    o = o || {};
    const mesh = new T.Mesh(new T.BoxGeometry(w, h, d), new T.MeshStandardMaterial({
      color, roughness: o.rough != null ? o.rough : 0.7, metalness: o.metal != null ? o.metal : 0.1,
      emissive: o.emissive || 0x000000, emissiveIntensity: o.emissiveIntensity || 1,
      transparent: !!o.transparent, opacity: o.opacity != null ? o.opacity : 1,
    }));
    mesh.castShadow = !o.noShadow; mesh.receiveShadow = !o.noShadow;
    return mesh;
  }

  function init(canvas) {
    renderer = new T.WebGLRenderer({ canvas, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = T.PCFSoftShadowMap;

    scene = new T.Scene();
    scene.background = new T.Color(COL.bg);
    scene.fog = new T.Fog(COL.bg, 30, 56);

    camera = new T.PerspectiveCamera(40, 1, 0.1, 100);
    camera.position.set(5.6, 9.4, 8.4);
    camera.lookAt(0, -0.2, 0.2);

    scene.add(new T.HemisphereLight(0xffffff, 0xcfcabd, 0.85));
    const key = new T.DirectionalLight(0xffffff, 1.1);
    key.position.set(7, 12, 6); key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048);
    key.shadow.camera.near = 1; key.shadow.camera.far = 44;
    const s = 9;
    key.shadow.camera.left = -s; key.shadow.camera.right = s;
    key.shadow.camera.top = s; key.shadow.camera.bottom = -s;
    key.shadow.bias = -0.0004; scene.add(key);
    const fill = new T.DirectionalLight(0xffffff, 0.35);
    fill.position.set(-8, 5, -4); scene.add(fill);

    const floor = new T.Mesh(new T.PlaneGeometry(70, 50),
      new T.MeshStandardMaterial({ color: COL.floor, roughness: 0.95 }));
    floor.rotation.x = -Math.PI / 2; floor.position.y = -0.6; floor.receiveShadow = true; scene.add(floor);
    const grid = new T.GridHelper(70, 70, COL.grid, COL.grid);
    grid.position.y = -0.599; grid.material.opacity = 0.32; grid.material.transparent = true; scene.add(grid);

    buildConveyor();
    buildGantry();
    buildKapstation();
    return { renderer, scene, camera };
  }

  /* ---------- conveyor: parallella kedjor längs X med springor ---------- */
  function buildConveyor() {
    // yttre ram-balkar
    for (const z of [-3.7, 3.7]) {
      const rail = box(28, 0.2, 0.22, COL.metal, { rough: 0.5, metal: 0.6 });
      rail.position.set(0, -0.22, z); scene.add(rail);
    }
    // tvärbalkar (chassi) under
    for (const x of [-9, -3, 3, 9]) {
      const cb = box(0.3, 0.16, 7.6, COL.metalDark, { rough: 0.5, metal: 0.5, noShadow: true });
      cb.position.set(x, -0.34, 0); scene.add(cb);
    }
    // kontinuerliga kedjesträngar (77 mm) längs matningsled, en per CHAIN_Z
    chains = [];
    for (const z of CHAIN_Z) {
      const strand = box(28, 0.05, 0.108, 0x4a4e54, { rough: 0.4, metal: 0.7, noShadow: true });
      strand.position.set(0, -0.12, z); scene.add(strand);
    }
    // undersidesensor i springan mellan kedja@0 och kedja@1.5
    const us = box(0.5, 0.4, 0.6, COL.housing, { rough: 0.4 });
    us.position.set(SCAN_X, -0.5, 0.75); scene.add(us);
    const lens = box(0.16, 0.04, 0.4, 0x0c0f14, { emissive: COL.blue, emissiveIntensity: 0.5, rough: 0.2, noShadow: true });
    lens.position.set(SCAN_X, -0.28, 0.75); scene.add(lens);
    underBeam = new T.Mesh(new T.ConeGeometry(0.22, 0.42, 16, 1, true),
      new T.MeshBasicMaterial({ color: COL.blue, transparent: true, opacity: 0.16, side: T.DoubleSide, depthWrite: false }));
    underBeam.position.set(SCAN_X, -0.05, 0.75); scene.add(underBeam);
  }

  /* ---------- mätbrygga längs Z (hela brädlängden) ---------- */
  function sheet(xTop, yTop, xBot, yBot, zHalf, color, op) {
    const geo = new T.BufferGeometry();
    geo.setAttribute("position", new T.BufferAttribute(new Float32Array([
      xTop, yTop, -zHalf, xTop, yTop, zHalf, xBot, yBot, zHalf,
      xTop, yTop, -zHalf, xBot, yBot, zHalf, xBot, yBot, -zHalf,
    ]), 3));
    geo.computeVertexNormals();
    return new T.Mesh(geo, new T.MeshBasicMaterial({ color, transparent: true, opacity: op, side: T.DoubleSide, depthWrite: false }));
  }

  function buildGantry() {
    const g = new T.Group();
    for (const z of [-3.9, 3.9]) {
      const post = box(0.24, 3.2, 0.24, COL.frame, { rough: 0.55, metal: 0.3 });
      post.position.set(SCAN_X, 0.95, z); g.add(post);
    }
    const beam = box(0.36, 0.36, 8.0, COL.frame, { rough: 0.55, metal: 0.3 });
    beam.position.set(SCAN_X, 2.55, 0); g.add(beam);

    // färgkodade sensormoduler längs bryggan
    const mod = (z, color, emi) => {
      const stalk = box(0.08, 0.5, 0.08, COL.frame, { rough: 0.55, metal: 0.3 });
      stalk.position.set(SCAN_X, 2.32, z); g.add(stalk);
      const m = box(0.46, 0.3, 0.5, color, emi ? { emissive: emi, emissiveIntensity: 0.5 } : {});
      m.position.set(SCAN_X, 2.02, z); g.add(m);
    };
    mod(-2.4, COL.metalDark, COL.laser);     // profillaser
    mod(-0.8, COL.housing);                  // RGB-kamera
    mod(0.8, COL.metalDark, COL.tracheid);   // tracheidlaser

    // LED-ring runt RGB-kameran (fotometrisk stereo)
    ledRing = [];
    for (let i = 0; i < 10; i++) {
      const a = (i / 10) * Math.PI * 2;
      const led = new T.Mesh(new T.SphereGeometry(0.05, 12, 12),
        new T.MeshStandardMaterial({ color: 0x222, emissive: COL.led, emissiveIntensity: 0.15 }));
      led.position.set(SCAN_X + Math.cos(a) * 0.34, 1.78, -0.8 + Math.sin(a) * 0.28);
      g.add(led); ledRing.push(led);
    }

    // Laser-array (cross-feed, alt A): NLAS moduler längs LÄNGDEN (Z). Varje
    // laserlinje löper LÄNGS sitt längdsegment (~1100 mm) med överlapp; brädan
    // matas i -X genom planet och varje modul profilerar sitt segment.
    laserStripes = []; laserFans = [];
    const segWu = (1100 / 5400) * BOARD_LEN;              // segmentlängd i wu
    const stepWu = ((1100 - 150) / 5400) * BOARD_LEN;     // steg (segment − överlapp)
    for (let i = 0; i < NLAS; i++) {
      let zc = -BOARD_LEN / 2 + segWu / 2 + i * stepWu;   // segmentcentrum längs Z
      zc = Math.min(zc, BOARD_LEN / 2 - segWu / 2);
      // ljusstripe på ytan, LÄNGS längdsegmentet (tunn i X = laserlinjebredd)
      const strip = new T.Mesh(new T.BoxGeometry(0.014, 0.01, segWu),
        new T.MeshBasicMaterial({ color: COL.laser, transparent: true, opacity: 0.95, depthWrite: false }));
      strip.position.set(SCAN_X, 0.034, zc);
      g.add(strip); laserStripes.push(strip);
      // laserblad (vertikal sheet längs segmentet) som triangulerar
      const fan = new T.Mesh(new T.PlaneGeometry(segWu, 1.9),
        new T.MeshBasicMaterial({ color: COL.laser, transparent: true, opacity: 0.1,
          side: T.DoubleSide, depthWrite: false }));
      fan.rotation.y = Math.PI / 2;                       // planet spänner Z (längd) × Y (höjd)
      fan.position.set(SCAN_X, 0.98, zc);
      g.add(fan); laserFans.push(fan);
    }
    tracheidBeam = sheet(SCAN_X + 0.25, 1.78, SCAN_X + 0.05, 0.03, BOARD_LEN / 2 * 0.92, COL.tracheid, 0.1); g.add(tracheidBeam);

    scene.add(g);
  }

  /* ---------- kapstation nedströms: dynamisk kapbalk + sortering ---------- */
  function buildKapstation() {
    const g = new T.Group();
    for (const z of [-3.95, 3.95]) {
      const post = box(0.2, 2.0, 0.2, COL.metal, { rough: 0.4, metal: 0.55 });
      post.position.set(SAW_X, 0.4, z); g.add(post);
    }
    const beam = box(0.3, 0.3, 8.1, COL.metal, { rough: 0.4, metal: 0.55 });
    beam.position.set(SAW_X, 1.45, 0); g.add(beam);
    const hus = box(0.5, 0.42, 1.0, COL.housing, { rough: 0.4 });
    hus.position.set(SAW_X, 1.18, 0); g.add(hus);
    // FASTA klingor: en pool skivor som sitter still vid SAW_X. Deras
    // längdpositioner sätts av Tillåtna kaplängder (setSawLengths) och ändras
    // ENBART när man ändrar kaplängderna i GUI – inte per bräda.
    // Disc i XY-planet (axel längs Z) kapar tvärs brädan vid en fast längdposition.
    sawBlades = [];
    for (let i = 0; i < 6; i++) {
      const blade = new T.Mesh(new T.CylinderGeometry(0.34, 0.34, 0.03, 36),
        new T.MeshStandardMaterial({ color: 0xeef2f6, metalness: 0.85, roughness: 0.25 }));
      blade.rotation.x = Math.PI / 2;
      blade.position.set(SAW_X, 0.12, 0); blade.visible = false; g.add(blade);
      const tab = box(0.16, 0.1, 0.06, COL.laser, { emissive: COL.laser, emissiveIntensity: 0.4, noShadow: true });
      tab.position.set(SAW_X, 1.28, 0); tab.visible = false; g.add(tab);
      sawBlades.push({ blade, tab });
    }
    // sidoknuffar (klaffar): UPPSTRÖMS sågen. De trycker brädan i ±Z (höger/
    // vänster) i god tid INNAN den når klingorna, så snitten linjerar mot de
    // fasta klingorna. De sitter inte ihop med klingorna.
    const mkPush = z => { const p = box(0.5, 0.32, 0.5, COL.dog, { rough: 0.5, metal: 0.4 }); p.position.set(SAW_X + 0.85, -0.02, z); g.add(p); return p; };
    pusherA = mkPush(3.95); pusherB = mkPush(-3.95);
    scene.add(g);
    setSawLengths([3.0, 2.7, 2.4]);     // standard tills GUI:t sätter riktiga
  }

  // Girig packning av nominell brädlängd med tillåtna kaplängder -> snittlinjer
  // (meter från referensänden). Endast detta styr de fasta klingornas läge.
  function packStations(lengths) {
    const avail = [...lengths].filter(l => l > 0).sort((a, b) => b - a);
    const cuts = []; let used = 0;
    if (avail.length) {
      const smallest = avail[avail.length - 1];
      while (NOMINAL_M - used > smallest - 1e-6 && cuts.length < 6) {
        const pick = avail.find(l => l <= NOMINAL_M - used + 1e-6);
        if (pick == null) break;
        used += pick;
        if (NOMINAL_M - used > 1e-3) cuts.push(used);   // intern snittlinje
      }
    }
    return cuts;
  }

  // Sätter de FASTA klingornas Z-läge utifrån tillåtna kaplängder (anropas av
  // GUI:t när kaplängderna ändras – annars rör sig klingorna aldrig).
  function setSawLengths(lengths) {
    const ZREF = -BOARD_LEN / 2;       // referensände (inmatning)
    bladeStations = packStations(lengths).map(m => ZREF + m * MWU);
    if (!sawBlades.length) return;
    for (let i = 0; i < sawBlades.length; i++) {
      const { blade, tab } = sawBlades[i];
      if (i < bladeStations.length) {
        tab.position.z = blade.position.z = bladeStations[i];
        blade.visible = tab.visible = true;
      } else blade.visible = tab.visible = false;
    }
  }
  /* ---------- flytande defektetiketter (sprites) ---------- */
  function makeLabelSprite() {
    const cv = document.createElement("canvas"); cv.width = 256; cv.height = 64;
    const tx = new T.CanvasTexture(cv);
    const sp = new T.Sprite(new T.SpriteMaterial({ map: tx, depthTest: false, transparent: true }));
    sp.scale.set(1.4, 0.35, 1); sp.visible = false; sp.userData = { cv, tx };
    scene.add(sp); return sp;
  }
  function setLabel(sp, text, rgb) {
    const { cv, tx } = sp.userData, c = cv.getContext("2d");
    c.clearRect(0, 0, 256, 64);
    c.fillStyle = "rgba(20,22,26,0.85)"; c.fillRect(2, 2, 252, 60);
    c.fillStyle = `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`; c.fillRect(12, 22, 18, 18);
    c.fillStyle = "#fff"; c.font = "600 28px 'IBM Plex Sans', sans-serif"; c.textBaseline = "middle";
    c.fillText(text, 40, 34);
    tx.needsUpdate = true;
  }
  function updateLabels(act) {
    if (labelSprites.length === 0) for (let i = 0; i < 6; i++) labelSprites.push(makeLabelSprite());
    const feats = ((act && act.data.stats && act.data.stats.features) || [])
      .filter(f => f.cls >= 1).sort((a, b) => (b.area || 0) - (a.area || 0)).slice(0, 6);
    const fresh = act && act.data.id !== lastActiveId;
    const C = window.LineConfig.CLASSES;
    for (let i = 0; i < labelSprites.length; i++) {
      const sp = labelSprites[i], f = feats[i];
      if (!f) { sp.visible = false; continue; }
      sp.visible = true;
      sp.position.set(act.x, 0.55, (f.u - 0.5) * BOARD_LEN);   // följer brädan i X
      if (fresh) {
        const pos = (f.posMm != null ? f.posMm : f.u * 5400) / 1000;
        const cls = C[f.cls] || { namn: "?", rgb: [40, 40, 40] };
        setLabel(sp, `${cls.namn} ${pos.toFixed(1)} m`, cls.rgb);
      }
    }
    if (act) lastActiveId = act.data.id;
  }

  function tex(canvas) {
    const t = new T.CanvasTexture(canvas);
    t.colorSpace = T.NoColorSpace;
    t.wrapS = t.wrapT = T.ClampToEdgeWrapping;
    t.minFilter = T.LinearFilter; t.magFilter = T.LinearFilter;
    t.anisotropy = renderer.capabilities.getMaxAnisotropy();
    return t;
  }

  function makeSlot() {
    const group = new T.Group();
    group.rotation.y = Math.PI / 2;        // brädans längd längs Z
    const topGeo = new T.PlaneGeometry(BOARD_LEN, REF_W, 240, 48);  // fler segment tvärs bredden -> vrid/skål syns
    topGeo.rotateX(-Math.PI / 2);
    const mat = new T.ShaderMaterial({
      uniforms: {
        uColorTex: { value: null }, uLabelTex: { value: null },
        uHeightTex: { value: null }, uTrachTex: { value: null },
        uChannel: { value: 0 }, uOverlay: { value: 0 }, uDistort: { value: 0 },
        uTime: { value: 0 }, uLeadX: { value: SCAN_X }, uDisp: { value: 0.16 }, uCoarse: { value: 0 },
        uCutOverlay: { value: 0 }, uPieceN: { value: 0 },
        uPieceA: { value: new Array(5).fill(0) },
        uPieceB: { value: new Array(5).fill(0) },
        uPieceCol: { value: Array.from({ length: 5 }, () => new T.Color(0, 0, 0)) },
        uScanColor: { value: new T.Color(COL.laser) },
        uBlank: { value: new T.Color(COL.blank) },
        uLightDir: { value: new T.Vector3(0.4, 0.55, 0.85).normalize() },
      }, vertexShader: VERT, fragmentShader: FRAG,
    });
    const top = new T.Mesh(topGeo, mat); top.position.y = 0.0;
    group.add(top);
    const body = new T.Mesh(new T.BoxGeometry(BOARD_LEN, BOARD_THICK, REF_W),
      new T.MeshStandardMaterial({ color: COL.blank, roughness: 0.85 }));
    body.position.y = -BOARD_THICK / 2 - 0.005; body.castShadow = true; body.receiveShadow = true;
    group.add(body);
    group.position.x = 99;
    group.scale.z = curW;
    scene.add(group);
    // runda medbringare (50 mm Ø), en per kedjesträng, bakom brädan
    const dogs = new T.Group();
    const dogMat = new T.MeshStandardMaterial({ color: 0x2c2f34, roughness: 0.4, metalness: 0.6 });
    for (const z of CHAIN_Z) {
      const d = new T.Mesh(new T.CylinderGeometry(0.035, 0.035, 0.14, 14), dogMat);
      d.position.set(0, -0.05, z); d.castShadow = true; dogs.add(d);
    }
    scene.add(dogs);
    return { group, mat, dataRef: null, texes: [], dogs };
  }

  // Inriktningsförskjutning (±Z, wu): hur långt klaffarna ska skjuta brädan så
  // att kapplanens startände trimmas mot referensänden och snitten linjerar mot
  // de fasta klingorna. Stabil per bräda (cache:ad).
  function alignZFor(data) {
    if (data._alignZ != null) return data._alignZ;
    let a = 0;
    if (data.plan && data.plan.pieces.length) {
      const aU0 = data.plan.pieces[0].aU || 0;   // trim före första biten
      a = -aU0 * BOARD_LEN;
    }
    data._alignZ = Math.max(-0.8, Math.min(0.8, a));
    return data._alignZ;
  }

  // arr: [{data, x}]  -> skapar/uppdaterar slots, laddar texturer vid behov
  function syncBoards(arr) {
    while (slots.length < arr.length) slots.push(makeSlot());
    for (let i = 0; i < arr.length; i++) {
      const s = slots[i], e = arr[i];
      if (s.dataRef !== e.data) {
        s.texes.forEach(t => t.dispose());
        const tc = tex(e.data.color), tl = tex(e.data.label), th = tex(e.data.height), tt = tex(e.data.tracheid);
        s.mat.uniforms.uColorTex.value = tc; s.mat.uniforms.uLabelTex.value = tl;
        s.mat.uniforms.uHeightTex.value = th; s.mat.uniforms.uTrachTex.value = tt;
        s.texes = [tc, tl, th, tt]; s.dataRef = e.data;
      }
      s.group.position.x = e.x;
      // klaffarna riktar brädan i ±Z UPPSTRÖMS sågen och den hålls kvar (ingen
      // studs): rampar klart vid SAW_X+0.5, dvs i god tid innan klingorna.
      const AX = SAW_X + 1.2, BX = SAW_X + 0.5;
      const t = Math.max(0, Math.min(1, (AX - e.x) / (AX - BX)));
      s.group.position.z = alignZFor(e.data) * t;
      s.dogs.position.x = e.x + curW / 2 + 0.05;  // rund medbringare bakom brädan (matning -X)
      const pl = e.data.plan;
      if (pl) {
        const u = s.mat.uniforms;
        u.uPieceN.value = Math.min(pl.pieces.length, 5);
        for (let k = 0; k < 5; k++) {
          const p = pl.pieces[k];
          u.uPieceA.value[k] = p ? p.aU : 0;
          u.uPieceB.value[k] = p ? p.bU : 0;
          if (p) u.uPieceCol.value[k].set(p.color);
        }
      }
    }
    // flytande defektetiketter på den aktiva brädan (min |x|)
    let act = arr[0];
    for (const b of arr) if (Math.abs(b.x) < Math.abs(act.x)) act = b;
    updateLabels(act);

    // Klingorna är FASTA (sätts av setSawLengths) – rörs inte här.
    // Klaffarna jobbar uppströms: hitta brädan i inriktningszonen och låt rätt
    // klaff sträcka ut sig (en i taget) medan den skjuter brädan på plats.
    if (pusherA) {
      const AX = SAW_X + 1.2, BX = SAW_X + 0.5, MID = (AX + BX) / 2;
      let alg = null, best = 1e9;
      for (const b of arr) {
        if (b.x < BX - 0.1) continue;                 // redan förbi klingorna
        const d = Math.abs(b.x - MID);
        if (d < best) { best = d; alg = b; }
      }
      let sA = 3.95, sB = -3.95;
      if (alg) {
        const tt = Math.max(0, Math.min(1, (AX - alg.x) / (AX - BX)));
        const reach = 0.9 * Math.sin(Math.PI * tt);   // 0→1→0 genom zonen
        const off = alignZFor(alg.data);
        if (off <= -1e-3) sA = 3.95 - reach;          // +Z-klaffen trycker mot −Z
        else if (off >= 1e-3) sB = -3.95 + reach;     // −Z-klaffen trycker mot +Z
      }
      pusherA.position.z = sA; pusherB.position.z = sB;
    }
  }

  function setWidth(wu) {
    curW = wu;
    for (const s of slots) s.group.scale.z = wu;
    // laserlinjerna ligger längs längden i mätplanet -> oberoende av brädbredden
  }

  function update(state) {
    for (const s of slots) {
      const u = s.mat.uniforms;
      u.uChannel.value = state.channel; u.uOverlay.value = state.overlay;
      u.uDistort.value = state.distort; u.uTime.value = state.time;
      u.uDisp.value = 0.55 * state.dispScale; u.uCoarse.value = state.coarse;  // överdriven warp för synlighet
      u.uCutOverlay.value = state.cutOverlay;
      if (state.channel === 1) {
        const a = state.time * 1.6;
        u.uLightDir.value.set(Math.cos(a) * 0.8, 0.55, Math.sin(a) * 0.8).normalize();
      } else u.uLightDir.value.set(0.4, 0.55, 0.85).normalize();
    }
    for (const s of laserStripes) s.material.opacity = 0.7 + 0.3 * Math.sin(state.time * 8);
    if (state.channel === 1) {
      const a = state.time * 1.6;
      const act = Math.floor((a / (Math.PI * 2)) * ledRing.length) % ledRing.length;
      ledRing.forEach((l, i) => l.material.emissiveIntensity = (i === act ? 2.4 : 0.12));
    } else ledRing.forEach(l => l.material.emissiveIntensity = 0.15);

    for (const f of laserFans) f.material.opacity = (state.channel === 4 || state.channel === 0) ? 0.14 : 0.06;
    tracheidBeam.material.opacity = state.channel === 2 ? 0.22 : 0.05;
    underBeam.material.opacity = state.showUnder ? 0.2 : 0.06;

    // kapstation: dynamiska klingor + klaffar + bansortering styrs i syncBoards.

    const sp = state.feed * 0.016;
    for (const grp of chains) for (const link of grp.children) {
      link.position.x -= sp;
      if (link.position.x < -14) link.position.x += grp.userData.span;
    }
    renderer.render(scene, camera);
  }

  function resize(w, h) { renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); }

  window.Scene = { init, syncBoards, update, resize, setWidth, setSawLengths, getW: () => curW, BOARD_LEN, SCAN_X };
})();
