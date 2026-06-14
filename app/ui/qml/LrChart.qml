import QtQuick

// LR400-spår: 3 punktlasrar (V/C/H) ger absolut tjocklek vid varje matningsrad →
// bygger tre tjockleksprofiler över brädans 75 mm-passage. track = [[[feed,thk],…]×3].
Item {
    id: root
    property var track: []
    property var lrx: []                 // [x_mm ×3] (laserns längdposition)
    property real nominal: 20
    property real widthMm: 75
    property var cols: ["#27d3e0", "#34e6b5", "#9a7bff"]
    onTrackChanged: cv.requestPaint()
    onWidthChanged: cv.requestPaint()

    Canvas {
        id: cv; anchors.fill: parent; antialiasing: true
        onPaint: {
            var c = getContext("2d"); c.reset()
            var w = width, h = height, padL = 30, padR = 6, padT = 8, padB = 16
            var gw = w - padL - padR, gh = h - padT - padB
            var t = root.track || []
            // tjockleksintervall (auto, runt nominellt)
            var mn = root.nominal - 4, mx = root.nominal + 4
            for (var s = 0; s < t.length; s++) for (var k = 0; k < (t[s]||[]).length; k++) {
                var v = t[s][k][1]; if (v < mn) mn = v - 1; if (v > mx) mx = v + 1
            }
            function X(f) { return padL + (f / root.widthMm) * gw }
            function Y(v) { return padT + gh - ((v - mn) / (mx - mn)) * gh }
            // rutnät + axlar
            c.strokeStyle = "rgba(120,140,165,0.14)"; c.lineWidth = 1; c.fillStyle = "#8595a8"
            c.font = "8px monospace"; c.textAlign = "right"
            for (var gy = 0; gy <= 4; gy++) {
                var vv = mn + (mx - mn) * gy / 4, yy = Y(vv)
                c.beginPath(); c.moveTo(padL, yy); c.lineTo(w - padR, yy); c.stroke()
                c.fillText(vv.toFixed(0), padL - 3, yy + 3)
            }
            // nominell tjocklek
            c.strokeStyle = "rgba(120,140,165,0.4)"; c.setLineDash([4, 3])
            c.beginPath(); c.moveTo(padL, Y(root.nominal)); c.lineTo(w - padR, Y(root.nominal)); c.stroke(); c.setLineDash([])
            // tre spår
            for (var si = 0; si < t.length; si++) {
                var pts = t[si] || []; if (pts.length < 1) continue
                c.strokeStyle = root.cols[si % root.cols.length]; c.lineWidth = 1.6; c.beginPath()
                for (var i = 0; i < pts.length; i++) {
                    var px = X(pts[i][0]), py = Y(pts[i][1])
                    i ? c.lineTo(px, py) : c.moveTo(px, py)
                }
                c.stroke()
                // sista punkten markerad
                var last = pts[pts.length - 1]
                c.fillStyle = root.cols[si % root.cols.length]
                c.beginPath(); c.arc(X(last[0]), Y(last[1]), 2.4, 0, 7); c.fill()
            }
            // x-etikett
            c.fillStyle = "#8595a8"; c.textAlign = "center"
            c.fillText("matning 0–" + root.widthMm.toFixed(0) + " mm (bredd)", padL + gw / 2, h - 4)
        }
    }
    // legend
    Row {
        anchors.top: parent.top; anchors.right: parent.right; anchors.rightMargin: 6; spacing: 8
        Repeater {
            model: [["V", root.cols[0]], ["C", root.cols[1]], ["H", root.cols[2]]]
            delegate: Row { spacing: 3
                Rectangle { width: 8; height: 3; radius: 1; color: modelData[1]; anchors.verticalCenter: parent.verticalCenter }
                Text { text: "LR-" + modelData[0]; color: Theme.ink3; font.family: Theme.mono; font.pixelSize: 8 } }
        }
    }
}
