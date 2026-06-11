import QtQuick
import QtQuick.Layouts

// Sensoröversikt — den LÅSTA hårdvaran med live status (devmgr) + telemetri (ctrl).
// Klicka på ett kort → hoppa till Kalibrering med enheten vald.
Flickable {
    id: root
    contentHeight: flow.height
    clip: true

    signal calibrate(string devId)

    function statusOf(id) {
        var s = devmgr.statusMap[id]
        return s ? s : {"connected": false, "status": "?"}
    }

    Flow {
        id: flow
        width: root.width; spacing: 12

        // --- profilkameror ---
        SCard {
            devId: "prof_red"
            sName: "Profilkamera RÖD 650"; sModel: "Hikrobot MV-CS050-10UM · mono"; sIface: "USB3 Vision"
            tag: "datablad: Sony IMX264 · 5 MP global shutter · 60 fps"
            spec: [["Upplösning","2448×2048"],["Pixel","3,45 µm"],["Slutare","global"],["Filter","bandpass 650 nm"]]
            live: [["Bildtakt",ctrl.telemetry.profRate],["Exponering",ctrl.telemetry.profExp],
                   ["Z-upplösning",ctrl.telemetry.profZres],["Datatakt",ctrl.telemetry.profData],
                   ["Signal",ctrl.telemetry.profSig]]
        }
        SCard {
            devId: "prof_green"
            sName: "Profilkamera GRÖN 520"; sModel: "Hikrobot MV-CS050-10UM · mono"; sIface: "USB3 Vision"
            tag: "datablad: Sony IMX264 · 5 MP global shutter · 60 fps"
            spec: [["Upplösning","2448×2048"],["Pixel","3,45 µm"],["Slutare","global"],["Filter","bandpass 520 nm"]]
            live: [["Bildtakt",ctrl.telemetry.profRate],["Exponering",ctrl.telemetry.profExp],
                   ["Z-upplösning",ctrl.telemetry.profZres],["Datatakt",ctrl.telemetry.profData],
                   ["Signal",ctrl.telemetry.profSig]]
        }
        // --- ytkamera (linjekamera) ---
        SCard {
            devId: "surface"
            sName: "Ytkamera · 4K linjekamera"; sModel: "HT-GELM44C-T2 · färg"; sIface: "GigE Vision"
            tag: "datablad: 7 µm · ~8 kHz färg · M42 · encoder-triggad (band B)"
            spec: [["Upplösning","4096×4 TDI"],["Pixel","7,0 µm"],["Färg","RGB888 8-bit"],["Lins","ZLKC TM2004MPC 20 mm"]]
            live: [["Radtakt",ctrl.telemetry.surfRate],["Rader/bräda",ctrl.telemetry.surfRows],
                   ["Upplösning",ctrl.telemetry.surfMmPx],["Datatakt",ctrl.telemetry.surfData],
                   ["Av kapacitet",ctrl.telemetry.surfCap]]
        }
        // --- transportör (RoboClaw) ---
        SCard {
            devId: "conveyor"
            sName: "Transportör · 2 band"; sModel: "RoboClaw 2x7A · sluten slinga"; sIface: "USB"
            tag: "designval: 50 mm/s nominellt · quadrature-FB · 5V-BEC matar encodrar"
            spec: [["Kanaler","M1 + M2 synkade"],["Spänning","24 V"],["Ström","2×7 A (30 A topp)"],["Återkoppling","EN1 + EN2"]]
            live: [["Hastighet",ctrl.telemetry.convSpeed],["Motorström",ctrl.telemetry.convCurrent],
                   ["Encoder",ctrl.telemetry.convEnc],["PWM-pådrag",ctrl.telemetry.convPwm]]
        }
        // --- encodrar ---
        SCard {
            devId: "enc_a"
            sName: "Encoder · band A"; sModel: "Omron E6B2-CWZ6C"; sIface: "→ RoboClaw EN1"
            tag: "single-ended · matas av RoboClaws 5V-BEC"
            spec: [["Typ","inkrementell 1000 ppr"],["Utgång","open collector A/B/Z"],["Roll","closed-loop band A"]]
            live: [["Position",ctrl.telemetry.convEnc]]
        }
        SCard {
            devId: "enc_b"
            sName: "Encoder · band B"; sModel: "Omron E6B2-CWZ1X"; sIface: "→ Kamera Line0 + 26C32→EN2"
            tag: "RS-422 line-driver · hårdvarutriggar linjekameran (ingen Jetson-kabel)"
            spec: [["Typ","inkrementell 1000 ppr"],["Utgång","RS-422 differentiell"],["Roll","kameratrigg + EN2"]]
            live: [["Triggade rader",ctrl.telemetry.surfRows]]
        }
        // --- punktlasrar (RS-485 Modbus, Waveshare 4CH) ---
        SCard {
            devId: "lr400"
            sName: "3× Punktlaser LR400"; sModel: "LR400 · CMOS-triangulering"; sIface: "RS-485 · 4CH ch1-3"
            tag: "Fas 2 · absolut tjocklek → ankrar trianguleringen (fusion.anchor) · ch4 reserv"
            spec: [["Mätområde","60–400 mm"],["Upplösning","8 µm"],["Protokoll","Modbus RTU"],
                   ["Positioner","x = "+ctrl.lrPositions.join(" / ")+" mm"]]
            live: [["Tjocklek V",(ctrl.lrThickness[0]!==undefined?ctrl.lrThickness[0].toFixed(2):"--")+" mm"],
                   ["Tjocklek C",(ctrl.lrThickness[1]!==undefined?ctrl.lrThickness[1].toFixed(2):"--")+" mm"],
                   ["Tjocklek H",(ctrl.lrThickness[2]!==undefined?ctrl.lrThickness[2].toFixed(2):"--")+" mm"],
                   ["Sampeltakt",ctrl.running?"~640 Hz":"0 Hz"]]
        }
        // --- lasrar + LED + fotocell ---
        SCard {
            devId: "laser_red"
            sName: "Linjelaser RÖD"; sModel: "650 nm · 100 mW · 60°"; sIface: "5 V · GPIO-enable"
            tag: "DC-barrel · enable via D4184/AO3400 MOSFET · klass 3B — interlock!"
            spec: [["Våglängd","650 nm"],["Effekt","100 mW"],["Linje","60° solfjäder"],["Mål linjebredd","< 0,3 mm @ WD"]]
            live: [["Status",ctrl.running ? "PÅ (skanning)" : "AV"]]
        }
        SCard {
            devId: "laser_green"
            sName: "Linjelaser GRÖN"; sModel: "520 nm · 50 mW · 60°"; sIface: "24 V · GPIO-enable"
            tag: "DC-barrel · enable via AOD4184 opto-MOSFET · klass 3B — interlock!"
            spec: [["Våglängd","520 nm"],["Effekt","50 mW"],["Linje","60° solfjäder"],["Mål linjebredd","< 0,3 mm @ WD"]]
            live: [["Status",ctrl.running ? "PÅ (skanning)" : "AV"]]
        }
        SCard {
            devId: "led_white"
            sName: "LED-belysning"; sModel: "24 V vit linjelist"; sIface: "GPIO-enable"
            tag: "jämnt vitt ljus för färgytan — 1 pass, ingen R/G/B-strobe"
            spec: [["Spänning","24 V"],["Roll","ytkamerans ljus"],["Korrektion","flat-field"]]
            live: [["Status",ctrl.running ? "PÅ" : "AV"]]
        }
        SCard {
            devId: "photocell"
            sName: "Fotocell · anslag"; sModel: "GTRIC LSZ-S30N1"; sIface: "GPIO in"
            tag: "NPN · diffus laser · brädstart + positionsnollning"
            spec: [["Typ","diffus reflektion"],["Utgång","NPN NO"],["Roll","brädstart-trigger"]]
            live: [["Senaste trigg",ctrl.boardCount > 0 ? "bräda #"+ctrl.boardCount : "—"]]
        }
        // --- system ---
        SCard {
            devId: "rig"
            sName: "Riggen · system"; sModel: "Dubbel-oblik 25°/50°"; sIface: "systemkalibrering"
            tag: "nollplan B(x) · huvud-alignment RÖD↔GRÖN · referensbräda end-to-end"
            spec: [["WD","760 mm"],["Baslinje","329 mm"],["Konvergens","35 mm över band"],["Tjocklekspann","15–50 mm"]]
            live: [["Genomflöde",ctrl.throughput.toFixed(1)+" br/min"]]
        }
        SCard {
            devId: "jetson"
            sName: "Jetson Orin Nano Super"; sModel: "1024 CUDA · 32 Tensor · 8 GB"; sIface: "aarch64 · JetPack"
            tag: "beräkningsnod — total inström"; ledWarn: ctrl.jetsonLoad > 80
            spec: [["GPU","Ampere 1024c"],["CPU","6× A78AE"],["Minne","8 GB LPDDR5"],["Läge","MAXN Super 25 W"]]
            live: [["CPU",ctrl.telemetry.jetCpu],["GPU",ctrl.telemetry.jetGpu],["RAM",ctrl.telemetry.jetRam],
                   ["Total inström",ctrl.telemetry.jetIngest],["Effekt",ctrl.telemetry.jetPwr],["Temp",ctrl.telemetry.jetTemp]]
        }
    }

    // --------------------------------------------------------- sensorkort
    component SCard: Rectangle {
        id: card
        property string devId: ""
        property string sName: ""; property string sModel: ""; property string sIface: ""; property string tag: ""
        property var spec: []; property var live: []
        property bool ledWarn: false
        readonly property var dstat: root.statusOf(devId)
        readonly property bool isConn: dstat.connected === true
        readonly property int calibDone: {
            var n = 0, ds = devmgr.devices
            for (var i = 0; i < ds.length; i++) if (ds[i].id === devId) return ds[i].calibDone
            return 0
        }
        readonly property int calibTotal: {
            var ds = devmgr.devices
            for (var i = 0; i < ds.length; i++) if (ds[i].id === devId) return ds[i].calibTotal
            return 0
        }
        width: (flow.width - 2*12) / 3 - 0.5
        implicitHeight: scol.height + 26
        radius: 14; color: Theme.panel
        border.color: cma.containsMouse ? Theme.cyan : Theme.line
        Behavior on border.color { ColorAnimation { duration: 120 } }

        MouseArea {
            id: cma; anchors.fill: parent; hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.calibrate(card.devId)
        }

        ColumnLayout {
            id: scol; x: 13; y: 13; width: parent.width - 26; spacing: 10
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                Rectangle { width: 9; height: 9; radius: 4.5; Layout.topMargin: 4
                    color: ledWarn ? Theme.amber : (isConn ? (ctrl.running ? Theme.teal : Theme.cyan) : Theme.red)
                    SequentialAnimation on opacity { running: isConn && ctrl.running; loops: Animation.Infinite
                        NumberAnimation { from: 1; to: 0.4; duration: 800 } NumberAnimation { from: 0.4; to: 1; duration: 800 } } }
                ColumnLayout { spacing: 1; Layout.fillWidth: true
                    Text { text: sName; color: Theme.ink; font.pixelSize: 13; font.weight: Font.DemiBold }
                    Text { text: sModel; color: Theme.ink3; font.family: Theme.mono; font.pixelSize: 10; elide: Text.ElideRight; Layout.fillWidth: true } }
                Rectangle { radius: 6; color: Theme.panel2; border.color: Theme.line; implicitWidth: ift.width+14; implicitHeight: 18
                    Text { id: ift; anchors.centerIn: parent; text: sIface; color: Theme.ink2; font.family: Theme.mono; font.pixelSize: 9 } }
            }
            // statusrad: anslutning + kalibrering
            RowLayout {
                Layout.fillWidth: true; spacing: 8
                Rectangle { radius: 6; implicitWidth: stt.width+12; implicitHeight: 18
                    color: isConn ? Qt.rgba(0.2,0.9,0.71,0.10) : Qt.rgba(1,0.3,0.37,0.10)
                    border.color: isConn ? Qt.rgba(0.2,0.9,0.71,0.3) : Qt.rgba(1,0.3,0.37,0.3)
                    Text { id: stt; anchors.centerIn: parent; text: dstat.status
                           color: isConn ? Theme.teal : Theme.red; font.family: Theme.mono; font.pixelSize: 9 } }
                Rectangle { visible: calibTotal > 0; radius: 6; implicitWidth: cbt.width+12; implicitHeight: 18
                    color: calibDone === calibTotal ? Qt.rgba(0.2,0.9,0.71,0.10) : Qt.rgba(1,0.7,0.24,0.10)
                    border.color: calibDone === calibTotal ? Qt.rgba(0.2,0.9,0.71,0.3) : Qt.rgba(1,0.7,0.24,0.3)
                    Text { id: cbt; anchors.centerIn: parent
                           text: "KAL " + calibDone + "/" + calibTotal
                           color: calibDone === calibTotal ? Theme.teal : Theme.amber
                           font.family: Theme.mono; font.pixelSize: 9 } }
                Item { Layout.fillWidth: true }
                Text { text: "kalibrera →"; visible: cma.containsMouse && calibTotal > 0
                       color: Theme.cyan; font.family: Theme.mono; font.pixelSize: 9 }
            }
            GridLayout {
                Layout.fillWidth: true; columns: 2; columnSpacing: 14; rowSpacing: 5
                Repeater { model: spec
                    delegate: RowLayout { Layout.fillWidth: true; spacing: 8
                        Text { text: modelData[0]; color: Theme.ink3; font.pixelSize: 10 }
                        Item { Layout.fillWidth: true }
                        Text { text: modelData[1]; color: Theme.ink2; font.family: Theme.mono; font.pixelSize: 11 } } }
                Repeater { model: live
                    delegate: RowLayout { Layout.fillWidth: true; spacing: 8
                        Text { text: modelData[0]; color: Theme.ink3; font.pixelSize: 10 }
                        Item { Layout.fillWidth: true }
                        Text { text: modelData[1]; color: Theme.cyan; font.family: Theme.mono; font.pixelSize: 11; font.weight: Font.DemiBold } } }
            }
            Rectangle { Layout.fillWidth: true; radius: 6; implicitHeight: tgt.height+10
                color: Qt.rgba(0.6,0.48,1,0.08); border.color: Qt.rgba(0.6,0.48,1,0.22)
                Text { id: tgt; x: 7; y: 5; width: parent.width-14; text: tag; color: Theme.violet; font.family: Theme.mono; font.pixelSize: 9; wrapMode: Text.WordWrap } }
        }
    }
}
