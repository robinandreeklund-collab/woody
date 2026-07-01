pragma Singleton
import QtQuick

// Ljust, kommersiellt designsystem ("SaaS"). Färgnamnen är BAKÅTKOMPATIBLA
// (ink/panel/cyan/teal … finns kvar) men värdena är ljus-tema. Nya tokens:
// semantiska roller (ok/warn/err/info), spacing-skala, radier, elevation, accent.
QtObject {
    // ---- ytor / bakgrund -------------------------------------------------
    readonly property color bg:     "#eef2f7"   // sid-bakgrund (ljus blågrå)
    readonly property color bg2:    "#f7f9fc"   // gradient-topp
    readonly property color panel:  "#ffffff"   // kort
    readonly property color panel2: "#f1f5f9"   // inset/sekundär yta
    readonly property color line:   "#e3e8ef"   // hårfina kanter
    readonly property color line2:  "#cfd8e3"   // tydligare kant

    // ---- text ------------------------------------------------------------
    readonly property color ink:    "#0f1b2d"   // primär (slate-900)
    readonly property color ink2:   "#48586b"   // sekundär
    readonly property color ink3:   "#8595a8"   // svag/etiketter

    // ---- accenter (vivida — funkar som fyllning med mörk/vit text) -------
    readonly property color accent: "#2563eb"   // primär handling (blå)
    readonly property color cyan:   "#0891b2"
    readonly property color teal:   "#0d9488"
    readonly property color grn:    "#16a34a"
    readonly property color red:    "#e11d48"
    readonly property color amber:  "#d97706"
    readonly property color violet: "#7c3aed"
    readonly property color blue:   "#2563eb"

    // ---- semantiska roller (status) -------------------------------------
    readonly property color ok:     "#16a34a"
    readonly property color warn:   "#d97706"
    readonly property color err:    "#e11d48"
    readonly property color info:   "#0ea5e9"
    readonly property color accentInk: "#ffffff"  // text ovanpå solid accent

    // grad-färger A/B/C/D (konsekventa i hela GUI:t)
    readonly property color gradeA: "#16a34a"
    readonly property color gradeB: "#0891b2"
    readonly property color gradeC: "#d97706"
    readonly property color gradeD: "#e11d48"
    function gradeColor(cls) {
        return cls === "A" ? gradeA : cls === "B" ? gradeB
             : cls === "C" ? gradeC : cls === "D" ? gradeD : ink3
    }

    // ---- elevation (mjuk skugga) ----------------------------------------
    readonly property color shadow: "#1b2b44"    // används med låg alpha

    // ---- spacing-skala / radier -----------------------------------------
    readonly property int sp1: 4
    readonly property int sp2: 8
    readonly property int sp3: 12
    readonly property int sp4: 16
    readonly property int sp5: 24
    readonly property int rSm: 8
    readonly property int rMd: 12
    readonly property int rLg: 16

    // ---- typografi -------------------------------------------------------
    readonly property string sans: "Inter, Segoe UI, Roboto, DejaVu Sans, sans-serif"
    readonly property string mono: "JetBrains Mono, DejaVu Sans Mono, monospace"

    // hjälp: en accentfärg som mjuk tintad bakgrund (pills/badges)
    function tint(c, a) { return Qt.rgba(c.r, c.g, c.b, a === undefined ? 0.12 : a) }
}
