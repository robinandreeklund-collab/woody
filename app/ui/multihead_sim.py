"""Master-GUI-kontroller för multihuvuds-simuleringen (live demo).

Wrappar ``app.processing.multihead.simulate`` i ett QObject + en bildprovider så
master-GUI:t kan visa N läshuvuden över en lång bräda med animerad encoder-svep
(synk) och fusion. Tunga beräkningen körs i en bakgrundstråd → GUI fryser inte.

QML: ``image://simhead/board?<rev>`` (ytfoto) och ``image://simhead/fused?<rev>``
(fuserad höjdkarta). ``simHead`` är kontext-egenskapen.
"""
from __future__ import annotations

import threading

import numpy as np
from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider

from ..processing.multihead import simulate

_DISP_LEN_PX = 2200          # nedsamplad längd för bilder (10800 → 2200 räcker visuellt
_PROFILE_PTS = 480           # punkter i profilkurvorna (QML Canvas)


def _turbo_rgb(z: np.ndarray) -> np.ndarray:
    """Höjdkarta (mm) → turbo-liknande RGB (uint8) för 3D/heatmap."""
    lo, hi = float(np.percentile(z, 1)), float(np.percentile(z, 99))
    t = np.clip((z - lo) / (hi - lo + 1e-6), 0, 1)
    r = np.clip(34 + t * 221, 0, 255)
    g = np.clip(40 + np.sin(t * np.pi) * 200, 0, 255)
    b = np.clip(220 - t * 180, 0, 255)
    return np.ascontiguousarray(np.stack([r, g, b], axis=-1).astype(np.uint8))


def _downsample_len(img: np.ndarray, target: int) -> np.ndarray:
    """Nedsampla en (H, W[,3])-bild i längdled (W) till ~target kolumner."""
    W = img.shape[1]
    if W <= target:
        return np.ascontiguousarray(img)
    xs = np.linspace(0, W - 1, target).astype(int)
    return np.ascontiguousarray(img[:, xs])


class MultiHeadSimImageProvider(QQuickImageProvider):
    def __init__(self, ctrl):
        super().__init__(QQuickImageProvider.Image)
        self._ctrl = ctrl

    def requestImage(self, image_id: str, size, requested_size):
        name = image_id.split("?", 1)[0]
        img = self._ctrl.image(name)
        if img is None or img.isNull():
            return QImage(2, 2, QImage.Format_RGB888)
        return img


