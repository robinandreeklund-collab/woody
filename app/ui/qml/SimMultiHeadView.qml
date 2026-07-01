import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

// Live-demo: N läshuvuden över en lång bräda + fusion. Driver app.ui.multihead_sim
// (kontext-egenskap `simHead`). Visar synk (en encoder → alla huvuden samma rad)
// och hur överlappen kalibrerar bort per-huvud-bias → sömlös fuserad bräda.
ColumnLayout {
    id: root
    spacing: Theme.sp3

    function headColor(i) {
        var pal = ["#2563eb","#d97706","#16a34a","#e11d48","#7c3aed","#0891b2",
                   "#db2777","#65a30d","#0d9488","#9333ea","#ea580c","#0ea5e9"]
        return pal[i % pal.length]
    }
    property var m: simHead.metrics

    // ---- kontrollrad ----
    Card {
        Layout.fillWidth: true; Layout.preferredHeight: 80
        title: "MULTIHUVUDS-SIMULERING"
        chip: simHead.nHeads + " huvuden · " + simHead.totalLen.toFixed(0) + " mm"
        chipColor: Theme.violet
        RowLayout {
            anchors.fill: parent; spacing: Theme.sp2
            Btn { text: simHead.running ? "Pausa" : (simHead.feed >= 1 ? "Spela igen" : "Starta svep")
                  primary: !simHead.running; onClicked: simHead.toggleRun() }
            Btn { text: "Ny bräda"; onClicked: simHead.newBoard() }
            Rectangle { width: 1; Layout.preferredHeight: 24; color: Theme.line }
            Text { text: "Antal huvuden"; color: Theme.ink3; font.pixelSize: 11; font.family: Theme.sans }
            Repeater {
                model: [4, 6, 8, 10]
                delegate: Rectangle {
                    radius: Theme.rSm; implicitWidth: ht.width + 18; implicitHeight: 28
                    color: simHead.nHeads === modelData ? Theme.accent : Theme.panel
                    border.color: simHead.nHeads === modelData ? "transparent" : Theme.line
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: simHead.setHeads(modelData) }
                    Text { id: ht; anchors.centerIn: parent; text: modelData; font.family: Theme.sans
                           color: simHead.nHeads === modelData ? Theme.accentInk : Theme.ink2
                           font.pixelSize: 12; font.weight: Font.DemiBold } }
            }
            Item { Layout.fillWidth: true }
            // synk-indikator
            RowLayout { spacing: 8
                Rectangle { width: 10; height: 10; radius: 5
                    color: simHead.busy ? Theme.warn : (simHead.running ? Theme.ok : Theme.ink3)
                    SequentialAnimation on opacity { running: simHead.running
                        loops: Animation.Infinite; NumberAnimation { to: 0.3; duration: 500 }
                        NumberAnimation { to: 1; duration: 500 } } }
                Text { text: simHead.busy ? "beräknar …"
                             : ("1 encoder · " + simHead.nHeads + " huvuden · rad "
                                + Math.round(simHead.feed * 100) + "%")
                       color: Theme.ink2; font.family: Theme.sans; font.pixelSize: 12; font.weight: Font.DemiBold }
            }
        }
    }

    // ---- huvudområde ----
    RowLayout {
        Layout.fillWidth: true; Layout.fillHeight: true; spacing: Theme.sp3

        // vänster: bräda + fusion + profil
        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: Theme.sp3

            // brädans toppvy + huvudband + svep
            Card {
                Layout.fillWidth: true; Layout.preferredHeight: 168
                title: "BRÄDA · varje huvud mäter sin sektion (delad encoder)"
                chip: "SVEP " + Math.round(simHead.feed * 100) + "%"; chipColor: Theme.cyan
                Item {
                    anchors.fill: parent
                    // huvud-etiketter
                    Item {
                        id: bandLabels; anchors.left: parent.left; anchors.right: parent.right
                        anchors.top: parent.top; height: 16
                        Repeater { model: simHead.heads
                            delegate: Text {
                                x: parent.width * (modelData.start_mm + modelData.end_mm) / 2 / simHead.totalLen - width/2
                                text: modelData.label; color: root.headColor(modelData.idx)
                                font.family: Theme.sans; font.pixelSize: 10; font.weight: Font.Bold } }
                    }
                    Rectangle {
                        id: strip
                        anchors.left: parent.left; anchors.right: parent.right
                        anchors.top: bandLabels.bottom; anchors.bottom: parent.bottom; anchors.topMargin: 2
                        radius: Theme.rSm; color: "#0b1220"; border.color: Theme.line; clip: true
                        Image {
                            id: boardImg; anchors.fill: parent; anchors.margins: 1
                            fillMode: Image.Stretch; cache: false; smooth: true
                            source: "image://simhead/board?" + simHead.rev
                        }
                        // huvud-band (täckning) + skarvar
                        Repeater { model: simHead.heads
                            delegate: Rectangle {
                                x: boardImg.x + boardImg.width * modelData.start_mm / simHead.totalLen
                                width: boardImg.width * (modelData.end_mm - modelData.start_mm) / simHead.totalLen
                                y: boardImg.y; height: boardImg.height
                                color: Qt.rgba(0,0,0,0); border.width: 1
                                border.color: root.headColor(modelData.idx)
                                Rectangle { anchors.fill: parent; color: root.headColor(modelData.idx); opacity: 0.10 } }
                        }
                        // o-skannad "gardin" (nedanför sveplinjen) + sveplinje
                        Rectangle {
                            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                            height: parent.height * (1 - simHead.feed)
                            color: Qt.rgba(0.04,0.07,0.11,0.82)
                            Rectangle { anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
                                height: 2; color: Theme.cyan } }
                    }
                }
            }

            // fuserad höjdkarta (byggs upp i synk)
            Card {
                Layout.fillWidth: true; Layout.preferredHeight: 110
                title: "FUSERAD HÖJDKARTA · sömlös trots " + simHead.nHeads + " separata huvuden"
                chip: "FUSION"; chipColor: Theme.teal
                Rectangle {
                    anchors.fill: parent; radius: Theme.rSm; color: "#0b1220"; border.color: Theme.line; clip: true
                    Image { id: fusedImg; anchors.fill: parent; anchors.margins: 1
                        fillMode: Image.Stretch; cache: false; smooth: true
                        source: "image://simhead/fused?" + simHead.rev }
                    Rectangle {
                        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                        height: parent.height * (1 - simHead.feed); color: Qt.rgba(0.04,0.07,0.11,0.82)
                        Rectangle { anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
                            height: 2; color: Theme.cyan } }
                }
            }

            // tjockleksprofil: sann vs naiv vs fusion
            Card {
                Layout.fillWidth: true; Layout.fillHeight: true
                title: "TJOCKLEKSPROFIL · fusion eliminerar skarvstegen"; chip: "mm"; chipColor: Theme.amber
                Item {
                    anchors.fill: parent
                    Canvas {
                        id: chart; anchors.fill: parent; anchors.topMargin: 4; antialiasing: true
                        property var tp: simHead.trueProfile
                        property var np_: simHead.naiveProfile
                        property var fp: simHead.fusedProfile
                        onTpChanged: requestPaint(); onWidthChanged: requestPaint()
                        function bounds() {
                            var all = tp.concat(np_).concat(fp); if (!all.length) return [0,1]
                            var mn = Math.min.apply(null, all), mx = Math.max.apply(null, all)
                            var pad = (mx-mn)*0.15 || 0.5; return [mn-pad, mx+pad]
                        }
                        function line(ctx, a, b, col, lo, w, dash) {
                            if (!a.length) return
                            ctx.beginPath(); ctx.lineWidth = w; ctx.strokeStyle = col
                            if (dash) ctx.setLineDash([5,4]); else ctx.setLineDash([])
                            for (var i=0;i<a.length;i++){
                                var x = (i/(a.length-1))*width
                                var y = height - ((a[i]-lo)/(b-lo))*height
                                i ? ctx.lineTo(x,y) : ctx.moveTo(x,y)
                            }
                            ctx.stroke()
                        }
                        onPaint: {
                            var ctx = getContext("2d"); ctx.reset()
                            var bb = bounds()
                            line(ctx, np_, bb[1], "#e11d48", bb[0], 1.2, false)
                            line(ctx, tp, bb[1], "#16a34a", bb[0], 2.2, false)
                            line(ctx, fp, bb[1], "#0891b2", bb[0], 1.6, true)
                        }
                    }
                    Row {
                        anchors.bottom: parent.bottom; anchors.right: parent.right; spacing: 12
                        Repeater {
                            model: [["sann","#16a34a"],["naiv","#e11d48"],["fusion","#0891b2"]]
                            delegate: Row { spacing: 4
                                Rectangle { width: 10; height: 3; radius: 1; color: modelData[1]; anchors.verticalCenter: parent.verticalCenter }
                                Text { text: modelData[0]; color: Theme.ink2; font.family: Theme.sans; font.pixelSize: 9 } } }
                    }
                }
            }
        }

        // höger: mätvärden + per-huvud-kalibrering + skarvar
        ColumnLayout {
            Layout.preferredWidth: 320; Layout.minimumWidth: 280; Layout.maximumWidth: 360
            Layout.fillHeight: true; spacing: Theme.sp3

            Card {
                Layout.fillWidth: true; Layout.preferredHeight: 150
                title: "MÄTNOGGRANNHET"; chip: "RMS vs sann"; chipColor: Theme.ok
                ColumnLayout {
                    anchors.fill: parent; spacing: Theme.sp2
                    RowLayout {
                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: Theme.sp2
                        Repeater {
                            model: [
                                {l:"Naiv hopfogning", v:(root.m.rms_naive_mm!==undefined?(root.m.rms_naive_mm*1000).toFixed(0):"–"), c:Theme.err},
                                {l:"Fusion", v:(root.m.rms_aligned_mm!==undefined?(root.m.rms_aligned_mm*1000).toFixed(0):"–"), c:Theme.ok}
                            ]
                            delegate: Rectangle {
                                Layout.fillWidth: true; Layout.fillHeight: true; radius: Theme.rMd
                                color: Theme.panel2; border.color: Theme.line
                                ColumnLayout { anchors.centerIn: parent; spacing: 2
                                    Text { text: modelData.l.toUpperCase(); color: Theme.ink3; font.family: Theme.sans
                                           font.pixelSize: 9; font.weight: Font.DemiBold; Layout.alignment: Qt.AlignHCenter }
                                    RowLayout { Layout.alignment: Qt.AlignHCenter; spacing: 3
                                        Text { text: modelData.v; color: modelData.c; font.family: Theme.sans
                                               font.pixelSize: 26; font.weight: Font.Bold }
                                        Text { text: "µm"; color: Theme.ink3; font.pixelSize: 10
                                               Layout.alignment: Qt.AlignBottom; bottomPadding: 4 } } }
                            }
                        }
                    }
                    Text { text: "Skarv-samstämmighet: " + ((root.m.seam_rms_before_mm||0)*1000).toFixed(0)
                                 + " → " + ((root.m.seam_rms_after_mm||0)*1000).toFixed(0) + " µm efter fusion"
                           color: Theme.ink2; font.family: Theme.sans; font.pixelSize: 10; Layout.alignment: Qt.AlignHCenter }
                }
            }

            Card {
                Layout.fillWidth: true; Layout.fillHeight: true
                title: "PER-HUVUD KALIBRERING"; chip: "ur överlapp"; chipColor: Theme.cyan
                ListView {
                    anchors.fill: parent; clip: true; spacing: 4
                    model: simHead.heads
                    delegate: Rectangle {
                        width: ListView.view.width; height: 40; radius: Theme.rSm
                        color: Theme.panel2; border.color: Theme.line
                        RowLayout {
                            anchors.fill: parent; anchors.leftMargin: 8; anchors.rightMargin: 8; spacing: 8
                            Rectangle { width: 22; height: 22; radius: 6
                                color: Theme.tint(root.headColor(modelData.idx), 0.18)
                                Text { anchors.centerIn: parent; text: modelData.label; color: root.headColor(modelData.idx)
                                       font.family: Theme.sans; font.pixelSize: 10; font.weight: Font.Bold } }
                            ColumnLayout { spacing: 0; Layout.fillWidth: true
                                Text { text: "bias " + (modelData.bias_mm>=0?"+":"") + modelData.bias_mm.toFixed(2) + " mm"
                                       color: Theme.ink2; font.family: Theme.mono; font.pixelSize: 10 }
                                Text { text: "korr " + (modelData.corr_mm>=0?"+":"") + modelData.corr_mm.toFixed(2) + " mm"
                                       color: Theme.ink3; font.family: Theme.mono; font.pixelSize: 9 } }
                            Rectangle { radius: 999; implicitWidth: sy.width+14; implicitHeight: 18
                                color: Theme.tint(Theme.ok, 0.14); border.color: Theme.tint(Theme.ok, 0.3)
                                Text { id: sy; anchors.centerIn: parent; text: "✓ synkad"; color: Qt.darker(Theme.ok,1.1)
                                       font.family: Theme.sans; font.pixelSize: 9; font.weight: Font.DemiBold } }
                        }
                    }
                }
            }
        }
    }
}
