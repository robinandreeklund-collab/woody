import QtQuick

// Återanvändbar profilplot: Z (mm) vs index, skala kring nominell tjocklek ±15 mm.
Canvas {
    id: plot
    anchors.fill: parent
    property var values: []
    property string axisLabel: ""
    property color accent: Theme.cyan
    Connections { target: ctrl; function onStateChanged() { plot.requestPaint() } }
    onPaint: {
        var c=getContext("2d"); c.reset();
        var w=width,h=height,m=34,gx=m,gy=8,gw=w-m-12,gh=h-24;
        var BT=ctrl.rig.thick, lo=BT-15, hi=BT+15;
        c.strokeStyle="#16222f"; c.lineWidth=1;
        for(var i=0;i<=5;i++){ var yy=gy+gh*i/5; c.beginPath(); c.moveTo(gx,yy); c.lineTo(gx+gw,yy); c.stroke(); }
        c.fillStyle="#3a4d62"; c.font="9px monospace"; c.textAlign="right";
        c.fillText(hi.toFixed(0),gx-4,gy+6); c.fillText(BT.toFixed(0),gx-4,gy+gh/2+3); c.fillText(lo.toFixed(0),gx-4,gy+gh-2);
        var zp=values;
        if(!zp || zp.length<2){ c.fillStyle="#3a4d62"; c.textAlign="center"; c.fillText("ingen aktiv profil",gx+gw/2,gy+gh/2); return; }
        function Y(z){ return gy+gh*(1-((z-lo)/30)); }
        c.beginPath(); c.moveTo(gx,gy+gh);
        for(var k=0;k<zp.length;k++) c.lineTo(gx+gw*k/(zp.length-1), Y(zp[k]));
        c.lineTo(gx+gw,gy+gh); c.closePath();
        var g=c.createLinearGradient(0,gy,0,gy+gh);
        g.addColorStop(0, Qt.rgba(accent.r,accent.g,accent.b,0.22)); g.addColorStop(1, Qt.rgba(accent.r,accent.g,accent.b,0));
        c.fillStyle=g; c.fill();
        c.beginPath();
        for(var j=0;j<zp.length;j++){ var X=gx+gw*j/(zp.length-1), yv=Y(zp[j]); j?c.lineTo(X,yv):c.moveTo(X,yv); }
        c.strokeStyle=accent; c.lineWidth=2; c.shadowColor=accent; c.shadowBlur=6; c.stroke(); c.shadowBlur=0;
        c.setLineDash([4,4]); c.strokeStyle="rgba(159,178,198,0.3)"; c.lineWidth=1;
        c.beginPath(); c.moveTo(gx,Y(BT)); c.lineTo(gx+gw,Y(BT)); c.stroke(); c.setLineDash([]);
        c.fillStyle="#61768c"; c.textAlign="center"; c.fillText(axisLabel, gx+gw/2, h-4);
    }
}
