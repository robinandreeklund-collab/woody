import QtQuick
import QtQuick3D
import QtQuick3D.AssetUtils
import QtQuick3D.Helpers
import Woody3D

// GPU-renderad 3D (Qt Quick 3D): ljus, MSAA, UV-foto-textur, mätverktyg.
// Turntable-orbit via nästlade yaw/pitch-noder → naturlig navigering.
Item {
    id: root
    anchors.fill: parent
    property int mode: 3
    property bool spin: false
    property real exag: 3
    property real yaw: -28
    property real pitch: -62
    property real dist: 820
    property real panX: 0
    property real panY: 0
    property real fov: 38            // vidvinkel; vy-knappar sätter smal (~platt/ortografisk)
    property bool measure: false
    property var measurePts: []         // modell-koordinater (mm)
    property real measureDist: -1

    // digital tvilling: riggens CAD (step/Rig.step → assets/rig.glb)
    property bool showRig: false
    property url rigUrl: Qt.resolvedUrl("../assets/rig.glb")
    // align rig-frame → bräd-frame (mm). Default: centrera bbox i origo; finjusteras
    // med ögat (säg till så tonar jag in brädan på bandet). bbox-center ≈ (277,469,-323).
    property vector3d rigOffset: Qt.vector3d(-277, -469, 323)
    property vector3d rigEuler: Qt.vector3d(0, 0, 0)
    property real rigScale: 1.0
    // brädans placering PÅ bandet vid anhållet (rig-frame: Y=upp, X=bredd, Z=matning).
    // aktiveras bara när tvillingen visas; annars ligger brädan i origo (vanlig vy).
    // -90° runt X → brädan platt, längd (500) tvärs bandet, matning längs Z.
    // förankrat mot meshen: bandyta rig-Y≈75, linjekam rig-Z≈73, din måttkedja
    // (anhåll→+339,4 linjekam) → anhåll rig-Z≈−266; belt-X-centrum rig≈310.
    // scene = rig + rigOffset(−277,−469,323): X 33, Y −385 (band), Z 57.
    property vector3d boardPos: Qt.vector3d(22, -391, 57)   // X/Y kalibrerat (Z används ej, se anhallZ)
    property vector3d boardEuler: Qt.vector3d(-90, 0, 0)
    // ANKARE = anhållet (din korrekta brädladdnings-Z). Lasrarna kommer från sidan
    // i vinkel (profil 25° / laser 50°) och konvergerar PÅ bandet — laser-centrum är
    // en punkt på ytan, 299,4 mm från anhållet (inget huvud rakt ovanför).
    // Allt härleds längs matningsriktningen feedDir: anhåll(0) → 129,4 LR400 →
    // 299,4 laser → 339,4 linjekamera.
    property real anhallZ: 360           // ← din korrekta anhålls-Z (kalibreras i GUI)
    property real feedDir: -1            // matningsriktning; flippa i GUI vid behov
    property real lr400Z:   anhallZ + feedDir * 129.404
    property real laserZ:   anhallZ + feedDir * 299.404   // laser-centrum på bandet
    property real lineCamZ: anhallZ + feedDir * 339.404
    property real frontZ:   anhallZ + feedDir * (339.404 + 50 + 37.5)
    property real boardTopY: -381        // brädans ovansida i scen-Y (på bandet)
    // dubbelt profilhuvud (head-mech.svg, LÅST geometri): per huvud kamera + laser på
    // SAMMA sida, RÖD ena sidan (+Z), GRÖN andra (−Z), båda mot samma laserlinje.
    // Offset i matningsled (±Z): laser ±582, kamera ±321. WD 760 slant.
    property real laserArmDeg: 50        // laser-arm fr lod (offset 582, höjd 489)
    property real camArmDeg: 25          // kamera-arm fr lod (offset 321, höjd 689)
    readonly property real _laserH: 489  // laserhöjd ö. bräda = WD·cos50
    readonly property real _laserZoff: 582      // = WD·sin50
    readonly property real _laserBeam: 760      // WD (slant)
    readonly property real _camH: 689           // kamerahöjd = WD·cos25
    readonly property real _camZoff: 321         // = WD·sin25
    readonly property real _camBeam: 760
    // KONVERGENS 35 mm ö. bandet (vald för 15–50 mm). På en bräda tunnare än 35 mm
    // korsas lasrarna OVANFÖR ytan → röd/grön landar SEPARERADE (parallax), inte på
    // varandra. Parallax på brädytan = (konvergenshöjd − brädtopp)·tan50°.
    property real boardThick: 20                 // brädtjocklek (mm) — styr parallaxen
    property real convergeAboveBelt: 35          // laserkonvergens ö. bandet (LÅST)
    readonly property real _beltY: boardTopY - boardThick
    readonly property real _convY: _beltY + convergeAboveBelt
    readonly property real _arm: laserArmDeg * Math.PI / 180
    readonly property real _laserParallax: (_convY - boardTopY) * Math.tan(_arm)
    readonly property real _fanCenterY: _convY + (_laserH - convergeAboveBelt) / 2
    readonly property real _fanZmag: (_laserZoff - convergeAboveBelt * Math.tan(_arm)) / 2
    readonly property real _fanLen: (_laserH + convergeAboveBelt) / Math.cos(_arm)
    property real laserFanDeg: 45        // MZLaser Powell-lins fan-vinkel → ~630 mm linje vid WD
    readonly property real _fanBaseW: 2 * _laserBeam * Math.tan(laserFanDeg / 2 * Math.PI / 180)
    // ÄKTA laserträff: var respektive laserplan möter ytan (band → kant → ovansida).
    // [Y, Z, påKant]. sign +1 = RÖD (+Z-huvud, ser +Z-kant), −1 = GRÖN (−Z-huvud).
    property vector3d redHit: laserHit(1)
    property vector3d greenHit: laserHit(-1)

    // levande tvilling: status från controllern (säkra guards för smoke utan ctrl)
    property bool scanActive: (typeof ctrl !== 'undefined' && ctrl) ? ctrl.scanActive : false
    property real scanProg:   (typeof ctrl !== 'undefined' && ctrl) ? ctrl.scanProgress : 0
    property var  defectList: (typeof ctrl !== 'undefined' && ctrl) ? ctrl.defects : []
    // matning: brädan vilar vid anhållet (feedPos 0) och glider tydligt framåt längs
    // bandet, förbi det fasta laserplanet. Kopplat till faktisk matningsposition →
    // glider även tillbaka mot anhållet i pass-lägets returfas.
    property real feedFrac: (typeof ctrl !== 'undefined' && ctrl) ? (ctrl.feedPos / 75) : 0
    // brädan ligger med KANTEN mot anhållet (nollpunkt) och kroppen 37,5 mm in i riggen
    // → mitt i vila = anhåll + feedDir·37,5. Matas sen framåt förbi linjekameran, åter i retur.
    property real boardRestZ: anhallZ + feedDir * 37.5
    property real boardFeedZ: root.boardRestZ + root.feedFrac * (root.frontZ - root.boardRestZ)
    // SmoothedAnimation följer det rörliga matningsvärdet med jämn hastighet (ingen
    // ease-out-restart per frame → inget hack). Velocity > max matningsbehov.
    Behavior on boardFeedZ { SmoothedAnimation { velocity: 3000; reversingMode: SmoothedAnimation.Sync } }

    // mesh + textur: lokalt ctrl.mesh3d / image://live, eller en fjärrnods data (master)
    property var mesh: (typeof ctrl !== 'undefined' && ctrl) ? ctrl.mesh3d : null
    property string texSource: (typeof ctrl !== 'undefined' && ctrl) ? ("image://live/surface/" + ctrl.surfaceRev) : ""
    onMeshChanged: if (typeof geom !== 'undefined' && geom) geom.setMesh(root.mesh || ({}))

    property real blen: (root.mesh && root.mesh.len) ? root.mesh.len : 500
    property real bwid: (root.mesh && root.mesh.width) ? root.mesh.width : 75
    property real bthk: (root.mesh && root.mesh.thick) ? root.mesh.thick : 15

    View3D {
        id: v3d
        anchors.fill: parent
        environment: ExtendedSceneEnvironment {
            clearColor: Theme.bg; backgroundMode: SceneEnvironment.Color
            antialiasingMode: SceneEnvironment.MSAA; antialiasingQuality: SceneEnvironment.High
            tonemapMode: SceneEnvironment.TonemapModeFilmic       // mjukare högdagrar
            aoStrength: 60; aoDistance: 55; aoSoftness: 28        // SSAO → djup (RTX-desktop)
            aoSampleRate: 4
            // glow ENDAST på mycket starka emissiva ytor (lasern) → ingen scen-dis.
            // Hög HDR-tröskel så bakgrund/rigg inte blommar; ingen bred bloom.
            glowEnabled: root.showRig
            glowStrength: 0.4; glowIntensity: 0.85; glowBloom: 0.0
            glowQualityHigh: true; glowUseBicubicUpscale: true
            glowHDRMinimumValue: 2.2; glowHDRMaximumValue: 9.0; glowHDRScale: 2.0
            vignetteEnabled: false
        }
        PerspectiveCamera { id: cam; x: root.panX; y: root.panY; z: root.dist
            fieldOfView: root.fov; clipFar: 30000; clipNear: 1 }
        // nyckelljus med mjuka slagskuggor (grundar riggen) + fyllnad + motljus
        // nyckelljus med MJUKA slagskuggor + två fyllnadsljus + topp → ljus, läsbar scen
        DirectionalLight {
            eulerRotation.x: -42; eulerRotation.y: -38
            brightness: 2.3 + ((root.showRig && root.scanActive) ? 0.5 : 0)   // LED-glöd
            castsShadow: root.showRig; shadowMapQuality: Light.ShadowMapQualityVeryHigh
            shadowFactor: 20; shadowMapFar: 4000; shadowBias: 18; pcfFactor: 8
        }
        DirectionalLight { eulerRotation.x: 18;  eulerRotation.y: 150; brightness: 1.0 }
        DirectionalLight { eulerRotation.x: -10; eulerRotation.y: 55;  brightness: 0.7 }
        DirectionalLight { eulerRotation.x: -85; eulerRotation.y: 0;   brightness: 0.45 }
        Texture { id: woodTex; source: root.texSource }

        // turntable: yaw kring världens vertikal, pitch kring den yaw-roterade horisontalen
        Node {
            id: yawNode
            eulerRotation.y: root.yaw
            Node {
                id: pitchNode
                eulerRotation.x: root.pitch

                // golv — grundar riggen och tar emot slagskuggor (matt → mörknar ej)
                Model {
                    visible: root.showRig
                    source: "#Rectangle"
                    eulerRotation.x: -90
                    position: Qt.vector3d(33, -458, 0)
                    scale: Qt.vector3d(30, 30, 1)
                    castsShadows: false; receivesShadows: true
                    materials: PrincipledMaterial { baseColor: "#39414c"; roughness: 0.8; metalness: 0.0 }
                }

                // scannad bräd-mesh: visas i analysvyn (dölj i tvillingen — där visas
                // i stället en statisk referensbräda vid anhållet, se nedan)
                Node {
                    id: boardAlign
                    visible: !root.showRig
                    position: root.showRig ? Qt.vector3d(root.boardPos.x, root.boardPos.y, root.boardFeedZ)
                                           : Qt.vector3d(0, 0, 0)
                    eulerRotation: root.showRig ? root.boardEuler : Qt.vector3d(0, 0, 0)
                    Model {
                        id: board
                        pickable: true
                        geometry: BoardGeometry { id: geom; mode: root.mode; exaggeration: root.exag }
                        materials: PrincipledMaterial {
                            baseColor: "white"; vertexColorsEnabled: true
                            baseColorMap: root.mode === 3 ? woodTex : null
                            roughness: 0.82; metalness: 0.0; cullMode: Material.NoCulling
                        }
                    }
                    // defekter som glödande markörer på brädans yta (följer med brädan)
                    Repeater3D {
                        model: root.showRig ? root.defectList : []
                        Model {
                            source: "#Sphere"
                            scale: Qt.vector3d(0.10, 0.10, 0.10)
                            position: Qt.vector3d(modelData.x - 250, modelData.y - 37.5, root.bthk / 2 + 3)
                            materials: PrincipledMaterial {
                                baseColor: modelData.color
                                emissiveFactor: Qt.vector3d(0.9, 0.55, 0.12)
                            }
                        }
                    }
                }

                // Referensbräda (500×75×20 mm). Vilar vid anhållet (kalibrerat) och MATAS
                // fram genom skanningen (boardFeedZ): anhåll → genom laser/linjekamera →
                // tillbaka i pass-retur. I vila (feedPos 0) = exakt vid anhållet.
                Model {
                    visible: root.showRig
                    source: "#Cube"
                    position: Qt.vector3d(root.boardPos.x, root.boardPos.y, root.boardFeedZ)
                    scale: Qt.vector3d(5.0, 0.20, 0.75)    // X 500 (längd) · Y 20 (tjock) · Z 75 (matning)
                    castsShadows: true; receivesShadows: true
                    materials: PrincipledMaterial { baseColor: "#c9a468"; roughness: 0.72; metalness: 0.0 }
                }

                // ÄKTA laserstripe DÄR DEN TRÄFFAR YTAN: band → klättrar lodrät kant →
                // ovansida. Ligger på redHit/greenHit (beräknat mot brädan). Tänds STARKARE
                // när den träffar en lodrät tjocklecksida (.z=1). Ocklusion: varje huvud
                // ser bara sin egen kant. Konvergens 35 mm ö. bandet → linjerna separerade.
                Model {                                   // RÖD 650 nm
                    visible: root.showRig
                    source: "#Cube"; scale: Qt.vector3d(5.0, 0.05, 0.05)
                    position: Qt.vector3d(root.boardPos.x, root.redHit.x, root.redHit.y)
                    materials: PrincipledMaterial { baseColor: "#1a0203"
                        emissiveFactor: root.redHit.z > 0.5 ? Qt.vector3d(5.2, 0.25, 0.3)
                                                            : Qt.vector3d(3.0, 0.14, 0.16) }
                }
                Model {                                   // GRÖN 520 nm
                    visible: root.showRig
                    source: "#Cube"; scale: Qt.vector3d(5.0, 0.05, 0.05)
                    position: Qt.vector3d(root.boardPos.x, root.greenHit.x, root.greenHit.y)
                    materials: PrincipledMaterial { baseColor: "#021a08"
                        emissiveFactor: root.greenHit.z > 0.5 ? Qt.vector3d(0.3, 5.2, 0.8)
                                                              : Qt.vector3d(0.2, 3.0, 0.55) }
                }
                // konvergenspunkt 35 mm ö. bandet (där linjerna SKULLE mötas)
                Model { source: "#Sphere"; visible: root.showRig; scale: Qt.vector3d(0.05, 0.05, 0.05)
                    position: Qt.vector3d(root.boardPos.x, root._convY, root.laserZ)
                    materials: PrincipledMaterial { baseColor: "#222"
                        emissiveFactor: Qt.vector3d(1.0, 0.9, 0.3) } }

                // LASER-RIDÅER (Powell-fan, ~38°): TRIANGEL från diod-huvudet → 500 mm linje
                // vid WD. Tillplattad kon (spets vid dioden, bas = linjen). RÖD +Z-huvud,
                // GRÖN −Z-huvud, lutade 50°, korsas vid konvergensen 35 mm ö. bandet.
                Model {                                   // RÖD-fan (638 nm Powell)
                    visible: root.showRig
                    source: "#Cone"; opacity: 0.22; castsShadows: false
                    position: Qt.vector3d(root.boardPos.x, root._convY + root._laserH/2,
                                          root.laserZ + root._laserZoff/2)
                    eulerRotation.x: root.laserArmDeg
                    scale: Qt.vector3d(root._fanBaseW/100, root._laserBeam/100, 0.02)   // 45° Powell-fan
                    materials: PrincipledMaterial { baseColor: "#ff1828"
                        alphaMode: PrincipledMaterial.Blend
                        emissiveFactor: Qt.vector3d(1.3, 0.05, 0.06) }
                }
                Model {                                   // GRÖN-fan (520 nm Powell)
                    visible: root.showRig
                    source: "#Cone"; opacity: 0.22; castsShadows: false
                    position: Qt.vector3d(root.boardPos.x, root._convY + root._laserH/2,
                                          root.laserZ - root._laserZoff/2)
                    eulerRotation.x: -root.laserArmDeg
                    scale: Qt.vector3d(root._fanBaseW/100, root._laserBeam/100, 0.02)
                    materials: PrincipledMaterial { baseColor: "#18ff40"
                        alphaMode: PrincipledMaterial.Blend
                        emissiveFactor: Qt.vector3d(0.06, 1.3, 0.22) }
                }

                // PROFILKAMERORNAS siktlinjer (kamera-arm 25°): RÖD-huvud +Z, GRÖN-huvud −Z,
                // båda mot samma laserlinje (triangulering θ 25°). Tunna, dämpade linjer.
                Model {                                   // RÖD-kamera siktlinje
                    visible: root.showRig
                    source: "#Cube"; opacity: 0.5; castsShadows: false
                    position: Qt.vector3d(root.boardPos.x, root.boardTopY + root._camH/2,
                                          root.laserZ + root._camZoff/2)
                    eulerRotation.x: root.camArmDeg
                    scale: Qt.vector3d(0.04, root._camBeam/100, 0.04)
                    materials: PrincipledMaterial { baseColor: "#3a1416"
                        emissiveFactor: Qt.vector3d(0.6, 0.18, 0.2) }
                }
                Model {                                   // GRÖN-kamera siktlinje
                    visible: root.showRig
                    source: "#Cube"; opacity: 0.5; castsShadows: false
                    position: Qt.vector3d(root.boardPos.x, root.boardTopY + root._camH/2,
                                          root.laserZ - root._camZoff/2)
                    eulerRotation.x: -root.camArmDeg
                    scale: Qt.vector3d(0.04, root._camBeam/100, 0.04)
                    materials: PrincipledMaterial { baseColor: "#14301a"
                        emissiveFactor: Qt.vector3d(0.16, 0.6, 0.26) }
                }

                // LINJEKAMERANS plan (blå linje) — 40 mm bortom lasern (339,4 från anhåll)
                Node {
                    visible: root.showRig
                    position: Qt.vector3d(root.boardPos.x, root.boardTopY + 1, root.lineCamZ)
                    Model { source: "#Cube"; scale: Qt.vector3d(5.0, 0.04, 0.04)
                        materials: PrincipledMaterial { baseColor: "#08121f"
                            emissiveFactor: Qt.vector3d(0.2, 0.5, 1.3) } }
                }
                // LR400-punkter (3 cyan) vid LR-planet — 129,4 från anhåll (uppströms)
                Repeater3D {
                    model: root.showRig && (typeof ctrl !== 'undefined' && ctrl) ? ctrl.lrPositions : []
                    Model {
                        source: "#Sphere"
                        scale: Qt.vector3d(0.09, 0.09, 0.09)
                        position: Qt.vector3d(root.boardPos.x - 250 + modelData, root.boardTopY + 5, root.lr400Z)
                        materials: PrincipledMaterial { baseColor: "#06201f"
                            emissiveFactor: Qt.vector3d(0.15, 1.4, 1.5) }
                    }
                }

                // vita LED-lister (×2) — glöder när vitljuset är på (skanning)
                Node {
                    visible: root.showRig && root.scanActive
                    position: Qt.vector3d(root.boardPos.x, root.boardTopY + 130, root.laserZ)
                    Model { source: "#Cube"; x: -120; scale: Qt.vector3d(4.2, 0.08, 0.12)
                        materials: PrincipledMaterial { baseColor: "#202018"
                            emissiveFactor: Qt.vector3d(1.7, 1.7, 1.55) } }
                    Model { source: "#Cube"; x: 120; scale: Qt.vector3d(4.2, 0.08, 0.12)
                        materials: PrincipledMaterial { baseColor: "#202018"
                            emissiveFactor: Qt.vector3d(1.7, 1.7, 1.55) } }
                }
                // mät-markörer (roterar med brädan)
                Repeater3D {
                    model: root.measurePts
                    Model { source: "#Sphere"; scale: Qt.vector3d(0.07,0.07,0.07)
                        position: modelData
                        materials: PrincipledMaterial { baseColor: Theme.cyan
                            emissiveFactor: Qt.vector3d(0.7,0.7,0.7) } }
                }

                // digital tvilling: hela riggen (CAD) orbitar med brädan
                Node {
                    id: rigAlign
                    visible: root.showRig
                    position: root.rigOffset
                    eulerRotation: root.rigEuler
                    scale: Qt.vector3d(root.rigScale, root.rigScale, root.rigScale)
                    RuntimeLoader {
                        // laddas först när tvillingen slås på (håller startup lätt)
                        source: root.showRig ? root.rigUrl : ""
                    }
                }
            }
        }
    }

    Component.onCompleted: geom.setMesh(root.mesh || ({}))
    Timer { running: root.spin; interval: 16; repeat: true; onTriggered: root.yaw += 0.35 }

    // återställ kameran till standardvyn (rigg- eller bräd-läge)
    function resetView() {
        root.panX = 0; root.panY = 0; root.spin = false; root.fov = 38;
        if (root.showRig) { root.yaw = 254; root.pitch = -2;  root.dist = 2034; }
        else              { root.yaw = -28; root.pitch = -62; root.dist = 820; }
    }
    // fast vy (vy-knappar): nollställ panorering + sätt vinkel/avstånd/vidvinkel.
    // Liten fov (~5°) + stort avstånd ≈ ortografisk → spikrak, platt CAD-vy.
    function setView(y, p, d, f) {
        root.spin = false; root.panX = 0; root.panY = 0;
        root.yaw = y; root.pitch = p; root.dist = d; root.fov = (f === undefined ? 38 : f);
    }
    // brädjustering (kalibrering): Z=matning (flyttar hela sensorkedjan), X=bredd, Y=höjd
    function nudge(axis, d) {
        if (axis === "z") root.anhallZ += d;        // flyttar anhållet → hela kedjan följer
        else if (axis === "x") root.boardPos = Qt.vector3d(root.boardPos.x + d, root.boardPos.y, root.boardPos.z);
        else if (axis === "y") root.boardPos = Qt.vector3d(root.boardPos.x, root.boardPos.y + d, root.boardPos.z);
    }
    function axisVal(axis) {
        return axis === "z" ? root.anhallZ : (axis === "x" ? root.boardPos.x : root.boardPos.y);
    }
    // var laserplanet (sign +1 röd / −1 grön) träffar ytan: ovansida, lodrät kant, eller band.
    // Plan: Z = laserZ + sign·(Y − convY)·tanArm. Ocklusion: varje huvud ser bara sin närkant.
    function laserHit(sign) {
        var tA = Math.tan(root._arm);
        var lz = root.laserZ, cY = root._convY, bt = root.boardTopY, bl = root._beltY;
        var fz = root.boardFeedZ, lo = fz - 37.5, hi = fz + 37.5;
        var topHitZ = lz + sign * (bt - cY) * tA;                 // plan @ brädtopp-höjd
        if (topHitZ >= lo && topHitZ <= hi)
            return Qt.vector3d(bt, topHitZ, 0);                   // på OVANSIDAN
        var nearEdgeZ = fz + sign * 37.5;                        // den kant detta huvud ser
        var yFace = cY + sign * (nearEdgeZ - lz) / tA;           // plan @ kantens Z
        if (yFace > bl && yFace < bt)
            return Qt.vector3d(yFace, nearEdgeZ, 1);             // på LODRÄT TJOCKLECKSKANT
        return Qt.vector3d(bl, lz + sign * (bl - cY) * tA, 0);  // på BANDET
    }

    function clickAt(mx, my) {
        if (!root.measure) return;
        var r = v3d.pick(mx, my);
        if (!r.objectHit) return;
        var local = pitchNode.mapPositionFromScene(r.scenePosition);
        var pts = root.measurePts.slice();
        if (pts.length >= 2) pts = [];
        pts.push(local);
        root.measurePts = pts;
        root.measureDist = (pts.length === 2) ? pts[0].minus(pts[1]).length() : -1;
    }

    MouseArea {
        id: drag
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
        property real px: 0; property real py: 0; property bool moved: false; property int btn: 0
        onPressed: (e)=>{ px=e.x; py=e.y; moved=false; btn=e.button; root.spin=false }
        onPositionChanged: (e)=>{
            var dx = e.x-px, dy = e.y-py;
            if (Math.abs(dx) + Math.abs(dy) > 2) moved=true;
            if (btn === Qt.LeftButton) {                          // vänster = rotera (grabb-känsla)
                root.yaw -= dx*0.35; root.pitch -= dy*0.35;
                root.pitch = Math.max(-89, Math.min(25, root.pitch));
            } else {                                              // höger/mitt = panorera
                var k = root.dist / 700;                          // skala med zoom
                root.panX -= dx*k; root.panY += dy*k;
            }
            px=e.x; py=e.y;
        }
        onReleased: (e)=>{ if (!moved && btn === Qt.LeftButton) root.clickAt(e.x, e.y) }
        onWheel: (e)=>{
            var nd = Math.max(150, Math.min(4000, root.dist * (e.angleDelta.y>0 ? 0.88 : 1.14)));
            var k = 2*Math.tan(root.fov*Math.PI/360)/height;   // världsenheter/px per dist-enhet
            root.panX += (e.x - width/2)  * k * (root.dist - nd);   // zooma mot pekaren
            root.panY -= (e.y - height/2) * k * (root.dist - nd);
            root.dist = nd;
        }
    }

    // verktyg (färgläge, mät, snurr)
    Row {
        anchors.top: parent.top; anchors.right: parent.right; spacing: 6
        Repeater {
            model: ["Höjd","Avvikelse","Skuggad","Foto"]
            delegate: Rectangle {
                radius: 7; implicitHeight: 24; implicitWidth: t.width+18
                color: root.mode===index ? Theme.cyan : Theme.panel2
                border.color: root.mode===index ? "transparent" : Theme.line
                Text { id: t; anchors.centerIn: parent; text: modelData
                       color: root.mode===index ? "#04222a" : Theme.ink2; font.pixelSize: 10; font.weight: Font.DemiBold }
                MouseArea { anchors.fill: parent; onClicked: root.mode=index }
            }
        }
        Rectangle {
            radius: 7; implicitHeight: 24; implicitWidth: mt.width+18
            color: root.measure ? Theme.amber : Theme.panel2; border.color: root.measure ? "transparent" : Theme.line
            Text { id: mt; anchors.centerIn: parent; text: "⊹ Mät"; color: root.measure ? "#2a1800" : Theme.ink2; font.pixelSize: 10; font.weight: Font.DemiBold }
            MouseArea { anchors.fill: parent; onClicked: { root.measure=!root.measure; root.measurePts=[]; root.measureDist=-1 } }
        }
        Rectangle {
            radius: 7; implicitHeight: 24; implicitWidth: st.width+18
            color: root.spin ? Theme.teal : Theme.panel2; border.color: root.spin ? "transparent" : Theme.line
            Text { id: st; anchors.centerIn: parent; text: "↻ Snurr"; color: root.spin ? "#04222a" : Theme.ink2; font.pixelSize: 10; font.weight: Font.DemiBold }
            MouseArea { anchors.fill: parent; onClicked: root.spin=!root.spin }
        }
        Rectangle {
            radius: 7; implicitHeight: 24; implicitWidth: rgt.width+18
            color: root.showRig ? Theme.violet : Theme.panel2; border.color: root.showRig ? "transparent" : Theme.line
            Text { id: rgt; anchors.centerIn: parent; text: "⌂ Rigg"; color: root.showRig ? "#fff" : Theme.ink2; font.pixelSize: 10; font.weight: Font.DemiBold }
            MouseArea { anchors.fill: parent; onClicked: {
                root.showRig = !root.showRig
                root.panX = 0; root.panY = 0; root.fov = 38             // nollställ panorering + vidvinkel
                if (root.showRig) {
                    root.yaw = 254; root.pitch = -2; root.dist = 2034   // inställd tvillingvy
                } else {
                    root.dist = 820; root.yaw = -28; root.pitch = -62   // tillbaka till bräd-vy (uppifrån)
                }
            } }
        }
        Rectangle {
            radius: 7; implicitHeight: 24; implicitWidth: rvt.width+18
            color: Theme.panel2; border.color: Theme.line
            Text { id: rvt; anchors.centerIn: parent; text: "⟲ Vy"; color: Theme.ink2; font.pixelSize: 10; font.weight: Font.DemiBold }
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.resetView() }
        }
    }

    // mät-overlay
    Rectangle {
        anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 10
        visible: root.measure
        radius: 8; color: Qt.rgba(0.05,0.08,0.11,0.85); border.color: Theme.line
        width: mtxt.width+20; height: mtxt.height+14
        Text { id: mtxt; x: 10; y: 7; color: Theme.amber; font.pixelSize: 11; font.weight: Font.DemiBold
               text: root.measureDist >= 0 ? ("Δ = " + root.measureDist.toFixed(1) + " mm")
                                           : "Mät: klicka två punkter på brädan" }
    }

    Text { visible: !root.showRig
           anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.margins: 8
           text: "mätt: topp + V-kant (röd) + H-kant (grön) · underside antagen · Qt Quick 3D (GPU)"
           color: Theme.ink3; font.pixelSize: 9; font.family: Theme.mono }

    // ---- vy-knappar (fasta vinklar) — tvillingvyn ----
    Column {
        visible: root.showRig
        anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; anchors.leftMargin: 10
        spacing: 5
        Repeater {
            // namn, yaw, pitch, avstånd, fov  (platta vyer: liten fov + stort avstånd)
            model: [["3D",   254, -2,  2034, 38],
                    ["Sida",  90,  0, 14000,  5],
                    ["Fram",   0,  0, 14000,  5],
                    ["Ovan",   0, -90, 14000, 5]]
            delegate: Rectangle {
                width: 66; height: 26; radius: 7; color: Theme.panel2; border.color: Theme.line
                Text { anchors.centerIn: parent; text: modelData[0]; color: Theme.ink2; font.pixelSize: 11; font.weight: Font.DemiBold }
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                    onClicked: root.setView(modelData[1], modelData[2], modelData[3], modelData[4]) }
            }
        }
    }

    // ---- brädjustering / kalibrering — tvillingvyn ----
    Rectangle {
        visible: root.showRig
        anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 10
        radius: 9; color: Qt.rgba(0.05,0.08,0.11,0.92); border.color: Theme.line
        width: cal.width + 20; height: cal.height + 16
        Column {
            id: cal; x: 10; y: 8; spacing: 5
            Text { text: "BRÄDA · KALIBRERING"; color: Theme.ink3; font.pixelSize: 9; font.letterSpacing: 0.5 }
            Repeater {
                model: [["Z anhåll","z",10],["X bredd","x",10],["Höjd Y","y",5]]
                delegate: Row {
                    spacing: 3
                    Text { text: modelData[0]; color: Theme.ink2; font.pixelSize: 10; width: 54
                           anchors.verticalCenter: parent.verticalCenter }
                    Rectangle { width: 24; height: 22; radius: 5; color: Theme.panel2; border.color: Theme.line
                        Text { anchors.centerIn: parent; text: "−" + modelData[2]; color: Theme.cyan; font.pixelSize: 9 }
                        MouseArea { anchors.fill: parent; onClicked: root.nudge(modelData[1], -modelData[2]) } }
                    Rectangle { width: 18; height: 22; radius: 5; color: Theme.panel2; border.color: Theme.line
                        Text { anchors.centerIn: parent; text: "−"; color: Theme.cyan; font.pixelSize: 13 }
                        MouseArea { anchors.fill: parent; onClicked: root.nudge(modelData[1], -1) } }
                    Text { width: 46; horizontalAlignment: Text.AlignHCenter; color: Theme.cyan
                           font.family: Theme.mono; font.pixelSize: 11; anchors.verticalCenter: parent.verticalCenter
                           text: root.axisVal(modelData[1]).toFixed(0) }
                    Rectangle { width: 18; height: 22; radius: 5; color: Theme.panel2; border.color: Theme.line
                        Text { anchors.centerIn: parent; text: "+"; color: Theme.cyan; font.pixelSize: 13 }
                        MouseArea { anchors.fill: parent; onClicked: root.nudge(modelData[1], 1) } }
                    Rectangle { width: 24; height: 22; radius: 5; color: Theme.panel2; border.color: Theme.line
                        Text { anchors.centerIn: parent; text: "+" + modelData[2]; color: Theme.cyan; font.pixelSize: 9 }
                        MouseArea { anchors.fill: parent; onClicked: root.nudge(modelData[1], modelData[2]) } }
                }
            }
            Row { spacing: 6
                Text { text: "Riktning"; color: Theme.ink2; font.pixelSize: 10; width: 54
                       anchors.verticalCenter: parent.verticalCenter }
                Rectangle { width: 122; height: 22; radius: 5; color: Theme.panel2; border.color: Theme.line
                    Text { anchors.centerIn: parent; color: Theme.amber; font.pixelSize: 10
                           text: root.feedDir > 0 ? "anhåll → fram" : "fram → anhåll" }
                    MouseArea { anchors.fill: parent; onClicked: root.feedDir = -root.feedDir } }
            }
            Text { color: Theme.ink3; font.pixelSize: 9; font.family: Theme.mono
                   text: "anhåll @ " + root.anhallZ.toFixed(0) + " · LR400 @ " + root.lr400Z.toFixed(0)
                         + " · laser @ " + root.laserZ.toFixed(0) + " · linjekam @ " + root.lineCamZ.toFixed(0) }
        }
    }

    // legend: MÄTTA ytor (topp + sidor) vs ANTAGEN underside (döljs i tvillingvyn)
    Row {
        visible: !root.showRig
        anchors.top: parent.top; anchors.left: parent.left; anchors.margins: 8; spacing: 10
        Repeater {
            model: [["Topp","#27d3e0"],["V-kant","#c73845"],["H-kant","#33b35c"],["Underside · antagen","#42505c"]]
            delegate: Row { spacing: 4
                Rectangle { width: 9; height: 9; radius: 2; color: modelData[1]
                    border.color: index===3 ? Theme.line2 : "transparent"
                    anchors.verticalCenter: parent.verticalCenter }
                Text { text: modelData[0]; color: Theme.ink2; font.pixelSize: 9; font.family: Theme.sans } }
        }
    }
    Text { anchors.bottom: parent.bottom; anchors.right: parent.right; anchors.margins: 8
           text: "vänsterdra = rotera · högerdra = panorera · hjul = zoom · ⟲ Vy = återställ"
           color: Theme.ink3; font.pixelSize: 9; font.family: Theme.mono }
}
