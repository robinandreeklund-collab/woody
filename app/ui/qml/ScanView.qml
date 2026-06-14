import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

// Skannings-dashboard för en fjärrnod (master) — speglar AppControllerns live-
// tillstånd via node.scan och styr via node.scan*-slots. Allt visuellt ligger i
// EN fillHeight-rad (kameror | 3D | grad/defekter/historik) → inget överlappar.
ColumnLayout {
    id: root
    property var node: null
    property var s: node ? node.scan : ({})
    spacing: 8

    // ---- körkontroll + status (fast höjd) ----
    Card {
        Layout.fillWidth: true; Layout.preferredHeight: 80
        title: "DRIFT"; chip: root.s.mode || "?"; chipColor: Theme.violet
        RowLayout {
            anchors.fill: parent; spacing: 8
            Btn { text: root.s.running ? "Pausa" : "Starta"; primary: !root.s.running; danger: root.s.running
                  onClicked: if (root.node) root.node.scanToggleRun() }
            Btn { text: root.s.pass_mode === "single" ? "Ladda ny" : "Nästa bräda"
                  visible: root.s.run_mode === "pass"
                  onClicked: if (root.node) root.node.scanNextBoard() }
            Rectangle { width: 1; Layout.preferredHeight: 24; color: Theme.line }
            Repeater { model: [["pass","Pass"],["flow","Flöde"]]
                delegate: Rectangle { radius: 6; implicitWidth: rmt.width+16; implicitHeight: 26
                    color: root.s.run_mode === modelData[0] ? Theme.teal : "transparent"; border.color: Theme.line
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: if (root.node) root.node.scanSetRunMode(modelData[0]) }
                    Text { id: rmt; anchors.centerIn: parent; text: modelData[1]
                           color: root.s.run_mode === modelData[0] ? "#04222a" : Theme.ink2; font.pixelSize: 11 } } }
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
                       font.family: Theme.mono; font.pixelSize: 12; font.weight: Font.DemiBold; Layout.alignment: Qt.AlignRight }
                Rectangle { width: 170; height: 5; radius: 2.5; color: Theme.line
                    Rectangle { width: parent.width * Math.max(0,Math.min(1,(root.s.progress||0))); height: parent.height
                        radius: 2.5; color: Theme.cyan; Behavior on width { NumberAnimation { duration: 120 } } } } }
        }
    }

    // ---- notis ----
    Rectangle {
        Layout.fillWidth: true; radius: 8; visible: (root.s.notify||"") !== ""
        Layout.preferredHeight: 30; color: Qt.rgba(0.15,0.83,0.88,0.10); border.color: Qt.rgba(0.15,0.83,0.88,0.35)
        RowLayout { anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 8
            Text { text: root.s.notify || ""; color: Theme.cyan; font.pixelSize: 11; Layout.fillWidth: true }
            Btn { text: "OK"; onClicked: if (root.node) root.node.scanDismissNotify() } }
    }

    // ---- KPI:er (fast höjd) ----
    RowLayout {
        Layout.fillWidth: true; Layout.preferredHeight: 56; spacing: 8
        Repeater {
            model: [
                {l:"Genomflöde", v:(root.s.throughput!==undefined?root.s.throughput.toFixed(1):"–"), u:"br/min", c:Theme.cyan},
                {l:"Brädor", v:(root.s.boards!==undefined?root.s.boards:"–"), u:"", c:Theme.ink},
                {l:"Profiltakt", v:(root.s.rate!==undefined?Math.round(root.s.rate):"–"), u:"Hz", c:Theme.teal},
                {l:"Nod-last", v:(root.s.load!==undefined?Math.round(root.s.load):"–"), u:"%", c:Theme.violet}
            ]
            delegate: Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true; radius: 8; color: Theme.panel2; border.color: Theme.line
                ColumnLayout { anchors.centerIn: parent; spacing: 1
                    Text { text: modelData.l; color: Theme.ink3; font.pixelSize: 9; font.family: Theme.mono; Layout.alignment: Qt.AlignHCenter }
                    RowLayout { Layout.alignment: Qt.AlignHCenter; spacing: 3
                        Text { text: modelData.v; color: modelData.c; font.pixelSize: 20; font.weight: Font.Bold }
                        Text { text: modelData.u; color: Theme.ink3; font.pixelSize: 10; Layout.alignment: Qt.AlignBottom; bottomPadding: 3 } } }
            }
        }
    }

    // ---- HUVUDOMRÅDE (allt i en fillHeight-rad → inget överlapp) ----
    RowLayout {
        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 10

        // kamera-feed (ytkamera + profilkamerornas laserstripe)
        Card {
            Layout.preferredWidth: 300; Layout.minimumWidth: 270; Layout.maximumWidth: 320
            Layout.fillHeight: true
            title: "KAMEROR · live"; chip: "FEED"; chipColor: Theme.cyan
            ColumnLayout {
                anchors.fill: parent; spacing: 6
                Repeater {
                    model: [["surface","Ytkamera (färg, 4096 px)"],
                            ["cam_red","Profil RÖD · 650 nm"],
                            ["cam_green","Profil GRÖN · 520 nm"]]
                    delegate: ColumnLayout {
                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 2
                        Text { text: modelData[1]; color: Theme.ink3; font.pixelSize: 9; font.family: Theme.mono }
                        Rectangle {
                            Layout.fillWidth: true; Layout.fillHeight: true; radius: 6
                            color: "#05080c"; border.color: Theme.line; clip: true
                            Image {
                                anchors.fill: parent; anchors.margins: 3; cache: false; smooth: true
                                fillMode: Image.PreserveAspectFit
                                source: (root.node && root.node.host && root.node.imgRev > 0)
                                        ? "image://remote/" + root.node.host + "/" + modelData[0] + "?" + root.node.imgRev : ""
                            }
                            Text { anchors.centerIn: parent; visible: !(root.node && root.node.imgRev > 0)
                                   text: "ingen signal"; color: Theme.ink3; font.pixelSize: 10 }
                        }
                    }
                }
            }
        }

        // 3D-rekonstruktion
        Card {
            Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumWidth: 300
            title: "3D-REKONSTRUKTION"; chip: "LIVE 3D"; chipColor: Theme.teal
            Board3DSoft {
                anchors.fill: parent; anchors.margins: 6
                mesh: root.node ? root.node.mesh3d : null
            }
        }

        // höger kolumn: betyg + defekter + historik (staplade)
        ColumnLayout {
            Layout.preferredWidth: 290; Layout.minimumWidth: 260; Layout.maximumWidth: 320
            Layout.fillHeight: true; spacing: 10

            Card {
                Layout.fillWidth: true; Layout.preferredHeight: 230
                title: "BEDÖMNING"; chip: "GRAD"; chipColor: Theme.amber
                ColumnLayout {
                    anchors.fill: parent; spacing: 6
                    Rectangle {
                        Layout.alignment: Qt.AlignHCenter; width: 84; height: 84; radius: 42
                        color: Qt.rgba(0,0,0,0.2); border.width: 3; border.color: root.s.grade_color || Theme.line
                        Text { anchors.centerIn: parent; text: root.s.grade_class || "–"
                               color: root.s.grade_color || Theme.ink3; font.pixelSize: 40; font.weight: Font.Bold } }
                    Text { text: root.s.grade_title || "Inväntar"; color: Theme.ink; font.pixelSize: 13
                           font.weight: Font.DemiBold; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap }
                    Text { text: root.s.grade_reason || "—"; color: Theme.ink3; font.pixelSize: 9; font.family: Theme.mono
                           Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap }
                    Item { Layout.fillHeight: true }
                }
            }

            Card {
                Layout.fillWidth: true; Layout.fillHeight: true
                title: "DEFEKTER"; chip: (root.s.defects ? root.s.defects.length : 0) + " st"; chipColor: Theme.red
                Flickable { anchors.fill: parent; contentHeight: dcol.height; clip: true
                    ColumnLayout { id: dcol; width: parent.width; spacing: 4
                        Repeater { model: root.s.defects || []
                            delegate: Rectangle { Layout.fillWidth: true; implicitHeight: 24; radius: 6
                                color: Theme.panel2; border.color: Theme.line
                                RowLayout { anchors.fill: parent; anchors.leftMargin: 8; anchors.rightMargin: 8; spacing: 8
                                    Rectangle { width: 8; height: 8; radius: 4; color: modelData.color || Theme.ink3 }
                                    Text { text: modelData.name; color: Theme.ink; font.pixelSize: 10; Layout.fillWidth: true }
                                    Text { text: "x"+modelData.x+" ⌀"+modelData.dia; color: Theme.ink3; font.family: Theme.mono; font.pixelSize: 9 } } } }
                        Text { visible: !(root.s.defects && root.s.defects.length); text: "Inga defekter"; color: Theme.ink3; font.pixelSize: 11 } }
                }
            }

            Card {
                Layout.fillWidth: true; Layout.fillHeight: true
                title: "HISTORIK"; chip: (root.s.history ? root.s.history.length : 0); chipColor: Theme.teal
                ListView {
                    anchors.fill: parent; clip: true; spacing: 3
                    model: root.s.history || []
                    delegate: Rectangle { width: ListView.view.width; height: 28; radius: 6
                        color: Theme.panel2; border.color: Theme.line
                        RowLayout { anchors.fill: parent; anchors.leftMargin: 8; anchors.rightMargin: 8; spacing: 8
                            Text { text: "#" + (modelData.n!==undefined?modelData.n:""); color: Theme.ink3; font.family: Theme.mono; font.pixelSize: 10 }
                            Text { text: modelData.cls || "?"; color: modelData.color || Theme.ink; font.pixelSize: 13; font.weight: Font.Bold }
                            Text { text: modelData.title || ""; color: Theme.ink2; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight } } }
                }
            }
        }
    }
}
