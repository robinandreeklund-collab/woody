import QtQuick

// LINJEKAMERA-bygge: en radkamera ser bara EN pixelrad i taget. Bilden byggs upp
// rad-för-rad medan brädan matas förbi → vi visar bara den del som passerat
// (skannats); resten är svart (ännu inte i kameran). Skannlinjen = aktuell rad.
Item {
    id: root
    anchors.fill: parent
    property string kind: "surface"      // "surface" | "height"
    property string bottomLabel: ""

    Item {
        id: box
        readonly property real asp: ctrl.rig.len / ctrl.rig.width
        width:  Math.min(parent.width, parent.height * asp)
        height: Math.min(parent.height, parent.width / asp)
        anchors.centerIn: parent

        // svart bakgrund = ännu inte skannat (har inte passerat kameran)
        Rectangle { anchors.fill: parent; color: "#05080c"; radius: 8 }

        // uppbyggd bild: visa BARA de rader som passerat (uppifrån = ledande kant)
        Item {
            id: clip
            x: 0; y: 0; width: parent.width
            height: Math.max(0, parent.height * ctrl.scanProgress)
            clip: true
            Image {
                x: 0; y: 0; width: box.width; height: box.height   // hel bräda, beskärs av clip
                fillMode: Image.Stretch; smooth: true
                cache: false; asynchronous: false
                source: "image://live/" + root.kind + "/" + ctrl.surfaceRev
            }
        }

        // skannlinje (aktuell pixelrad som just nu exponeras)
        Rectangle {
            visible: ctrl.running && ctrl.scanProgress < 1
            x: 0; width: parent.width; height: 2
            y: parent.height * ctrl.scanProgress - 1; color: "white"
            Rectangle { anchors.bottom: parent.top; width: parent.width; height: 10
                gradient: Gradient {
                    GradientStop { position: 0; color: "transparent" }
                    GradientStop { position: 1; color: Qt.rgba(1,1,1,0.55) } } }
        }

        Rectangle { anchors.fill: parent; color: "transparent"; radius: 8; border.color: Theme.line2 }
        Text { text: "0"; color: Theme.ink3; font.family: Theme.mono; font.pixelSize: 9
               anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 3 }
        Text { text: root.bottomLabel; color: Theme.ink3; font.family: Theme.mono; font.pixelSize: 9
               anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 3 }
        Text { text: "matning ↓ (en rad i taget)"; color: Theme.ink3; font.family: Theme.mono; font.pixelSize: 9
               anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 3 }
    }
}
