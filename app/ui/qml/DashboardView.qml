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

        // ---- rigg ändvy (montering, = head-mech.svg) ----
        Card {
            Layout.fillWidth: true; Layout.fillHeight: false; Layout.preferredHeight: 210
            title: "RIGG · ÄNDVY (optik & montering)"
            chip: "WD " + ctrl.rig.wd.toFixed(0) + " · armar " + ctrl.rig.camArm.toFixed(0) + "°/" + ctrl.rig.laserArm.toFixed(0) + "°"
            Canvas {
                id: rigCv; anchors.fill: parent
                Connections { target: ctrl; function onStateChanged() { rigCv.requestPaint() } }
                onPaint: {
                    var c=getContext("2d"); c.reset();
                    var w=width, h=height, R=ctrl.rig;
                    var cx=w*0.5, by=h-26;                       // brädans topp-mitt (origo)
                    var sc=Math.min((h-50)/R.camHeight, (w*0.46)/R.laserOffset);
                    function P(xmm,zmm){ return [cx + xmm*sc, by - zmm*sc]; }   // x höger, z upp
                    // tvärbalk
                    var beamY=by - R.camHeight*sc - 6;
                    c.strokeStyle="#27384a"; c.lineWidth=6; c.beginPath();
                    c.moveTo(cx-R.camOffset*sc-20, beamY); c.lineTo(cx+R.camOffset*sc+20, beamY); c.stroke();
                    // bräda (bredd × tjocklek)
                    var bw=R.width*sc, bt=Math.max(4,R.thick*sc);
                    c.fillStyle="#caa46a"; c.fillRect(cx-bw/2, by-bt, bw, bt);
                    c.strokeStyle="#7a5230"; c.lineWidth=1; c.strokeRect(cx-bw/2, by-bt, bw, bt);
                    // funktion för ett huvud
                    function head(sign, col, nm){
                        var cam=P(sign*R.camOffset, R.camHeight), las=P(sign*R.laserOffset, R.laserHeight), brd=P(0,0);
                        // arm (tvärbalk → laser via kamera)
                        c.strokeStyle="#3a4d62"; c.lineWidth=3;
                        c.beginPath(); c.moveTo(cx+sign*R.camOffset*sc, beamY); c.lineTo(cam[0],cam[1]); c.lineTo(las[0],las[1]); c.stroke();
                        // siktlinjer till brädmitt
                        c.setLineDash([4,3]); c.lineWidth=1.4;
                        c.strokeStyle=Qt.rgba(1,1,1,0.18); c.beginPath(); c.moveTo(cam[0],cam[1]); c.lineTo(brd[0],brd[1]); c.stroke();
                        c.strokeStyle=col; c.beginPath(); c.moveTo(las[0],las[1]); c.lineTo(brd[0],brd[1]); c.stroke();
                        c.setLineDash([]);
                        // kamera + laser
                        c.fillStyle="#16212e"; c.strokeStyle=col; c.lineWidth=1.5;
                        c.fillRect(cam[0]-13,cam[1]-9,26,18); c.strokeRect(cam[0]-13,cam[1]-9,26,18);
                        c.fillStyle=col; c.beginPath(); c.arc(las[0],las[1],5,0,7); c.fill();
                        c.fillStyle="#9fb2c6"; c.font="9px monospace"; c.textAlign = sign<0?"end":"start";
                        c.fillText(nm, cam[0]+sign*18, cam[1]-12);
                    }
                    head(-1, Theme.red, "RÖD 650");
                    head(1, Theme.grn, "GRÖN 520");
                    // ytkamera i centrum, rakt ned
                    var sca=P(0, R.surfWd);
                    c.strokeStyle="#3a4d62"; c.lineWidth=2; c.beginPath(); c.moveTo(cx,beamY); c.lineTo(sca[0],sca[1]); c.stroke();
                    c.fillStyle="#16212e"; c.strokeStyle=Theme.blue; c.lineWidth=1.5;
                    c.fillRect(sca[0]-12,sca[1]-8,24,16); c.strokeRect(sca[0]-12,sca[1]-8,24,16);
                    c.setLineDash([3,3]); c.strokeStyle=Qt.rgba(0.29,0.66,1,0.5); c.beginPath(); c.moveTo(sca[0],sca[1]); c.lineTo(cx,by); c.stroke(); c.setLineDash([]);
                    c.fillStyle="#9fb2c6"; c.font="9px monospace"; c.textAlign="center"; c.fillText("ytkamera (4K)", sca[0], sca[1]-12);
                    // mått
                    c.fillStyle="#61768c"; c.textAlign="center";
                    c.fillText("θ "+R.theta.toFixed(0)+"° · obliquitet "+R.oblique.toFixed(0)+"° · baslinje "+R.baseline.toFixed(0)+" mm", cx, h-6);
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
