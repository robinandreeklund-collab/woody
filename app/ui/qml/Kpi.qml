import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    property string label: ""
    property var value: ""
    property string unit: ""
    property color accent: Theme.ink
    radius: 10; color: Theme.panel2; border.color: Theme.line
    implicitWidth: Math.max(92, kcol.width + 26); implicitHeight: 46
    ColumnLayout {
        id: kcol; anchors.centerIn: parent; spacing: 0
        Text { text: root.label.toUpperCase(); color: Theme.ink3; font.pixelSize: 9; font.letterSpacing: 0.7 }
        RowLayout { spacing: 3
            Text { text: root.value; color: root.accent; font.family: Theme.mono
                   font.pixelSize: 17; font.weight: Font.DemiBold }
            Text { text: root.unit; visible: root.unit !== ""; color: Theme.ink2
                   font.pixelSize: 10; Layout.alignment: Qt.AlignBottom; bottomPadding: 2 }
        }
    }
}
