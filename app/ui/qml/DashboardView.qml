import QtQuick
import QtQuick.Layouts

RowLayout {
    spacing: 12

    // ===================== VÄNSTER ==========================================
    ColumnLayout {
        Layout.fillWidth: true; Layout.fillHeight: true
        Layout.preferredWidth: 1000; Layout.minimumWidth: 520
        spacing: 12

        // ---- topp: ytkamera + höjdkarta ----
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12

            Card {
                Layout.fillWidth: true; Layout.fillHeight: true
                title: "YTKAMERA · 4K FÄRG-RADSKANNER"; chipColor: Theme.teal
                chip: "Huateng · GigE · " + ctrl.rig.len.toFixed(0) + "×" + ctrl.rig.width.toFixed(0) + " mm"
                BoardImage { kind: "surface"; bottomLabel: ctrl.rig.len.toFixed(0) + " mm (längd, X)" }
            }
            Card {
                Layout.preferredWidth: 300; Layout.fillHeight: true
                title: "HÖJDKARTA"; chip: "Z " + ctrl.rig.thick.toFixed(0) + " mm ± skevhet"
                BoardImage { kind: "height"; bottomLabel: "höjd-/djupkanal" }
            }
        }

        // ---- mitten: tvärsnitt + profilstripe ----
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: false; Layout.preferredHeight: 210; spacing: 12

            Card {
                Layout.fillWidth: true; Layout.fillHeight: true
                title: "LÄNGSPROFIL · LIVE Z(x) längs 500 mm"; chip: "θ " + ctrl.rig.theta.toFixed(0) + "° · RÖD+GRÖN"
                Canvas {
                    id: crossCv; anchors.fill: parent
                    Connections { target: ctrl; function onStateChanged() { crossCv.requestPaint() } }
                    onPaint: {
                        var c = getContext("2d"); c.reset();
                        var w = width, h = height, m = 34, gx = m, gy = 10, gw = w - m - 12, gh = h - 26;
                        var BT = ctrl.rig.thick, lo = BT - 15, hi = BT + 15;
                        c.strokeStyle = "#16222f"; c.lineWidth = 1;
                        for (var i=0;i<=5;i++){ var yy=gy+gh*i/5; c.beginPath(); c.moveTo(gx,yy); c.lineTo(gx+gw,yy); c.stroke(); }
                        c.fillStyle = "#3a4d62"; c.font = "9px monospace"; c.textAlign = "right";
                        c.fillText(hi.toFixed(0),gx-4,gy+6); c.fillText(BT.toFixed(0),gx-4,gy+gh/2+3); c.fillText(lo.toFixed(0),gx-4,gy+gh-2);
                        var zp = ctrl.zProfile;
                        if (!zp || zp.length < 2) { c.fillStyle="#3a4d62"; c.textAlign="center"; c.fillText("ingen aktiv profil",gx+gw/2,gy+gh/2); return; }
                        function Y(z){ return gy + gh*(1-((z-lo)/30)); }
                        c.beginPath(); c.moveTo(gx,gy+gh);
                        for (var k=0;k<zp.length;k++) c.lineTo(gx+gw*k/(zp.length-1), Y(zp[k]));
                        c.lineTo(gx+gw,gy+gh); c.closePath();
                        var g=c.createLinearGradient(0,gy,0,gy+gh); g.addColorStop(0,"rgba(39,211,224,0.22)"); g.addColorStop(1,"rgba(39,211,224,0)");
                        c.fillStyle=g; c.fill();
                        c.beginPath();
                        for (var j=0;j<zp.length;j++){ var X=gx+gw*j/(zp.length-1), yv=Y(zp[j]); j?c.lineTo(X,yv):c.moveTo(X,yv); }
                        c.strokeStyle=Theme.cyan; c.lineWidth=2; c.shadowColor=Theme.cyan; c.shadowBlur=6; c.stroke(); c.shadowBlur=0;
                        c.setLineDash([4,4]); c.strokeStyle="rgba(159,178,198,0.3)"; c.lineWidth=1;
                        c.beginPath(); c.moveTo(gx,Y(BT)); c.lineTo(gx+gw,Y(BT)); c.stroke(); c.setLineDash([]);
                        c.fillStyle="#61768c"; c.textAlign="center"; c.fillText("x längs bräda (0–"+ctrl.rig.len.toFixed(0)+" mm)",gx+gw/2,h-4);
                    }
                }
            }
            Card {
                Layout.preferredWidth: 360; Layout.fillHeight: true
                title: "PROFILKAMEROR · RÅ LASERSTRIPE"; chip: "MV-CS050 mono ×2"
                RowLayout {
                    anchors.fill: parent; spacing: 8
                    Repeater {
                        model: [{c:"#ff4d5e",bg:"#1a0608",nm:"RÖD 650 · vänster",side:0},
                                {c:"#52ff7a",bg:"#04140a",nm:"GRÖN 520 · höger",side:1}]
                        delegate: Canvas {
                            id: stripeCanvas
                            Layout.fillWidth: true; Layout.fillHeight: true
                            property var d: modelData
                            Connections { target: ctrl; function onStateChanged() { stripeCanvas.requestPaint() } }
                            onPaint: {
                                var c=getContext("2d"); c.reset();
                                c.fillStyle=d.bg; c.fillRect(0,0,width,height);
                                c.strokeStyle="#1d2a38"; c.strokeRect(0.5,0.5,width-1,height-1);
                                c.fillStyle="rgba(255,255,255,0.55)"; c.font="9px monospace"; c.textAlign="left"; c.fillText(d.nm,6,13);
                                var zp=ctrl.zProfile; if(!zp||zp.length<2) return;
                                // tvärsnitt som en oblik profilkamera ser det: band-baslinje,
                                // upphöjd platå (brädans ovansida) + vinklade sågkanter.
                                var baseline=height-12, g=(baseline-18)/Math.max(ctrl.rig.thick,1);
                                var gx=10, gw=width-20, n=zp.length;
                                function topY(i){ return baseline - zp[i]*g; }
                                // undersidan mäts EJ idag → svag streckad linje
                                c.strokeStyle="rgba(120,140,165,0.20)"; c.lineWidth=1; c.setLineDash([5,4]);
                                c.beginPath(); c.moveTo(gx,baseline); c.lineTo(gx+gw,baseline); c.stroke(); c.setLineDash([]);
                                // vinklade kant-fasetter (band → brädans ovansida)
                                c.lineWidth=2.0; c.strokeStyle=d.c; c.globalAlpha=d.side===0?1:0.4;
                                c.beginPath(); c.moveTo(gx,baseline); c.lineTo(gx,topY(0)); c.stroke();
                                c.globalAlpha=d.side===1?1:0.4;
                                c.beginPath(); c.moveTo(gx+gw,baseline); c.lineTo(gx+gw,topY(n-1)); c.stroke();
                                c.globalAlpha=1;
                                // ovansidan (platå) med relief — bortre halvan skuggas (oblik vy)
                                c.lineWidth=2.4; c.shadowColor=d.c; c.shadowBlur=6;
                                c.beginPath();
                                for(var i=0;i<n;i++){
                                    var fx=i/(n-1), px=gx+gw*fx, py=topY(i);
                                    i?c.lineTo(px,py):c.moveTo(px,py);
                                }
                                var grad=c.createLinearGradient(gx,0,gx+gw,0);
                                grad.addColorStop(0, d.side===0?d.c:"rgba(120,130,150,0.35)");
                                grad.addColorStop(1, d.side===1?d.c:"rgba(120,130,150,0.35)");
                                c.strokeStyle=grad; c.stroke(); c.shadowBlur=0;
                                c.fillStyle="rgba(255,255,255,0.28)"; c.font="8px monospace";
                                c.textAlign = d.side===0?"right":"left"; c.fillText("ocklusion", d.side===0?width-6:6, height-6);
                                c.textAlign="left"; c.fillStyle="rgba(255,255,255,0.22)"; c.fillText("underside · mäts ej", 8, baseline-3);
                            }
                        }
                    }
                }
            }
        }

        // ---- rigg ovanifrån (sensorlayout) — laserlinjen längs 500 mm ----
        Card {
            Layout.fillWidth: true; Layout.fillHeight: false; Layout.preferredHeight: 210
            title: "RIGG · OVANIFRÅN (sensorlayout)"
            chip: "laserlinje längs X · 500 mm · θ " + ctrl.rig.theta.toFixed(0) + "°"
            Canvas {
                id: rigCv; anchors.fill: parent
                Connections { target: ctrl; function onStateChanged() { rigCv.requestPaint() } }
                // Maskinvy: sensorerna är FASTA, brädan matas igenom. Ledande kanten
                // passerar LR400-ankaret (uppströms) FÖRST → 3 absolutmått, sedan laser/yta.
                onPaint: {
                    var c=getContext("2d"); c.reset();
                    var w=width, h=height, R=ctrl.rig;
                    var hpad=58, vpad=24;
                    var bx=hpad, bw=w-2*hpad;
                    var mmY=(h-2*vpad)/(R.width + R.lrLead + 70);    // px per mm i matningsled
                    var bhB=R.width*mmY;
                    var yLAS=h*0.60;                                 // FAST laserlinje + ytkamera
                    var yLR=yLAS - R.lrLead*mmY;                     // FAST LR-plan uppströms
                    var p=ctrl.scanProgress;
                    var yLead=yLAS + p*bhB;                          // ledande kant (nedströms)
                    var yTrail=yLead - bhB;                          // bakkant (uppströms)
                    // transportband vid längd-ändarna
                    c.fillStyle="#0c121a"; c.fillRect(bx-16, vpad, 12, h-2*vpad); c.fillRect(bx+bw+4, vpad, 12, h-2*vpad);
                    c.strokeStyle="#1b2735"; c.lineWidth=1;
                    for(var bb=vpad; bb<h-vpad; bb+=10){ c.beginPath(); c.moveTo(bx-16,bb); c.lineTo(bx-4,bb); c.moveTo(bx+bw+4,bb); c.lineTo(bx+bw+16,bb); c.stroke(); }
                    // BRÄDAN glider genom (klippt till zonen)
                    c.save(); c.beginPath(); c.rect(bx-2, vpad-2, bw+4, h-2*vpad+4); c.clip();
                    if(p>0){
                        c.fillStyle="#c9a468"; c.fillRect(bx, yTrail, bw, bhB);
                        c.strokeStyle="#7a5230"; c.lineWidth=1; c.strokeRect(bx, yTrail, bw, bhB);
                        if(yLead>yLAS){ c.fillStyle="rgba(39,211,224,0.07)"; c.fillRect(bx, yLAS, bw, Math.min(yLead,h-vpad)-yLAS); }
                    }
                    c.restore();
                    c.fillStyle="#3a4d62"; c.font="9px monospace"; c.textAlign="left"; c.fillText("matning ↓", bx+2, vpad+11);
                    // ---- FASTA sensorer ----
                    // LR400-ankarplan (uppströms — mäts FÖRST). Lyser när brädan är under det.
                    var lrOn = (p>0 && yLR<=yLead && yLR>=yTrail);
                    c.strokeStyle=Qt.rgba(0.15,0.83,0.88,lrOn?0.75:0.3); c.setLineDash([5,4]); c.lineWidth=1.4;
                    c.beginPath(); c.moveTo(bx,yLR); c.lineTo(bx+bw,yLR); c.stroke(); c.setLineDash([]);
                    var lp=ctrl.lrPositions;
                    for(var i=0;i<lp.length;i++){ var px=bx+bw*(lp[i]/R.len);
                        c.fillStyle=lrOn?Theme.cyan:Qt.rgba(0.15,0.83,0.88,0.35); c.beginPath(); c.arc(px,yLR,3.6,0,7); c.fill();
                        c.strokeStyle=Qt.rgba(0.15,0.83,0.88,0.4); c.beginPath(); c.arc(px,yLR,6.5,0,7); c.stroke(); }
                    c.fillStyle=Theme.cyan; c.font="8px monospace"; c.textAlign="left";
                    c.fillText("3× LR400 ankare · uppströms — mäts FÖRST (utanför FOV)", bx+2, yLR-7);
                    // FASTA huvuden + laserlinje + ytkamera
                    function head(off,col,nm,dir){ var hy=yLAS+off;
                        c.globalAlpha=0.15; c.fillStyle=col; c.beginPath();
                        c.moveTo((bx+bx+bw)/2,hy); c.lineTo(bx,yLAS); c.lineTo(bx+bw,yLAS); c.closePath(); c.fill(); c.globalAlpha=1;
                        c.fillStyle="#16212e"; c.strokeStyle=col; c.lineWidth=1.5;
                        c.fillRect((bx+bx+bw)/2-20,hy-8,40,16); c.strokeRect((bx+bx+bw)/2-20,hy-8,40,16);
                        c.fillStyle="#9fb2c6"; c.font="8px monospace"; c.textAlign="center"; c.fillText(nm,(bx+bx+bw)/2, dir<0?hy-11:hy+18); }
                    head(-36,Theme.red,"RÖD 650 (huvud A)",-1);
                    head(36,Theme.grn,"GRÖN 520 (huvud B)",1);
                    c.lineWidth=3; c.strokeStyle=Theme.red; c.shadowColor=Theme.red; c.shadowBlur=8;
                    c.beginPath(); c.moveTo(bx,yLAS-1.5); c.lineTo(bx+bw,yLAS-1.5); c.stroke();
                    c.strokeStyle=Theme.grn; c.shadowColor=Theme.grn; c.beginPath(); c.moveTo(bx,yLAS+1.5); c.lineTo(bx+bw,yLAS+1.5); c.stroke(); c.shadowBlur=0;
                    c.fillStyle="#16212e"; c.strokeStyle=Theme.blue; c.lineWidth=1.5;
                    c.fillRect((bx+bx+bw)/2-13, yLAS-7, 26, 14); c.strokeRect((bx+bx+bw)/2-13, yLAS-7, 26, 14);
                    // etiketter
                    c.fillStyle="#61768c"; c.font="9px monospace";
                    c.textAlign="left"; c.fillText("0", bx, h-8);
                    c.textAlign="right"; c.fillText(R.len.toFixed(0)+" mm (längd X — laserlinjen)", bx+bw, h-8);
                    c.fillStyle="#3a4d62"; c.textAlign="center"; c.fillText("sensorer FASTA — brädan matas igenom", (bx+bx+bw)/2, h-8);
                }
            }
        }
    }

    // ===================== HÖGER ============================================
    ColumnLayout {
        Layout.fillHeight: true; Layout.fillWidth: false
        Layout.preferredWidth: 372; Layout.minimumWidth: 344; Layout.maximumWidth: 430
        spacing: 12

        Card {
            Layout.fillWidth: true; Layout.preferredHeight: 196
            title: "PUNKTLASER · ABSOLUT TJOCKLEK"; chip: "3× LR400 · uppströms · RS-485"
            ColumnLayout {
                anchors.fill: parent; spacing: 8
                Repeater {
                    model: 3
                    delegate: Rectangle {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        radius: 10; color: Theme.panel2; border.color: Theme.line
                        property real val: ctrl.lrThickness[index] !== undefined ? ctrl.lrThickness[index] : ctrl.rig.thick
                        property real dev: val - ctrl.rig.thick
                        property color cc: Math.abs(dev)<1.2 ? Theme.teal : (Math.abs(dev)<3 ? Theme.amber : Theme.red)
                        RowLayout {
                            anchors.fill: parent; anchors.margins: 10; spacing: 12
                            ColumnLayout { spacing: 1; Layout.preferredWidth: 120
                                Text { text: ["LR-V","LR-C","LR-H"][index] + " · ch" + (index+1); color: Theme.cyan; font.family: Theme.mono; font.pixelSize: 10 }
                                Text { text: "x = " + ctrl.lrPositions[index] + " mm"; color: Theme.ink3; font.pixelSize: 9 }
                            }
                            Item { Layout.fillWidth: true }
                            ColumnLayout { spacing: 0; Layout.alignment: Qt.AlignRight
                                RowLayout { Layout.alignment: Qt.AlignRight; spacing: 4
                                    Text { text: val.toFixed(2); color: cc; font.family: Theme.mono; font.pixelSize: 22; font.weight: Font.DemiBold }
                                    Text { text: "mm"; color: Theme.ink2; font.pixelSize: 11; Layout.alignment: Qt.AlignBottom; bottomPadding: 3 } }
                                Text { text: "Δ " + (dev>=0?"+":"") + dev.toFixed(2) + " mm"; color: cc; font.family: Theme.mono; font.pixelSize: 10; Layout.alignment: Qt.AlignRight }
                            }
                            Rectangle { Layout.preferredWidth: 6; Layout.fillHeight: true; Layout.topMargin: 2; Layout.bottomMargin: 2
                                radius: 3; color: "#16222f"
                                Rectangle { width: parent.width; radius: 3; color: cc; anchors.bottom: parent.bottom
                                    height: parent.height * Math.max(0, Math.min(1, (val-(ctrl.rig.thick-15))/30))
                                    Behavior on height { NumberAnimation { duration: 90 } } } }
                        }
                    }
                }
            }
        }

        Card {
            Layout.fillWidth: true; Layout.preferredHeight: 96
            title: "KVALITETSSORTERING"
            RowLayout {
                anchors.fill: parent; spacing: 13
                Rectangle { width: 58; height: 58; radius: 13; color: ctrl.gradeColor
                    Behavior on color { ColorAnimation { duration: 350 } }
                    Text { anchors.centerIn: parent; text: ctrl.gradeClass; color: "#06121a"; font.family: Theme.mono; font.pixelSize: 28; font.weight: Font.Bold } }
                ColumnLayout { spacing: 2; Layout.fillWidth: true
                    Text { text: "KVALITETSKLASS"; color: Theme.ink3; font.pixelSize: 9; font.letterSpacing: 0.6 }
                    Text { text: ctrl.gradeTitle; color: Theme.ink; font.pixelSize: 14; font.weight: Font.DemiBold }
                    Text { text: ctrl.gradeReason; color: Theme.ink2; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight } }
            }
        }

        Card {
            id: defectCard
            Layout.fillWidth: true; Layout.fillHeight: true
            title: "DEFEKTER"; chip: defectCard.defectModel.length + " st"
            property var defectModel: []
            Connections { target: ctrl; function onDefectsChanged() { defectCard.defectModel = ctrl.defects } }
            ListView {
                id: defList; anchors.fill: parent; clip: true; spacing: 5; model: defectCard.defectModel
                delegate: Rectangle {
                    width: ListView.view.width; height: 30; radius: 8; color: Theme.panel2; border.color: Theme.line
                    RowLayout { anchors.fill: parent; anchors.leftMargin: 9; anchors.rightMargin: 9; spacing: 9
                        Rectangle { width: 9; height: 9; radius: 3; color: modelData.color }
                        Text { text: modelData.name; color: Theme.ink; font.pixelSize: 11; font.weight: Font.DemiBold }
                        Item { Layout.fillWidth: true }
                        Text { text: "x"+modelData.x+" y"+modelData.y+" · ⌀"+modelData.dia+"mm"; color: Theme.ink3; font.family: Theme.mono; font.pixelSize: 10 } }
                }
                Text { anchors.centerIn: parent; visible: defList.count===0; text: "Inga defekter registrerade"; color: Theme.ink3; font.pixelSize: 11; font.italic: true }
            }
        }
    }
}
