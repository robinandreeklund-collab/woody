import QtQuick

// Ytbild (linjekamera) med defekt-markörer ovanpå. Defekt-koordinater ligger i
// brädans pixelrum (= ytbildens sourceSize) → normaliseras mot den faktiskt
// ritade bilden (PreserveAspectFit centrerar, så vi räknar ut paint-rektangeln).
Item {
    id: root
    property string imgSource: ""
    property var defects: []
    property bool ready: img.status === Image.Ready && img.sourceSize.width > 0

    Rectangle { anchors.fill: parent; radius: Theme.rSm; color: "#0b1220"; border.color: Theme.line }

    Image {
        id: img
        anchors.fill: parent; anchors.margins: 4
        fillMode: Image.PreserveAspectFit; cache: false; smooth: true
        source: root.imgSource
    }

    // ritad bild-rektangel inom img (PreserveAspectFit)
    readonly property real _scale: ready ? Math.min(img.width / img.sourceSize.width,
                                                    img.height / img.sourceSize.height) : 1
    readonly property real _pw: ready ? img.sourceSize.width * _scale : 0
    readonly property real _ph: ready ? img.sourceSize.height * _scale : 0
    readonly property real _ox: img.x + (img.width - _pw) / 2
    readonly property real _oy: img.y + (img.height - _ph) / 2

    Repeater {
        model: root.ready ? root.defects : []
        delegate: Item {
            property real fx: modelData.x / img.sourceSize.width
            property real fy: modelData.y / img.sourceSize.height
            property real d: Math.max(10, (modelData.dia || 4) * root._scale)
            x: root._ox + fx * root._pw - d / 2
            y: root._oy + fy * root._ph - d / 2
            width: d; height: d
            Rectangle {
                anchors.fill: parent; radius: width / 2; color: "transparent"
                border.color: modelData.color || Theme.warn; border.width: 2
                Rectangle { anchors.centerIn: parent; width: 3; height: 3; radius: 1.5
                            color: modelData.color || Theme.warn }
            }
        }
    }

    Text {
        anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 8
        visible: !root.ready
        text: "ingen ytbild"; color: Theme.ink3; font.family: Theme.sans; font.pixelSize: 10
    }
}
