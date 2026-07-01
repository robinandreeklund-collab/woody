import QtQuick

// SaaS-knapp: primär = solid accent + vit text; danger = röd; default = vit/kant.
Rectangle {
    id: root
    property string text: ""
    property bool primary: false
    property bool danger: false
    property bool flat: false                 // ren textknapp (ingen yta)
    signal clicked()
    radius: Theme.rSm; implicitHeight: 36; implicitWidth: lbl.width + 36

    readonly property color baseFill:
        danger ? Theme.err : (primary ? Theme.accent : Theme.panel)
    color: flat ? "transparent"
         : (primary || danger)
            ? (ma.containsMouse ? Qt.darker(baseFill, 1.12) : baseFill)
            : (ma.containsMouse ? Theme.panel2 : Theme.panel)
    border.color: (primary || danger || flat) ? "transparent"
                : (ma.containsMouse ? Theme.line2 : Theme.line)
    Behavior on color { ColorAnimation { duration: 120 } }

    Text { id: lbl; anchors.centerIn: parent; text: root.text
           font.family: Theme.sans; font.pixelSize: 13; font.weight: Font.DemiBold
           color: (root.primary || root.danger) ? Theme.accentInk
                : root.flat ? Theme.accent : Theme.ink }

    MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true
                cursorShape: Qt.PointingHandCursor; onClicked: root.clicked() }
}
