import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

RowLayout {
    id: root
    property string label: ""
    property real from: 0
    property real to: 100
    property real step: 1
    property real value: 0
    property string suffix: ""
    property real v: sld.value
    signal moved()
    spacing: 9
    Text { text: root.label.toUpperCase(); color: Theme.ink3; font.pixelSize: 10; font.letterSpacing: 0.6 }
    Slider {
        id: sld; from: root.from; to: root.to; stepSize: root.step; value: root.value
        implicitWidth: 140
        onMoved: root.moved()
        background: Rectangle {
            x: sld.leftPadding; y: sld.topPadding + sld.availableHeight/2 - 2
            width: sld.availableWidth; height: 4; radius: 2; color: Theme.line2
            Rectangle { width: sld.visualPosition * parent.width; height: parent.height; radius: 2; color: Theme.cyan }
        }
        handle: Rectangle {
            x: sld.leftPadding + sld.visualPosition * (sld.availableWidth - width)
            y: sld.topPadding + sld.availableHeight/2 - height/2
            width: 15; height: 15; radius: 8; color: Theme.cyan; border.color: "#0b0f14"
        }
    }
    Text { text: Math.round(sld.value) + root.suffix; color: Theme.cyan
           font.family: Theme.mono; font.pixelSize: 13; Layout.minimumWidth: 60 }
}
