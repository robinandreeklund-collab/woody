import QtQuick
import QtQuick.Layouts

// KPI-bricka: stor tabular siffra + etikett. Ljus yta, accentfärgat värde.
Rectangle {
    id: root
    property string label: ""
    property var value: ""
    property string unit: ""
    property color accent: Theme.ink
    radius: Theme.rMd; color: Theme.panel; border.color: Theme.line
    implicitWidth: Math.max(104, kcol.width + 28); implicitHeight: 56
    ColumnLayout {
        id: kcol; anchors.centerIn: parent; spacing: 2
        Text { text: root.label.toUpperCase(); color: Theme.ink3; font.family: Theme.sans
               font.pixelSize: 9; font.weight: Font.DemiBold; font.letterSpacing: 0.8
               Layout.alignment: Qt.AlignHCenter }
        RowLayout { spacing: 3; Layout.alignment: Qt.AlignHCenter
            Text { text: root.value; color: root.accent; font.family: Theme.sans
                   font.pixelSize: 22; font.weight: Font.Bold
                   font.features: { "tnum": 1 } }
            Text { text: root.unit; visible: root.unit !== ""; color: Theme.ink2
                   font.pixelSize: 11; Layout.alignment: Qt.AlignBottom; bottomPadding: 3 }
        }
    }
}
