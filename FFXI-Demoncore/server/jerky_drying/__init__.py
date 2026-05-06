"""Jerky drying — preserve meat for travel.

Raw meat spoils. Cooked meat lasts a few hours. Jerky
lasts days. The drying station turns raw meat into
travel-stable jerky over a fixed cure time, requiring
salt and dry air (won't cure during RAIN/THUNDERSTORM).

A drying rack holds N slabs simultaneously. Each slab
goes through stages:
    FRESH    just placed, 0..30% cured
    DRYING   30..70%
    NEARLY   70..99%
    READY    100% — pull off the rack as jerky

If interrupted by humid weather mid-cure, slab regresses
back to FRESH (lose progress). Salt cost: 1 unit per slab.

Public surface
--------------
    DryingStage enum
    JerkySlab dataclass (mutable)
    JerkyDryingRack
        .place_slab(slab_id, rack_id, raw_meat_kind,
                    salt_available, started_at) -> bool
        .tick(rack_id, dt_seconds, weather_humid) -> int
            (returns how many slabs are READY)
        .pull_slab(slab_id) -> Optional[str]    (jerky kind)
        .stage_of(slab_id) -> DryingStage
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class DryingStage(str, enum.Enum):
    FRESH = "fresh"
    DRYING = "drying"
    NEARLY = "nearly"
    READY = "ready"


_RACK_CAPACITY = 6
_CURE_SECONDS = 3600   # 1 hr per slab


@dataclasses.dataclass
class JerkySlab:
    slab_id: str
    rack_id: str
    raw_meat_kind: str
    progress_seconds: int = 0


def _stage_for(progress: int) -> DryingStage:
    pct = (progress * 100) // _CURE_SECONDS
    if pct >= 100:
        return DryingStage.READY
    if pct >= 70:
        return DryingStage.NEARLY
    if pct >= 30:
        return DryingStage.DRYING
    return DryingStage.FRESH


@dataclasses.dataclass
class JerkyDryingRack:
    _racks: dict[str, list[str]] = dataclasses.field(
        default_factory=dict,
    )
    _slabs: dict[str, JerkySlab] = dataclasses.field(
        default_factory=dict,
    )

    def place_slab(
        self, *, slab_id: str, rack_id: str,
        raw_meat_kind: str, salt_available: int,
        started_at: int,
    ) -> bool:
        if not slab_id or not rack_id:
            return False
        if not raw_meat_kind.startswith("raw_"):
            return False
        if salt_available < 1:
            return False
        rack = self._racks.setdefault(rack_id, [])
        if len(rack) >= _RACK_CAPACITY:
            return False
        if slab_id in self._slabs:
            return False
        self._slabs[slab_id] = JerkySlab(
            slab_id=slab_id, rack_id=rack_id,
            raw_meat_kind=raw_meat_kind,
            progress_seconds=0,
        )
        rack.append(slab_id)
        return True

    def tick(
        self, *, rack_id: str, dt_seconds: int,
        weather_humid: bool = False,
    ) -> int:
        rack = self._racks.get(rack_id)
        if rack is None:
            return 0
        if dt_seconds <= 0:
            return self._count_ready(rack_id)
        for sid in rack:
            s = self._slabs[sid]
            if weather_humid:
                # regress to FRESH
                s.progress_seconds = 0
            else:
                s.progress_seconds = min(
                    _CURE_SECONDS,
                    s.progress_seconds + dt_seconds,
                )
        return self._count_ready(rack_id)

    def _count_ready(self, rack_id: str) -> int:
        rack = self._racks.get(rack_id, [])
        return sum(
            1 for sid in rack
            if self._slabs[sid].progress_seconds >= _CURE_SECONDS
        )

    def pull_slab(
        self, *, slab_id: str,
    ) -> t.Optional[str]:
        s = self._slabs.get(slab_id)
        if s is None:
            return None
        if s.progress_seconds < _CURE_SECONDS:
            return None
        # remove from rack and slabs
        rack = self._racks.get(s.rack_id, [])
        if slab_id in rack:
            rack.remove(slab_id)
        del self._slabs[slab_id]
        # raw_meat → jerky (e.g. raw_buffalo → jerky_buffalo)
        return "jerky_" + s.raw_meat_kind[4:]

    def stage_of(
        self, *, slab_id: str,
    ) -> DryingStage:
        s = self._slabs.get(slab_id)
        if s is None:
            return DryingStage.FRESH
        return _stage_for(s.progress_seconds)

    def total_slabs(self) -> int:
        return len(self._slabs)


__all__ = [
    "DryingStage", "JerkySlab", "JerkyDryingRack",
]
