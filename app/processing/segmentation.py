"""Grind/segmentering för löpande flöde — encoder-klockad, gated av närvaro.

Delar en kontinuerlig ström av matningspositioner i enskilda brädor. REN
tillståndsmaskin (ingen I/O) → enhetstestbar utan hårdvara: mata in
(position_mm, present) löpande via :meth:`BoardGate.update` → få ut händelser
RAD / SLUT per bräda.

Modell:
- ``position_mm`` är monoton bandposition (RoboClaw-encoder). Encodern är
  radklockan: en rad var ``row_pitch_mm``.
- ``present`` är närvarogivaren (fotocell + ev. LR400-höjd). Givaren sitter
  UPPSTRÖMS imaging-linjen (``sensor_offset_mm``), så varje närvaroflank
  översätts till den bandposition där brädkanten når linjen.

Detta klarar godtyckligt mellanrum mellan brädor: mellan brädor är state=TOM och
inga rader klockas; nästa stigande flank startar nästa bräda. ``min_gap_mm``
skiljer en äkta lucka från brus/ådring, ``min_board_mm`` kastar för korta segment.

Avgränsning: grinden är 1D (en bräda i bredd). Två brädor sida vid sida kräver
lateral segmentering per LR400-kanal/kolumn i höjdkartan — separat steg.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class GateState(Enum):
    TOM = auto()        # inget vid/på väg till imaging-linjen
    ARMERAD = auto()    # bräda detekterad uppströms, ej framme vid linjen än
    BRADA = auto()      # bräda passerar linjen → klocka rader


@dataclass
class GateConfig:
    row_pitch_mm: float = 0.5       # matningssteg per rad (encoder-radtrigg)
    sensor_offset_mm: float = 0.0   # givarens avstånd uppströms imaging-linjen
    min_gap_mm: float = 5.0         # present måste vara låg så länge för att avsluta
    min_board_mm: float = 50.0      # kortare segment = brus, kasseras


@dataclass
class GateEvent:
    kind: str            # "rad" | "slut"
    position_mm: float   # bandposition (imaging-linjen) för händelsen
    board_id: int


class BoardGate:
    """Position-/närvarodriven tillståndsmaskin → RAD/SLUT-händelser per bräda."""

    def __init__(self, cfg: GateConfig | None = None):
        self.cfg = cfg or GateConfig()
        self.state = GateState.TOM
        self._board_id = 0
        self._prev_present = False
        self._open_at: float | None = None      # imaging-pos där brädan börjar
        self._board_start: float = 0.0
        self._last_row: float = 0.0
        self._low_since: float | None = None     # pos där present senast blev låg
        self._pending_close: float | None = None  # imaging-pos för bakkanten

    @property
    def board_id(self) -> int:
        return self._board_id

    def update(self, pos_mm: float, present: bool) -> list[GateEvent]:
        cfg = self.cfg
        ev: list[GateEvent] = []
        rising = present and not self._prev_present
        falling = (not present) and self._prev_present
        self._prev_present = present

        if rising:
            # bräda (åter)detekterad → avbryt ev. pågående stängning
            self._pending_close = None
            self._low_since = None
            if self.state is GateState.TOM:
                self._open_at = pos_mm + cfg.sensor_offset_mm
                self.state = GateState.ARMERAD
        if falling and self.state is GateState.BRADA:
            self._low_since = pos_mm
            self._pending_close = pos_mm + cfg.sensor_offset_mm

        # framkanten når linjen → öppna grind
        if self.state is GateState.ARMERAD and pos_mm >= (self._open_at or 0.0):
            self._board_id += 1
            self._board_start = self._open_at or pos_mm
            self._last_row = self._board_start
            self.state = GateState.BRADA
            if not present:
                # framkanten redan passerad utan present vid linjen → self-stäng (brus)
                self._low_since = pos_mm
                self._pending_close = pos_mm + cfg.sensor_offset_mm

        if self.state is GateState.BRADA:
            # klocka rader fram till nuvarande pos, men inte förbi bakkanten
            limit = pos_mm if self._pending_close is None else min(pos_mm, self._pending_close)
            while self._last_row + cfg.row_pitch_mm <= limit:
                self._last_row += cfg.row_pitch_mm
                ev.append(GateEvent("rad", self._last_row, self._board_id))
            # stäng först när gapet bekräftats (debounce) och bakkanten passerat linjen
            if (self._pending_close is not None
                    and self._low_since is not None
                    and (pos_mm - self._low_since) >= cfg.min_gap_mm
                    and pos_mm >= self._pending_close):
                length = self._last_row - self._board_start
                if length >= cfg.min_board_mm:
                    ev.append(GateEvent("slut", self._last_row, self._board_id))
                else:
                    self._board_id -= 1          # för kort → kassera id:t
                self.state = GateState.TOM
                self._open_at = self._low_since = self._pending_close = None
        return ev
