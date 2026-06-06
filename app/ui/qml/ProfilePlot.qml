import QtQuick

// Återanvändbar profilplot. Standard: Z (mm) vs index kring nominell ±15 mm.
// crossSection=true: rita brädans TVÄRSNITT som en solid ⊓ (topp + två
// tjockleks-sidor) — vänster sida RÖD, höger GRÖN (de två oblika huvudena).
Canvas {
    id: plot
    anchors.fill: parent
    property var values: []
    property string axisLabel: ""
    property color accent: Theme.cyan
    property bool crossSection: false
    Connections { target: ctrl; function onStateChanged() { plot.requestPaint() } }
    onPaint: {
        var c=getContext("2d"); c.reset();
        var w=width,h=height,m=34,gx=m,gy=8,gw=w-m-12,gh=h-24;
        var BT=ctrl.rig.thick;
        var lo = crossSection ? 0 : BT-15;
        var hi = crossSection ? BT+10 : BT+15;
        var rng = hi-lo;
        c.strokeStyle="#16222f"; c.lineWidth=1;
        for(var i=0;i<=5;i++){ var yy=gy+gh*i/5; c.beginPath(); c.moveTo(gx,yy); c.lineTo(gx+gw,yy); c.stroke(); }
        c.fillStyle="#3a4d62"; c.font="9px monospace"; c.textAlign="right";
        c.fillText(hi.toFixed(0),gx-4,gy+6); c.fillText(((hi+lo)/2).toFixed(0),gx-4,gy+gh/2+3); c.fillText(lo.toFixed(0),gx-4,gy+gh-2);
        var zp=values;
        if(!zp || zp.length<2){ c.fillStyle="#3a4d62"; c.textAlign="center"; c.fillText("ingen aktiv profil",gx+gw/2,gy+gh/2); return; }
        function X(k){ return gx+gw*k/(zp.length-1); }
        function Y(z){ return gy+gh*(1-((z-lo)/rng)); }

        if(crossSection){
            // solid tvärsnitt: fyll från botten (z=0) upp till toppytan
            c.beginPath(); c.moveTo(X(0), Y(0));
            for(var k=0;k<zp.length;k++) c.lineTo(X(k), Y(zp[k]));
            c.lineTo(X(zp.length-1), Y(0)); c.closePath();
            c.fillStyle="rgba(201,164,104,0.14)"; c.fill();            // trä-snitt (antaget)
            // TOPPYTA = MÄTT (heldragen)
            c.beginPath();
            for(var j=0;j<zp.length;j++){ var xx=X(j),yv=Y(zp[j]); j?c.lineTo(xx,yv):c.moveTo(xx,yv); }
            c.strokeStyle=accent; c.lineWidth=2; c.stroke();
            // BOTTEN + SIDOR = ANTAGNA (ej mätt → streckat/dämpat)
            c.setLineDash([4,3]);
            c.strokeStyle="rgba(159,178,198,0.35)"; c.lineWidth=1.2;
            c.beginPath(); c.moveTo(X(0),Y(0)); c.lineTo(X(zp.length-1),Y(0)); c.stroke();
            c.lineWidth=2; c.lineCap="round";
            c.strokeStyle=Qt.rgba(Theme.red.r,Theme.red.g,Theme.red.b,0.5);
            c.beginPath(); c.moveTo(X(0),Y(0)); c.lineTo(X(0),Y(zp[0])); c.stroke();
            c.strokeStyle=Qt.rgba(Theme.grn.r,Theme.grn.g,Theme.grn.b,0.5);
            c.beginPath(); c.moveTo(X(zp.length-1),Y(0)); c.lineTo(X(zp.length-1),Y(zp[zp.length-1])); c.stroke();
            c.setLineDash([]); c.lineCap="butt";
            c.fillStyle=Theme.red;  c.font="8px monospace"; c.textAlign="left";  c.fillText("RÖD", X(0)+3, Y(zp[0])-4);
            c.fillStyle=Theme.grn;  c.textAlign="right"; c.fillText("GRÖN", X(zp.length-1)-3, Y(zp[zp.length-1])-4);
            c.fillStyle="#3a4d62"; c.font="8px monospace"; c.textAlign="left";
            c.fillText("— mätt topp · - - botten/sidor antagna (band-datum)", X(0)+2, Y(0)-5);
        } else {
            c.beginPath(); c.moveTo(gx,gy+gh);
            for(var a=0;a<zp.length;a++) c.lineTo(X(a), Y(zp[a]));
            c.lineTo(gx+gw,gy+gh); c.closePath();
            var g=c.createLinearGradient(0,gy,0,gy+gh);
            g.addColorStop(0, Qt.rgba(accent.r,accent.g,accent.b,0.22)); g.addColorStop(1, Qt.rgba(accent.r,accent.g,accent.b,0));
            c.fillStyle=g; c.fill();
            c.beginPath();
            for(var b=0;b<zp.length;b++){ var x2=X(b),y2=Y(zp[b]); b?c.lineTo(x2,y2):c.moveTo(x2,y2); }
            c.strokeStyle=accent; c.lineWidth=2; c.shadowColor=accent; c.shadowBlur=6; c.stroke(); c.shadowBlur=0;
            c.setLineDash([4,4]); c.strokeStyle="rgba(159,178,198,0.3)"; c.lineWidth=1;
            c.beginPath(); c.moveTo(gx,Y(BT)); c.lineTo(gx+gw,Y(BT)); c.stroke(); c.setLineDash([]);
        }
        c.fillStyle="#61768c"; c.textAlign="center"; c.fillText(axisLabel, gx+gw/2, h-4);
    }
}
