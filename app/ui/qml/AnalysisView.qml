import QtQuick
import QtQuick.Layouts

RowLayout {
    id: aroot
    spacing: 12

    // ============================ 3D-REKONSTRUKTION ========================
    Card {
        Layout.fillWidth: true; Layout.fillHeight: true
        title: "3D-REKONSTRUKTION"
        chip: ctrl.mesh3d.cls ? ("klass " + ctrl.mesh3d.cls + " · skevhet ×" + view3d.exag) : "skanna en bräda"

        Item {
            anchors.fill: parent

            Canvas {
                id: view3d
                anchors.fill: parent
                property real yaw: -0.6
                property real pitch: 0.95
                property real zoom: 1.0
                property real exag: 8
                property int mode: 0          // 0=höjd 1=avvikelse 2=skuggad
                property bool spin: true

                Connections { target: ctrl; function onMeshChanged() { view3d.requestPaint() } }
                Timer { running: view3d.spin; interval: 33; repeat: true
                        onTriggered: { view3d.yaw += 0.012; view3d.requestPaint() } }

                function turbo(t){ t=Math.max(0,Math.min(1,t));
                    return [Math.round(34+t*221), Math.round(60+Math.sin(t*Math.PI)*180), Math.round(220-t*180)]; }
                function diverge(t){ // -1..1 → blå-vit-röd
                    t=Math.max(-1,Math.min(1,t));
                    if(t<0) return [Math.round(80+175*(1+t)),Math.round(140+115*(1+t)),255];
                    return [255,Math.round(255-150*t),Math.round(255-200*t)]; }

                onPaint: {
                    var c=getContext("2d"); c.reset();
                    var w=width,h=height; c.clearRect(0,0,w,h);
                    var m=ctrl.mesh3d;
                    if(!m || !m.z || m.z.length<4){
                        c.fillStyle="#3a4d62"; c.font="13px sans-serif"; c.textAlign="center";
                        c.fillText("Skanna en bräda → 3D-modell visas här", w/2, h/2); return;
                    }
                    var nx=m.nx, ny=m.ny, Z=m.z, L=m.len, W=m.width;
                    var zmin=m.zmin, zmax=m.zmax, span=Math.max(0.5,zmax-zmin);
                    var maxabs=Math.max(Math.abs(zmin),Math.abs(zmax),0.5);
                    var cy=Math.cos(yaw),sy=Math.sin(yaw),cp=Math.cos(pitch),sp=Math.sin(pitch);
                    var s=Math.min(w,h)*0.62/L*zoom, cx=w/2, cyc=h*0.52;
                    function P(i,j){
                        var x=(i/(nx-1)-0.5)*L, y=(j/(ny-1)-0.5)*W, z=Z[j*nx+i]*exag;
                        var x1=x*cy - y*sy, y1=x*sy + y*cy;          // yaw kring vertikal
                        var y2=y1*cp - z*sp, z2=y1*sp + z*cp;        // pitch
                        return {sx:cx + x1*s, sy:cyc - z2*s, d:y2};
                    }
                    // referensplan (ideal, platt) — visar avvikelse
                    var p00=P(0,0),p10=P(nx-1,0),p11=P(nx-1,ny-1),p01=P(0,ny-1);
                    // OBS: referensplanet ritas vid z=0 → approximera med exag*0 (platt)
                    function flat(i,j){ var x=(i/(nx-1)-0.5)*L,y=(j/(ny-1)-0.5)*W;
                        var x1=x*cy-y*sy,y1=x*sy+y*cy; var y2=y1*cp,z2=y1*sp; return {sx:cx+x1*s,sy:cyc-z2*s}; }
                    var f00=flat(0,0),f10=flat(nx-1,0),f11=flat(nx-1,ny-1),f01=flat(0,ny-1);
                    c.beginPath(); c.moveTo(f00.sx,f00.sy); c.lineTo(f10.sx,f10.sy); c.lineTo(f11.sx,f11.sy); c.lineTo(f01.sx,f01.sy); c.closePath();
                    c.strokeStyle="rgba(159,178,198,0.25)"; c.lineWidth=1; c.setLineDash([5,4]); c.stroke(); c.setLineDash([]);

                    // bygg quads med djup + färg + skuggning
                    var light=[0.35,0.45,0.82];
                    var quads=[];
                    for(var j=0;j<ny-1;j++) for(var i=0;i<nx-1;i++){
                        var a=P(i,j),b=P(i+1,j),cc=P(i+1,j+1),d=P(i,j+1);
                        // normal i världsrymd (för skuggning)
                        var zv=Z[j*nx+i];
                        var nzx=(Z[j*nx+i+1]-zv)*exag, nzy=(Z[(j+1)*nx+i]-zv)*exag;
                        var dx=L/(nx-1), dy=W/(ny-1);
                        var nlen=Math.hypot(nzx*dy, nzy*dx, dx*dy)||1;
                        var shade=0.5+0.5*Math.max(0,(-nzx*dy*light[0]-nzy*dx*light[1]+dx*dy*light[2])/nlen);
                        var col;
                        if(mode===0){ col=turbo((zv-zmin)/span); }
                        else if(mode===1){ col=diverge(zv/maxabs); }
                        else { var g=Math.round(120+120*shade); col=[g,g,g]; }
                        quads.push({pts:[a,b,cc,d], depth:(a.d+b.d+cc.d+d.d)/4,
                                    col:[Math.round(col[0]*shade),Math.round(col[1]*shade),Math.round(col[2]*shade)]});
                    }
                    quads.sort(function(p,q){ return q.depth-p.depth; });   // bortre först
                    for(var k=0;k<quads.length;k++){ var Q=quads[k];
                        c.beginPath(); c.moveTo(Q.pts[0].sx,Q.pts[0].sy);
                        for(var t=1;t<4;t++) c.lineTo(Q.pts[t].sx,Q.pts[t].sy); c.closePath();
                        c.fillStyle="rgb("+Q.col[0]+","+Q.col[1]+","+Q.col[2]+")"; c.fill();
                        c.strokeStyle="rgba(0,0,0,0.12)"; c.lineWidth=0.5; c.stroke();
                    }
                    // axel-etikett
                    c.fillStyle="#61768c"; c.font="9px monospace"; c.textAlign="left";
                    c.fillText("längd 500 · bredd 75 · tjocklek 20 mm  (skevhet förstorad ×"+exag+")", 8, h-8);
                }

                MouseArea {
                    anchors.fill: parent; acceptedButtons: Qt.LeftButton
                    property real px: 0; property real py: 0
                    onPressed: (e)=>{ px=e.x; py=e.y; view3d.spin=false }
                    onPositionChanged: (e)=>{
                        view3d.yaw += (e.x-px)*0.01; view3d.pitch += (e.y-py)*0.01;
                        view3d.pitch=Math.max(0.05,Math.min(1.5,view3d.pitch));
                        px=e.x; py=e.y; view3d.requestPaint();
                    }
                    onWheel: (e)=>{ view3d.zoom=Math.max(0.4,Math.min(3,view3d.zoom*(e.angleDelta.y>0?1.1:0.9))); view3d.requestPaint(); }
                }
            }

            // verktyg (färgläge, snurr)
            Row {
                anchors.top: parent.top; anchors.right: parent.right; spacing: 6
                Repeater {
                    model: ["Höjd","Avvikelse","Skuggad"]
                    delegate: Rectangle {
                        radius: 7; implicitHeight: 24; implicitWidth: t.width+18
                        color: view3d.mode===index ? Theme.cyan : Theme.panel2
                        border.color: view3d.mode===index ? "transparent" : Theme.line
                        Text { id: t; anchors.centerIn: parent; text: modelData
                               color: view3d.mode===index ? "#04222a" : Theme.ink2; font.pixelSize: 10; font.weight: Font.DemiBold }
                        MouseArea { anchors.fill: parent; onClicked: { view3d.mode=index; view3d.requestPaint() } }
                    }
                }
                Rectangle {
                    radius: 7; implicitHeight: 24; implicitWidth: st.width+18
                    color: view3d.spin ? Theme.teal : Theme.panel2; border.color: view3d.spin ? "transparent" : Theme.line
                    Text { id: st; anchors.centerIn: parent; text: "↻ Snurr"; color: view3d.spin ? "#04222a" : Theme.ink2; font.pixelSize: 10; font.weight: Font.DemiBold }
                    MouseArea { anchors.fill: parent; onClicked: { view3d.spin=!view3d.spin; if(view3d.spin) view3d.requestPaint() } }
                }
            }
            Text { anchors.bottom: parent.bottom; anchors.right: parent.right; anchors.margins: 6
                   text: "dra = rotera · hjul = zoom"; color: Theme.ink3; font.pixelSize: 9; font.family: Theme.mono }
        }
    }

    // ============================ HÖGER: skevhet + profiler ================
    ColumnLayout {
        Layout.fillHeight: true; Layout.fillWidth: false
        Layout.preferredWidth: 400; Layout.minimumWidth: 360; Layout.maximumWidth: 460
        spacing: 12

        Card {
            Layout.fillWidth: true; Layout.preferredHeight: 176
            title: "SKEVHET (uppmätt)"; chip: ctrl.mesh3d.cls ? "klass " + ctrl.mesh3d.cls : "—"
            ColumnLayout {
                anchors.fill: parent; spacing: 8
                Repeater {
                    model: [["Bukt / krok (bow)","bow",3.0],["Kupa (cup)","cup",2.5],
                            ["Vridning (twist)","twist",3.0],["Plankrok (crook)","crook",3.0]]
                    delegate: RowLayout {
                        Layout.fillWidth: true; spacing: 10
                        property real val: ctrl.mesh3d[modelData[1]] !== undefined ? ctrl.mesh3d[modelData[1]] : 0
                        Text { text: modelData[0]; color: Theme.ink2; font.pixelSize: 11; Layout.preferredWidth: 150 }
                        Rectangle { Layout.fillWidth: true; height: 8; radius: 4; color: "#16222f"
                            Rectangle { radius: 4; height: parent.height
                                width: parent.width * Math.max(0, Math.min(1, val/modelData[2]))
                                color: val < modelData[2]*0.5 ? Theme.teal : (val < modelData[2]*0.85 ? Theme.amber : Theme.red)
                                Behavior on width { NumberAnimation { duration: 200 } } } }
                        Text { text: val.toFixed(2) + " mm"; color: Theme.cyan; font.family: Theme.mono; font.pixelSize: 11; Layout.preferredWidth: 64; horizontalAlignment: Text.AlignRight }
                    }
                }
            }
        }

        Card {
            Layout.fillWidth: true; Layout.fillHeight: true
            title: "LÄNGSPROFIL Z(x) · längs 500 mm"
            ProfilePlot { values: ctrl.zProfile; axisLabel: "x längs bräda (0–500 mm)" }
        }
        Card {
            Layout.fillWidth: true; Layout.fillHeight: true
            title: "TVÄRPROFIL Z(y) · topp + kanter (75 mm)"; chip: "vankant/kupa"
            ProfilePlot { values: ctrl.zProfileWidth; axisLabel: "y tvärs bräda (0–75 mm)"; accent: Theme.violet }
        }
    }
}
