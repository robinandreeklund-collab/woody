import QtQuick
import QtQuick3D
import QtQuick3D.AssetUtils
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
    property vector3d boardPos: Qt.vector3d(33, -385, 57)
    property vector3d boardEuler: Qt.vector3d(-90, 0, 0)

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
        environment: SceneEnvironment {
            clearColor: Theme.bg; backgroundMode: SceneEnvironment.Color
            antialiasingMode: SceneEnvironment.MSAA; antialiasingQuality: SceneEnvironment.High
        }
        PerspectiveCamera { id: cam; z: root.dist; fieldOfView: 38; clipFar: 6000; clipNear: 1 }
        DirectionalLight { eulerRotation.x: -38; eulerRotation.y: -35; brightness: 1.15 }
        DirectionalLight { eulerRotation.x: 30;  eulerRotation.y: 150; brightness: 0.45 }
        Texture { id: woodTex; source: root.texSource }

        // turntable: yaw kring världens vertikal, pitch kring den yaw-roterade horisontalen
        Node {
            id: yawNode
            eulerRotation.y: root.yaw
            Node {
                id: pitchNode
                eulerRotation.x: root.pitch

                // när tvillingen visas läggs brädan platt på bandet vid anhållet;
                // annars i origo upprätt (vanlig analysvy)
                Node {
                    id: boardAlign
                    position: root.showRig ? root.boardPos : Qt.vector3d(0, 0, 0)
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
        property real px: 0; property real py: 0; property bool moved: false
        onPressed: (e)=>{ px=e.x; py=e.y; moved=false; root.spin=false }
        onPositionChanged: (e)=>{
            if (Math.abs(e.x-px) + Math.abs(e.y-py) > 2) moved=true;
            root.yaw += (e.x-px)*0.45; root.pitch += (e.y-py)*0.45;
            root.pitch = Math.max(-89, Math.min(-2, root.pitch));
            px=e.x; py=e.y;
        }
        onReleased: (e)=>{ if (!moved) root.clickAt(e.x, e.y) }
        onWheel: (e)=> root.dist = Math.max(280, Math.min(2200, root.dist * (e.angleDelta.y>0 ? 0.9 : 1.1)))
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
                if (root.showRig) {
                    root.dist = Math.max(root.dist, 1750)   // rama in hela riggen
                    root.yaw = -32; root.pitch = -14        // riggen är Y-upp → nästan ögonhöjd
                } else {
                    root.dist = 820; root.yaw = -28; root.pitch = -62   // tillbaka till bräd-vy (uppifrån)
                }
            } }
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

    Text { anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.margins: 8
           text: "mätt: topp + V-kant (röd) + H-kant (grön) · underside antagen · Qt Quick 3D (GPU)"
           color: Theme.ink3; font.pixelSize: 9; font.family: Theme.mono }

    // legend: MÄTTA ytor (topp + sidor) vs ANTAGEN underside
    Row {
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
           text: "dra = rotera · hjul = zoom"; color: Theme.ink3; font.pixelSize: 9; font.family: Theme.mono }

    // vy-avläsning (endast när tvillingen visas) → läs upp siffrorna för exakt default-vy
    Text {
        visible: root.showRig
        anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottomMargin: 8
        text: "VY  yaw " + root.yaw.toFixed(0) + "°   pitch " + root.pitch.toFixed(0)
              + "°   dist " + root.dist.toFixed(0)
        color: Theme.amber; font.pixelSize: 11; font.family: Theme.mono; font.weight: Font.DemiBold
    }
}
