import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

// Skannings-dashboard för en fjärrnod (master) — speglar AppControllerns live-
// tillstånd via node.scan, styr via node.scan*-slots. Kommersiell layout:
// driftrad · KPI:er · [profilkameror | yta+defekter över 3D | bedömning/historik].
ColumnLayout {
    id: root
    property var node: null
    property var s: node ? node.scan : ({})
    spacing: Theme.sp2

    function imgUrl(name) {
        return (node && node.host && node.imgRev > 0)
            ? "image://remote/" + node.host + "/" + name + "?" + node.imgRev : ""
    }
    // grad-fördelning från historiken (sessions-donut)
    function dist() {
        var d = { A: 0, B: 0, C: 0, D: 0 }, h = root.s.history || []
        for (var i = 0; i < h.length; i++) { var c = h[i].cls; if (d[c] !== undefined) d[c]++ }
        return d
    }
    function yieldPct() {
        var d = dist(), t = d.A + d.B + d.C + d.D
        return t > 0 ? Math.round((d.A + d.B) / t * 100) : 0
    }

    // ---- driftrad ----
    Card {
        Layout.fillWidth: true; Layout.preferredHeight: 78
        title: "DRIFT"; chip: root.s.mode || "?"; chipColor: Theme.violet
        RowLayout {
            anchors.fill: parent; spacing: Theme.sp2
            Btn { text: root.s.running ? "Pausa" : "Starta"; primary: !root.s.running; danger: root.s.running === true
                  onClicked: if (root.node) root.node.scanToggleRun() }
            Btn { text: root.s.pass_mode === "single" ? "Ladda ny" : "Nästa bräda"
                  visible: root.s.run_mode === "pass"
                  onClicked: if (root.node) root.node.scanNextBoard() }
            Rectangle { width: 1; Layout.preferredHeight: 24; color: Theme.line }
            Repeater { model: [["pass","Pass"],["flow","Flöde"]]
                delegate: Rectangle { radius: Theme.rSm; implicitWidth: rmt.width+18; implicitHeight: 28
                    color: root.s.run_mode === modelData[0] ? Theme.accent : Theme.panel
                    border.color: root.s.run_mode === modelData[0] ? "transparent" : Theme.line
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: if (root.node) root.node.scanSetRunMode(modelData[0]) }
                    Text { id: rmt; anchors.centerIn: parent; text: modelData[1]; font.family: Theme.sans
                           color: root.s.run_mode === modelData[0] ? Theme.accentInk : Theme.ink2
                           font.pixelSize: 11; font.weight: Font.DemiBold } } }
            Repeater { model: root.s.run_mode === "pass" ? [["single","Enkel"],["multi","Multi"]] : []
                delegate: Rectangle { radius: Theme.rSm; implicitWidth: pmt.width+18; implicitHeight: 28
                    color: root.s.pass_mode === modelData[0] ? Theme.cyan : Theme.panel
                    border.color: root.s.pass_mode === modelData[0] ? "transparent" : Theme.line
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: if (root.node) root.node.scanSetPassMode(modelData[0]) }
                    Text { id: pmt; anchors.centerIn: parent; text: modelData[1]; font.family: Theme.sans
                           color: root.s.pass_mode === modelData[0] ? Theme.accentInk : Theme.ink2
                           font.pixelSize: 11; font.weight: Font.DemiBold } } }
            Item { Layout.fillWidth: true }
            ColumnLayout { spacing: 3
                Text { text: root.s.status || "—"; color: root.s.running ? Theme.ok : Theme.warn
                       font.family: Theme.sans; font.pixelSize: 13; font.weight: Font.DemiBold; Layout.alignment: Qt.AlignRight }
                Rectangle { width: 180; height: 6; radius: 3; color: Theme.panel2
                    Rectangle { width: parent.width * Math.max(0,Math.min(1,(root.s.progress||0))); height: parent.height
                        radius: 3; color: Theme.accent; Behavior on width { NumberAnimation { duration: 120 } } } } }
        }
    }

    // ---- notis ----
    Rectangle {
        Layout.fillWidth: true; radius: Theme.rSm; visible: (root.s.notify||"") !== ""
        Layout.preferredHeight: 32; color: Theme.tint(Theme.info, 0.10); border.color: Theme.tint(Theme.info, 0.35)
        RowLayout { anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 8
            Text { text: "ⓘ  " + (root.s.notify || ""); color: Qt.darker(Theme.info,1.1); font.family: Theme.sans
                   font.pixelSize: 11; Layout.fillWidth: true }
            Btn { text: "OK"; onClicked: if (root.node) root.node.scanDismissNotify() } }
    }

    // ---- KPI-remsa ----
    RowLayout {
        Layout.fillWidth: true; Layout.preferredHeight: 60; spacing: Theme.sp2
        Repeater {
            model: [
                {l:"Genomflöde", v:(root.s.throughput!==undefined?root.s.throughput.toFixed(1):"–"), u:"br/min", c:Theme.accent},
                {l:"Brädor", v:(root.s.boards!==undefined?root.s.boards:"–"), u:"", c:Theme.ink},
                {l:"Utbyte A+B", v:root.yieldPct(), u:"%", c:Theme.ok},
                {l:"Profiltakt", v:(root.s.rate!==undefined?Math.round(root.s.rate):"–"), u:"Hz", c:Theme.teal},
                {l:"Nod-last", v:(root.s.load!==undefined?Math.round(root.s.load):"–"), u:"%", c:Theme.violet}
            ]
            delegate: Kpi {
                Layout.fillWidth: true; Layout.fillHeight: true
                label: modelData.l; value: modelData.v; unit: modelData.u; accent: modelData.c
            }
        }
    }

    // ---- HUVUDOMRÅDE ----
    RowLayout {
        Layout.fillWidth: true; Layout.fillHeight: true; spacing: Theme.sp3

        // vänster: profilkameror (laserstripe)
        Card {
            Layout.preferredWidth: 230; Layout.minimumWidth: 200; Layout.maximumWidth: 260
            Layout.fillHeight: true
            title: "PROFILKAMEROR"; chip: "LIVE"; chipColor: Theme.cyan
            ColumnLayout {
                anchors.fill: parent; spacing: Theme.sp2
                Repeater {
                    model: [["cam_red","Profil RÖD · 650 nm"], ["cam_green","Profil GRÖN · 520 nm"]]
                    delegate: ColumnLayout {
                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 2
                        Text { text: modelData[1]; color: Theme.ink3; font.family: Theme.sans; font.pixelSize: 9; font.weight: Font.DemiBold }
                        Rectangle {
                            Layout.fillWidth: true; Layout.fillHeight: true; radius: Theme.rSm
                            color: "#0b1220"; border.color: Theme.line; clip: true
                            Image {
                                anchors.fill: parent; anchors.margins: 3; cache: false; smooth: true
                                fillMode: Image.PreserveAspectFit; source: root.imgUrl(modelData[0])
                            }
                            Text { anchors.centerIn: parent; visible: !(root.node && root.node.imgRev > 0)
                                   text: "ingen signal"; color: Theme.ink3; font.family: Theme.sans; font.pixelSize: 10 }
                        }
                    }
                }
            }
        }

        // mitten: yta+defekter (strip) över 3D (hero)
        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumWidth: 320; spacing: Theme.sp3
            Card {
                Layout.fillWidth: true; Layout.preferredHeight: 150
                title: "YTA · linjekamera + defekter"
                chip: (root.s.defects ? root.s.defects.length : 0) + " defekter"; chipColor: Theme.warn
                BoardOverlay {
                    anchors.fill: parent
                    imgSource: root.imgUrl("surface"); defects: root.s.defects || []
                }
            }
            Card {
                Layout.fillWidth: true; Layout.fillHeight: true
                title: "3D-REKONSTRUKTION"
                chip: (typeof quick3dAvailable !== 'undefined' && quick3dAvailable) ? "GPU 3D" : "SOFT 3D"
                chipColor: Theme.teal
                Loader {
                    id: viewer3d
                    anchors.fill: parent
                    source: (typeof quick3dAvailable !== 'undefined' && quick3dAvailable)
                            ? "Board3DGpu.qml" : "Board3DSoft.qml"
                    onLoaded: {
                        item.mesh = Qt.binding(function(){ return root.node ? root.node.mesh3d : null })
                        if (item.hasOwnProperty("texSource"))
                            item.texSource = Qt.binding(function(){ return root.imgUrl("surface") })
                    }
                }
            }
        }

        // höger: bedömning + defekter + historik
        ColumnLayout {
            Layout.preferredWidth: 290; Layout.minimumWidth: 260; Layout.maximumWidth: 320
            Layout.fillHeight: true; spacing: Theme.sp3

            Card {
                Layout.fillWidth: true; Layout.preferredHeight: 220
                title: "BEDÖMNING"; chip: "AKTUELL"; chipColor: Theme.amber
                RowLayout {
                    anchors.fill: parent; spacing: Theme.sp3
                    // aktuell grad
                    ColumnLayout {
                        Layout.alignment: Qt.AlignVCenter; spacing: 6
                        Rectangle {
                            Layout.alignment: Qt.AlignHCenter; width: 78; height: 78; radius: Theme.rMd
                            color: Theme.tint(root.s.grade_color || Theme.ink3, 0.14)
                            border.width: 2; border.color: root.s.grade_color || Theme.line
                            Text { anchors.centerIn: parent; text: root.s.grade_class || "–"
                                   color: root.s.grade_color || Theme.ink3; font.family: Theme.sans
                                   font.pixelSize: 38; font.weight: Font.Black } }
                        Text { text: root.s.grade_title || "Inväntar"; color: Theme.ink; font.family: Theme.sans
                               font.pixelSize: 12; font.weight: Font.DemiBold; Layout.preferredWidth: 110
                               horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap }
                    }
                    // sessions-fördelning
                    ColumnLayout {
                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 4
                        GradeDonut {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            dist: root.dist(); centerValue: root.yieldPct() + "%"; centerLabel: "UTBYTE"
                        }
                        RowLayout {
                            Layout.alignment: Qt.AlignHCenter; spacing: 8
                            Repeater { model: ["A","B","C","D"]
                                delegate: RowLayout { spacing: 3
                                    Rectangle { width: 8; height: 8; radius: 2; color: Theme.gradeColor(modelData) }
                                    Text { text: root.dist()[modelData]; color: Theme.ink2
                                           font.family: Theme.sans; font.pixelSize: 10; font.weight: Font.DemiBold } } }
                        }
                    }
                }
            }

            Card {
                Layout.fillWidth: true; Layout.fillHeight: true
                title: "DEFEKTER"; chip: (root.s.defects ? root.s.defects.length : 0) + " st"; chipColor: Theme.err
                Flickable { anchors.fill: parent; contentHeight: dcol.height; clip: true
                    ColumnLayout { id: dcol; width: parent.width; spacing: 4
                        Repeater { model: root.s.defects || []
                            delegate: Rectangle { Layout.fillWidth: true; implicitHeight: 26; radius: Theme.rSm
                                color: Theme.panel2; border.color: Theme.line
                                RowLayout { anchors.fill: parent; anchors.leftMargin: 8; anchors.rightMargin: 8; spacing: 8
                                    Rectangle { width: 8; height: 8; radius: 4; color: modelData.color || Theme.ink3 }
                                    Text { text: modelData.name; color: Theme.ink; font.family: Theme.sans; font.pixelSize: 11; Layout.fillWidth: true }
                                    Text { text: "x"+modelData.x+" ⌀"+modelData.dia; color: Theme.ink3; font.family: Theme.mono; font.pixelSize: 9 } } } }
                        Text { visible: !(root.s.defects && root.s.defects.length); text: "Inga defekter"; color: Theme.ink3; font.family: Theme.sans; font.pixelSize: 11 } }
                }
            }

            Card {
                Layout.fillWidth: true; Layout.fillHeight: true
                title: "HISTORIK"; chip: (root.s.history ? root.s.history.length : 0); chipColor: Theme.teal
                ListView {
                    anchors.fill: parent; clip: true; spacing: 3
                    model: root.s.history || []
                    delegate: Rectangle { width: ListView.view.width; height: 30; radius: Theme.rSm
                        color: Theme.panel2; border.color: Theme.line
                        RowLayout { anchors.fill: parent; anchors.leftMargin: 8; anchors.rightMargin: 8; spacing: 8
                            Text { text: "#" + (modelData.n!==undefined?modelData.n:""); color: Theme.ink3; font.family: Theme.mono; font.pixelSize: 10 }
                            Rectangle { width: 22; height: 22; radius: 6; color: Theme.tint(modelData.color || Theme.ink, 0.16)
                                Text { anchors.centerIn: parent; text: modelData.cls || "?"; color: modelData.color || Theme.ink
                                       font.family: Theme.sans; font.pixelSize: 13; font.weight: Font.Bold } }
                            Text { text: modelData.title || ""; color: Theme.ink2; font.family: Theme.sans; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight } } }
                }
            }
        }
    }
}
