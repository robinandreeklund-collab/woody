import QtQuick

Rectangle {
    id: root
    property string text: ""
    property bool active: false
    signal clicked()
    radius: 8; implicitHeight: 30; implicitWidth: lbl.width + 28
    color: active ? Theme.panel : (ma.containsMouse ? Theme.panel2 : "transparent")
    Text { id: lbl; anchors.centerIn: parent; text: root.text
           color: root.active ? Theme.ink : Theme.ink3; font.pixelSize: 12; font.weight: Font.DemiBold }
    MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true
                cursorShape: Qt.PointingHandCursor; onClicked: root.clicked() }
}
