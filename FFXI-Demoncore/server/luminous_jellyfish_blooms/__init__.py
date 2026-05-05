"""Luminous jellyfish blooms — LUMINOUS_DRIFT gathering loop.

The jellyfish gel-cities of LUMINOUS_DRIFT bloom on a slow
tide-gated cycle. Each bloom event releases BLOOM_ESSENCE
nodes — drifting bioluminescent globules that players can
harvest while the bloom is open. Closed blooms are cold and
empty; open blooms saturate the zone with light.

Tide gate: blooms only OPEN during the HIGH tide phase
(per tide_cycle_clock). Outside HIGH, the city is dormant
and harvesting is rejected.

Bloom kinds:
  PEARLBLOOM      - common; small light pearls
  EMBERBLOOM      - mid; warm-glow gel; FIRE-element craft
  REQUIEMBLOOM    - rare; only blooms after a SUNKEN_CROWN
                    sighting in nearby waters; ICE-element

Per-bloom node yield decays as more harvesters pull from it
in the same window. We don't track node-level coordinates —
each player just rolls against bloom_strength which decays
1 per harvest within the same tide-window.

Public surface
--------------
    BloomKind enum
    BloomState enum
    HarvestResult dataclass
    LuminousBlooms
        .open_bloom(kind, tide_phase, now_seconds)
        .close_bloom(kind, now_seconds)
        .harvest(player_id, kind, tide_phase, now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class BloomKind(str, enum.Enum):
    PEARLBLOOM = "pearlbloom"
    EMBERBLOOM = "emberbloom"
    REQUIEMBLOOM = "requiembloom"


class BloomState(str, enum.Enum):
    DORMANT = "dormant"
    OPEN = "open"


_BASE_STRENGTH: dict[BloomKind, int] = {
    BloomKind.PEARLBLOOM: 30,
    BloomKind.EMBERBLOOM: 18,
    BloomKind.REQUIEMBLOOM: 8,
}

# only HIGH tide phase opens blooms
_HIGH_TIDE = "high"


@dataclasses.dataclass
class _Bloom:
    kind: BloomKind
    state: BloomState
    strength: int = 0
    opened_at: int = 0


@dataclasses.dataclass(frozen=True)
class HarvestResult:
    accepted: bool
    kind: t.Optional[BloomKind] = None
    units: int = 0
    strength_after: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class LuminousBlooms:
    _blooms: dict[BloomKind, _Bloom] = dataclasses.field(
        default_factory=dict,
    )

    def open_bloom(
        self, *, kind: BloomKind,
        tide_phase: str,
        now_seconds: int,
    ) -> bool:
        if kind not in _BASE_STRENGTH:
            return False
        if tide_phase != _HIGH_TIDE:
            return False
        existing = self._blooms.get(kind)
        if existing is not None and existing.state == BloomState.OPEN:
            return False
        self._blooms[kind] = _Bloom(
            kind=kind,
            state=BloomState.OPEN,
            strength=_BASE_STRENGTH[kind],
            opened_at=now_seconds,
        )
        return True

    def close_bloom(
        self, *, kind: BloomKind, now_seconds: int,
    ) -> bool:
        bloom = self._blooms.get(kind)
        if bloom is None or bloom.state != BloomState.OPEN:
            return False
        bloom.state = BloomState.DORMANT
        bloom.strength = 0
        return True

    def state_of(self, *, kind: BloomKind) -> BloomState:
        bloom = self._blooms.get(kind)
        if bloom is None:
            return BloomState.DORMANT
        return bloom.state

    def harvest(
        self, *, player_id: str,
        kind: BloomKind,
        tide_phase: str,
        now_seconds: int,
    ) -> HarvestResult:
        if not player_id:
            return HarvestResult(False, reason="bad player")
        if kind not in _BASE_STRENGTH:
            return HarvestResult(False, reason="unknown bloom")
        if tide_phase != _HIGH_TIDE:
            return HarvestResult(
                False, reason="tide not high",
            )
        bloom = self._blooms.get(kind)
        if bloom is None or bloom.state != BloomState.OPEN:
            return HarvestResult(
                False, reason="bloom not open",
            )
        if bloom.strength <= 0:
            return HarvestResult(
                False, kind=kind,
                strength_after=0,
                reason="bloom depleted",
            )
        bloom.strength -= 1
        return HarvestResult(
            accepted=True,
            kind=kind,
            units=1,
            strength_after=bloom.strength,
        )

    def strength_of(self, *, kind: BloomKind) -> int:
        bloom = self._blooms.get(kind)
        return bloom.strength if bloom else 0


__all__ = [
    "BloomKind", "BloomState", "HarvestResult",
    "LuminousBlooms",
]
