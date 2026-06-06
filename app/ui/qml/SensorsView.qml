import QtQuick
import QtQuick.Layouts

Flickable {
    id: root
    contentHeight: flow.height
    clip: true

    Flow {
        id: flow
        width: root.width; spacing: 12

        // --- profilkameror ---
        SCard {
            sName: "Profilkamera RÖD 650"; sModel: "Hikrobot MV-CS050-10UM · mono"; sIface: "USB3 Vision"
            tag: "datablad: Sony IMX264 · 5 MP global shutter"; ledOn: ctrl.running
            spec: [["Upplösning","2448×2048"],["Pixel","3,45 µm"],["Slutare","global"],["Filter","bandpass 650 nm"]]
            live: [["Bildtakt",ctrl.telemetry.profRate],["Exponering",ctrl.telemetry.profExp],
                   ["Z-upplösning",ctrl.telemetry.profZres],["Datatakt",ctrl.telemetry.profData],
                   ["Signal",ctrl.telemetry.profSig]]
        }
        SCard {
            sName: "Profilkamera GRÖN 520"; sModel: "Hikrobot MV-CS050-10UM · mono"; sIface: "USB3 Vision"
            tag: "datablad: Sony IMX264 · 5 MP global shutter"; ledOn: ctrl.running
            spec: [["Upplösning","2448×2048"],["Pixel","3,45 µm"],["Slutare","global"],["Filter","bandpass 520 nm"]]
            live: [["Bildtakt",ctrl.telemetry.profRate],["Exponering",ctrl.telemetry.profExp],
                   ["Z-upplösning",ctrl.telemetry.profZres],["Datatakt",ctrl.telemetry.profData],
                   ["Signal",ctrl.telemetry.profSig]]
        }
        // --- ytkamera ---
        SCard {
            sName: "Ytkamera · 4K färg-radskanner"; sModel: "Huateng 4096×4 TDI · färg"; sIface: "GigE Vision"
            tag: "datablad: 7 µm · ~8 kHz färg · M42"; ledOn: ctrl.running
            spec: [["Upplösning","4096×4 TDI"],["Pixel","7,0 µm"],["Färg","RGB888 8-bit"],["Lins","20 mm ZLKC M42"]]
            live: [["Radtakt",ctrl.telemetry.surfRate],["Rader/bräda",ctrl.telemetry.surfRows],
                   ["Upplösning",ctrl.telemetry.surfMmPx],["Datatakt",ctrl.telemetry.surfData],
                   ["Av kapacitet",ctrl.telemetry.surfCap]]
        }
        // --- punktlasrar ---
        Repeater {
            model: 3
            delegate: SCard {
                sName: "Punktlaser " + ["LR-V","LR-C","LR-H"][index]; sModel: "LR400 · CMOS-triangulering"
                sIface: "RS-485 ch" + (index+1); tag: "datablad: 60–400 mm · 8 µm"; ledOn: ctrl.running
                spec: [["Mätområde","60–400 mm"],["Position","x = "+ctrl.lrPositions[index]+" mm"],["Upplösning","8 µm"],["Protokoll","Modbus RTU"]]
                live: [["Tjocklek",(ctrl.lrThickness[index]!==undefined?ctrl.lrThickness[index].toFixed(2):"--")+" mm"],
                       ["Δ nominell",((ctrl.lrThickness[index]!==undefined?(ctrl.lrThickness[index]-ctrl.rig.thick):0)>=0?"+":"")+(ctrl.lrThickness[index]!==undefined?(ctrl.lrThickness[index]-ctrl.rig.thick).toFixed(2):"0")+" mm"],
                       ["Sampeltakt",ctrl.running?"~640 Hz":"0 Hz"]]
            }
        }
        // --- transportör ---
        SCard {
            sName: "Transportör · matning"; sModel: "24 V DC · Jrk G2"; sIface: "USB"; ledOn: ctrl.running
            tag: "designval: 50 mm/s nominellt"
            spec: [["Matarhjul","Ø ~50 mm"],["Drivare","Jrk G2 21v3"],["Spänning","24 V"],["Återkoppling","Hall/kvadratur"]]
            live: [["Hastighet",ctrl.telemetry.convSpeed],["Motorström",ctrl.telemetry.convCurrent],
                   ["Encoder",ctrl.telemetry.convEnc],["PWM-pådrag",ctrl.telemetry.convPwm]]
        }
        // --- Jetson ---
        SCard {
            sName: "Jetson Orin Nano Super"; sModel: "1024 CUDA · 32 Tensor · 8 GB"; sIface: "aarch64 · JetPack"
            tag: "beräkningsnod — total inström"; ledOn: ctrl.running; ledWarn: ctrl.jetsonLoad > 80
            spec: [["GPU","Ampere 1024c"],["CPU","6× A78AE"],["Minne","8 GB LPDDR5"],["Läge","MAXN Super 25 W"]]
            live: [["CPU",ctrl.telemetry.jetCpu],["GPU",ctrl.telemetry.jetGpu],["RAM",ctrl.telemetry.jetRam],
                   ["Total inström",ctrl.telemetry.jetIngest],["Effekt",ctrl.telemetry.jetPwr],["Temp",ctrl.telemetry.jetTemp]]
        }
    }

    // --------------------------------------------------------- sensorkort
    component SCard: Rectangle {
        property string sName: ""; property string sModel: ""; property string sIface: ""; property string tag: ""
        property var spec: []; property var live: []
        property bool ledOn: false; property bool ledWarn: false
        width: (flow.width - 2*12) / 3 - 0.5
        implicitHeight: scol.height + 26
        radius: 14; color: Theme.panel; border.color: Theme.line
        ColumnLayout {
            id: scol; x: 13; y: 13; width: parent.width - 26; spacing: 10
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                Rectangle { width: 9; height: 9; radius: 4.5; Layout.topMargin: 4
                    color: ledWarn ? Theme.amber : (ledOn ? Theme.teal : Theme.ink3)
                    SequentialAnimation on opacity { running: ledOn; loops: Animation.Infinite
                        NumberAnimation { from: 1; to: 0.4; duration: 800 } NumberAnimation { from: 0.4; to: 1; duration: 800 } } }
                ColumnLayout { spacing: 1; Layout.fillWidth: true
                    Text { text: sName; color: Theme.ink; font.pixelSize: 13; font.weight: Font.DemiBold }
                    Text { text: sModel; color: Theme.ink3; font.family: Theme.mono; font.pixelSize: 10; elide: Text.ElideRight; Layout.fillWidth: true } }
                Rectangle { radius: 6; color: Theme.panel2; border.color: Theme.line; implicitWidth: ift.width+14; implicitHeight: 18
                    Text { id: ift; anchors.centerIn: parent; text: sIface; color: Theme.ink2; font.family: Theme.mono; font.pixelSize: 9 } }
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
