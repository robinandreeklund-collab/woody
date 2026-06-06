import QtQuick
import QtQuick3D
import Woody3D

// GPU-renderad 3D (Qt Quick 3D) — ljus, MSAA, hög upplösning. Desktop.
Item {
    id: root
    anchors.fill: parent
    property int mode: 0
    property bool spin: true
    property real exag: 3
    property real yaw: -28
    property real pitch: -62
    property real dist: 820

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

        Node {
            id: pivot
            eulerRotation.x: root.pitch
            eulerRotation.y: root.yaw
            Behavior on eulerRotation.y { enabled: !drag.active; NumberAnimation { duration: 80 } }
            Model {
                id: board
                geometry: BoardGeometry { id: geom; mode: root.mode; exaggeration: root.exag }
                materials: PrincipledMaterial {
                    baseColor: "white"; vertexColorsEnabled: true
                    roughness: 0.82; metalness: 0.0; cullMode: Material.NoCulling
                }
            }
        }
    }

    Connections { target: ctrl; function onMeshChanged() { geom.setMesh(ctrl.mesh3d) } }
    Component.onCompleted: geom.setMesh(ctrl.mesh3d)

    Timer { running: root.spin; interval: 16; repeat: true
            onTriggered: root.yaw += 0.35 }

    MouseArea {
        id: drag
        anchors.fill: parent
        property real px: 0; property real py: 0
        property bool active: false
        onPressed: (e)=>{ px=e.x; py=e.y; active=true; root.spin=false }
        onReleased: active=false
        onPositionChanged: (e)=>{
            root.yaw += (e.x-px)*0.3; root.pitch += (e.y-py)*0.3;
            root.pitch = Math.max(-89, Math.min(-5, root.pitch));
            px=e.x; py=e.y;
        }
        onWheel: (e)=> root.dist = Math.max(280, Math.min(2200, root.dist * (e.angleDelta.y>0 ? 0.9 : 1.1)))
    }

    // verktyg (färgläge, snurr)
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
            radius: 7; implicitHeight: 24; implicitWidth: st.width+18
            color: root.spin ? Theme.teal : Theme.panel2; border.color: root.spin ? "transparent" : Theme.line
            Text { id: st; anchors.centerIn: parent; text: "↻ Snurr"; color: root.spin ? "#04222a" : Theme.ink2; font.pixelSize: 10; font.weight: Font.DemiBold }
            MouseArea { anchors.fill: parent; onClicked: root.spin=!root.spin }
        }
    }
    Text { anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.margins: 8
           text: "mätt: topp + sidor (röd/grön huvud) · underside antagen · Qt Quick 3D (GPU)"
           color: Theme.ink3; font.pixelSize: 9; font.family: Theme.mono }
    Text { anchors.bottom: parent.bottom; anchors.right: parent.right; anchors.margins: 8
           text: "dra = rotera · hjul = zoom"; color: Theme.ink3; font.pixelSize: 9; font.family: Theme.mono }
}
