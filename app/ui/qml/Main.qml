import QtQuick
import QtQuick.Window
import QtQuick.Controls.Basic
import QtQuick.Layouts

ApplicationWindow {
    id: win
    width: 1560; height: 940
    visible: true
    visibility: startFullscreen ? Window.FullScreen : Window.Windowed
    title: "VIRKE · Kontrollsystem"
    color: Theme.bg

    property int navIndex: 0
    Component.onCompleted: ctrl.start()

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.bg2 }
            GradientStop { position: 1.0; color: Theme.bg }
        }
    }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 12; spacing: 12

        // ---------------------------------------------------------- HEADER
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 64
            radius: 14; color: Theme.panel; border.color: Theme.line
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 18; anchors.rightMargin: 16; spacing: 16
                Rectangle {
                    width: 38; height: 38; radius: 11
                    gradient: Gradient { orientation: Gradient.Horizontal
                        GradientStop { position: 0; color: Theme.cyan }
                        GradientStop { position: 1; color: Theme.violet } }
                    Rectangle { anchors.centerIn: parent; width: 32; height: 32; radius: 8; color: Theme.panel
                        Canvas { anchors.fill: parent; onPaint: {
                            var c = getContext("2d"); c.reset();
                            c.strokeStyle = Theme.cyan; c.lineWidth = 1.6; c.lineJoin="round"; c.lineCap="round";
                            c.beginPath(); c.moveTo(6,22); c.lineTo(13,7); c.lineTo(18,15); c.lineTo(22,10); c.lineTo(27,22); c.stroke();
                        } } }
                }
                ColumnLayout {
                    spacing: 0
                    Text { text: "VIRKE · Kontrollsystem"; color: Theme.ink; font.pixelSize: 15; font.weight: Font.DemiBold }
                    Text { text: "Dubbel-oblik laserskanner · Prototyp 500 mm"; color: Theme.ink3; font.pixelSize: 10; font.family: Theme.mono; font.capitalization: Font.AllUppercase }
                }
                // ---- navigering ----
                Rectangle {
                    Layout.leftMargin: 8; radius: 11; color: Theme.panel2; border.color: Theme.line
                    implicitWidth: navRow.width + 8; implicitHeight: 38
                    RowLayout {
                        id: navRow; anchors.centerIn: parent; spacing: 4
                        NavTab { text: "Översikt";    active: navIndex===0; onClicked: navIndex=0 }
                        NavTab { text: "Sensorer";    active: navIndex===1; onClicked: navIndex=1 }
                        NavTab { text: "Logg";        active: navIndex===2; onClicked: navIndex=2 }
                        NavTab { text: "Kalibrering"; active: navIndex===3; onClicked: navIndex=3 }
                    }
                }
                Item { Layout.fillWidth: true }
                Kpi { label: "Genomflöde"; value: ctrl.throughput.toFixed(1); unit: "br/min"; accent: Theme.cyan }
                Kpi { label: "Brädor";     value: ctrl.boardCount }
                Kpi { label: "Jetson last"; value: Math.round(ctrl.jetsonLoad); unit: "%"; accent: Theme.teal }
                Kpi { label: "Profiltakt"; value: Math.round(ctrl.profileRate); unit: "Hz" }
                Rectangle {
                    radius: 8; color: Theme.panel2; border.color: Theme.line2
                    implicitWidth: modeT.width + 18; implicitHeight: 26
                    Text { id: modeT; anchors.centerIn: parent; text: "LÄGE " + ctrl.modeText; color: Theme.violet; font.family: Theme.mono; font.pixelSize: 10; font.weight: Font.DemiBold }
                }
                Rectangle {
                    radius: 999; implicitWidth: stRow.width + 28; implicitHeight: 38; color: Theme.panel2
                    border.color: ctrl.running ? Qt.rgba(0.2,0.9,0.71,0.35) : Qt.rgba(1,0.7,0.24,0.35)
                    RowLayout {
                        id: stRow; anchors.centerIn: parent; spacing: 9
                        Rectangle { width: 9; height: 9; radius: 4.5; color: ctrl.running ? Theme.teal : Theme.amber
                            SequentialAnimation on opacity { running: ctrl.running; loops: Animation.Infinite
                                NumberAnimation { from: 1; to: 0.3; duration: 700 }
                                NumberAnimation { from: 0.3; to: 1; duration: 700 } } }
                        Text { text: ctrl.statusText; color: ctrl.running ? Theme.teal : Theme.amber
                               font.family: Theme.mono; font.pixelSize: 12; font.weight: Font.DemiBold }
                    }
                }
            }
        }

        // ---------------------------------------------------------- VYER
        StackLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            currentIndex: navIndex
            DashboardView {}
            SensorsView {}
            LogView {}
            CalibrationView {}
        }

        // ---------------------------------------------------------- FOOTER
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 56
            radius: 14; color: Theme.panel; border.color: Theme.line
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 16; spacing: 14
                Btn { primary: true; danger: ctrl.running; text: ctrl.running ? "Pausa" : "Starta"; onClicked: ctrl.toggleRun() }
                Btn { text: "Nästa bräda"; onClicked: ctrl.nextBoard() }
                CtrlSlider { label: "Matning"; from: 10; to: 120; step: 5; value: ctrl.feedSpeed; suffix: " mm/s"; onMoved: ctrl.setFeed(v) }
                CtrlSlider { label: "Profiltakt"; from: 200; to: 800; step: 50; value: ctrl.profileRate; suffix: " Hz"; onMoved: ctrl.setRate(v) }
                Item { Layout.fillWidth: true }
                Rectangle {
                    radius: 9; implicitHeight: 34; implicitWidth: autoRow.width + 22
                    color: Theme.panel2; border.color: ctrl.autoAdvance ? Qt.rgba(0.2,0.9,0.71,0.35) : Theme.line
                    RowLayout { id: autoRow; anchors.centerIn: parent; spacing: 8
                        Rectangle { width: 30; height: 16; radius: 8
                            color: ctrl.autoAdvance ? Qt.rgba(0.2,0.9,0.71,0.35) : Theme.line2
                            Rectangle { width: 12; height: 12; radius: 6; y: 2; x: ctrl.autoAdvance ? 16 : 2
                                color: ctrl.autoAdvance ? Theme.teal : Theme.ink3
                                Behavior on x { NumberAnimation { duration: 120 } } } }
                        Text { text: "Auto-mata"; color: ctrl.autoAdvance ? Theme.teal : Theme.ink2; font.pixelSize: 11 } }
                    MouseArea { anchors.fill: parent; onClicked: ctrl.setAuto(!ctrl.autoAdvance) }
                }
            }
        }
    }
}
