import QtQuick
import QtQuick3D
import Woody3D

// GPU-renderad 3D (Qt Quick 3D): ljus, MSAA, UV-foto-textur, defekt-pins, mätverktyg.
Item {
    id: root
    anchors.fill: parent
    property int mode: 3
    property bool spin: true
    property real exag: 3
    property real yaw: -28
    property real pitch: -62
    property real dist: 820
    property bool measure: false
    property var measurePts: []         // modell-koordinater (mm)
    property real measureDist: -1
    property string pickedInfo: ""

    readonly property real blen: ctrl.rig.len
    readonly property real bwid: ctrl.rig.width
    readonly property real bthk: ctrl.rig.thick

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

        Texture { id: woodTex; source: "image://live/surface/" + ctrl.surfaceRev }

        Node {
            id: pivot
            eulerRotation.x: root.pitch
            eulerRotation.y: root.yaw

            Model {
                id: board
                geometry: BoardGeometry { id: geom; mode: root.mode; exaggeration: root.exag }
                materials: PrincipledMaterial {
                    baseColor: "white"; vertexColorsEnabled: true
                    baseColorMap: root.mode === 3 ? woodTex : null
                    roughness: 0.82; metalness: 0.0; cullMode: Material.NoCulling
                }
            }

            // defekt-pins (klickbara) — i brädans toppyta
            Repeater3D {
                model: ctrl.defects
                Node {
                    position: Qt.vector3d(modelData.x - root.blen/2, modelData.y - root.bwid/2, root.bthk/2 + 3)
                    Model {
                        source: "#Sphere"; scale: Qt.vector3d(0.12,0.12,0.12)
                        objectName: "pin:" + modelData.name + " @x" + modelData.x + " y" + modelData.y
                        materials: PrincipledMaterial { baseColor: modelData.color
                            emissiveFactor: Qt.vector3d(0.5,0.5,0.5); roughness: 0.4 }
                    }
                }
            }

            // mät-markörer
            Repeater3D {
                model: root.measurePts
                Model { source: "#Sphere"; scale: Qt.vector3d(0.09,0.09,0.09)
                    position: modelData
                    materials: PrincipledMaterial { baseColor: Theme.cyan
                        emissiveFactor: Qt.vector3d(0.6,0.6,0.6) } }
            }
        }
    }

    Connections { target: ctrl; function onMeshChanged() { geom.setMesh(ctrl.mesh3d) } }
    Component.onCompleted: geom.setMesh(ctrl.mesh3d)
    Timer { running: root.spin; interval: 16; repeat: true; onTriggered: root.yaw += 0.35 }

    function clickAt(mx, my) {
        var r = v3d.pick(mx, my);
        if (!r.objectHit) return;
        if (root.measure) {
            var local = pivot.mapPositionFromScene(r.scenePosition);
            var pts = root.measurePts.slice();
            if (pts.length >= 2) pts = [];
            pts.push(local);
            root.measurePts = pts;
            root.measureDist = (pts.length === 2) ? pts[0].minus(pts[1]).length() : -1;
        } else {
            root.pickedInfo = r.objectHit.objectName || "";
        }
    }

    MouseArea {
        id: drag
        anchors.fill: parent
        property real px: 0; property real py: 0; property bool moved: false
        onPressed: (e)=>{ px=e.x; py=e.y; moved=false }
        onPositionChanged: (e)=>{
            if (Math.abs(e.x-px) + Math.abs(e.y-py) > 3) { moved=true; root.spin=false; }
            root.yaw += (e.x-px)*0.3; root.pitch += (e.y-py)*0.3;
            root.pitch = Math.max(-89, Math.min(-5, root.pitch));
            px=e.x; py=e.y;
        }
        onReleased: (e)=>{ if (!moved) root.clickAt(e.x, e.y) }
        onWheel: (e)=> root.dist = Math.max(280, Math.min(2200, root.dist * (e.angleDelta.y>0 ? 0.9 : 1.1)))
    }

    // verktyg (färgläge, snurr, mät)
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
    }

    // info-overlay (mätning / pickad defekt)
    Rectangle {
        anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 10
        visible: root.measure || root.pickedInfo !== ""
        radius: 8; color: Qt.rgba(0.05,0.08,0.11,0.85); border.color: Theme.line
        width: col.width+20; height: col.height+14
        Column { id: col; x: 10; y: 7; spacing: 3
            Text { visible: root.measure; color: Theme.amber; font.pixelSize: 11; font.weight: Font.DemiBold
                   text: root.measureDist >= 0 ? ("Δ = " + root.measureDist.toFixed(1) + " mm")
                                               : "Mät: klicka två punkter på brädan" }
            Text { visible: root.pickedInfo !== "" && !root.measure; color: Theme.ink2; font.pixelSize: 11
                   text: root.pickedInfo }
        }
    }

    Text { anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.margins: 8
           text: "mätt: topp + sidor (röd/grön) · underside antagen · Qt Quick 3D (GPU)"
           color: Theme.ink3; font.pixelSize: 9; font.family: Theme.mono }
    Text { anchors.bottom: parent.bottom; anchors.right: parent.right; anchors.margins: 8
           text: "dra = rotera · hjul = zoom · pins = klicka"; color: Theme.ink3; font.pixelSize: 9; font.family: Theme.mono }
}
