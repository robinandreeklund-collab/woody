import QtQuick
import QtQuick.Layouts

ColumnLayout {
    spacing: 12

    // ============================ LIVE KAMEROR (header) ====================
    // RÖD/GRÖN profilkamera + linjekamera. REAL = riktig stream, SIM = demo-data.
    RowLayout {
        Layout.fillWidth: true; Layout.preferredHeight: 138
        spacing: 12
        Repeater {
            model: [["RÖD · MV-CS050 mono · 638 nm", "cam_red",   Theme.red],
                    ["GRÖN · MV-CS050 mono · 520 nm", "cam_green", Theme.grn],
                    ["Linjekamera · HT-GELM44C 4K",   "cam_line",  Theme.blue]]
            delegate: Card {
                id: camCard
                Layout.fillWidth: true; Layout.fillHeight: true
                title: modelData[0]; chipColor: modelData[2]
                chip: ctrl.modeText === "REAL" ? "● LIVE" : "DEMO"
                property int camKind: index
                property string camName: modelData[1]
                property bool q3d: typeof quick3dAvailable !== "undefined" && quick3dAvailable
                Rectangle {
                    anchors.fill: parent; radius: 8; color: "#05080c"; clip: true
                    // ÄKTA renderad kameravy (scenen sedd från kamerans pose + lins-FOV).
                    // Faller tillbaka till bild-providern i mjukvaruläge (utan Quick3D).
                    Loader {
                        anchors.fill: parent; anchors.margins: 2
                        active: camCard.q3d
                        sourceComponent: Component { CamView3D { camKind: camCard.camKind } }
                    }
                    Item {
                        anchors.fill: parent; anchors.margins: 2; visible: !camCard.q3d
                        Image {
                            anchors.fill: parent
                            fillMode: Image.PreserveAspectFit; smooth: true
                            cache: false; asynchronous: false
                            source: "image://live/" + camName + "/" + ctrl.camRev
                        }
                        Text {
                            anchors.centerIn: parent; visible: ctrl.camRev === 0
                            text: "väntar på skanning…"; color: Theme.ink3; font.pixelSize: 11; font.italic: true
                        }
                    }
                }
            }
        }
    }

    // ============================ 3D + ANALYS ==============================
    RowLayout {
        id: aroot
        Layout.fillWidth: true; Layout.fillHeight: true
        spacing: 12

        // ---- 3D-REKONSTRUKTION ----
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

        // ---- HÖGER: skevhet + profiler ----
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
}
