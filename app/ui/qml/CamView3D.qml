import QtQuick
import QtQuick3D
import QtQuick3D.Helpers

// ÄKTA renderad PROFILKAMERA-vy (area-scan MV-CS050, mono). Scenen sedd från
// kamerans FASTA pose + lins-FOV. Profilkameran sitter på kamera-armen 25° från
// lod (WD 760, ±321 mm i matningsled), GRÖN på −Z-sidan, RÖD på +Z. Via bandpass
// (BP650/BP525) ser den BARA sin egen laserstripe där den träffar ytan
// (band → lodrät tjocklecksida → ovansida). Brädan matas genom FOV → bilden byggs
// i realtid precis som den riktiga kameran skulle se den.
//   camKind 0 = RÖD (BP650 · +Z-huvud) · 1 = GRÖN (BP525 · −Z-huvud)
Item {
    id: root
    anchors.fill: parent
    property int camKind: 0
    readonly property real sign: camKind === 0 ? 1 : -1     // +Z = RÖD-huvud, −Z = GRÖN
    property real fov: 38                                    // 12 mm-lins ≈ 38° över 500 mm @ WD

    // levande tillstånd (säkra guards för smoke utan ctrl)
    property bool scanActive: (typeof ctrl !== 'undefined' && ctrl) ? ctrl.scanActive : false
    property real feedPos:    (typeof ctrl !== 'undefined' && ctrl) ? ctrl.feedPos : 0
    property real scanProg:   (typeof ctrl !== 'undefined' && ctrl) ? ctrl.scanProgress : 0
    readonly property bool hasBoard: scanProg > 0.0001 || scanActive
    readonly property real feedFrac: feedPos / 75
    readonly property real feedZ: RigCal.feedZ(feedFrac)
    readonly property vector3d hit: RigCal.laserHit(sign, feedZ)

    // kamerans pose i scen-koordinater (samma frame som tvillingen)
    readonly property vector3d camPos:
        Qt.vector3d(RigCal.boardX, RigCal.boardTopY + RigCal.camH, RigCal.laserZ + sign * RigCal.camZoff)
    readonly property vector3d camTgt:
        Qt.vector3d(RigCal.boardX, RigCal.boardTopY, RigCal.laserZ)

    onCamPosChanged: relook()
    onCamTgtChanged: relook()
    function relook() { cam.lookAt(root.camTgt) }

    View3D {
        id: v3d
        anchors.fill: parent
        camera: cam
        environment: ExtendedSceneEnvironment {
            clearColor: "#05080c"; backgroundMode: SceneEnvironment.Color
            antialiasingMode: SceneEnvironment.MSAA; antialiasingQuality: SceneEnvironment.High
            tonemapMode: SceneEnvironment.TonemapModeFilmic
            // MONO: profilkameran är en gråskale-sensor → nollställ mättnaden
            colorAdjustmentsEnabled: true; adjustmentSaturation: 0.0
            // glow så laserstripen "lyser" mot den mörka (bandpass) bakgrunden
            glowEnabled: true
            glowStrength: 0.5; glowIntensity: 0.9; glowBloom: 0.0
            glowHDRMinimumValue: 2.0; glowHDRMaximumValue: 9.0; glowHDRScale: 2.0
            glowQualityHigh: true
        }
        PerspectiveCamera {
            id: cam
            position: root.camPos
            fieldOfView: root.fov
            clipNear: 1; clipFar: 8000
        }
        // dämpat ljus: profilkameran ser mest sin laserstripe (bandpass blockerar omgivning)
        DirectionalLight { eulerRotation.x: -55; eulerRotation.y: -25; brightness: 0.9 }
        DirectionalLight { eulerRotation.x: -20; eulerRotation.y: 140; brightness: 0.4 }

        // transportband (mörk yta) — referens under brädan
        Model {
            source: "#Rectangle"; eulerRotation.x: -90
            position: Qt.vector3d(RigCal.boardX, RigCal.beltY, RigCal.laserZ)
            scale: Qt.vector3d(12, 12, 1)
            materials: PrincipledMaterial { baseColor: "#12161c"; roughness: 0.95; metalness: 0.0 }
        }

        // BRÄDAN (500×tjock×75) — matas genom kamerans FOV (boardFeedZ)
        Model {
            visible: root.hasBoard
            source: "#Cube"
            position: Qt.vector3d(RigCal.boardX, RigCal.boardY, root.feedZ)
            scale: Qt.vector3d(5.0, RigCal.boardThick / 100, 0.75)
            materials: PrincipledMaterial { baseColor: "#c9a468"; roughness: 0.78; metalness: 0.0 }
        }

        // ÄKTA laserstripe där den träffar ytan (band → lodrät kant → ovansida).
        // Endast den EGNA lasern syns (bandpass): RÖD-kameran ser RÖD, GRÖN ser GRÖN.
        Model {
            visible: root.scanActive && root.hasBoard
            source: "#Cube"; scale: Qt.vector3d(5.0, 0.05, 0.05)
            position: Qt.vector3d(RigCal.boardX, root.hit.x, root.hit.y)
            materials: PrincipledMaterial {
                baseColor: root.camKind === 0 ? "#1a0203" : "#021a08"
                emissiveFactor: root.camKind === 0
                    ? (root.hit.z > 0.5 ? Qt.vector3d(5.2, 0.25, 0.3) : Qt.vector3d(3.0, 0.14, 0.16))
                    : (root.hit.z > 0.5 ? Qt.vector3d(0.3, 5.2, 0.8) : Qt.vector3d(0.2, 3.0, 0.55))
            }
        }
    }

    Component.onCompleted: relook()

    // overlay: väntar på skanning
    Text {
        anchors.centerIn: parent; visible: !root.hasBoard
        text: "väntar på skanning…"; color: Theme.ink3; font.pixelSize: 11; font.italic: true
    }
}
