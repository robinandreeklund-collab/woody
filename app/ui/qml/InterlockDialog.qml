import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

// Lasersäkerhet (klass 3B): modal interlock-checklista. ALLA punkter måste kryssas
// innan "Arma lasrar" går att trycka. Emitterar armed() vid bekräftelse.
Popup {
    id: dlg
    modal: true; dim: true
    anchors.centerIn: Overlay.overlay
    width: 480; padding: 0
    closePolicy: Popup.CloseOnEscape

    signal armed()

    // Checklistan — tona mot den fysiska riggens faktiska skydd vid idrifttagning.
    property var items: [
        "Mätzonen är inkapslad och luckan/dörren är stängd",
        "Dörrinterlock aktiv (bryter lasern om skyddet öppnas)",
        "Skyddsglasögon på alla i rummet (HM326-C, OD för 650 + 520 nm)",
        "Inga personer eller reflekterande föremål i strålgången",
        "Behörig operatör närvarande och ansvarig"
    ]
    property int mask: 0
    function bit(i) { return 1 << i }
    function isOn(i) { return (mask & bit(i)) !== 0 }
    function allOn() { return mask === (bit(items.length) - 1) }
    onAboutToShow: mask = 0

    background: Rectangle { color: Theme.panel; radius: 14
        border.color: Qt.rgba(1,0.3,0.37,0.55); border.width: 1 }

    contentItem: ColumnLayout {
        spacing: 12
        Rectangle { Layout.fillWidth: true; implicitHeight: 44; radius: 14
            color: Qt.rgba(1,0.3,0.37,0.12)
            Text { anchors.centerIn: parent; text: "⚠  LASERSÄKERHET · KLASS 3B"
                   color: Theme.red; font.pixelSize: 15; font.weight: Font.Bold; font.family: Theme.mono } }

        Text { Layout.fillWidth: true; Layout.leftMargin: 16; Layout.rightMargin: 16
               text: "Bekräfta VARJE punkt innan lasern armas. Efter arm får auto-"
                   + "kalibreringen tända→mäta→släcka via kamerorna."
               color: Theme.ink3; font.pixelSize: 11; wrapMode: Text.WordWrap }

        ColumnLayout {
            Layout.fillWidth: true; Layout.leftMargin: 16; Layout.rightMargin: 16; spacing: 8
            Repeater {
                model: dlg.items
                delegate: Rectangle {
                    Layout.fillWidth: true; radius: 9; implicitHeight: irow.height + 16
                    color: dlg.isOn(index) ? Qt.rgba(0.2,0.9,0.71,0.10) : Theme.panel2
                    border.color: dlg.isOn(index) ? Qt.rgba(0.2,0.9,0.71,0.4) : Theme.line
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: dlg.mask = dlg.mask ^ dlg.bit(index) }
                    RowLayout {
                        id: irow; x: 11; y: 8; width: parent.width - 22; spacing: 10
                        Rectangle { width: 20; height: 20; radius: 5
                            color: dlg.isOn(index) ? Theme.teal : "transparent"
                            border.color: dlg.isOn(index) ? Theme.teal : Theme.line2
                            Text { anchors.centerIn: parent; visible: dlg.isOn(index)
                                   text: "✓"; color: "#04222a"; font.pixelSize: 13; font.weight: Font.Bold } }
                        Text { text: modelData; color: Theme.ink; font.pixelSize: 12
                               Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true; Layout.leftMargin: 16; Layout.rightMargin: 16
            Layout.bottomMargin: 14; spacing: 10
            Text { text: dlg.allOn() ? "Alla punkter bekräftade" : "Kryssa alla punkter"
                   color: dlg.allOn() ? Theme.teal : Theme.amber
                   font.family: Theme.mono; font.pixelSize: 10; Layout.fillWidth: true }
            Btn { text: "Avbryt"; onClicked: dlg.close() }
            Btn {
                text: "ARMA LASRAR"; danger: true; primary: dlg.allOn()
                enabled: dlg.allOn(); opacity: enabled ? 1 : 0.4
                onClicked: { dlg.armed(); dlg.close() }
            }
        }
    }
}
