import QtQuick
import QtQuick.Layouts

RowLayout {
    id: aroot
    spacing: 12

    // ============================ 3D-REKONSTRUKTION ========================
    Card {
        Layout.fillWidth: true; Layout.fillHeight: true
        title: "3D-REKONSTRUKTION"
        chip: ctrl.mesh3d.cls ? ("klass " + ctrl.mesh3d.cls) : "skanna en bräda"

        Loader {
            anchors.fill: parent
            source: (typeof quick3dAvailable !== "undefined" && quick3dAvailable)
                    ? "Board3DGpu.qml" : "Board3DSoft.qml"
        }
    }

    // ============================ HÖGER: skevhet + profiler ================
    ColumnLayout {
        Layout.fillHeight: true; Layout.fillWidth: false
        Layout.preferredWidth: 400; Layout.minimumWidth: 360; Layout.maximumWidth: 460
        spacing: 12

        Card {
            Layout.fillWidth: true; Layout.preferredHeight: 176
            title: "SKEVHET (uppmätt)"; chip: ctrl.mesh3d.cls ? "klass " + ctrl.mesh3d.cls : "—"
            ColumnLayout {
                anchors.fill: parent; spacing: 8
                Repeater {
                    model: [["Bukt / krok (bow)","bow",3.0],["Kupa (cup)","cup",2.5],
                            ["Vridning (twist)","twist",3.0],["Plankrok (crook)","crook",3.0]]
                    delegate: RowLayout {
                        Layout.fillWidth: true; spacing: 10
                        property real val: ctrl.mesh3d[modelData[1]] !== undefined ? ctrl.mesh3d[modelData[1]] : 0
                        Text { text: modelData[0]; color: Theme.ink2; font.pixelSize: 11; Layout.preferredWidth: 150 }
                        Rectangle { Layout.fillWidth: true; height: 8; radius: 4; color: "#16222f"
                            Rectangle { radius: 4; height: parent.height
                                width: parent.width * Math.max(0, Math.min(1, val/modelData[2]))
                                color: val < modelData[2]*0.5 ? Theme.teal : (val < modelData[2]*0.85 ? Theme.amber : Theme.red)
                                Behavior on width { NumberAnimation { duration: 200 } } } }
                        Text { text: val.toFixed(2) + " mm"; color: Theme.cyan; font.family: Theme.mono; font.pixelSize: 11; Layout.preferredWidth: 64; horizontalAlignment: Text.AlignRight }
                    }
                }
            }
        }

        Card {
            Layout.fillWidth: true; Layout.fillHeight: true
            title: "LÄNGSPROFIL Z(x) · längs 500 mm"
            ProfilePlot { values: ctrl.zProfile; axisLabel: "x längs bräda (0–500 mm)" }
        }
        Card {
            Layout.fillWidth: true; Layout.fillHeight: true
            title: "TVÄRPROFIL Z(y) · topp + kanter (75 mm)"; chip: "vankant/kupa"
            ProfilePlot { values: ctrl.zProfileWidth; axisLabel: "y tvärs bräda (0–75 mm)"; accent: Theme.violet
                          crossSection: true; leftFacet: ctrl.leftFacet; rightFacet: ctrl.rightFacet }
        }
    }
}
