pragma Singleton
import QtQuick

// EN sanningskälla för riggens kalibrerade geometri (scen-koordinater, mm).
// Delas av tvillingen (Board3DGpu, turntable) OCH de äkta kameravyern (CamView3D)
// så att en kalibrering i GUI:t omedelbart syns i båda. Y = upp, X = brädans längd,
// Z = matningsled. Allt förankrat mot anhållet (din korrekta brädladdnings-Z).
QtObject {
    id: cal

    // ---- KALIBRERING (skrivs av tvillingens nudge-knappar) ----------------
    property real anhallZ: 360            // anhållets Z (brädladdning)
    property real feedDir: -1             // matningsriktning (flippas i GUI)
    property real boardX:  22             // brädans X-centrum (bredd-led)
    property real boardY:  -391           // brädans Y-centrum (höjd) → ovansida = boardTopY
    property real boardThick: 20          // brädtjocklek (mm) — styr parallax

    // ---- LÅST GEOMETRI (head-mech.svg) ------------------------------------
    readonly property real boardTopY: -381        // brädans ovansida på bandet
    readonly property real convergeAboveBelt: 35  // laserkonvergens ö. bandet
    readonly property real laserArmDeg: 50         // laser-arm fr lod
    readonly property real camArmDeg: 25           // profilkamera-arm fr lod
    readonly property real laserFanDeg: 45         // MZLaser Powell-lins fan-vinkel
    readonly property real laserH: 489             // laserhöjd ö. bräda = WD·cos50
    readonly property real laserZoff: 582          // = WD·sin50
    readonly property real laserBeam: 760          // WD (slant)
    readonly property real camH: 689               // kamerahöjd = WD·cos25
    readonly property real camZoff: 321            // = WD·sin25
    readonly property real camBeam: 760

    // rig-frame → scen-frame (CAD-bbox centrerad + förskjuten mot bandet)
    readonly property vector3d rigOffset: Qt.vector3d(-277, -469, 323)

    // ---- HÄRLETT (matningskedja: anhåll → LR400 → laser → linjekamera) -----
    readonly property real lr400Z:   anhallZ + feedDir * 129.404
    readonly property real laserZ:    anhallZ + feedDir * 299.404   // laser-centrum på bandet
    readonly property real lineCamZ:  anhallZ + feedDir * 339.404
    readonly property real frontZ:    anhallZ + feedDir * (339.404 + 50 + 37.5)
    readonly property real beltY:     boardTopY - boardThick
    readonly property real convY:     beltY + convergeAboveBelt
    readonly property real arm:       laserArmDeg * Math.PI / 180
    readonly property real fanBaseW:  2 * laserBeam * Math.tan(laserFanDeg / 2 * Math.PI / 180)
    // brädan vilar med KANTEN mot anhållet, kroppen 37,5 mm in i riggen
    readonly property real boardRestZ: anhallZ + feedDir * 37.5

    // brädans matnings-Z för en given matningsandel (feedFrac 0..1)
    function feedZ(feedFrac) {
        return boardRestZ + feedFrac * (frontZ - boardRestZ)
    }

    // var laserplanet (sign +1 RÖD / −1 GRÖN) träffar ytan för brädan @ fz (matnings-Z).
    // Returnerar [Y, Z, påKant]: band → lodrät tjocklecksida → ovansida. Ocklusion:
    // varje huvud ser bara sin närkant. Samma matte som tvillingen.
    function laserHit(sign, fz) {
        var tA = Math.tan(arm)
        var lz = laserZ, cY = convY, bt = boardTopY, bl = beltY
        var lo = fz - 37.5, hi = fz + 37.5
        var topHitZ = lz + sign * (bt - cY) * tA           // plan @ brädtopp-höjd
        if (topHitZ >= lo && topHitZ <= hi)
            return Qt.vector3d(bt, topHitZ, 0)             // på OVANSIDAN
        var nearEdgeZ = fz + sign * 37.5                   // kanten detta huvud ser
        var yFace = cY + sign * (nearEdgeZ - lz) / tA      // plan @ kantens Z
        if (yFace > bl && yFace < bt)
            return Qt.vector3d(yFace, nearEdgeZ, 1)        // på LODRÄT TJOCKLECKSKANT
        return Qt.vector3d(bl, lz + sign * (bl - cY) * tA, 0)  // på BANDET
    }
}
