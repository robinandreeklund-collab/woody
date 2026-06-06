import QtQuick
import QtQuick.Layouts

Card {
    id: root
    title: "BRÄD-LOGG · HISTORIK"
    chip: model.length + " brädor"
    property var model: []
    property string exportMsg: ""
    Connections { target: ctrl
        function onHistoryChanged() { root.model = ctrl.history }
        function onExportDone(msg) { root.exportMsg = msg }
    }
    Component.onCompleted: root.model = ctrl.history

    ColumnLayout {
        anchors.fill: parent; spacing: 0
        // verktygsrad
        RowLayout {
            Layout.fillWidth: true; Layout.bottomMargin: 8; spacing: 12
            Btn { text: "Exportera CSV"; onClicked: ctrl.exportLog() }
            Text { text: root.exportMsg; color: Theme.teal; font.family: Theme.mono; font.pixelSize: 10; Layout.fillWidth: true }
        }
        // rubrikrad
        Rectangle {
            Layout.fillWidth: true; height: 28; color: "transparent"
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10; spacing: 0
                Text { text: "#";       color: Theme.ink3; font.pixelSize: 10; Layout.preferredWidth: 60 }
                Text { text: "TID";     color: Theme.ink3; font.pixelSize: 10; Layout.preferredWidth: 90 }
                Text { text: "KLASS";   color: Theme.ink3; font.pixelSize: 10; Layout.preferredWidth: 60 }
                Text { text: "BESKRIVNING"; color: Theme.ink3; font.pixelSize: 10; Layout.fillWidth: true }
                Text { text: "DEFEKTER"; color: Theme.ink3; font.pixelSize: 10; Layout.preferredWidth: 90 }
                Text { text: "POÄNG";   color: Theme.ink3; font.pixelSize: 10; Layout.preferredWidth: 70; horizontalAlignment: Text.AlignRight }
            }
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.line }
        ListView {
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true; model: root.model
            delegate: Rectangle {
                width: ListView.view.width; height: 34
                color: index % 2 ? "transparent" : Qt.rgba(1,1,1,0.018)
                RowLayout {
                    anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10; spacing: 0
                    Text { text: "#" + modelData.n; color: Theme.ink2; font.family: Theme.mono; font.pixelSize: 11; Layout.preferredWidth: 60 }
                    Text { text: modelData.time; color: Theme.ink3; font.family: Theme.mono; font.pixelSize: 11; Layout.preferredWidth: 90 }
                    Item { Layout.preferredWidth: 60
                        Rectangle { width: 24; height: 24; radius: 7; color: modelData.color
                            Text { anchors.centerIn: parent; text: modelData.cls; color: "#06121a"; font.family: Theme.mono; font.pixelSize: 13; font.weight: Font.Bold } } }
                    Text { text: modelData.title; color: Theme.ink; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight }
                    Text { text: modelData.ndef + " st"; color: Theme.ink2; font.family: Theme.mono; font.pixelSize: 11; Layout.preferredWidth: 90 }
                    Text { text: modelData.score + "/100"; color: Theme.ink2; font.family: Theme.mono; font.pixelSize: 11; Layout.preferredWidth: 70; horizontalAlignment: Text.AlignRight }
                }
            }
            Text { anchors.centerIn: parent; visible: root.model.length === 0
                   text: "Inga brädor loggade ännu — starta körningen"; color: Theme.ink3; font.pixelSize: 12; font.italic: true }
        }
    }
}
