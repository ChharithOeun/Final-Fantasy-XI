"""Spell casting — cast time, fast cast, recast, interrupt.

Casting goes through three phases:
    READY (waiting on recast) -> CASTING (interruptible) -> RECAST

Fast Cast % shortens the CASTING phase. Spell interrupts roll
during damage taken — high MND/aquaveil reduce. Recast clamps to
a minimum of half the base.

Public surface
--------------
    CastingState enum
    SpellCast lifecycle
        .begin(spell_id, cast_time, recast)
        .tick(now)
        .interrupt() / .complete()
    cast_time_with_fast_cast(base, fast_cast_pct)
    recast_with_recast_pct(base, recast_pct)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Caps per canonical FFXI
FAST_CAST_CAP_PCT = 80     # fast cast caps at -80% (50% direct,
                            # 30% gear-cap +30%)
RECAST_CAP_PCT = 80        # recast reduction caps similarly


class CastingState(str, enum.Enum):
    READY = "ready"
    CASTING = "casting"
    RECAST = "recast"


def cast_time_with_fast_cast(
    *, base_seconds: float, fast_cast_pct: int,
) -> float:
    """Apply fast cast to base cast time. Caps at FAST_CAST_CAP_PCT."""
    if base_seconds <= 0:
        raise ValueError("base_seconds must be > 0")
    pct = max(0, min(FAST_CAST_CAP_PCT, fast_cast_pct))
    return max(0.5, base_seconds * (1.0 - pct / 100.0))


def recast_with_recast_pct(
    *, base_seconds: float, recast_pct: int,
) -> float:
    """Apply recast reduction. Caps at RECAST_CAP_PCT."""
    if base_seconds <= 0:
        raise ValueError("base_seconds must be > 0")
    pct = max(0, min(RECAST_CAP_PCT, recast_pct))
    return max(0.5, base_seconds * (1.0 - pct / 100.0))


@dataclasses.dataclass(frozen=True)
class CastResult:
    accepted: bool
    state: CastingState
    finishes_at_tick: t.Optional[float] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class SpellCast:
    actor_id: str
    state: CastingState = CastingState.READY
    casting_spell_id: t.Optional[str] = None
    cast_finishes_at: float = 0.0
    recast_finishes_at: float = 0.0
    fast_cast_pct: int = 0
    recast_pct: int = 0

    def begin(
        self, *,
        spell_id: str,
        base_cast_seconds: float,
        base_recast_seconds: float,
        now_tick: float,
    ) -> CastResult:
        if self.state == CastingState.CASTING:
            return CastResult(
                False, self.state,
                reason="already casting",
            )
        if self.state == CastingState.RECAST and \
                now_tick < self.recast_finishes_at:
            return CastResult(
                False, self.state,
                reason="on recast",
            )
        actual_cast = cast_time_with_fast_cast(
            base_seconds=base_cast_seconds,
            fast_cast_pct=self.fast_cast_pct,
        )
        actual_recast = recast_with_recast_pct(
            base_seconds=base_recast_seconds,
            recast_pct=self.recast_pct,
        )
        self.state = CastingState.CASTING
        self.casting_spell_id = spell_id
        self.cast_finishes_at = now_tick + actual_cast
        self.recast_finishes_at = now_tick + actual_recast
        return CastResult(
            accepted=True,
            state=CastingState.CASTING,
            finishes_at_tick=self.cast_finishes_at,
        )

    def tick(self, *, now_tick: float) -> CastingState:
        """Advance state machine based on current tick."""
        if self.state == CastingState.CASTING:
            if now_tick >= self.cast_finishes_at:
                self.state = CastingState.RECAST
                self.casting_spell_id = None
        if self.state == CastingState.RECAST:
            if now_tick >= self.recast_finishes_at:
                self.state = CastingState.READY
        return self.state

    def interrupt(self) -> bool:
        """Interrupt an active cast. Returns True if a cast was
        actually interrupted."""
        if self.state != CastingState.CASTING:
            return False
        self.state = CastingState.RECAST
        self.casting_spell_id = None
        return True

    def force_complete(self, *, now_tick: float) -> bool:
        """Test/admin helper: force the cast to complete now."""
        if self.state != CastingState.CASTING:
            return False
        self.cast_finishes_at = now_tick
        self.tick(now_tick=now_tick)
        return True


__all__ = [
    "FAST_CAST_CAP_PCT", "RECAST_CAP_PCT",
    "CastingState", "CastResult",
    "cast_time_with_fast_cast", "recast_with_recast_pct",
    "SpellCast",
]
