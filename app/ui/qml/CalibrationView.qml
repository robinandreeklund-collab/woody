import QtQuick
import QtQuick.Layouts

// Kalibrering — välj enhet (vänster) → kör dess metoder (mitten) → geometri (höger).
// Status persisteras (data/calibration.json) och syns även på sensorkorten.
RowLayout {
    id: root
    spacing: 12

    // dm = enheten vi styr: lokal DeviceManager (devmgr) ELLER en fjärrnod (RemoteNode).
    // Samma gränssnitt → samma vy driver både lokalt och master/slave-fjärrstyrt.
    property var dm: (typeof devmgr !== 'undefined' && devmgr) ? devmgr : null
    property var rig: (typeof ctrl !== 'undefined' && ctrl) ? root.rig : null
    property string selectedId: "prof_red"
    property var methods: []

    function select(devId) {
        selectedId = devId
        reload()
    }
    function reload() { methods = dm ? dm.methodsFor(selectedId) : [] }
    Component.onCompleted: reload()
    Connections { target: root.dm; function onMethodsChanged() { root.reload() } }

    function devName(id) {
        var ds = dm.devices
        for (var i = 0; i < ds.length; i++) if (ds[i].id === id) return ds[i].name
        return id
    }

    // ------------------------------------------------------------- enheter
    Card {
        Layout.preferredWidth: 290; Layout.fillHeight: true
        title: "ENHETER"; chip: dm.mode.toUpperCase(); chipColor: Theme.violet
        ListView {
            anchors.fill: parent; clip: true; spacing: 6
            model: dm.devices
            delegate: Rectangle {
                width: ListView.view.width; height: 56; radius: 10
                color: modelData.id === root.selectedId ? Qt.rgba(0.15,0.83,0.88,0.10) : Theme.panel2
                border.color: modelData.id === root.selectedId ? Qt.rgba(0.15,0.83,0.88,0.4)
                              : (dma.containsMouse ? Theme.line2 : Theme.line)
                MouseArea { id: dma; anchors.fill: parent; hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor; onClicked: root.select(modelData.id) }
                RowLayout {
                    anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10; spacing: 9
                    Rectangle { width: 8; height: 8; radius: 4
                        color: modelData.connected ? Theme.teal : Theme.red }
                    ColumnLayout { spacing: 1; Layout.fillWidth: true
                        Text { text: modelData.name; color: Theme.ink; font.pixelSize: 12
                               font.weight: Font.DemiBold; elide: Text.ElideRight; Layout.fillWidth: true }
                        Text { text: modelData.status; color: modelData.connected ? Theme.ink3 : Theme.red
                               font.family: Theme.mono; font.pixelSize: 9; elide: Text.ElideRight; Layout.fillWidth: true } }
                    Rectangle {
                        visible: modelData.calibTotal > 0
                        radius: 6; implicitWidth: cb.width + 10; implicitHeight: 16
                        color: modelData.calibDone === modelData.calibTotal
                               ? Qt.rgba(0.2,0.9,0.71,0.12) : Qt.rgba(1,0.7,0.24,0.12)
                        Text { id: cb; anchors.centerIn: parent
                               text: modelData.calibDone + "/" + modelData.calibTotal
                               color: modelData.calibDone === modelData.calibTotal ? Theme.teal : Theme.amber
                               font.family: Theme.mono; font.pixelSize: 9 } }
                }
            }
        }
    }

    // ------------------------------------------------------------- metoder
    Card {
        Layout.fillWidth: true; Layout.fillHeight: true
        title: "KALIBRERINGSMETODER · " + root.devName(root.selectedId).toUpperCase()
        chip: root.methods.length + " metoder"; chipColor: Theme.cyan
        ColumnLayout {
            anchors.fill: parent; spacing: 10

            Flickable {
                Layout.fillWidth: true; Layout.fillHeight: true
                contentHeight: mcol.height; clip: true
                ColumnLayout {
                    id: mcol; width: parent.width; spacing: 8
                    Repeater {
                        model: root.methods
                        delegate: Rectangle {
                            Layout.fillWidth: true; radius: 10
                            color: Theme.panel2; border.color: Theme.line
                            implicitHeight: mic.height + 20
                            ColumnLayout {
                                id: mic; x: 12; y: 10; width: parent.width - 24; spacing: 4
                                RowLayout {
                                    Layout.fillWidth: true; spacing: 8
                                    Text { text: modelData.title; color: Theme.ink; font.pixelSize: 13; font.weight: Font.DemiBold }
                                    Rectangle {
                                        visible: modelData.auto === true
                                        radius: 5; implicitWidth: aut.width+10; implicitHeight: 16
                                        color: Qt.rgba(0.15,0.83,0.88,0.13); border.color: Qt.rgba(0.15,0.83,0.88,0.4)
                                        Text { id: aut; anchors.centerIn: parent; text: "AUTO"
                                               color: Theme.cyan; font.family: Theme.mono; font.pixelSize: 8; font.weight: Font.DemiBold }
                                    }
                                    Rectangle { radius: 6; implicitWidth: mst.width+12; implicitHeight: 18
                                        color: modelData.done ? Qt.rgba(0.2,0.9,0.71,0.12) : Qt.rgba(1,0.7,0.24,0.12)
                                        border.color: modelData.done ? Qt.rgba(0.2,0.9,0.71,0.3) : Qt.rgba(1,0.7,0.24,0.3)
                                        Text { id: mst; anchors.centerIn: parent
                                               text: modelData.done ? "KALIBRERAD " + modelData.date : "EJ KALIBRERAD"
                                               color: modelData.done ? Theme.teal : Theme.amber
                                               font.family: Theme.mono; font.pixelSize: 9 } }
                                    Item { Layout.fillWidth: true }
                                    Btn {
                                        text: dm.calibRunning ? "Kör…" : (modelData.done ? "Kör om" : "Kör")
                                        primary: !modelData.done
                                        enabled: !dm.calibRunning
                                        opacity: enabled ? 1 : 0.45
                                        onClicked: dm.startCalibration(root.selectedId, modelData.id)
                                    }
                                }
                                Text { text: modelData.desc; color: Theme.ink3; font.pixelSize: 11
                                       Layout.fillWidth: true; wrapMode: Text.WordWrap }
                                Text { visible: modelData.summary !== ""
                                       text: modelData.summary; color: Theme.cyan
                                       font.family: Theme.mono; font.pixelSize: 10
                                       Layout.fillWidth: true; wrapMode: Text.WordWrap }
                                RowLayout {
                                    spacing: 6
                                    Repeater { model: modelData.steps
                                        delegate: Rectangle { radius: 5; implicitWidth: stp.width+10; implicitHeight: 16
                                            color: Qt.rgba(1,1,1,0.03); border.color: Theme.line
                                            Text { id: stp; anchors.centerIn: parent; text: (index+1)+". "+modelData
                                                   color: Theme.ink3; font.pixelSize: 8; font.family: Theme.mono } } }
                                }
                            }
                        }
                    }
                }
            }

            // -------------------------------------------------- pågående körning
            Rectangle {
                Layout.fillWidth: true; radius: 10
                visible: dm.calibRunning || dm.calibResult !== ""
                color: Theme.panel2
                border.color: dm.calibRunning ? Qt.rgba(0.15,0.83,0.88,0.4)
                              : (dm.calibOk ? Qt.rgba(0.2,0.9,0.71,0.35) : Qt.rgba(1,0.3,0.37,0.35))
                implicitHeight: wcol.height + 20
                ColumnLayout {
                    id: wcol; x: 12; y: 10; width: parent.width - 24; spacing: 6
                    RowLayout {
                        Layout.fillWidth: true; spacing: 10
                        Text {
                            text: dm.calibRunning
                                  ? "KÖR: " + dm.calibTitle + " · " + root.devName(dm.calibDevice)
                                  : (dm.calibOk ? "KLAR: " + dm.calibTitle : "AVBRUTEN/FEL: " + dm.calibTitle)
                            color: dm.calibRunning ? Theme.cyan : (dm.calibOk ? Theme.teal : Theme.red)
                            font.pixelSize: 12; font.weight: Font.DemiBold; font.family: Theme.mono
                        }
                        Item { Layout.fillWidth: true }
                        Btn { visible: dm.calibRunning; text: "Avbryt"; onClicked: dm.cancelCalibration() }
                    }
                    Rectangle {
                        Layout.fillWidth: true; height: 8; radius: 4; color: Theme.line
                        Rectangle { width: parent.width * dm.calibPct; height: parent.height; radius: 4
                            color: dm.calibRunning ? Theme.cyan : (dm.calibOk ? Theme.teal : Theme.red)
                            Behavior on width { NumberAnimation { duration: 110 } } }
                    }
                    Repeater { model: dm.calibLog
                        delegate: Text { text: modelData; color: Theme.teal; font.family: Theme.mono; font.pixelSize: 10 } }
                    Text { visible: dm.calibRunning; text: "▸ " + dm.calibStep
                           color: Theme.ink2; font.family: Theme.mono; font.pixelSize: 10 }
                    Text { visible: !dm.calibRunning && dm.calibResult !== ""
                           text: dm.calibResult; color: dm.calibOk ? Theme.cyan : Theme.red
                           font.family: Theme.mono; font.pixelSize: 10
                           Layout.fillWidth: true; wrapMode: Text.WordWrap }
                }
            }
        }
    }

    // ------------------------------------------------------------- geometri
    Card {
        visible: root.rig !== null            // döljs i master-drill-in (ingen lokal ctrl)
        Layout.preferredWidth: visible ? 330 : 0; Layout.fillHeight: true
        title: "RIGGENS GEOMETRI"; chip: "sanningskälla"; chipColor: Theme.teal
        Flickable {
            anchors.fill: parent; contentHeight: gcol.height; clip: true
            ColumnLayout {
                id: gcol; width: parent.width; spacing: 0
                Repeater {
                    model: root.rig ? [
                        ["Brädans längd (X)", root.rig.len.toFixed(0) + " mm"],
                        ["Brädans bredd (Y)", root.rig.width.toFixed(0) + " mm"],
                        ["Brädans tjocklek (Z)", root.rig.thick.toFixed(0) + " mm"],
                        ["Arbetsavstånd WD", root.rig.wd.toFixed(0) + " mm"],
                        ["Kamera-arm (fr. lod)", root.rig.camArm.toFixed(0) + "°"],
                        ["Laser-arm (fr. lod)", root.rig.laserArm.toFixed(0) + "°"],
                        ["Trianguleringsvinkel θ", root.rig.theta.toFixed(0) + "°"],
                        ["Obliquitet", root.rig.oblique.toFixed(1) + "°"],
                        ["Kamerahöjd", root.rig.camHeight + " mm"],
                        ["Kamera-offset", root.rig.camOffset + " mm"],
                        ["Laserhöjd", root.rig.laserHeight + " mm"],
                        ["Laser-offset", root.rig.laserOffset + " mm"],
                        ["Baslinje kamera↔laser", root.rig.baseline + " mm"],
                        ["Ytkamera WD (centrum)", root.rig.surfWd.toFixed(0) + " mm"],
                        ["Ytupplösning", root.rig.surfMmPx.toFixed(3) + " mm/px"],
                        ["Profil lateral uppl.", root.rig.profLatMmPx.toFixed(3) + " mm/px"],
                    ] : []
                    delegate: Rectangle {
                        Layout.fillWidth: true; height: 30
                        color: index % 2 ? "transparent" : Qt.rgba(1,1,1,0.018)
                        RowLayout { anchors.fill: parent; anchors.leftMargin: 4; anchors.rightMargin: 4
                            Text { text: modelData[0]; color: Theme.ink2; font.pixelSize: 11 }
                            Item { Layout.fillWidth: true }
                            Text { text: modelData[1]; color: Theme.cyan; font.family: Theme.mono; font.pixelSize: 11; font.weight: Font.DemiBold } }
                    }
                }
            }
        }
    }
}
