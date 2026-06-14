import QtQuick
import QtQuick.Layouts

// Ett kort i flott-"video wall":n — ett läshuvud i ett ögonkast.
// Stor gradbokstav, genomflöde, last-stapel, status. Klick → drill-in.
Item {
    id: root
    property var node: null
    property var summary: ({})
    property var s: node ? node.scan : ({})
    property bool online: summary.connected === true
    signal activated()

    // faux-skugga bakom ytan (renderas alltid, kort försvinner aldrig)
    Rectangle {
        anchors.fill: surface; anchors.topMargin: 5; anchors.bottomMargin: -5
        radius: surface.radius + 2
        color: Qt.rgba(Theme.shadow.r, Theme.shadow.g, Theme.shadow.b, ma.containsMouse ? 0.10 : 0.06)
    }
    Rectangle {
        id: surface
        anchors.fill: parent; radius: Theme.rLg
        color: Theme.panel
        border.color: ma.containsMouse ? Theme.tint(Theme.accent, 0.5) : Theme.line
        border.width: ma.containsMouse ? 2 : 1
        Behavior on border.color { ColorAnimation { duration: 120 } }
    }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: Theme.sp3; spacing: Theme.sp2

        // rad: status + namn + LEAD
        RowLayout {
            Layout.fillWidth: true; spacing: 7
            Rectangle { width: 9; height: 9; radius: 5; color: root.online ? Theme.ok : Theme.err
                SequentialAnimation on opacity { running: !root.online
                    loops: Animation.Infinite; NumberAnimation { to: 0.3; duration: 700 }
                    NumberAnimation { to: 1; duration: 700 } } }
            Text { text: root.summary.name || "—"; color: Theme.ink; font.family: Theme.sans
                   font.pixelSize: 14; font.weight: Font.Bold; elide: Text.ElideRight; Layout.fillWidth: true }
            Rectangle {
                visible: root.summary.has_conveyor === true
                radius: 999; implicitWidth: lt.width+12; implicitHeight: 17
                color: Theme.tint(Theme.violet, 0.14); border.color: Theme.tint(Theme.violet, 0.32)
                Text { id: lt; anchors.centerIn: parent; text: "LEAD"; color: Qt.darker(Theme.violet,1.1)
                       font.family: Theme.sans; font.pixelSize: 9; font.weight: Font.Bold } }
        }

        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: Theme.sp3

            // gradbricka
            Rectangle {
                Layout.preferredWidth: 64; Layout.preferredHeight: 64; Layout.alignment: Qt.AlignVCenter
                radius: Theme.rMd
                color: root.online && root.s.grade_class ? Theme.tint(Theme.gradeColor(root.s.grade_class), 0.14) : Theme.panel2
                border.color: root.online && root.s.grade_class ? Theme.tint(Theme.gradeColor(root.s.grade_class), 0.4) : Theme.line
                Text { anchors.centerIn: parent; text: root.online ? (root.s.grade_class || "–") : "–"
                       color: root.online && root.s.grade_class ? Theme.gradeColor(root.s.grade_class) : Theme.ink3
                       font.family: Theme.sans; font.pixelSize: 34; font.weight: Font.Black }
            }

            ColumnLayout {
                Layout.fillWidth: true; spacing: 3
                // genomflöde
                RowLayout { spacing: 5
                    Text { text: (root.online && root.s.throughput!==undefined) ? root.s.throughput.toFixed(1) : "–"
                           color: Theme.ink; font.family: Theme.sans; font.pixelSize: 20; font.weight: Font.Bold }
                    Text { text: "br/min"; color: Theme.ink3; font.pixelSize: 10
                           Layout.alignment: Qt.AlignBottom; bottomPadding: 3 } }
                Text { text: root.online ? (root.s.status || (root.s.running ? "kör" : "stopp"))
                                         : "ej ansluten · " + (root.summary.host || "")
                       color: root.online ? Theme.ink3 : Theme.err; font.family: Theme.mono
                       font.pixelSize: 9; elide: Text.ElideRight; Layout.fillWidth: true }
                Item { Layout.fillHeight: true }
                // last-stapel
                RowLayout { Layout.fillWidth: true; spacing: 6
                    Text { text: "LAST"; color: Theme.ink3; font.family: Theme.sans; font.pixelSize: 9; font.weight: Font.DemiBold }
                    Rectangle {
                        Layout.fillWidth: true; height: 6; radius: 3; color: Theme.panel2
                        Rectangle {
                            property real f: (root.online && root.s.load!==undefined) ? Math.max(0,Math.min(1, root.s.load/100)) : 0
                            width: parent.width * f; height: parent.height; radius: 3
                            color: f > 0.85 ? Theme.err : f > 0.65 ? Theme.warn : Theme.ok
                            Behavior on width { NumberAnimation { duration: 200 } } } }
                    Text { text: (root.online && root.s.load!==undefined) ? Math.round(root.s.load)+"%" : "–"
                           color: Theme.ink2; font.family: Theme.sans; font.pixelSize: 10; font.weight: Font.DemiBold } }
            }
        }
    }

    MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true
        cursorShape: Qt.PointingHandCursor; onClicked: root.activated() }
}
