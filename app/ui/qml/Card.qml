import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    default property alias content: body.data
    property string title: ""
    property string chip: ""
    property color chipColor: Theme.ink3
    radius: 14; color: Theme.panel; border.color: Theme.line

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 12; spacing: 8
        RowLayout {
            Layout.fillWidth: true; spacing: 8
            Text { text: root.title; color: Theme.ink2; font.pixelSize: 11
                   font.weight: Font.DemiBold; font.letterSpacing: 0.5 }
            Item { Layout.fillWidth: true }
            Rectangle {
                visible: root.chip !== ""; radius: 6; color: Theme.panel2; border.color: Theme.line
                implicitWidth: chipT.width + 14; implicitHeight: 18
                Text { id: chipT; anchors.centerIn: parent; text: root.chip
                       color: root.chipColor; font.family: Theme.mono; font.pixelSize: 9 }
            }
        }
        Item { id: body; Layout.fillWidth: true; Layout.fillHeight: true }
    }
}
