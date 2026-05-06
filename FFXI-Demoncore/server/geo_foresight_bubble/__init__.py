"""GEO Foresight bubble — Indi-Foresight / Geo-Foresight.

A new GEO spell pair joining the existing luopan system.
Where Indi-Frailty weakens enemy DEF and Geo-Wilt drains
their stats, FORESIGHT does something different: it grants
TELEGRAPH VISIBILITY to allies within the bubble radius.
The boss's wind-ups, AOE shapes, cone markers, and ring
indicators become visible only to players standing inside
the GEO's area of effect.

Two flavors, mirroring the canonical GEO spell pattern:
    INDI_FORESIGHT     — anchored on the GEO caster, follows
                         their position, lasts up to 5 minutes
                         active, drains MP per perpetuation
                         tick (3 MP/sec)
    GEO_FORESIGHT      — placed on a Luopan at a fixed
                         location, lasts up to 5 minutes,
                         drains HP per tick from the Luopan
                         (which has its own HP pool); when
                         the Luopan dies, bubble ends

Both consume MP to cast (180 MP base) and require the GEO
job. Radius is 8 yalms by default (extendable via Luopan
Bias and the Bolster JA).

This module bridges to telegraph_visibility_gate: every
TICK while a Foresight bubble is up, it iterates over the
allies inside the radius and refreshes their
GEO_FORESIGHT visibility grant. Allies who leave the
radius lose visibility on the next tick (graceful 2-second
expiry to avoid stutter).

Public surface
--------------
    ForesightFlavor enum
    ForesightBubble dataclass (mutable)
    BubbleResult dataclass (frozen)
    GeoForesightBubble
        .cast(caster_id, flavor, anchor_position,
              now_seconds) -> BubbleResult
        .tick(bubble_id, now_seconds,
              allies_in_radius, gate) -> int
        .end_bubble(bubble_id, reason)
        .active_bubble(caster_id) -> Optional[ForesightBubble]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.telegraph_visibility_gate import (
    TelegraphVisibilityGate, VisibilitySource,
)


class ForesightFlavor(str, enum.Enum):
    INDI_FORESIGHT = "indi_foresight"
    GEO_FORESIGHT = "geo_foresight"


# Tuning knobs
INDI_PERP_MP_PER_SEC = 3
GEO_LUOPAN_HP = 600           # Luopan HP pool
GEO_PERP_HP_PER_SEC = 5       # Luopan loses HP per sec
DEFAULT_RADIUS_YALMS = 8
MAX_DURATION_SECONDS = 300    # 5 minutes
CAST_MP_COST = 180
GRACE_EXPIRY_SECONDS = 2      # how long visibility lingers after
                               # leaving radius
INITIAL_VISIBILITY_SECONDS = 5  # first grant lasts this long; tick
                                 # extends


@dataclasses.dataclass
class ForesightBubble:
    bubble_id: str
    caster_id: str
    flavor: ForesightFlavor
    anchor_id: t.Optional[str]   # for INDI: caster_id; for GEO:
                                  # luopan_id
    radius_yalms: int
    cast_at: int
    expires_at: int
    luopan_hp: int = 0    # 0 for INDI (uses caster MP elsewhere)
    ended: bool = False
    end_reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class BubbleResult:
    accepted: bool
    bubble_id: str = ""
    flavor: t.Optional[ForesightFlavor] = None
    expires_at: int = 0
    mp_cost: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class GeoForesightBubble:
    _bubbles: dict[str, ForesightBubble] = dataclasses.field(
        default_factory=dict,
    )
    # caster_id -> bubble_id (one bubble of each flavor per caster)
    _by_caster: dict[tuple[str, ForesightFlavor], str] = (
        dataclasses.field(default_factory=dict)
    )
    _next_id: int = 0

    def cast(
        self, *, caster_id: str, flavor: ForesightFlavor,
        anchor_id: t.Optional[str] = None,
        radius_yalms: int = DEFAULT_RADIUS_YALMS,
        now_seconds: int = 0,
    ) -> BubbleResult:
        if not caster_id:
            return BubbleResult(False, reason="blank caster")
        if radius_yalms <= 0:
            return BubbleResult(False, reason="bad radius")
        # one of each flavor per caster
        key = (caster_id, flavor)
        if key in self._by_caster:
            old_id = self._by_caster[key]
            old = self._bubbles.get(old_id)
            if old and not old.ended and now_seconds < old.expires_at:
                return BubbleResult(
                    False, reason="already active",
                )
        if flavor == ForesightFlavor.INDI_FORESIGHT:
            anchor = caster_id
            luopan_hp = 0
        else:
            if not anchor_id:
                return BubbleResult(False, reason="luopan_id required")
            anchor = anchor_id
            luopan_hp = GEO_LUOPAN_HP
        self._next_id += 1
        bid = f"foresight_{self._next_id}"
        b = ForesightBubble(
            bubble_id=bid, caster_id=caster_id, flavor=flavor,
            anchor_id=anchor, radius_yalms=radius_yalms,
            cast_at=now_seconds,
            expires_at=now_seconds + MAX_DURATION_SECONDS,
            luopan_hp=luopan_hp,
        )
        self._bubbles[bid] = b
        self._by_caster[key] = bid
        return BubbleResult(
            accepted=True, bubble_id=bid, flavor=flavor,
            expires_at=b.expires_at, mp_cost=CAST_MP_COST,
        )

    def tick(
        self, *, bubble_id: str, now_seconds: int,
        allies_in_radius: t.Iterable[str],
        gate: TelegraphVisibilityGate,
        dt_seconds: int = 1,
    ) -> int:
        b = self._bubbles.get(bubble_id)
        if b is None or b.ended:
            return 0
        if now_seconds >= b.expires_at:
            self._end(b, reason="duration_expired")
            return 0
        # GEO Luopan ticks down its HP
        if b.flavor == ForesightFlavor.GEO_FORESIGHT:
            b.luopan_hp -= GEO_PERP_HP_PER_SEC * dt_seconds
            if b.luopan_hp <= 0:
                b.luopan_hp = 0
                self._end(b, reason="luopan_hp_zero")
                return 0
        # Refresh visibility for each ally in radius
        granted = 0
        # Each tick extends grant to now + INITIAL_VISIBILITY_SECONDS
        # (but at minimum grace period from now)
        for ally in allies_in_radius:
            if not ally:
                continue
            ok = gate.grant_visibility(
                player_id=ally,
                source=VisibilitySource.GEO_FORESIGHT,
                granted_at=now_seconds,
                expires_at=now_seconds + INITIAL_VISIBILITY_SECONDS,
                granted_by=b.caster_id,
            )
            if ok:
                granted += 1
        return granted

    def damage_luopan(
        self, *, bubble_id: str, amount: int,
    ) -> bool:
        b = self._bubbles.get(bubble_id)
        if b is None or b.ended or amount <= 0:
            return False
        if b.flavor != ForesightFlavor.GEO_FORESIGHT:
            return False
        b.luopan_hp = max(0, b.luopan_hp - amount)
        if b.luopan_hp == 0:
            self._end(b, reason="luopan_killed")
        return True

    def _end(self, b: ForesightBubble, *, reason: str) -> None:
        b.ended = True
        b.end_reason = reason
        # also drop _by_caster entry if it points to this bubble
        key = (b.caster_id, b.flavor)
        if self._by_caster.get(key) == b.bubble_id:
            del self._by_caster[key]

    def end_bubble(
        self, *, bubble_id: str, reason: str = "manual",
    ) -> bool:
        b = self._bubbles.get(bubble_id)
        if b is None or b.ended:
            return False
        self._end(b, reason=reason)
        return True

    def active_bubble(
        self, *, caster_id: str, flavor: ForesightFlavor,
    ) -> t.Optional[ForesightBubble]:
        key = (caster_id, flavor)
        bid = self._by_caster.get(key)
        if bid is None:
            return None
        b = self._bubbles.get(bid)
        if b is None or b.ended:
            return None
        return b


__all__ = [
    "ForesightFlavor", "ForesightBubble", "BubbleResult",
    "GeoForesightBubble",
    "INDI_PERP_MP_PER_SEC", "GEO_LUOPAN_HP",
    "GEO_PERP_HP_PER_SEC", "DEFAULT_RADIUS_YALMS",
    "MAX_DURATION_SECONDS", "CAST_MP_COST",
    "GRACE_EXPIRY_SECONDS", "INITIAL_VISIBILITY_SECONDS",
]
