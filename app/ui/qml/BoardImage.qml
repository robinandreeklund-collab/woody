import QtQuick

// Bräd-bild i KORREKT proportion (längd:bredd) med skann-reveal + skannlinje.
Item {
    id: root
    anchors.fill: parent                 // fyll Card-kroppen
    property string kind: "surface"      // "surface" | "height"
    property string bottomLabel: ""

    Item {
        id: box
        readonly property real asp: ctrl.rig.len / ctrl.rig.width
        width:  Math.min(parent.width, parent.height * asp)
        height: Math.min(parent.height, parent.width / asp)
        anchors.centerIn: parent

        Rectangle { anchors.fill: parent; color: "#070b10"; radius: 8 }
        Image {
            anchors.fill: parent; fillMode: Image.Stretch; smooth: true
            cache: false; asynchronous: false
            source: "image://live/" + root.kind + "/" + ctrl.surfaceRev
        }
        // dämpa ej-skannad del (matning uppifrån och ned)
        Rectangle {
            x: 0; width: parent.width
            y: parent.height * ctrl.scanProgress
            height: parent.height * (1 - ctrl.scanProgress)
            color: Qt.rgba(0.03,0.05,0.07,0.62)
        }
        // skannlinje
        Rectangle {
            visible: ctrl.running && ctrl.scanProgress < 1
            x: 0; width: parent.width; height: 2
            y: parent.height * ctrl.scanProgress - 1; color: "white"
            Rectangle { anchors.bottom: parent.top; width: parent.width; height: 9
                gradient: Gradient {
                    GradientStop { position: 0; color: "transparent" }
                    GradientStop { position: 1; color: Qt.rgba(1,1,1,0.5) } } }
        }
        Rectangle { anchors.fill: parent; color: "transparent"; radius: 8; border.color: Theme.line2 }
        Text { text: "0"; color: Theme.ink3; font.family: Theme.mono; font.pixelSize: 9
               anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 3 }
        Text { text: root.bottomLabel; color: Theme.ink3; font.family: Theme.mono; font.pixelSize: 9
               anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 3 }
        Text { text: "matning ↓"; color: Theme.ink3; font.family: Theme.mono; font.pixelSize: 9
               anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 3 }
    }
}
