import QtQuick

Rectangle {
    id: root
    property string text: ""
    property bool primary: false
    property bool danger: false
    signal clicked()
    radius: 10; implicitHeight: 36; implicitWidth: lbl.width + 34
    color: primary ? (danger ? Theme.red : Theme.cyan)
                   : (ma.containsMouse ? Theme.line : Theme.panel2)
    border.color: primary ? "transparent" : (ma.containsMouse ? Theme.cyan : Theme.line2)
    Behavior on color { ColorAnimation { duration: 130 } }
    Text { id: lbl; anchors.centerIn: parent; text: root.text
           color: root.primary ? "#04222a" : Theme.ink; font.pixelSize: 13; font.weight: Font.DemiBold }
    MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true
                cursorShape: Qt.PointingHandCursor; onClicked: root.clicked() }
}
