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
                title: "TVÄRSNITT · LIVE-PROFIL Z(x)"; chip: "θ " + ctrl.rig.theta.toFixed(0) + "° · RÖD+GRÖN"
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
                                var top=20, bh=height-top-8;
                                c.lineWidth=2.2; c.strokeStyle=d.c; c.shadowColor=d.c; c.shadowBlur=6;
                                c.beginPath(); var started=false;
                                for(var i=0;i<zp.length;i++){
                                    var fx=i/(zp.length-1);
                                    var occ = d.side===0 ? fx : (1-fx);
                                    var dz = zp[i]-ctrl.rig.thick;
                                    var px=6+(width-12)*fx, py=top+bh*0.5 - dz*4;
                                    if(occ>0.9 && dz<-2){ c.stroke(); c.beginPath(); started=false; }
                                    else { started?c.lineTo(px,py):c.moveTo(px,py); started=true; }
                                }
                                c.stroke(); c.shadowBlur=0;
                                c.fillStyle="rgba(255,255,255,0.25)"; c.font="8px monospace";
                                c.textAlign = d.side===0?"right":"left"; c.fillText("ocklusion", d.side===0?width-6:6, height-6);
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
                onPaint: {
                    var c=getContext("2d"); c.reset();
                    var w=width, h=height, R=ctrl.rig;
                    // brädans yta uppifrån: X (längd 500) horisontellt, Y (bredd 75) vertikalt
                    var asp=R.len/R.width, hpad=70, vpad=42;
                    var bw=Math.min(w-2*hpad, (h-2*vpad)*asp), bh=bw/asp;
                    var bx=(w-bw)/2, by=(h-bh)/2;
                    // transportband vid längd-ändarna (vänster/höger)
                    c.fillStyle="#0c121a";
                    c.fillRect(bx-16, by-6, 12, bh+12); c.fillRect(bx+bw+4, by-6, 12, bh+12);
                    c.strokeStyle="#1b2735"; c.lineWidth=1;
                    for (var bb=by-4; bb<by+bh; bb+=9){ c.beginPath(); c.moveTo(bx-16,bb); c.lineTo(bx-4,bb); c.moveTo(bx+bw+4,bb); c.lineTo(bx+bw+16,bb); c.stroke(); }
                    // bräda
                    c.fillStyle="#c9a468"; c.fillRect(bx,by,bw,bh);
                    c.strokeStyle="#7a5230"; c.lineWidth=1; c.strokeRect(bx,by,bw,bh);
                    // matningsled
                    var ly=by + bh*ctrl.scanProgress;
                    // RÖD huvud (ovanför brädan) — fläkt täcker hela 500 mm
                    function head(yPos, col, nm, align){
                        c.strokeStyle=col; c.globalAlpha=0.18; c.lineWidth=1;
                        c.beginPath(); c.moveTo((bx+bx+bw)/2, yPos); c.lineTo(bx, ly); c.lineTo(bx+bw, ly); c.closePath();
                        c.fillStyle=col; c.fill(); c.globalAlpha=1;
                        // kamera+laser-modul
                        c.fillStyle="#16212e"; c.strokeStyle=col; c.lineWidth=1.5;
                        c.fillRect((bx+bx+bw)/2-22, yPos-9, 44, 18); c.strokeRect((bx+bx+bw)/2-22, yPos-9, 44, 18);
                        c.fillStyle="#9fb2c6"; c.font="9px monospace"; c.textAlign="center";
                        c.fillText(nm, (bx+bx+bw)/2, align<0 ? yPos-13 : yPos+22);
                    }
                    head(by-26, Theme.red, "RÖD 650 (huvud A)", -1);
                    head(by+bh+26, Theme.grn, "GRÖN 520 (huvud B)", 1);
                    // laserlinjen (längs hela längden) — röd+grön
                    c.lineWidth=3; c.strokeStyle=Theme.red; c.shadowColor=Theme.red; c.shadowBlur=8;
                    c.beginPath(); c.moveTo(bx,ly-1.5); c.lineTo(bx+bw,ly-1.5); c.stroke();
                    c.strokeStyle=Theme.grn; c.shadowColor=Theme.grn;
                    c.beginPath(); c.moveTo(bx,ly+1.5); c.lineTo(bx+bw,ly+1.5); c.stroke(); c.shadowBlur=0;
                    // punktlasrar (LR400) längs linjen
                    var lp=ctrl.lrPositions;
                    for (var i=0;i<lp.length;i++){ var px=bx+bw*(lp[i]/R.len);
                        c.fillStyle=Theme.cyan; c.beginPath(); c.arc(px,ly,3.2,0,7); c.fill();
                        c.strokeStyle=Qt.rgba(0.15,0.83,0.88,0.4); c.beginPath(); c.arc(px,ly,6,0,7); c.stroke(); }
                    // ytkamera i centrum
                    c.fillStyle="#16212e"; c.strokeStyle=Theme.blue; c.lineWidth=1.5;
                    c.fillRect((bx+bx+bw)/2-14, by+bh/2-7, 28, 14); c.strokeRect((bx+bx+bw)/2-14, by+bh/2-7, 28, 14);
                    c.fillStyle=Theme.blue; c.font="8px monospace"; c.textAlign="center"; c.fillText("ytkamera 4K", (bx+bx+bw)/2, by+bh/2+18);
                    // etiketter
                    c.fillStyle="#61768c"; c.font="9px monospace";
                    c.textAlign="left"; c.fillText("0", bx, by+bh+16);
                    c.textAlign="right"; c.fillText(R.len.toFixed(0)+" mm  (längd X — laserlinjens riktning)", bx+bw, by+bh+16);
                    c.textAlign="left"; c.fillText("matning ↓ (bredd "+R.width.toFixed(0)+" mm, Y)", bx, by-14);
                    c.fillStyle=Theme.cyan; c.textAlign="center";
                    c.fillText("laserlinje "+R.len.toFixed(0)+" mm — täcker hela långsidan", (bx+bx+bw)/2, ly>by+bh/2 ? ly-8 : ly+16);
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
            title: "PUNKTLASER · ABSOLUT TJOCKLEK"; chip: "3× LR400 · RS-485"
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
