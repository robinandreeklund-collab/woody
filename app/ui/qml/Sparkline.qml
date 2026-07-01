import QtQuick

// Liten trend-sparkline (Canvas). values = array av tal. Fyllning under linjen.
Item {
    id: root
    property var values: []
    property color stroke: Theme.accent
    property bool fill: true
    implicitWidth: 120; implicitHeight: 36
    onValuesChanged: cv.requestPaint()
    onWidthChanged: cv.requestPaint()

    Canvas {
        id: cv; anchors.fill: parent; antialiasing: true
        onPaint: {
            var ctx = getContext("2d"); ctx.reset()
            var v = root.values || []
            if (v.length < 2) return
            var mn = Math.min.apply(null, v), mx = Math.max.apply(null, v)
            var span = (mx - mn) || 1
            var pad = 2, w = width - pad * 2, h = height - pad * 2
            function px(i) { return pad + (i / (v.length - 1)) * w }
            function py(val) { return pad + h - ((val - mn) / span) * h }
            if (root.fill) {
                ctx.beginPath(); ctx.moveTo(px(0), height - pad)
                for (var i = 0; i < v.length; i++) ctx.lineTo(px(i), py(v[i]))
                ctx.lineTo(px(v.length - 1), height - pad); ctx.closePath()
                ctx.fillStyle = Qt.rgba(root.stroke.r, root.stroke.g, root.stroke.b, 0.12); ctx.fill()
            }
            ctx.beginPath(); ctx.moveTo(px(0), py(v[0]))
            for (var j = 1; j < v.length; j++) ctx.lineTo(px(j), py(v[j]))
            ctx.lineWidth = 2; ctx.lineJoin = "round"; ctx.strokeStyle = root.stroke; ctx.stroke()
            // sista punkten markerad
            ctx.beginPath(); ctx.arc(px(v.length - 1), py(v[v.length - 1]), 2.6, 0, Math.PI * 2)
            ctx.fillStyle = root.stroke; ctx.fill()
        }
    }
}
