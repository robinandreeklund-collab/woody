"""Qt Quick 3D-geometri för den skannade brädan — byggs på GPU:n (desktop).

Tar controllerns mesh (höjdrutnät + färg) och bygger en indexerad-fri triangelmesh
med position, normal och per-vertex-färg → renderas med ljus/MSAA i View3D.
Färgläge: 0 höjd · 1 avvikelse · 2 skuggad (vit, ljussätts) · 3 foto (äkta yta).
Solid: mätt topp + sidofasetter (röd/grön) + antagen underside.
"""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import QByteArray, Property, Signal, Slot
from PySide6.QtGui import QVector3D
from PySide6.QtQuick3D import QQuick3DGeometry

_A = QQuick3DGeometry.Attribute


def _turbo(t):
    t = np.clip(t, 0, 1)
    return np.clip(np.stack([(34 + t * 221) / 255,
                             (60 + np.sin(t * np.pi) * 180) / 255,
                             (220 - t * 180) / 255], -1), 0, 1).astype(np.float32)


def _diverge(t):
    t = np.clip(t, -1, 1); neg = t < 0
    r = np.where(neg, (80 + 175 * (1 + t)) / 255, 1.0)
    g = np.where(neg, (140 + 115 * (1 + t)) / 255, (255 - 150 * t) / 255)
    b = np.where(neg, 1.0, (255 - 200 * t) / 255)
    return np.clip(np.stack([r, g, b], -1), 0, 1).astype(np.float32)


def _quads(P, C):
    """P,C: (h,w,3/4). → (N,10) [pos3, normal3, rgba4], 2 tris/cell, plana normaler."""
    a, b, c, d = P[:-1, :-1], P[:-1, 1:], P[1:, 1:], P[1:, :-1]
    Ca, Cb, Cc, Cd = C[:-1, :-1], C[:-1, 1:], C[1:, 1:], C[1:, :-1]
    n1 = np.cross(b - a, c - a); n1 /= np.linalg.norm(n1, axis=-1, keepdims=True) + 1e-9
    n2 = np.cross(c - a, d - a); n2 /= np.linalg.norm(n2, axis=-1, keepdims=True) + 1e-9

    def pk(pos, nor, col):
        nb = np.broadcast_to(nor, pos.shape)
        return np.concatenate([pos, nb, col], axis=-1)

    t1 = np.stack([pk(a, n1, Ca), pk(b, n1, Cb), pk(c, n1, Cc)], axis=2)
    t2 = np.stack([pk(a, n2, Ca), pk(c, n2, Cc), pk(d, n2, Cd)], axis=2)
    return np.concatenate([t1, t2], axis=2).reshape(-1, 10).astype(np.float32)


def _wall(p0, p1, color):
    """Två rader (botten→topp) längs en kant. p0,p1: (n,3) botten/topp. → quads."""
    P = np.stack([p0, p1], axis=0)                       # (2,n,3)
    C = np.broadcast_to(np.array(color + [1.0], np.float32), (2, p0.shape[0], 4))
    return _quads(P, C)


class BoardGeometry(QQuick3DGeometry):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mesh: dict = {}
        self._mode = 0
        self._exag = 3.0

    @Slot("QVariantMap")
    def setMesh(self, mesh):
        self._mesh = dict(mesh) if mesh else {}
        self._rebuild()

    def getMode(self): return self._mode
    def setMode(self, m):
        if m != self._mode:
            self._mode = int(m); self._rebuild(); self.changed.emit()
    mode = Property(int, getMode, setMode, notify=changed)

    def getExag(self): return self._exag
    def setExag(self, e):
        if e != self._exag:
            self._exag = float(e); self._rebuild(); self.changed.emit()
    exaggeration = Property(float, getExag, setExag, notify=changed)

    # ------------------------------------------------------------------ build
    def _rebuild(self):
        m = self._mesh
        z = m.get("z") if m else None
        self.clear()
        if not z:
            self.update(); return
        nx, ny = int(m["nx"]), int(m["ny"])
        L, W, T = float(m["len"]), float(m["width"]), float(m["thick"])
        wf = float(m.get("wfrac", 1.0)); exag = self._exag
        zmin, zmax = float(m["zmin"]), float(m["zmax"])
        span = max(0.5, zmax - zmin); maxabs = max(abs(zmin), abs(zmax), 0.5)
        Z = np.asarray(z, np.float32).reshape(ny, nx)
        rgb = m.get("rgb")
        RGB = (np.asarray(rgb, np.float32).reshape(ny, nx, 3) / 255.0) if rgb else None

        X = ((np.arange(nx) / (nx - 1)) - 0.5) * L
        Y = -W / 2 + (np.arange(ny) / (ny - 1)) * (W * wf)
        Ztop = T + Z * exag
        P = np.stack([np.broadcast_to(X[None, :], (ny, nx)),
                      np.broadcast_to(Y[:, None], (ny, nx)),
                      (Ztop - T / 2)], -1).astype(np.float32)

        if self._mode == 0:
            C = _turbo((Z - zmin) / span)
        elif self._mode == 1:
            C = _diverge(Z / maxabs)
        elif self._mode == 3 and RGB is not None:
            C = RGB
        else:
            C = np.full((ny, nx, 3), 0.80, np.float32)
        C = np.concatenate([C, np.ones((ny, nx, 1), np.float32)], -1)

        parts = [_quads(P, C)]                                   # MÄTT topp
        # sidofasetter (MÄTTA): framkant röd, bakkant grön (när helt skannad) annars neutral
        zc0 = -T / 2.0
        def edge(j):
            top = P[j]                                            # (nx,3)
            bot = top.copy(); bot[:, 2] = zc0
            return bot, top
        b0, t0 = edge(0)
        parts.append(_wall(b0, t0, [0.59, 0.16, 0.20]))          # röd långsida
        b1, t1 = edge(ny - 1)
        green = [0.20, 0.67, 0.33] if wf >= 0.999 else [0.24, 0.28, 0.34]
        parts.append(_wall(b1, t1, green))
        # ändar (kapsnitt) neutrala
        for i in (0, nx - 1):
            col = [0.31, 0.36, 0.42]
            topcol = P[:, i]; botcol = topcol.copy(); botcol[:, 2] = zc0
            parts.append(_wall(botcol, topcol, col))
        # underside (antagen, platt) — 2×2 räcker
        bx = np.array([-L / 2, L / 2], np.float32)
        by = np.array([-W / 2, -W / 2 + W * wf], np.float32)
        Pb = np.stack([np.broadcast_to(bx[None, :], (2, 2)),
                       np.broadcast_to(by[:, None], (2, 2)),
                       np.full((2, 2), zc0, np.float32)], -1).astype(np.float32)
        Cb = np.broadcast_to(np.array([0.06, 0.10, 0.14, 1.0], np.float32), (2, 2, 4))
        parts.append(_quads(Pb, Cb))

        buf = np.concatenate(parts, 0).astype(np.float32)
        self.setVertexData(QByteArray(buf.tobytes()))
        self.setStride(40)
        self.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Triangles)
        self.addAttribute(_A.PositionSemantic, 0, _A.F32Type)
        self.addAttribute(_A.NormalSemantic, 12, _A.F32Type)
        self.addAttribute(_A.ColorSemantic, 24, _A.F32Type)
        self.setBounds(QVector3D(-L / 2, -W / 2, zc0), QVector3D(L / 2, W / 2, T))
        self.update()
