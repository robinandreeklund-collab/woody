import QtQuick
import QtQuick.Layouts

RowLayout {
    spacing: 12

    // ---- riggens geometri (sanningskälla) ----
    Card {
        Layout.fillWidth: true; Layout.fillHeight: true
        title: "RIGGENS GEOMETRI"; chip: "= head-mech.svg"; chipColor: Theme.teal
        Flickable {
            anchors.fill: parent; contentHeight: gcol.height; clip: true
            ColumnLayout {
                id: gcol; width: parent.width; spacing: 0
                Repeater {
                    model: [
                        ["Brädans längd (X)", ctrl.rig.len.toFixed(0) + " mm"],
                        ["Brädans bredd (Y)", ctrl.rig.width.toFixed(0) + " mm"],
                        ["Brädans tjocklek (Z)", ctrl.rig.thick.toFixed(0) + " mm"],
                        ["Arbetsavstånd WD", ctrl.rig.wd.toFixed(0) + " mm"],
                        ["Kamera-arm (fr. lod)", ctrl.rig.camArm.toFixed(0) + "°"],
                        ["Laser-arm (fr. lod)", ctrl.rig.laserArm.toFixed(0) + "°"],
                        ["Trianguleringsvinkel θ", ctrl.rig.theta.toFixed(0) + "°"],
                        ["Obliquitet", ctrl.rig.oblique.toFixed(0) + "°"],
                        ["Kamerahöjd", ctrl.rig.camHeight + " mm"],
                        ["Kamera-offset", ctrl.rig.camOffset + " mm"],
                        ["Laserhöjd", ctrl.rig.laserHeight + " mm"],
                        ["Laser-offset", ctrl.rig.laserOffset + " mm"],
                        ["Baslinje kamera↔laser", ctrl.rig.baseline + " mm"],
                        ["Ytkamera WD (centrum)", ctrl.rig.surfWd.toFixed(0) + " mm"],
                        ["Ytupplösning", ctrl.rig.surfMmPx.toFixed(3) + " mm/px"],
                        ["Profil lateral uppl.", ctrl.rig.profLatMmPx.toFixed(3) + " mm/px"],
                    ]
                    delegate: Rectangle {
                        Layout.fillWidth: true; height: 32
                        color: index % 2 ? "transparent" : Qt.rgba(1,1,1,0.018)
                        RowLayout { anchors.fill: parent; anchors.leftMargin: 4; anchors.rightMargin: 4
                            Text { text: modelData[0]; color: Theme.ink2; font.pixelSize: 12 }
                            Item { Layout.fillWidth: true }
                            Text { text: modelData[1]; color: Theme.cyan; font.family: Theme.mono; font.pixelSize: 12; font.weight: Font.DemiBold } }
                    }
                }
            }
        }
    }

    // ---- kalibreringsflöden (Fas 3) ----
    Card {
        Layout.preferredWidth: 480; Layout.fillHeight: true
        title: "KALIBRERINGSFLÖDEN"; chip: "Fas 3"; chipColor: Theme.amber
        ColumnLayout {
            anchors.fill: parent; spacing: 10
            Repeater {
                model: [
                    ["Kamera-intrinsics", "Schackbräde/charuco per profilkamera → linsdistorsion + fokallängd.", "Ej kalibrerad"],
                    ["Trianguleringsplan", "Mät känd referenstrappa → laser/kamera-plan → mm/px i Z.", "Ej kalibrerad"],
                    ["Nollplan (bandbaslinje B(x))", "Tomt band → spara band-profilen som noll. Tjocklek = topp − B(x). Se docs/zero-reference.md.", "Ej satt"],
                    ["Auto-omnollning", "Uppdatera B(x) i varje brädmellanrum (glidande medel) → kompenserar drift/slitage.", "Inaktiv"],
                    ["Referensskenor", "Fasta datum-skenor vid linjens ändar → absolut noll + nivå i varje bild.", "Ej monterade"],
                    ["Punktlaser-nollning", "Nolla LR400 mot tomt band (D0) → absolut tjocklek-ankare.", "Ej kalibrerad"],
                    ["Ytkamera-vitbalans", "Vitreferens under LED → färg/skin-korrektion.", "Ej kalibrerad"],
                    ["Matnings-encoder", "Mät känd sträcka → mm/puls för positionslås.", "Ej kalibrerad"],
                ]
                delegate: Rectangle {
                    Layout.fillWidth: true; radius: 10; color: Theme.panel2; border.color: Theme.line
                    implicitHeight: ic.height + 20
                    ColumnLayout {
                        id: ic; x: 12; y: 10; width: parent.width - 24; spacing: 3
                        RowLayout { Layout.fillWidth: true
                            Text { text: modelData[0]; color: Theme.ink; font.pixelSize: 13; font.weight: Font.DemiBold }
                            Item { Layout.fillWidth: true }
                            Rectangle { radius: 6; color: Qt.rgba(1,0.7,0.24,0.12); border.color: Qt.rgba(1,0.7,0.24,0.3)
                                implicitWidth: stt.width+12; implicitHeight: 18
                                Text { id: stt; anchors.centerIn: parent; text: modelData[2]; color: Theme.amber; font.family: Theme.mono; font.pixelSize: 9 } }
                        }
                        Text { text: modelData[1]; color: Theme.ink3; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    }
                }
            }
            Item { Layout.fillHeight: true }
            Text { text: "Kalibreringsrutinerna aktiveras i Fas 3/4 tillsammans med verklig hårdvara. Värdena lagras i config och används av behandlingspipelinen."
                   color: Theme.ink3; font.pixelSize: 10; font.italic: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        }
    }
}
