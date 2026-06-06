import QtQuick
import QtQuick.Window
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Shapes

ApplicationWindow {
    id: win
    width: 1500; height: 900
    visible: true
    visibility: startFullscreen ? Window.FullScreen : Window.Windowed
    title: "VIRKE · Kontrollsystem"
    color: pal.bg

    // ----------------------------------------------------------- designsystem
    QtObject {
        id: pal
        readonly property color bg:     "#0b0f14"
        readonly property color panel:  "#111923"
        readonly property color panel2: "#0d141d"
        readonly property color line:   "#1d2a38"
        readonly property color line2:  "#27384a"
        readonly property color ink:    "#e7eef6"
        readonly property color ink2:   "#9fb2c6"
        readonly property color ink3:   "#61768c"
        readonly property color cyan:   "#27d3e0"
        readonly property color teal:   "#34e6b5"
        readonly property color red:    "#ff4d5e"
        readonly property color grn:    "#52ff7a"
        readonly property color amber:  "#ffb33d"
        readonly property color violet: "#9a7bff"
    }
    readonly property string mono: "monospace"

    Component.onCompleted: ctrl.start()

    // mörk bakgrundsglöd
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0e1620" }
            GradientStop { position: 1.0; color: pal.bg }
        }
    }

    // ===================================================================== UI
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12

        // ---------------------------------------------------------- HEADER
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 64
            radius: 14; color: pal.panel; border.color: pal.line
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 18; anchors.rightMargin: 16
                spacing: 16
                // brand
                Rectangle {
                    width: 38; height: 38; radius: 11
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0; color: pal.cyan }
                        GradientStop { position: 1; color: pal.violet }
                    }
                    Rectangle { anchors.centerIn: parent; width: 32; height: 32; radius: 8; color: pal.panel
                        Canvas { anchors.fill: parent; onPaint: {
                            var c = getContext("2d"); c.reset();
                            c.strokeStyle = pal.cyan; c.lineWidth = 1.6; c.lineJoin="round"; c.lineCap="round";
                            c.beginPath(); c.moveTo(6,22); c.lineTo(13,7); c.lineTo(18,15); c.lineTo(22,10); c.lineTo(27,22); c.stroke();
                        } }
                    }
                }
                ColumnLayout {
                    spacing: 0
                    Text { text: "VIRKE · Kontrollsystem"; color: pal.ink; font.pixelSize: 15; font.weight: Font.DemiBold }
                    Text { text: "Dubbel-oblik laserskanner · Prototyp 500 mm"; color: pal.ink3; font.pixelSize: 10; font.family: mono; font.capitalization: Font.AllUppercase }
                }
                Item { Layout.fillWidth: true }
                // KPI:er
                Kpi { label: "Genomflöde"; value: ctrl.throughput.toFixed(1); unit: "br/min"; accent: pal.cyan }
                Kpi { label: "Brädor";     value: ctrl.boardCount }
                Kpi { label: "Jetson last"; value: Math.round(ctrl.jetsonLoad); unit: "%"; accent: pal.teal }
                Kpi { label: "Profiltakt"; value: Math.round(ctrl.profileRate); unit: "Hz" }
                // läge
                Rectangle {
                    radius: 8; color: pal.panel2; border.color: pal.line2
                    implicitWidth: modeT.width + 18; implicitHeight: 26
                    Text { id: modeT; anchors.centerIn: parent; text: "LÄGE " + ctrl.modeText; color: pal.violet; font.family: mono; font.pixelSize: 10; font.weight: Font.DemiBold }
                }
                // status
                Rectangle {
                    radius: 999; implicitWidth: stRow.width + 28; implicitHeight: 38
                    color: pal.panel2
                    border.color: ctrl.running ? Qt.rgba(0.2,0.9,0.71,0.35) : Qt.rgba(1,0.7,0.24,0.35)
                    RowLayout {
                        id: stRow; anchors.centerIn: parent; spacing: 9
                        Rectangle {
                            width: 9; height: 9; radius: 4.5
                            color: ctrl.running ? pal.teal : pal.amber
                            SequentialAnimation on opacity {
                                running: ctrl.running; loops: Animation.Infinite
                                NumberAnimation { from: 1; to: 0.3; duration: 700 }
                                NumberAnimation { from: 0.3; to: 1; duration: 700 }
                            }
                        }
                        Text { text: ctrl.statusText; color: ctrl.running ? pal.teal : pal.amber
                               font.family: mono; font.pixelSize: 12; font.weight: Font.DemiBold }
                    }
                }
            }
        }

        // ---------------------------------------------------------- BODY
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12

            // === VÄNSTER: yt-vy (korrekt proportion) + tvärsnitt ===========
            ColumnLayout {
                Layout.fillHeight: true
                Layout.fillWidth: true; Layout.preferredWidth: 1000; Layout.minimumWidth: 480
                spacing: 12

                // -------- YTKAMERA (centrerad live-vy i RÄTT proportion) -----
                Card {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    title: "YTKAMERA · 4K FÄRG-RADSKANNER"
                    chip: "Huateng · GigE · " + ctrl.boardLen.toFixed(0) + "×" + ctrl.boardWidth.toFixed(0) + " mm"

                    Item {
                        anchors.fill: parent
                        // brädans rektangel i KORREKT bild-proportion (längd:bredd)
                        Item {
                            id: boardBox
                            readonly property real asp: ctrl.boardAspect
                            width:  Math.min(parent.width, parent.height * asp)
                            height: Math.min(parent.height, parent.width / asp)
                            anchors.centerIn: parent

                            Rectangle { anchors.fill: parent; color: "#070b10"; radius: 8 }
                            Image {
                                id: surf
                                anchors.fill: parent
                                fillMode: Image.Stretch
                                cache: false; asynchronous: false
                                source: "image://live/surface/" + ctrl.surfaceRev
                                smooth: true
                            }
                            // odämpad del = redan skannad (uppifrån), dämpa resten
                            Rectangle {
                                x: 0; width: parent.width
                                y: parent.height * ctrl.scanProgress
                                height: parent.height * (1 - ctrl.scanProgress)
                                color: Qt.rgba(0.03,0.05,0.07,0.62)
                            }
                            // skannlinje (matningsled = vertikalt i denna vy)
                            Rectangle {
                                visible: ctrl.running && ctrl.scanProgress < 1
                                x: 0; width: parent.width; height: 2
                                y: parent.height * ctrl.scanProgress - 1
                                color: "white"
                                Rectangle { anchors.bottom: parent.top; width: parent.width; height: 9
                                    gradient: Gradient {
                                        GradientStop { position: 0; color: "transparent" }
                                        GradientStop { position: 1; color: Qt.rgba(1,1,1,0.5) } } }
                            }
                            Rectangle { anchors.fill: parent; color: "transparent"; radius: 8; border.color: pal.line2 }
                            // axeletiketter
                            Text { text: "0"; color: pal.ink3; font.family: mono; font.pixelSize: 9
                                   anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 3 }
                            Text { text: ctrl.boardLen.toFixed(0) + " mm (längd, X)"; color: pal.ink3; font.family: mono; font.pixelSize: 9
                                   anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 3 }
                            Text { text: "matning ↓ (bredd " + ctrl.boardWidth.toFixed(0) + " mm)"; color: pal.ink3; font.family: mono; font.pixelSize: 9
                                   rotation: 0; anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 3 }
                        }
                    }
                }

                // -------- TVÄRSNITT (live Z(x)) -----------------------------
                Card {
                    Layout.fillWidth: true; Layout.preferredHeight: 230
                    title: "TVÄRSNITT · LIVE-PROFIL Z(x)"
                    chip: "θ " + (ctrl ? "30°" : "") + " · RÖD+GRÖN"
                    Canvas {
                        id: crossCv
                        anchors.fill: parent
                        Connections { target: ctrl; function onStateChanged() { crossCv.requestPaint() } }
                        onPaint: {
                            var c = getContext("2d"); c.reset();
                            var w = width, h = height, m = 34, gx = m, gy = 10, gw = w - m - 12, gh = h - 26;
                            var BT = ctrl.nominalThick, lo = BT - 15, hi = BT + 15;
                            c.strokeStyle = "#16222f"; c.lineWidth = 1;
                            for (var i = 0; i <= 5; i++){ var yy = gy + gh*i/5; c.beginPath(); c.moveTo(gx,yy); c.lineTo(gx+gw,yy); c.stroke(); }
                            c.fillStyle = "#3a4d62"; c.font = "9px monospace"; c.textAlign = "right";
                            c.fillText(hi.toFixed(0), gx-4, gy+6); c.fillText(BT.toFixed(0), gx-4, gy+gh/2+3); c.fillText(lo.toFixed(0), gx-4, gy+gh-2);
                            var zp = ctrl.zProfile; if (!zp || zp.length < 2) { c.fillStyle="#3a4d62"; c.textAlign="center"; c.fillText("ingen aktiv profil", gx+gw/2, gy+gh/2); return; }
                            function Y(z){ return gy + gh*(1-((z-lo)/30)); }
                            // fylld area
                            c.beginPath(); c.moveTo(gx, gy+gh);
                            for (var k=0;k<zp.length;k++){ c.lineTo(gx+gw*k/(zp.length-1), Y(zp[k])); }
                            c.lineTo(gx+gw, gy+gh); c.closePath();
                            var g = c.createLinearGradient(0,gy,0,gy+gh);
                            g.addColorStop(0,"rgba(39,211,224,0.22)"); g.addColorStop(1,"rgba(39,211,224,0)");
                            c.fillStyle = g; c.fill();
                            // sammanslagen linje
                            c.beginPath();
                            for (var j=0;j<zp.length;j++){ var X=gx+gw*j/(zp.length-1), yv=Y(zp[j]); j? c.lineTo(X,yv):c.moveTo(X,yv); }
                            c.strokeStyle = pal.cyan; c.lineWidth = 2; c.shadowColor = pal.cyan; c.shadowBlur = 6; c.stroke(); c.shadowBlur = 0;
                            // nominell
                            c.setLineDash([4,4]); c.strokeStyle="rgba(159,178,198,0.3)"; c.lineWidth=1;
                            c.beginPath(); c.moveTo(gx,Y(BT)); c.lineTo(gx+gw,Y(BT)); c.stroke(); c.setLineDash([]);
                            c.fillStyle="#61768c"; c.textAlign="center"; c.fillText("x längs bräda (0–"+ctrl.boardLen.toFixed(0)+" mm)", gx+gw/2, h-4);
                        }
                    }
                }
            }

            // === HÖGER: tjocklek + gradering + defekter ====================
            ColumnLayout {
                Layout.fillHeight: true; Layout.fillWidth: false
                Layout.preferredWidth: 370; Layout.minimumWidth: 340; Layout.maximumWidth: 430
                spacing: 12

                // -------- LR400 punktlaser ----------------------------------
                Card {
                    Layout.fillWidth: true; Layout.preferredHeight: 196
                    title: "PUNKTLASER · ABSOLUT TJOCKLEK"; chip: "3× LR400 · RS-485"
                    ColumnLayout {
                        anchors.fill: parent; spacing: 8
                        Repeater {
                            model: 3
                            delegate: Rectangle {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                radius: 10; color: pal.panel2; border.color: pal.line
                                property real val: ctrl.lrThickness[index] !== undefined ? ctrl.lrThickness[index] : ctrl.nominalThick
                                property real dev: val - ctrl.nominalThick
                                property color cc: Math.abs(dev) < 1.2 ? pal.teal : (Math.abs(dev) < 3 ? pal.amber : pal.red)
                                RowLayout {
                                    anchors.fill: parent; anchors.margins: 10; spacing: 12
                                    ColumnLayout {
                                        spacing: 1; Layout.preferredWidth: 120
                                        Text { text: ["LR-V","LR-C","LR-H"][index] + " · ch" + (index+1); color: pal.cyan; font.family: mono; font.pixelSize: 10 }
                                        Text { text: "x = " + ctrl.lrPositions[index] + " mm"; color: pal.ink3; font.pixelSize: 10 }
                                    }
                                    Item { Layout.fillWidth: true }
                                    ColumnLayout {
                                        spacing: 0; Layout.alignment: Qt.AlignRight
                                        RowLayout { Layout.alignment: Qt.AlignRight; spacing: 4
                                            Text { text: val.toFixed(2); color: cc; font.family: mono; font.pixelSize: 22; font.weight: Font.DemiBold }
                                            Text { text: "mm"; color: pal.ink2; font.pixelSize: 11; Layout.alignment: Qt.AlignBottom; bottomPadding: 3 }
                                        }
                                        Text { text: "Δ " + (dev>=0?"+":"") + dev.toFixed(2) + " mm"; color: cc; font.family: mono; font.pixelSize: 10; Layout.alignment: Qt.AlignRight }
                                    }
                                    // mini-stapel
                                    Rectangle {
                                        Layout.preferredWidth: 6; Layout.fillHeight: true; Layout.topMargin: 2; Layout.bottomMargin: 2
                                        radius: 3; color: "#16222f"
                                        Rectangle {
                                            width: parent.width; radius: 3; color: cc
                                            height: parent.height * Math.max(0, Math.min(1, (val - (ctrl.nominalThick-15)) / 30))
                                            anchors.bottom: parent.bottom
                                            Behavior on height { NumberAnimation { duration: 90 } }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // -------- GRADERING -----------------------------------------
                Card {
                    Layout.fillWidth: true; Layout.preferredHeight: 96
                    title: "KVALITETSSORTERING"
                    RowLayout {
                        anchors.fill: parent; spacing: 13
                        Rectangle {
                            width: 58; height: 58; radius: 13
                            color: ctrl.gradeColor
                            Behavior on color { ColorAnimation { duration: 350 } }
                            Text { anchors.centerIn: parent; text: ctrl.gradeClass; color: "#06121a"; font.family: mono; font.pixelSize: 28; font.weight: Font.Bold }
                        }
                        ColumnLayout {
                            spacing: 2; Layout.fillWidth: true
                            Text { text: "KVALITETSKLASS"; color: pal.ink3; font.pixelSize: 10; font.letterSpacing: 0.6 }
                            Text { text: ctrl.gradeTitle; color: pal.ink; font.pixelSize: 14; font.weight: Font.DemiBold }
                            Text { text: ctrl.gradeReason; color: pal.ink2; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight }
                        }
                    }
                }

                // -------- DEFEKTER ------------------------------------------
                Card {
                    id: defectCard
                    Layout.fillWidth: true; Layout.fillHeight: true
                    title: "DEFEKTER"; chip: defectCard.defectModel.length + " st"
                    property var defectModel: []
                    Connections { target: ctrl; function onDefectsChanged() { defectCard.defectModel = ctrl.defects } }
                    ListView {
                        id: defList
                        anchors.fill: parent; clip: true; spacing: 5
                        model: defectCard.defectModel
                        delegate: Rectangle {
                            width: ListView.view.width; height: 30; radius: 8
                            color: pal.panel2; border.color: pal.line
                            RowLayout {
                                anchors.fill: parent; anchors.leftMargin: 9; anchors.rightMargin: 9; spacing: 9
                                Rectangle { width: 9; height: 9; radius: 3; color: modelData.color }
                                Text { text: modelData.name; color: pal.ink; font.pixelSize: 11; font.weight: Font.DemiBold }
                                Item { Layout.fillWidth: true }
                                Text { text: "x" + modelData.x + " y" + modelData.y + " · ⌀" + modelData.dia + "mm"
                                       color: pal.ink3; font.family: mono; font.pixelSize: 10 }
                            }
                        }
                        Text {
                            anchors.centerIn: parent; visible: defList.count === 0
                            text: "Inga defekter registrerade"; color: pal.ink3; font.pixelSize: 11; font.italic: true
                        }
                    }
                }
            }
        }

        // ---------------------------------------------------------- FOOTER
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 56
            radius: 14; color: pal.panel; border.color: pal.line
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 16; spacing: 14
                // Start/Pausa
                Btn {
                    primary: true; danger: ctrl.running
                    text: ctrl.running ? "Pausa" : "Starta"
                    onClicked: ctrl.toggleRun()
                }
                Btn { text: "Nästa bräda"; onClicked: ctrl.nextBoard() }

                CtrlSlider { label: "Matning"; from: 10; to: 120; step: 5; value: ctrl.feedSpeed
                    suffix: " mm/s"; onMoved: ctrl.setFeed(v) }
                CtrlSlider { label: "Profiltakt"; from: 200; to: 800; step: 50; value: ctrl.profileRate
                    suffix: " Hz"; onMoved: ctrl.setRate(v) }

                Item { Layout.fillWidth: true }

                Rectangle {
                    radius: 9; implicitHeight: 34; implicitWidth: autoRow.width + 22
                    color: pal.panel2; border.color: ctrl.autoAdvance ? Qt.rgba(0.2,0.9,0.71,0.35) : pal.line
                    RowLayout {
                        id: autoRow; anchors.centerIn: parent; spacing: 8
                        Rectangle {
                            width: 30; height: 16; radius: 8
                            color: ctrl.autoAdvance ? Qt.rgba(0.2,0.9,0.71,0.35) : pal.line2
                            Rectangle { width: 12; height: 12; radius: 6; y: 2
                                x: ctrl.autoAdvance ? 16 : 2
                                color: ctrl.autoAdvance ? pal.teal : pal.ink3
                                Behavior on x { NumberAnimation { duration: 120 } } }
                        }
                        Text { text: "Auto-mata"; color: ctrl.autoAdvance ? pal.teal : pal.ink2; font.pixelSize: 11 }
                    }
                    MouseArea { anchors.fill: parent; onClicked: ctrl.setAuto(!ctrl.autoAdvance) }
                }
            }
        }
    }

    // ================================================== återanvändbara delar
    component Kpi: Rectangle {
        property string label: ""
        property var value: ""
        property string unit: ""
        property color accent: pal.ink
        radius: 10; color: pal.panel2; border.color: pal.line
        implicitWidth: Math.max(92, kcol.width + 26); implicitHeight: 46
        ColumnLayout {
            id: kcol; anchors.centerIn: parent; spacing: 0
            Text { text: label.toUpperCase(); color: pal.ink3; font.pixelSize: 10; font.letterSpacing: 0.7 }
            RowLayout { spacing: 3
                Text { text: value; color: accent; font.family: mono; font.pixelSize: 17; font.weight: Font.DemiBold }
                Text { text: unit; visible: unit !== ""; color: pal.ink2; font.pixelSize: 10; Layout.alignment: Qt.AlignBottom; bottomPadding: 2 }
            }
        }
    }

    component Card: Rectangle {
        default property alias content: body.data
        property string title: ""
        property string chip: ""
        radius: 14; color: pal.panel; border.color: pal.line
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 12; spacing: 8
            RowLayout {
                Layout.fillWidth: true; spacing: 8
                Text { text: title; color: pal.ink2; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.5 }
                Item { Layout.fillWidth: true }
                Rectangle {
                    visible: chip !== ""; radius: 6; color: pal.panel2; border.color: pal.line
                    implicitWidth: chipT.width + 14; implicitHeight: 18
                    Text { id: chipT; anchors.centerIn: parent; text: chip; color: pal.ink3; font.family: mono; font.pixelSize: 9 }
                }
            }
            Item { id: body; Layout.fillWidth: true; Layout.fillHeight: true }
        }
    }

    component Btn: Rectangle {
        property string text: ""
        property bool primary: false
        property bool danger: false
        signal clicked()
        radius: 10; implicitHeight: 36; implicitWidth: lbl.width + 34
        color: primary ? (danger ? pal.red : pal.cyan) : pal.panel2
        border.color: primary ? "transparent" : pal.line2
        Behavior on color { ColorAnimation { duration: 150 } }
        Text { id: lbl; anchors.centerIn: parent; text: parent.text
               color: primary ? "#04222a" : pal.ink; font.pixelSize: 13; font.weight: Font.DemiBold }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: parent.clicked() }
    }

    component CtrlSlider: RowLayout {
        property string label: ""
        property real from: 0
        property real to: 100
        property real step: 1
        property real value: 0
        property string suffix: ""
        property real v: sld.value
        signal moved()
        spacing: 9
        Text { text: label.toUpperCase(); color: pal.ink3; font.pixelSize: 10; font.letterSpacing: 0.6 }
        Slider {
            id: sld; from: parent.from; to: parent.to; stepSize: parent.step; value: parent.value
            implicitWidth: 140
            onMoved: parent.moved()
            background: Rectangle { x: sld.leftPadding; y: sld.topPadding + sld.availableHeight/2 - 2
                width: sld.availableWidth; height: 4; radius: 2; color: pal.line2
                Rectangle { width: sld.visualPosition * parent.width; height: parent.height; radius: 2; color: pal.cyan } }
            handle: Rectangle { x: sld.leftPadding + sld.visualPosition * (sld.availableWidth - width)
                y: sld.topPadding + sld.availableHeight/2 - height/2
                width: 15; height: 15; radius: 8; color: pal.cyan; border.color: "#0b0f14" }
        }
        Text { text: Math.round(sld.value) + suffix; color: pal.cyan; font.family: mono; font.pixelSize: 13
               Layout.minimumWidth: 60 }
    }
}
