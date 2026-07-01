import QtQuick

// Grad-fördelnings-donut (A/B/C/D) med ett centrumvärde (t.ex. utbyte-%).
// dist = { A: n, B: n, C: n, D: n }. Ritas på Canvas → inga extra moduler.
Item {
    id: root
    property var dist: ({})
    property string centerValue: ""
    property string centerLabel: ""
    property real thickness: 0.26          // andel av radien
    implicitWidth: 150; implicitHeight: 150

    readonly property var _order: ["A", "B", "C", "D"]
    function _total() {
        var t = 0; for (var i = 0; i < _order.length; i++) t += (dist[_order[i]] || 0); return t
    }
    onDistChanged: cv.requestPaint()

    Canvas {
        id: cv; anchors.fill: parent; antialiasing: true
        onPaint: {
            var ctx = getContext("2d"); ctx.reset()
            var cx = width / 2, cy = height / 2
            var r = Math.min(width, height) / 2 - 4
            var lw = r * root.thickness
            var total = root._total()
            // spårring
            ctx.beginPath(); ctx.arc(cx, cy, r - lw / 2, 0, Math.PI * 2)
            ctx.lineWidth = lw; ctx.strokeStyle = Qt.rgba(0, 0, 0, 0.06); ctx.stroke()
            if (total <= 0) return
            var a0 = -Math.PI / 2
            for (var i = 0; i < root._order.length; i++) {
                var n = root.dist[root._order[i]] || 0
                if (n <= 0) continue
                var a1 = a0 + (n / total) * Math.PI * 2
                ctx.beginPath(); ctx.arc(cx, cy, r - lw / 2, a0 + 0.012, a1 - 0.012)
                ctx.lineWidth = lw; ctx.lineCap = "butt"
                ctx.strokeStyle = Theme.gradeColor(root._order[i]); ctx.stroke()
                a0 = a1
            }
        }
    }
    Column {
        anchors.centerIn: parent; spacing: 0
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: root.centerValue
               color: Theme.ink; font.family: Theme.sans; font.pixelSize: Math.max(16, root.height * 0.20)
               font.weight: Font.Bold }
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: root.centerLabel
               color: Theme.ink3; font.family: Theme.sans; font.pixelSize: 9; font.weight: Font.DemiBold
               font.letterSpacing: 0.6 }
    }
}
