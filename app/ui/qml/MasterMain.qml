import QtQuick
import QtQuick.Window
import QtQuick.Controls.Basic
import QtQuick.Layouts

// MASTER-skal (kommersiellt, ljust). Två nivåer:
//   ÖVERSIKT  — flott-KPI:er + grad-donut + "video wall" med ett kort per läshuvud.
//   DETALJ    — vald nod: enheter, laser-arm, position, Skanning/Kalibrering.
ApplicationWindow {
    id: win
    width: 1560; height: 940; visible: true
    minimumWidth: 1280; minimumHeight: 800     // under detta börjar täta vyer trängas
    visibility: startFullscreen ? Window.FullScreen : Window.Windowed
    title: "woody · Inspection Control"
    color: Theme.bg

    property int selIndex: -1
    property var sel: null
    property int view: 0             // 0 = Översikt, 1 = Detalj
    property int nodeTab: 0          // 0 = Skanning (live), 1 = Sensorer & kalibrering
    function pick(i) { selIndex = i; sel = nodeManager.node(i); view = 1 }

    // ---- live klocka ----
    property string clock: "--:--"
    Timer { interval: 1000; running: true; repeat: true; triggeredOnStart: true
        onTriggered: win.clock = Qt.formatTime(new Date(), "HH:mm") }

    // ---- flott-aggregat (uppdateras 1 Hz) ----
    property real fleetThroughput: 0
    property int  fleetOnline: 0
    property int  fleetBoards: 0
    property int  fleetAlarms: 0
    property var  fleetDist: ({})
    property real fleetYield: 0
    property var  fleetTrend: []          // rullande genomflöde (≤60 sampel)
    Timer { interval: 1000; running: true; repeat: true; triggeredOnStart: true
        onTriggered: win.recompute() }
    function recompute() {
        var thr = 0, online = 0, boards = 0, alarms = 0
        var dist = { A: 0, B: 0, C: 0, D: 0 }
        for (var i = 0; i < nodeManager.count; i++) {
            var nd = nodeManager.node(i); if (!nd) continue
            if (nd.connected) online++; else alarms++
            var s = nd.scan || {}
            if (s.throughput !== undefined) thr += s.throughput
            if (s.boards !== undefined) boards += s.boards
            var h = s.history || []
            for (var j = 0; j < h.length; j++) { var c = h[j].cls; if (dist[c] !== undefined) dist[c]++ }
        }
        var tot = dist.A + dist.B + dist.C + dist.D
        win.fleetThroughput = thr; win.fleetOnline = online; win.fleetBoards = boards
        win.fleetAlarms = alarms; win.fleetDist = dist
        win.fleetYield = tot > 0 ? Math.round((dist.A + dist.B) / tot * 100) : 0
        var tr = win.fleetTrend.slice(); tr.push(thr)
        while (tr.length > 60) tr.shift()
        win.fleetTrend = tr
    }

    background: Rectangle {
        gradient: Gradient { GradientStop { position: 0.0; color: Theme.bg2 }
                             GradientStop { position: 1.0; color: Theme.bg } }
    }

    ColumnLayout {
        anchors.fill: parent; spacing: 0

        // ============================ BRAND-HEADER ============================
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 60
            color: Theme.panel; border.color: Theme.line
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: Theme.sp4; anchors.rightMargin: Theme.sp4
                spacing: Theme.sp3
                // logo-märke
                Rectangle {
                    width: 34; height: 34; radius: 9
                    gradient: Gradient { GradientStop { position: 0; color: Theme.accent }
                                         GradientStop { position: 1; color: Theme.violet } }
                    Text { anchors.centerIn: parent; text: "W"; color: "white"
                           font.family: Theme.sans; font.pixelSize: 19; font.weight: Font.Black }
                }
                ColumnLayout { spacing: -2
                    Text { text: "woody"; color: Theme.ink; font.family: Theme.sans
                           font.pixelSize: 17; font.weight: Font.Bold }
                    Text { text: "INSPECTION CONTROL"; color: Theme.ink3; font.family: Theme.sans
                           font.pixelSize: 9; font.weight: Font.DemiBold; font.letterSpacing: 1.4 }
                }
                Rectangle { width: 1; height: 28; color: Theme.line }
                // online-status
                RowLayout { spacing: 6
                    Rectangle { width: 9; height: 9; radius: 5
                        color: win.fleetOnline > 0 ? Theme.ok : Theme.err }
                    Text { text: win.fleetOnline + "/" + nodeManager.count + " online"
                           color: Theme.ink2; font.family: Theme.sans; font.pixelSize: 12; font.weight: Font.DemiBold }
                }
                Item { Layout.fillWidth: true }
                // larm-badge
                Rectangle {
                    visible: win.fleetAlarms > 0
                    radius: 999; implicitWidth: alm.width + 18; implicitHeight: 24
                    color: Theme.tint(Theme.err, 0.14); border.color: Theme.tint(Theme.err, 0.3)
                    RowLayout { id: alm; anchors.centerIn: parent; spacing: 5
                        Text { text: "⚠"; color: Theme.err; font.pixelSize: 12 }
                        Text { text: win.fleetAlarms + " larm"; color: Qt.darker(Theme.err, 1.1)
                               font.family: Theme.sans; font.pixelSize: 11; font.weight: Font.DemiBold } }
                }
                Text { text: win.clock; color: Theme.ink; font.family: Theme.sans
                       font.pixelSize: 14; font.weight: Font.DemiBold }
                // roll
                Rectangle {
                    radius: 999; implicitWidth: rl.width + 22; implicitHeight: 30
                    color: Theme.panel2; border.color: Theme.line
                    RowLayout { id: rl; anchors.centerIn: parent; spacing: 7
                        Rectangle { width: 20; height: 20; radius: 10; color: Theme.tint(Theme.accent, 0.18)
                            Text { anchors.centerIn: parent; text: "O"; color: Theme.accent
                                   font.family: Theme.sans; font.pixelSize: 10; font.weight: Font.Bold } }
                        Text { text: "Operatör"; color: Theme.ink2; font.family: Theme.sans
                               font.pixelSize: 12; font.weight: Font.DemiBold }
                        Text { text: "▾"; color: Theme.ink3; font.pixelSize: 10 } }
                }
            }
        }

        // ============================ SEGMENT-FLIKAR ============================
        RowLayout {
            Layout.fillWidth: true; Layout.leftMargin: Theme.sp4; Layout.rightMargin: Theme.sp4
            Layout.topMargin: Theme.sp3; spacing: Theme.sp2
            Repeater {
                model: [["Översikt", 0, true], ["Nod-detalj", 1, win.sel !== null],
                        ["Simulering · multihuvud", 2, true]]
                delegate: Rectangle {
                    radius: Theme.rSm; implicitWidth: sgt.width + 30; implicitHeight: 34
                    enabled: modelData[2]
                    opacity: modelData[2] ? 1 : 0.4
                    color: win.view === modelData[1] ? Theme.accent : Theme.panel
                    border.color: win.view === modelData[1] ? "transparent" : Theme.line
                    MouseArea { anchors.fill: parent; enabled: modelData[2]
                        cursorShape: Qt.PointingHandCursor; onClicked: win.view = modelData[1] }
                    Text { id: sgt; anchors.centerIn: parent; text: modelData[0]
                           color: win.view === modelData[1] ? Theme.accentInk : Theme.ink2
                           font.family: Theme.sans; font.pixelSize: 13; font.weight: Font.DemiBold }
                }
            }
            Item { Layout.fillWidth: true }
            Text { text: "Noder · data/nodes.json"; color: Theme.ink3
                   font.family: Theme.sans; font.pixelSize: 10 }
        }

        // ============================ INNEHÅLL ============================
        Loader {
            Layout.fillWidth: true; Layout.fillHeight: true
            Layout.margins: Theme.sp4; Layout.topMargin: Theme.sp3
            sourceComponent: win.view === 0 ? overviewComp
                           : win.view === 1 ? detailComp : simComp
        }
    }

    Component { id: simComp; SimMultiHeadView {} }

    // ---------------------------------------------------------------- ÖVERSIKT
    Component {
        id: overviewComp
        ColumnLayout {
            spacing: Theme.sp3

            // flott-KPI:er + grad-donut
            RowLayout {
                Layout.fillWidth: true; Layout.preferredHeight: 168; spacing: Theme.sp3

                Card {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    title: "FLOTTA · NU"; chip: "LIVE"; chipColor: Theme.ok
                    ColumnLayout {
                        anchors.fill: parent; spacing: Theme.sp2
                        RowLayout {
                            Layout.fillWidth: true; Layout.fillHeight: true; spacing: Theme.sp4
                            Repeater {
                                model: [
                                    {l: "Genomflöde", v: win.fleetThroughput.toFixed(1), u: "br/min", c: Theme.accent},
                                    {l: "Läshuvuden", v: win.fleetOnline + "/" + nodeManager.count, u: "", c: Theme.ink},
                                    {l: "Brädor idag", v: win.fleetBoards, u: "", c: Theme.teal},
                                    {l: "Utbyte A+B", v: win.fleetYield, u: "%", c: Theme.ok}
                                ]
                                delegate: ColumnLayout {
                                    Layout.fillWidth: true; Layout.alignment: Qt.AlignTop; spacing: 3
                                    Text { text: modelData.l.toUpperCase(); color: Theme.ink3
                                           font.family: Theme.sans; font.pixelSize: 10; font.weight: Font.DemiBold
                                           font.letterSpacing: 0.7 }
                                    RowLayout { spacing: 4
                                        Text { text: modelData.v; color: modelData.c; font.family: Theme.sans
                                               font.pixelSize: 34; font.weight: Font.Bold; font.features: { "tnum": 1 } }
                                        Text { text: modelData.u; visible: modelData.u !== ""; color: Theme.ink3
                                               font.pixelSize: 13; Layout.alignment: Qt.AlignBottom; bottomPadding: 6 } }
                                }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true; Layout.preferredHeight: 30; spacing: Theme.sp2
                            Text { text: "GENOMFLÖDE · TREND"; color: Theme.ink3; font.family: Theme.sans
                                   font.pixelSize: 9; font.weight: Font.DemiBold; font.letterSpacing: 0.7 }
                            Sparkline { Layout.fillWidth: true; Layout.preferredHeight: 28
                                        values: win.fleetTrend; stroke: Theme.accent }
                        }
                    }
                }

                Card {
                    Layout.preferredWidth: 280; Layout.fillHeight: true
                    title: "GRADFÖRDELNING · skift"; chip: "A/B/C/D"; chipColor: Theme.violet
                    RowLayout {
                        anchors.fill: parent; spacing: Theme.sp3
                        GradeDonut {
                            Layout.preferredWidth: 118; Layout.fillHeight: true
                            dist: win.fleetDist; centerValue: win.fleetYield + "%"; centerLabel: "UTBYTE"
                        }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 5
                            Repeater {
                                model: ["A", "B", "C", "D"]
                                delegate: RowLayout {
                                    Layout.fillWidth: true; spacing: 7
                                    Rectangle { width: 11; height: 11; radius: 3; color: Theme.gradeColor(modelData) }
                                    Text { text: "Klass " + modelData; color: Theme.ink2
                                           font.family: Theme.sans; font.pixelSize: 12; Layout.fillWidth: true }
                                    Text { text: (win.fleetDist[modelData] || 0); color: Theme.ink
                                           font.family: Theme.sans; font.pixelSize: 13; font.weight: Font.Bold }
                                }
                            }
                        }
                    }
                }
            }

            // video wall
            Card {
                Layout.fillWidth: true; Layout.fillHeight: true
                title: "LÄSHUVUDEN"; chip: nodeManager.count + " noder"; chipColor: Theme.accent
                Flickable {
                    anchors.fill: parent; contentHeight: wall.height; clip: true
                    GridLayout {
                        id: wall; width: parent.width; columns: Math.max(1, Math.floor(width / 330))
                        rowSpacing: Theme.sp3; columnSpacing: Theme.sp3
                        Repeater {
                            model: nodeManager.count
                            delegate: NodeTile {
                                Layout.fillWidth: true; Layout.preferredHeight: 150
                                node: nodeManager.node(index)
                                summary: nodeManager.nodeSummaries[index] || ({})
                                onActivated: win.pick(index)
                            }
                        }
                        // tom-tillstånd
                        Text {
                            visible: nodeManager.count === 0
                            text: "Inga noder i data/nodes.json — lägg till dina Jetson-läshuvuden"
                            color: Theme.ink3; font.family: Theme.sans; font.pixelSize: 13
                        }
                    }
                }
            }
        }
    }

    // ---------------------------------------------------------------- DETALJ
    Component {
        id: detailComp
        RowLayout {
            spacing: Theme.sp3

            // vänster: nodlista
            Card {
                Layout.preferredWidth: 320; Layout.fillHeight: true
                title: "LÄSHUVUDEN"; chip: win.fleetOnline + "/" + nodeManager.count; chipColor: Theme.accent
                ListView {
                    anchors.fill: parent; clip: true; spacing: 6
                    model: nodeManager.nodeSummaries
                    delegate: Rectangle {
                        width: ListView.view.width; height: 64; radius: Theme.rMd
                        color: index === win.selIndex ? Theme.tint(Theme.accent, 0.10) : Theme.panel2
                        border.color: index === win.selIndex ? Theme.tint(Theme.accent, 0.5) : Theme.line
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: win.pick(index) }
                        RowLayout {
                            anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10; spacing: 9
                            Rectangle { width: 10; height: 10; radius: 5
                                color: modelData.connected ? Theme.ok : Theme.err
                                SequentialAnimation on opacity { running: !modelData.connected
                                    loops: Animation.Infinite; NumberAnimation { to: 0.3; duration: 700 }
                                    NumberAnimation { to: 1; duration: 700 } } }
                            ColumnLayout { spacing: 1; Layout.fillWidth: true
                                Text { text: modelData.name; color: Theme.ink; font.family: Theme.sans
                                       font.pixelSize: 13; font.weight: Font.DemiBold; elide: Text.ElideRight; Layout.fillWidth: true }
                                Text { text: (modelData.connected ? "ansluten · " + (modelData.mode||"?") : "ej ansluten")
                                             + " · " + modelData.host
                                       color: modelData.connected ? Theme.ink3 : Theme.err
                                       font.family: Theme.mono; font.pixelSize: 9; elide: Text.ElideRight; Layout.fillWidth: true } }
                            Rectangle {
                                visible: modelData.has_conveyor === true
                                radius: 999; implicitWidth: ld.width+12; implicitHeight: 17
                                color: Theme.tint(Theme.violet, 0.14); border.color: Theme.tint(Theme.violet, 0.35)
                                Text { id: ld; anchors.centerIn: parent; text: "LEAD"
                                       color: Qt.darker(Theme.violet,1.1); font.family: Theme.sans; font.pixelSize: 9; font.weight: Font.Bold } }
                        }
                    }
                }
            }

            // höger: vald nod
            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true; spacing: Theme.sp3
                visible: win.sel !== null

                // enhetsremsa + laser-arm
                Card {
                    Layout.fillWidth: true; Layout.preferredHeight: 92
                    title: win.sel ? ("NOD · " + win.sel.nodeName.toUpperCase()) : "NOD"
                    chip: win.sel && win.sel.connected ? "ANSLUTEN" : "EJ ANSLUTEN"
                    chipColor: win.sel && win.sel.connected ? Theme.ok : Theme.err
                    RowLayout {
                        anchors.fill: parent; spacing: Theme.sp2
                        // enheter: EN rad, konstant höjd, scrollar horisontellt
                        // (wrappar ALDRIG → kan inte växa och måla över korten under)
                        Flickable {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            contentWidth: pillRow.width; contentHeight: height
                            clip: true; flickableDirection: Flickable.HorizontalFlick
                            Row {
                                id: pillRow; height: parent.height; spacing: 6
                                Repeater { model: win.sel ? win.sel.devices : []
                                    delegate: Rectangle { radius: 999; implicitWidth: dn.width+16; height: 22
                                        anchors.verticalCenter: parent.verticalCenter
                                        color: modelData.connected ? Theme.tint(Theme.ok, 0.12) : Theme.panel2
                                        border.color: modelData.connected ? Theme.tint(Theme.ok, 0.3) : Theme.line
                                        Text { id: dn; anchors.centerIn: parent; text: modelData.name
                                               color: modelData.connected ? Qt.darker(Theme.ok,1.1) : Theme.ink3
                                               font.family: Theme.sans; font.pixelSize: 10 } } }
                            }
                        }
                        Btn { text: "Proba om"; onClicked: if (win.sel) win.sel.refresh() }
                        Btn { text: "Arma lasrar"; danger: true
                              onClicked: if (win.sel) win.sel.armLasers(true) }
                        Btn { text: "Avarma"; onClicked: if (win.sel) win.sel.disarmLasers() }
                    }
                }

                // position
                Card {
                    id: posCard
                    Layout.fillWidth: true; Layout.preferredHeight: 80
                    title: "POSITION · brädsektion huvudet täcker"; chip: "SEKTION"; chipColor: Theme.cyan
                    property var node: win.sel
                    onNodeChanged: if (node) {
                        lblF.text = node.posLabel
                        startF.text = node.posStart.toFixed(0)
                        endF.text = node.posEnd.toFixed(0) }
                    component PField: TextField {
                        color: Theme.ink; font.family: Theme.mono; font.pixelSize: 12
                        background: Rectangle { color: Theme.panel2; radius: Theme.rSm; border.color: Theme.line } }
                    RowLayout {
                        anchors.fill: parent; spacing: Theme.sp2
                        Text { text: "Etikett"; color: Theme.ink3; font.pixelSize: 11 }
                        PField { id: lblF; Layout.preferredWidth: 150; placeholderText: "t.ex. Vänster" }
                        Text { text: "Start"; color: Theme.ink3; font.pixelSize: 11 }
                        PField { id: startF; Layout.preferredWidth: 70; placeholderText: "mm" }
                        Text { text: "Slut"; color: Theme.ink3; font.pixelSize: 11 }
                        PField { id: endF; Layout.preferredWidth: 70; placeholderText: "mm" }
                        Text { text: "mm längs brädan"; color: Theme.ink3; font.pixelSize: 10; font.family: Theme.mono }
                        Item { Layout.fillWidth: true }
                        Btn { text: "Spara position"; primary: true
                              onClicked: if (win.sel) win.sel.setPosition(
                                  lblF.text, parseFloat(startF.text) || 0, parseFloat(endF.text) || 0) }
                    }
                }

                // flikar: Skanning | Sensorer & kalibrering
                RowLayout {
                    Layout.fillWidth: true; spacing: Theme.sp2
                    Repeater {
                        model: ["Skanning (live)", "Sensorer & kalibrering"]
                        delegate: Rectangle {
                            radius: Theme.rSm; implicitWidth: tt.width + 28; implicitHeight: 32
                            color: win.nodeTab === index ? Theme.tint(Theme.cyan, 0.14) : Theme.panel
                            border.color: win.nodeTab === index ? Theme.tint(Theme.cyan, 0.45) : Theme.line
                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: win.nodeTab = index }
                            Text { id: tt; anchors.centerIn: parent; text: modelData
                                   color: win.nodeTab === index ? Qt.darker(Theme.cyan,1.1) : Theme.ink2
                                   font.family: Theme.sans; font.pixelSize: 12; font.weight: Font.DemiBold } }
                    }
                    Item { Layout.fillWidth: true }
                }

                Loader {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    active: win.sel !== null
                    sourceComponent: win.nodeTab === 0 ? scanComp : calibComp
                }
                Component { id: scanComp;  ScanView { node: win.sel } }
                Component { id: calibComp; CalibrationView { dm: win.sel } }
            }
        }
    }
}