class MultiHeadSimController(QObject):
    configChanged = Signal()
    resultChanged = Signal()
    feedChanged = Signal()
    runningChanged = Signal()
    busyChanged = Signal()
    _resultReady = Signal(object)        # korsar tråd → _apply körs på GUI-tråden

    def __init__(self, n_heads=6, total_len_mm=5400.0, overlap_mm=80.0, parent=None):
        super().__init__(parent)
        self._n = n_heads
        self._len = total_len_mm
        self._overlap = overlap_mm
        self._seed = 20240614
        self._res = None
        self._images: dict = {}
        self._rev = 0
        self._busy = False
        self._feed = 0.0                  # 0..1 (encoder-svep)
        self._running = False
        self._timer = QTimer(self); self._timer.setInterval(40)   # ~25 fps
        self._timer.timeout.connect(self._tick)
        self._resultReady.connect(self._apply)    # queued (worker-tråd → GUI-tråd)
        self.recompute()

    # ----------------------------------------------------- beräkning (tråd)
    @Slot()
    def recompute(self):
        if self._busy:
            return
        self._busy = True; self.busyChanged.emit()
        n, L, ov, seed = self._n, self._len, self._overlap, self._seed
        threading.Thread(target=self._worker, args=(n, L, ov, seed), daemon=True).start()

    def _worker(self, n, L, ov, seed):
        try:
            # lägre px/mm → snabb generering; räcker gott för demo-visningen
            res = simulate(total_len_mm=L, n_heads=n, overlap_mm=ov, seed=seed,
                           px_per_mm=0.8)
        except Exception as exc:
            print("[simhead] beräkning misslyckades:", exc)
            res = None
        self._resultReady.emit(res)              # → _apply på GUI-tråden (queued)

    @Slot(object)
    def _apply(self, res):
        self._busy = False; self.busyChanged.emit()
        if res is None:
            return
        self._res = res
        # bygg bilder en gång (nedsamplade i längd)
        surf = _downsample_len(res.board.surface, _DISP_LEN_PX)
        h, w = surf.shape[:2]
        self._images["board"] = QImage(bytes(surf.tobytes()), w, h, 3 * w,
                                       QImage.Format_RGB888).copy()
        fused = _turbo_rgb(_downsample_len(res.fused_zmap, _DISP_LEN_PX))
        fh, fw = fused.shape[:2]
        self._images["fused"] = QImage(bytes(fused.tobytes()), fw, fh, 3 * fw,
                                       QImage.Format_RGB888).copy()
        self._rev += 1
        self._feed = 0.0
        self.resultChanged.emit(); self.feedChanged.emit()

    def image(self, name: str):
        return self._images.get(name)

    # ----------------------------------------------------- animation
    def _tick(self):
        if self._res is None:
            return
        self._feed = min(1.0, self._feed + 0.012)
        self.feedChanged.emit()
        if self._feed >= 1.0:
            self._running = False; self._timer.stop(); self.runningChanged.emit()

    @Slot()
    def toggleRun(self):
        if self._res is None:
            return
        if self._feed >= 1.0:
            self._feed = 0.0
        self._running = not self._running
        self._timer.start() if self._running else self._timer.stop()
        self.runningChanged.emit(); self.feedChanged.emit()

    @Slot()
    def restart(self):
        self._feed = 0.0; self.feedChanged.emit()

    @Slot()
    def newBoard(self):
        self._seed = (self._seed * 1103515245 + 12345) & 0x7FFFFFFF
        self.recompute()

    @Slot(int)
    def setHeads(self, n: int):
        n = max(2, min(12, int(n)))
        if n != self._n:
            self._n = n; self.configChanged.emit(); self.recompute()

    # ----------------------------------------------------- egenskaper
    @Property(int, notify=configChanged)
    def nHeads(self): return self._n
    @Property(float, notify=configChanged)
    def totalLen(self): return self._len
    @Property(float, notify=configChanged)
    def overlap(self): return self._overlap
    @Property(bool, notify=busyChanged)
    def busy(self): return self._busy
    @Property(bool, notify=runningChanged)
    def running(self): return self._running
    @Property(float, notify=feedChanged)
    def feed(self): return self._feed
    @Property(int, notify=resultChanged)
    def rev(self): return self._rev

    @Property(float, notify=configChanged)
    def widthMm(self):
        return self._res.width_mm if self._res else 75.0

    @Property("QVariantList", notify=resultChanged)
    def heads(self):
        if not self._res:
            return []
        corr = self._res.metrics["corrections_mm"]
        return [{"idx": h.idx, "label": h.label, "start_mm": h.start_mm, "end_mm": h.end_mm,
                 "bias_mm": round(h.bias_mm, 3), "corr_mm": round(corr[h.idx], 3)}
                for h in self._res.heads]

    @Property("QVariantList", notify=resultChanged)
    def seams(self):
        if not self._res:
            return []
        return [{"x_mm": round(s["x_mm"], 1), "lo_mm": round(s["lo_mm"], 1),
                 "hi_mm": round(s["hi_mm"], 1), "before_mm": round(s["rms_before_mm"], 3),
                 "after_mm": round(s["rms_after_mm"], 3), "heads": list(s["heads"])}
                for s in self._res.seams]

    @Property("QVariantMap", notify=resultChanged)
    def metrics(self):
        return dict(self._res.metrics) if self._res else {}

    def _prof(self, arr):
        a = np.asarray(arr, dtype=float)
        xs = np.linspace(0, len(a) - 1, min(_PROFILE_PTS, len(a))).astype(int)
        return [round(float(v), 4) for v in a[xs]]

    @Property("QVariantList", notify=resultChanged)
    def trueProfile(self): return self._prof(self._res.true_profile) if self._res else []
    @Property("QVariantList", notify=resultChanged)
    def naiveProfile(self): return self._prof(self._res.naive_profile) if self._res else []
    @Property("QVariantList", notify=resultChanged)
    def fusedProfile(self): return self._prof(self._res.anchored_profile) if self._res else []
