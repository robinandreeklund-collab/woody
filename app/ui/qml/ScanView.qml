import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

// Skannings-dashboard för en fjärrnod (master) — speglar AppControllerns live-
// tillstånd via node.scan och styr via node.scan*-slots. Visar sim-skanningen
// (KPI:er, körkontroll, grad, defekter, profil, historik) på distans.
ColumnLayout {
    id: root
    property var node: null
    property var s: node ? node.scan : ({})
    spacing: 10

    // ---- körkontroll + status ----
    Card {
        Layout.fillWidth: true; Layout.preferredHeight: 92
        title: "DRIFT"; chip: root.s.mode || "?"; chipColor: Theme.violet
        RowLayout {
            anchors.fill: parent; spacing: 8
            Btn { text: root.s.running ? "Pausa" : "Starta"; primary: !root.s.running; danger: root.s.running
                  onClicked: if (root.node) root.node.scanToggleRun() }
            Btn { text: root.s.pass_mode === "single" ? "Ladda ny" : "Nästa bräda"
                  visible: root.s.run_mode === "pass"
                  onClicked: if (root.node) root.node.scanNextBoard() }
            Rectangle { width: 1; Layout.fillHeight: true; Layout.margins: 8; color: Theme.line }
            // körläge
            Repeater { model: [["pass","Pass"],["flow","Flöde"]]
                delegate: Rectangle { radius: 6; implicitWidth: rmt.width+16; implicitHeight: 26
                    color: root.s.run_mode === modelData[0] ? Theme.teal : "transparent"; border.color: Theme.line
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: if (root.node) root.node.scanSetRunMode(modelData[0]) }
                    Text { id: rmt; anchors.centerIn: parent; text: modelData[1]
                           color: root.s.run_mode === modelData[0] ? "#04222a" : Theme.ink2; font.pixelSize: 11 } } }
            Rectangle { width: 1; Layout.fillHeight: true; Layout.margins: 8; color: Theme.line; visible: root.s.run_mode==="pass" }
            Repeater { model: root.s.run_mode === "pass" ? [["single","Enkel"],["multi","Multi"]] : []
                delegate: Rectangle { radius: 6; implicitWidth: pmt.width+16; implicitHeight: 26
                    color: root.s.pass_mode === modelData[0] ? Theme.cyan : "transparent"; border.color: Theme.line
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: if (root.node) root.node.scanSetPassMode(modelData[0]) }
                    Text { id: pmt; anchors.centerIn: parent; text: modelData[1]
                           color: root.s.pass_mode === modelData[0] ? "#04222a" : Theme.ink2; font.pixelSize: 11 } } }
            Item { Layout.fillWidth: true }
            ColumnLayout { spacing: 2
                Text { text: root.s.status || "—"; color: root.s.running ? Theme.teal : Theme.amber
                       font.family: Theme.mono; font.pixelSize: 12; font.weight: Font.DemiBold }
                Rectangle { width: 160; height: 5; radius: 2.5; color: Theme.line
                    Rectangle { width: parent.width * Math.max(0,Math.min(1,(root.s.progress||0))); height: parent.height
                        radius: 2.5; color: Theme.cyan; Behavior on width { NumberAnimation { duration: 120 } } } } }
        }
    }

    // ---- notis ----
    Rectangle {
        Layout.fillWidth: true; radius: 8; visible: (root.s.notify||"") !== ""
        implicitHeight: 32; color: Qt.rgba(0.15,0.83,0.88,0.10); border.color: Qt.rgba(0.15,0.83,0.88,0.35)
        RowLayout { anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 8
            Text { text: root.s.notify || ""; color: Theme.cyan; font.pixelSize: 11; Layout.fillWidth: true }
            Btn { text: "OK"; onClicked: if (root.node) root.node.scanDismissNotify() } }
    }

    // ---- KPI:er ----
    RowLayout {
        Layout.fillWidth: true; spacing: 8
        Repeater {
            model: [
                {l:"Genomflöde", v:(root.s.throughput!==undefined?root.s.throughput.toFixed(1):"–"), u:"br/min", c:Theme.cyan},
                {l:"Brädor", v:(root.s.boards!==undefined?root.s.boards:"–"), u:"", c:Theme.ink},
                {l:"Profiltakt", v:(root.s.rate!==undefined?Math.round(root.s.rate):"–"), u:"Hz", c:Theme.teal},
                {l:"Nod-last", v:(root.s.load!==undefined?Math.round(root.s.load):"–"), u:"%", c:Theme.violet}
            ]
            delegate: Rectangle {
                Layout.fillWidth: true; implicitHeight: 56; radius: 8; color: Theme.panel2; border.color: Theme.line
                ColumnLayout { anchors.centerIn: parent; spacing: 1
                    Text { text: modelData.l; color: Theme.ink3; font.pixelSize: 9; font.family: Theme.mono; Layout.alignment: Qt.AlignHCenter }
                    RowLayout { Layout.alignment: Qt.AlignHCenter; spacing: 3
                        Text { text: modelData.v; color: modelData.c; font.pixelSize: 20; font.weight: Font.Bold }
                        Text { text: modelData.u; color: Theme.ink3; font.pixelSize: 10; Layout.alignment: Qt.AlignBottom; bottomPadding: 3 } } }
            }
        }
    }

    // ---- live bilder: ytkamera + topp/höjd ----
    Card {
        Layout.fillWidth: true; Layout.preferredHeight: 210
        title: "LIVE BILD · ytkamera + topp/höjd"; chip: "BILD"; chipColor: Theme.cyan
        RowLayout {
            anchors.fill: parent; spacing: 10
            Repeater {
                model: [["surface","Ytkamera (färg)"], ["height","Topp-/höjdkarta"]]
                delegate: ColumnLayout {
                    Layout.fillWidth: true; Layout.fillHeight: true; spacing: 3
                    Text { text: modelData[1]; color: Theme.ink3; font.pixelSize: 10; font.family: Theme.mono }
                    Rectangle {
                        Layout.fillWidth: true; Layout.fillHeight: true; radius: 8
                        color: "#05080c"; border.color: Theme.line; clip: true
                        Image {
                            anchors.fill: parent; anchors.margins: 4; cache: false; smooth: true
                            fillMode: Image.PreserveAspectFit
                            source: (root.node && root.node.host && root.node.imgRev > 0)
                                    ? "image://remote/" + root.node.host + "/" + modelData[0] + "?" + root.node.imgRev : ""
                        }
                        Text { anchors.centerIn: parent
                               visible: !(root.node && root.node.imgRev > 0)
                               text: "väntar på skanning…"; color: Theme.ink3; font.pixelSize: 11 }
                    }
                }
            }
        }
    }

    // ---- grad + defekter + historik ----
    RowLayout {
        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 10

        // betyg
        Card {
            Layout.preferredWidth: 240; Layout.fillHeight: true
            title: "BEDÖMNING"; chip: "GRAD"; chipColor: Theme.amber
            ColumnLayout {
                anchors.fill: parent; spacing: 8
                Rectangle {
                    Layout.alignment: Qt.AlignHCenter; width: 96; height: 96; radius: 48
                    color: Qt.rgba(0,0,0,0.2); border.width: 3; border.color: root.s.grade_color || Theme.line
                    Text { anchors.centerIn: parent; text: root.s.grade_class || "–"
                           color: root.s.grade_color || Theme.ink3; font.pixelSize: 46; font.weight: Font.Bold } }
                Text { text: root.s.grade_title || "Inväntar"; color: Theme.ink; font.pixelSize: 14
                       font.weight: Font.DemiBold; Layout.alignment: Qt.AlignHCenter; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                Text { text: root.s.grade_reason || "—"; color: Theme.ink3; font.pixelSize: 10; font.family: Theme.mono
                       Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap }
                Text { visible: (root.s.grade_governing||"")!==""; text: "styrande: " + (root.s.grade_governing||"")
                       color: Theme.amber; font.pixelSize: 9; font.family: Theme.mono; Layout.alignment: Qt.AlignHCenter }
                Item { Layout.fillHeight: true }
            }
        }

        // defekter
        Card {
            Layout.fillWidth: true; Layout.fillHeight: true
            title: "DEFEKTER"; chip: (root.s.defects ? root.s.defects.length : 0) + " st"; chipColor: Theme.red
            Flickable { anchors.fill: parent; contentHeight: dcol.height; clip: true
                ColumnLayout { id: dcol; width: parent.width; spacing: 4
                    Repeater { model: root.s.defects || []
                        delegate: Rectangle { Layout.fillWidth: true; implicitHeight: 26; radius: 6
                            color: Theme.panel2; border.color: Theme.line
                            RowLayout { anchors.fill: parent; anchors.leftMargin: 8; anchors.rightMargin: 8; spacing: 8
                                Rectangle { width: 9; height: 9; radius: 4.5; color: modelData.color || Theme.ink3 }
                                Text { text: modelData.name; color: Theme.ink; font.pixelSize: 11; Layout.fillWidth: true }
                                Text { text: "x"+modelData.x+" y"+modelData.y+" ⌀"+modelData.dia; color: Theme.ink3
                                       font.family: Theme.mono; font.pixelSize: 9 } } } }
                    Text { visible: !(root.s.defects && root.s.defects.length); text: "Inga defekter"
                           color: Theme.ink3; font.pixelSize: 11 } }
            }
        }

        // historik
        Card {
            Layout.preferredWidth: 240; Layout.fillHeight: true
            title: "HISTORIK"; chip: (root.s.history ? root.s.history.length : 0); chipColor: Theme.teal
            Flickable { anchors.fill: parent; contentHeight: hcol.height; clip: true
                ColumnLayout { id: hcol; width: parent.width; spacing: 4
                    Repeater { model: root.s.history || []
                        delegate: Rectangle { Layout.fillWidth: true; implicitHeight: 30; radius: 6
                            color: Theme.panel2; border.color: Theme.line
                            RowLayout { anchors.fill: parent; anchors.leftMargin: 8; anchors.rightMargin: 8; spacing: 8
                                Text { text: "#" + (modelData.n!==undefined?modelData.n:"") ; color: Theme.ink3; font.family: Theme.mono; font.pixelSize: 10 }
                                Text { text: modelData.cls || modelData.gradeClass || "?"; color: modelData.color || Theme.ink
                                       font.pixelSize: 13; font.weight: Font.Bold }
                                Text { text: modelData.title || ""; color: Theme.ink2; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight } } } }
                    Text { visible: !(root.s.history && root.s.history.length); text: "Ingen historik än"
                           color: Theme.ink3; font.pixelSize: 11 } }
            }
        }
    }
}
