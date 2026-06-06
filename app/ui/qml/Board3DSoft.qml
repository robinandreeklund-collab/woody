import QtQuick

// Software-3D (Canvas) — fallback när Qt Quick 3D inte är tillgängligt.
Item {
    anchors.fill: parent

    Canvas {
        id: view3d
        anchors.fill: parent
        property real yaw: -0.6
        property real pitch: 0.62
        property real zoom: 1.0
        property real exag: 3
        property int mode: 0
        property bool spin: true

        Connections { target: ctrl; function onMeshChanged() { view3d.requestPaint() } }
        Timer { running: view3d.spin; interval: 33; repeat: true
                onTriggered: { view3d.yaw += 0.012; view3d.requestPaint() } }

        function turbo(t){ t=Math.max(0,Math.min(1,t));
            return [Math.round(34+t*221), Math.round(60+Math.sin(t*Math.PI)*180), Math.round(220-t*180)]; }
        function diverge(t){ t=Math.max(-1,Math.min(1,t));
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
            var nx=m.nx, ny=m.ny, Z=m.z, L=m.len, W=m.width, T=m.thick;
            var RGB=m.rgb, wf=(m.wfrac!==undefined)?m.wfrac:1.0;
            var zmin=m.zmin, zmax=m.zmax, span=Math.max(0.5,zmax-zmin);
            var maxabs=Math.max(Math.abs(zmin),Math.abs(zmax),0.5);
            var cy=Math.cos(yaw),sy=Math.sin(yaw),cp=Math.cos(pitch),sp=Math.sin(pitch);
            var s=Math.min(w,h)*0.56/L*zoom, cx=w/2, cyc=h*0.56;
            function topZ(i,j){ return T + Z[j*nx+i]*exag; }
            function vx(i){ return (i/(nx-1)-0.5)*L; }
            function vy(j){ return -W/2 + (j/(ny-1))*(W*wf); }
            function proj(x,y,z){ var zc=z - T/2;
                var x1=x*cy - y*sy, y1=x*sy + y*cy;
                var y2=y1*cp - zc*sp, z2=y1*sp + zc*cp;
                return {sx:cx + x1*s, sy:cyc - z2*s, d:y2}; }
            var light=[0.35,0.45,0.82], faces=[];
            function add(pts,col){ var d=0; for(var t=0;t<pts.length;t++) d+=pts[t].d; faces.push({pts:pts, depth:d/pts.length, col:col}); }
            function tint(col,sh){ return [Math.round(col[0]*sh),Math.round(col[1]*sh),Math.round(col[2]*sh)]; }
            var dx=L/(nx-1), dy=W/(ny-1);
            for(var j=0;j<ny-1;j++) for(var i=0;i<nx-1;i++){
                var a=proj(vx(i),vy(j),topZ(i,j)), b=proj(vx(i+1),vy(j),topZ(i+1,j)),
                    cc=proj(vx(i+1),vy(j+1),topZ(i+1,j+1)), d2=proj(vx(i),vy(j+1),topZ(i,j+1));
                var zv=Z[j*nx+i];
                var nzx=(Z[j*nx+i+1]-zv)*exag, nzy=(Z[(j+1)*nx+i]-zv)*exag;
                var nlen=Math.hypot(nzx*dy,nzy*dx,dx*dy)||1;
                var sh=0.55+0.45*Math.max(0,(-nzx*dy*light[0]-nzy*dx*light[1]+dx*dy*light[2])/nlen);
                var col;
                if(mode===0) col=turbo((zv-zmin)/span);
                else if(mode===1) col=diverge(zv/maxabs);
                else if(mode===3 && RGB){ var p=(j*nx+i)*3; col=[RGB[p],RGB[p+1],RGB[p+2]]; }
                else { var g=Math.round(120+120*sh); col=[g,g,g]; }
                add([a,b,cc,d2], tint(col,sh));
            }
            var nbx=16, nby=4;
            for(var jb=0;jb<nby;jb++) for(var ib=0;ib<nbx;ib++){
                var bx0=(ib/nbx-0.5)*L, bx1=((ib+1)/nbx-0.5)*L;
                var by0=-W/2+(jb/nby)*(W*wf), by1=-W/2+((jb+1)/nby)*(W*wf);
                add([proj(bx0,by0,0),proj(bx1,by0,0),proj(bx1,by1,0),proj(bx0,by1,0)],[16,24,34]);
            }
            var done = wf >= 0.999, backCol = done ? [50,170,84] : [60,72,86];
            for(var i2=0;i2<nx-1;i2++){
                add([proj(vx(i2),vy(0),0),proj(vx(i2+1),vy(0),0),proj(vx(i2+1),vy(0),topZ(i2+1,0)),proj(vx(i2),vy(0),topZ(i2,0))],[150,40,52]);
                var jj=ny-1;
                add([proj(vx(i2),vy(jj),0),proj(vx(i2+1),vy(jj),0),proj(vx(i2+1),vy(jj),topZ(i2+1,jj)),proj(vx(i2),vy(jj),topZ(i2,jj))],backCol);
            }
            for(var j2=0;j2<ny-1;j2++){
                add([proj(vx(0),vy(j2),0),proj(vx(0),vy(j2+1),0),proj(vx(0),vy(j2+1),topZ(0,j2+1)),proj(vx(0),vy(j2),topZ(0,j2))],[78,92,108]);
                var ii=nx-1;
                add([proj(vx(ii),vy(j2),0),proj(vx(ii),vy(j2+1),0),proj(vx(ii),vy(j2+1),topZ(ii,j2+1)),proj(vx(ii),vy(j2),topZ(ii,j2))],[78,92,108]);
            }
            faces.sort(function(p,q){ return q.depth-p.depth; });
            for(var k=0;k<faces.length;k++){ var Q=faces[k];
                c.beginPath(); c.moveTo(Q.pts[0].sx,Q.pts[0].sy);
                for(var t2=1;t2<Q.pts.length;t2++) c.lineTo(Q.pts[t2].sx,Q.pts[t2].sy); c.closePath();
                c.fillStyle="rgb("+Q.col[0]+","+Q.col[1]+","+Q.col[2]+")"; c.fill();
                c.strokeStyle="rgba(0,0,0,0.06)"; c.lineWidth=0.25; c.stroke();
            }
            c.fillStyle="#61768c"; c.font="9px monospace"; c.textAlign="left";
            c.fillText("mätt: topp + sidor · underside antagen · software-3D · skevhet ×"+exag, 8, h-8);
        }
        MouseArea {
            anchors.fill: parent; acceptedButtons: Qt.LeftButton
            property real px: 0; property real py: 0
            onPressed: (e)=>{ px=e.x; py=e.y; view3d.spin=false }
            onPositionChanged: (e)=>{ view3d.yaw += (e.x-px)*0.01; view3d.pitch += (e.y-py)*0.01;
                view3d.pitch=Math.max(0.05,Math.min(1.5,view3d.pitch)); px=e.x; py=e.y; view3d.requestPaint(); }
            onWheel: (e)=>{ view3d.zoom=Math.max(0.4,Math.min(3,view3d.zoom*(e.angleDelta.y>0?1.1:0.9))); view3d.requestPaint(); }
        }
    }

    Row {
        anchors.top: parent.top; anchors.right: parent.right; spacing: 6
        Repeater {
            model: ["Höjd","Avvikelse","Skuggad","Foto"]
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
