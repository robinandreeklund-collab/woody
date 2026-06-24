import QtQuick
import QtQuick3D
import QtQuick3D.Helpers

// ÄKTA renderad kameravy: scenen sedd från en av riggens FASTA kameror, i rätt
// pose + lins-FOV. Brädan matas igenom (samma boardFeedZ-logik som tvillingen),
// så vyn bygger sig i realtid precis som den riktiga kameran skulle se.
//  camKind 0 = RÖD profilkamera (mono, BP650 → ser bara RÖD stripe)
//          1 = GRÖN profilkamera (mono, BP525 → ser bara GRÖN stripe)
//          2 = linjekamera (färg, rakt ned, laser UTANFÖR FOV)
// Profilkamerorna sitter 25° från lod (kamera-arm), lasern 50° → triangulering.
Item {
    id: root
    anchors.fill: parent
    property int camKind: 0
    readonly property bool isLine: camKind === 2
    readonly property bool mono: !isLine
    readonly property real sign: camKind === 0 ? 1 : -1     // +Z = RÖD-huvud, −Z = GRÖN
    // 12 mm-lins (MV-CS050) ≈ 38° över 500 mm-linjen @ WD; 20 mm-lins (linje) snävare
    property real fov: isLine ? 42 : 38

    // levande tillstånd (säkra guards för smoke utan ctrl)
    property bool scanActive: (typeof ctrl !== 'undefined' && ctrl) ? ctrl.scanActive : false
    property real feedPos:    (typeof ctrl !== 'undefined' && ctrl) ? ctrl.feedPos : 0
    property real scanProg:   (typeof ctrl !== 'undefined' && ctrl) ? ctrl.scanProgress : 0
    property string texSource:(typeof ctrl !== 'undefined' && ctrl) ? ("image://live/surface/" + ctrl.surfaceRev) : ""
    readonly property bool hasBoard: scanProg > 0.0001 || scanActive
    readonly property real feedFrac: feedPos / 75
    readonly property real feedZ: RigCal.feedZ(feedFrac)
    readonly property vector3d hit: RigCal.laserHit(sign, feedZ)

    // kamerans pose i scen-koordinater (samma frame som tvillingen)
    readonly property vector3d camPos: isLine
        ? Qt.vector3d(RigCal.boardX, RigCal.boardTopY + RigCal.camH, RigCal.lineCamZ)
        : Qt.vector3d(RigCal.boardX, RigCal.boardTopY + RigCal.camH, RigCal.laserZ + sign * RigCal.camZoff)
    readonly property vector3d camTgt: isLine
        ? Qt.vector3d(RigCal.boardX, RigCal.boardTopY, RigCal.lineCamZ)
        : Qt.vector3d(RigCal.boardX, RigCal.boardTopY, RigCal.laserZ)

    onCamPosChanged: relook()
    onCamTgtChanged: relook()
    function relook() {
        if (root.isLine) cam.eulerRotation = Qt.vector3d(-90, 0, 0)   // rakt ned
        else cam.lookAt(root.camTgt)
    }

    View3D {
        id: v3d
        anchors.fill: parent
        camera: cam
        environment: ExtendedSceneEnvironment {
            clearColor: "#05080c"; backgroundMode: SceneEnvironment.Color
            antialiasingMode: SceneEnvironment.MSAA; antialiasingQuality: SceneEnvironment.High
            tonemapMode: SceneEnvironment.TonemapModeFilmic
            // MONO: profilkamerorna är gråskale-sensorer → nollställ mättnaden
            colorAdjustmentsEnabled: root.mono
            adjustmentSaturation: root.mono ? 0.0 : 1.0
            // glow så laserstripen "lyser" mot den mörka (bandpass) bakgrunden
            glowEnabled: !root.isLine
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
        // dämpat ljus: profilkameran ser mest sin laserstripe (bandpass), linjekameran
        // ser belyst yta (vit-LED). Två riktade ljus räcker för läsbar volym.
        DirectionalLight { eulerRotation.x: -55; eulerRotation.y: -25
            brightness: root.isLine ? 2.4 : 0.9 }
        DirectionalLight { eulerRotation.x: -20; eulerRotation.y: 140
            brightness: root.isLine ? 1.0 : 0.4 }
        Texture { id: surfTex; source: root.texSource }

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
            materials: PrincipledMaterial {
                baseColor: "#c9a468"
                baseColorMap: (root.isLine && root.texSource !== "") ? surfTex : null
                roughness: 0.78; metalness: 0.0
            }
        }

        // ÄKTA laserstripe där den träffar ytan (band → kant → ovansida).
        // Endast den EGNA lasern syns (bandpass): RÖD-kameran ser RÖD, GRÖN ser GRÖN.
        // Linjekameran ser ingen laser (utanför FOV).
        Model {
            visible: !root.isLine && root.scanActive && root.hasBoard
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
