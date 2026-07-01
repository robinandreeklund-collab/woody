"""Qt Quick 3D-geometri för den skannade brädan — byggs på GPU:n (desktop).

Tar controllerns mesh (höjdrutnät + färg) och bygger en triangelmesh med
position, normal, UV och per-vertex-färg → renderas med ljus/MSAA i View3D.
Färgläge: 0 höjd · 1 avvikelse · 2 skuggad · 3 foto (UV-mappad äkta yttextur).
Solid: mätt topp + sidofasetter (röd/grön) + antagen underside.
"""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import QByteArray, Property, Signal, Slot
from PySide6.QtGui import QVector3D
from PySide6.QtQuick3D import QQuick3DGeometry

_A = QQuick3DGeometry.Attribute
_STRIDE = 12 * 4          # pos3 + normal3 + uv2 + color4


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


def _quads(P, U, C):
    """P(h,w,3) U(h,w,2) C(h,w,4) → (N,12) [pos3,normal3,uv2,rgba4], 2 tris/cell."""
    a, b, c, d = P[:-1, :-1], P[:-1, 1:], P[1:, 1:], P[1:, :-1]
    Ua, Ub, Uc, Ud = U[:-1, :-1], U[:-1, 1:], U[1:, 1:], U[1:, :-1]
    Ca, Cb, Cc, Cd = C[:-1, :-1], C[:-1, 1:], C[1:, 1:], C[1:, :-1]
    n1 = np.cross(b - a, c - a); n1 /= np.linalg.norm(n1, axis=-1, keepdims=True) + 1e-9
    n2 = np.cross(c - a, d - a); n2 /= np.linalg.norm(n2, axis=-1, keepdims=True) + 1e-9

    def pk(pos, nor, uv, col):
        return np.concatenate([pos, np.broadcast_to(nor, pos.shape), uv, col], axis=-1)

    t1 = np.stack([pk(a, n1, Ua, Ca), pk(b, n1, Ub, Cb), pk(c, n1, Uc, Cc)], axis=2)
    t2 = np.stack([pk(a, n2, Ua, Ca), pk(c, n2, Uc, Cc), pk(d, n2, Ud, Cd)], axis=2)
    return np.concatenate([t1, t2], axis=2).reshape(-1, 12).astype(np.float32)


def _wall(line_top, zc0, uv_line, color, y_off=0.0):
    """En sidovägg från en topplinje ner till z=zc0. line_top,uv_line: (n,..).
    ``y_off`` lutar väggens underkant i Y (sågad kant-fas → sidan ej spikrak)."""
    top = line_top
    bot = top.copy(); bot[:, 2] = zc0; bot[:, 1] += y_off
    P = np.stack([bot, top], 0)                          # (2,n,3)
    U = np.stack([uv_line, uv_line], 0)                  # (2,n,2)
    C = np.broadcast_to(np.array(color + [1.0], np.float32), (2, top.shape[0], 4))
    return _quads(P, U, C)


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

        X = ((np.arange(nx) / (nx - 1)) - 0.5) * L
        Y = -W / 2 + (np.arange(ny) / (ny - 1)) * (W * wf)
        zc0 = -T / 2.0
        P = np.stack([np.broadcast_to(X[None, :], (ny, nx)),
                      np.broadcast_to(Y[:, None], (ny, nx)),
                      (T + Z * exag - T / 2)], -1).astype(np.float32)
        # UV: u längs längden (0..1), v längs skannad bredd (0..wf)
        u = (np.arange(nx) / (nx - 1)).astype(np.float32)
        v = ((np.arange(ny) / (ny - 1)) * wf).astype(np.float32)
        U = np.stack([np.broadcast_to(u[None, :], (ny, nx)),
                      np.broadcast_to(v[:, None], (ny, nx))], -1).astype(np.float32)

        if self._mode == 0:
            C = _turbo((Z - zmin) / span)
        elif self._mode == 1:
            C = _diverge(Z / maxabs)
        elif self._mode == 3:
            C = np.ones((ny, nx, 3), np.float32)             # vit → texturen ger färgen
        else:
            C = np.full((ny, nx, 3), 0.80, np.float32)
        C = np.concatenate([C, np.ones((ny, nx, 1), np.float32)], -1)

        parts = [_quads(P, U, C)]                            # MÄTT topp
        whitew = self._mode == 3
        bev = m.get("bevel", [0.0, 0.0])                     # sågad kant-lutning (mm)
        # MÄTTA sidoytor: V-kant (RÖD-huvudet) + H-kant (GRÖN-huvudet) — alltid
        # tydligt färgade. 500 mm-ändar + underside = EJ mätta (neutralt/mörkt).
        red = [1.0, 1.0, 1.0] if whitew else [0.78, 0.22, 0.27]   # V-kant (RÖD)
        grn = [1.0, 1.0, 1.0] if whitew else ([0.20, 0.70, 0.36] if wf >= 0.999
                                              else [0.24, 0.28, 0.34])  # H-kant (GRÖN)
        neu = [1.0, 1.0, 1.0] if whitew else [0.26, 0.31, 0.38]   # ände — ej mätt
        parts.append(_wall(P[0].copy(), zc0, U[0], red, y_off=+float(bev[0])))     # V-kant
        parts.append(_wall(P[ny - 1].copy(), zc0, U[ny - 1], grn, y_off=-float(bev[1])))  # H-kant
        parts.append(_wall(P[:, 0].copy(), zc0, U[:, 0], neu))
        parts.append(_wall(P[:, nx - 1].copy(), zc0, U[:, nx - 1], neu))
        # underside (antagen, platt) — 2×2
        bx = np.array([-L / 2, L / 2], np.float32)
        by = np.array([-W / 2, -W / 2 + W * wf], np.float32)
        Pb = np.stack([np.broadcast_to(bx[None, :], (2, 2)),
                       np.broadcast_to(by[:, None], (2, 2)),
                       np.full((2, 2), zc0, np.float32)], -1).astype(np.float32)
        Ub = np.full((2, 2, 2), 0.5, np.float32)
        cb = [1.0, 1.0, 1.0] if whitew else [0.06, 0.10, 0.14]
        Cb = np.broadcast_to(np.array(cb + [1.0], np.float32), (2, 2, 4))
        parts.append(_quads(Pb, Ub, Cb))

        buf = np.concatenate(parts, 0).astype(np.float32)
        self.setVertexData(QByteArray(buf.tobytes()))
        self.setStride(_STRIDE)
        self.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Triangles)
        self.addAttribute(_A.PositionSemantic, 0, _A.F32Type)
        self.addAttribute(_A.NormalSemantic, 12, _A.F32Type)
        self.addAttribute(_A.TexCoord0Semantic, 24, _A.F32Type)
        self.addAttribute(_A.ColorSemantic, 32, _A.F32Type)
        self.setBounds(QVector3D(-L / 2, -W / 2, zc0), QVector3D(L / 2, W / 2, T))
        self.update()
