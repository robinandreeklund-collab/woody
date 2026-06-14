import QtQuick
import QtQuick.Window
import QtQuick.Controls.Basic
import QtQuick.Layouts

// MASTER-skal: lista alla läshuvuden (Jetson-noder) → klicka en → styr dess
// sensorer + kalibrering på distans (CalibrationView med dm = vald RemoteNode).
ApplicationWindow {
    id: win
    width: 1560; height: 940; visible: true
    visibility: startFullscreen ? Window.FullScreen : Window.Windowed
    title: "VIRKE · MASTER"
    color: Theme.bg

    property int selIndex: -1
    property var sel: null
    function pick(i) { selIndex = i; sel = nodeManager.node(i) }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient { GradientStop { position: 0.0; color: Theme.bg2 }
                             GradientStop { position: 1.0; color: Theme.bg } }

        ColumnLayout {
            anchors.fill: parent; anchors.margins: 12; spacing: 10

            // ---- topbar ----
            RowLayout {
                Layout.fillWidth: true; spacing: 12
                Text { text: "woody · MASTER"; color: Theme.ink; font.pixelSize: 18; font.weight: Font.Bold }
                Rectangle { radius: 6; implicitWidth: mc.width+14; implicitHeight: 22; color: Theme.panel2
                    Text { id: mc; anchors.centerIn: parent
                           text: nodeManager.count + " läshuvuden"; color: Theme.violet
                           font.family: Theme.mono; font.pixelSize: 11 } }
                Item { Layout.fillWidth: true }
                Text { text: "Noder ur data/nodes.json"; color: Theme.ink3; font.pixelSize: 10; font.family: Theme.mono }
            }

            RowLayout {
                Layout.fillWidth: true; Layout.fillHeight: true; spacing: 10

                // ---- vänster: nodlista ----
                Card {
                    Layout.preferredWidth: 340; Layout.fillHeight: true
                    title: "LÄSHUVUDEN"; chip: "MASTER"; chipColor: Theme.violet
                    ListView {
                        anchors.fill: parent; clip: true; spacing: 6
                        model: nodeManager.nodeSummaries
                        delegate: Rectangle {
                            width: ListView.view.width; height: 66; radius: 10
                            color: index === win.selIndex ? Qt.rgba(0.55,0.36,0.96,0.12) : Theme.panel2
                            border.color: index === win.selIndex ? Qt.rgba(0.55,0.36,0.96,0.5) : Theme.line
                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                onClicked: win.pick(index) }
                            RowLayout {
                                anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10; spacing: 9
                                Rectangle { width: 10; height: 10; radius: 5
                                    color: modelData.connected ? Theme.teal : Theme.red
                                    SequentialAnimation on opacity { running: !modelData.connected
                                        loops: Animation.Infinite; NumberAnimation { to: 0.3; duration: 700 }
                                        NumberAnimation { to: 1; duration: 700 } } }
                                ColumnLayout { spacing: 1; Layout.fillWidth: true
                                    Text { text: modelData.name; color: Theme.ink; font.pixelSize: 13
                                           font.weight: Font.DemiBold; elide: Text.ElideRight; Layout.fillWidth: true }
                                    Text { text: (modelData.connected ? "ansluten · " + (modelData.mode||"?")
                                                                       : "ej ansluten") + " · " + modelData.host
                                           color: modelData.connected ? Theme.ink3 : Theme.red
                                           font.family: Theme.mono; font.pixelSize: 9; elide: Text.ElideRight; Layout.fillWidth: true } }
                                Rectangle {
                                    visible: modelData.connected && modelData.calib_total > 0
                                    radius: 6; implicitWidth: cb.width+10; implicitHeight: 16
                                    color: modelData.calib_done === modelData.calib_total
                                           ? Qt.rgba(0.2,0.9,0.71,0.12) : Qt.rgba(1,0.7,0.24,0.12)
                                    Text { id: cb; anchors.centerIn: parent
                                           text: (modelData.calib_done||0)+"/"+(modelData.calib_total||0)
                                           color: modelData.calib_done === modelData.calib_total ? Theme.teal : Theme.amber
                                           font.family: Theme.mono; font.pixelSize: 9 } }
                            }
                        }
                    }
                }

                // ---- höger: vald nod ----
                ColumnLayout {
                    Layout.fillWidth: true; Layout.fillHeight: true; spacing: 10
                    visible: win.sel !== null

                    // enhetsremsa + laser-arm
                    Card {
                        Layout.fillWidth: true; Layout.preferredHeight: 96
                        title: win.sel ? ("NOD · " + win.sel.nodeName.toUpperCase()) : "NOD"
                        chip: win.sel && win.sel.connected ? "ANSLUTEN" : "EJ ANSLUTEN"
                        chipColor: win.sel && win.sel.connected ? Theme.teal : Theme.red
                        RowLayout {
                            anchors.fill: parent; spacing: 8
                            Flow { Layout.fillWidth: true; spacing: 6
                                Repeater { model: win.sel ? win.sel.devices : []
                                    delegate: Rectangle { radius: 6; implicitWidth: dn.width+14; implicitHeight: 22
                                        color: Theme.panel2; border.color: modelData.connected ? Qt.rgba(0.2,0.9,0.71,0.3) : Theme.line
                                        Text { id: dn; anchors.centerIn: parent; text: modelData.name
                                               color: modelData.connected ? Theme.teal : Theme.ink3
                                               font.family: Theme.mono; font.pixelSize: 9 } } } }
                            Btn { text: "Proba om"; onClicked: if (win.sel) win.sel.refresh() }
                            Btn { text: "Arma lasrar (interlock)"; danger: true
                                  onClicked: if (win.sel) win.sel.armLasers(true) }
                            Btn { text: "Avarma"; onClicked: if (win.sel) win.sel.disarmLasers() }
                        }
                    }

                    // återanvänd kalibreringsvyn — driver fjärrnoden via samma gränssnitt.
                    // Loader: instansiera först när en nod valts (annars vore dm null).
                    Loader {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        active: win.sel !== null
                        sourceComponent: Component {
                            CalibrationView { dm: win.sel }
                        }
                    }
                }

                // tomt läge
                Card {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    visible: win.sel === null
                    title: "VÄLJ ETT LÄSHUVUD"
                    Text { anchors.centerIn: parent
                           text: nodeManager.count > 0 ? "Klicka en nod till vänster för att styra dess sensorer + kalibrering"
                                                       : "Inga noder i data/nodes.json — lägg till dina Jetson-läshuvuden"
                           color: Theme.ink3; font.pixelSize: 13 }
                }
            }
        }
    }
}
