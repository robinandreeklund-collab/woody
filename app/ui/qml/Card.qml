import QtQuick
import QtQuick.Layouts

// Kommersiellt kort: vit yta, mjuk (faux) skugga, tintad pill-chip.
// Skuggan ligger BAKOM ytan som egna lågalfa-lager → om den inte renderas
// (t.ex. software-backend) försvinner aldrig själva kortet.
Item {
    id: root
    default property alias content: body.data
    property string title: ""
    property string chip: ""
    property color chipColor: Theme.ink3
    property int radius: Theme.rLg
    property bool elevated: true

    implicitWidth: 120; implicitHeight: 80

    // faux-skugga (tre lågalfa-lager med växande offset)
    Rectangle {
        visible: root.elevated; anchors.fill: surface
        anchors.topMargin: 6; anchors.bottomMargin: -6
        radius: surface.radius + 2; color: Qt.rgba(Theme.shadow.r, Theme.shadow.g, Theme.shadow.b, 0.05)
    }
    Rectangle {
        visible: root.elevated; anchors.fill: surface
        anchors.topMargin: 3; anchors.bottomMargin: -3
        radius: surface.radius + 1; color: Qt.rgba(Theme.shadow.r, Theme.shadow.g, Theme.shadow.b, 0.06)
    }

    Rectangle {
        id: surface
        anchors.fill: parent
        radius: root.radius
        color: Theme.panel
        border.color: Theme.line
    }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: Theme.sp3; spacing: Theme.sp2
        RowLayout {
            Layout.fillWidth: true; spacing: Theme.sp2
            visible: root.title !== "" || root.chip !== ""
            Text { text: root.title; color: Theme.ink2; font.family: Theme.sans
                   font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.4 }
            Item { Layout.fillWidth: true }
            Rectangle {
                visible: root.chip !== ""; radius: 999
                color: Theme.tint(root.chipColor, 0.14)
                border.color: Theme.tint(root.chipColor, 0.32)
                implicitWidth: chipT.width + 16; implicitHeight: 20
                Text { id: chipT; anchors.centerIn: parent; text: root.chip
                       color: Qt.darker(root.chipColor, 1.15); font.family: Theme.sans
                       font.pixelSize: 10; font.weight: Font.DemiBold; font.letterSpacing: 0.3 }
            }
        }
        Item { id: body; Layout.fillWidth: true; Layout.fillHeight: true; clip: true }
    }
}
