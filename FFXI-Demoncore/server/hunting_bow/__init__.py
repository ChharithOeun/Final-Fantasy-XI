"""Hunting bow — quiet kills at distance.

A different mechanic from active combat (ranged_combat
already handles raid-style auto-fire). The hunting bow
is the patient shot: nock an arrow, draw, hold, release.
Hold too long and your aim wavers; release too early and
you have no power. Different bows have different draw
weights and different optimal hold windows.

Bow tiers
---------
    SHORT_BOW    light, fast draw — small game
    LONGBOW      classic compromise
    COMPOSITE    layered horn/sinew, heavy hit
    GREATBOW     two-person draw, war piece

Arrow heads
-----------
    BLUNT        knocks small game without ruining hide
    BROADHEAD    standard hunting tip
    BODKIN       armor-piercing
    POISON_TIP   slow but deadly to large game
    BARBED       refuses to fall out, bleeds heavily

Shot resolution
---------------
The shot is a 4-input function:
    (bow, arrow, draw_seconds, target_armor_class)
    -> ShotResult(damage, broke_arrow, ruined_hide)

draw_seconds matters: each bow has a min_draw and an
optimal_draw. Below min_draw, damage is halved (weak
release). Above optimal, damage falls off (held too long,
arm shaking). Right in the window: full damage.

ruined_hide is the hunter's curse — broadhead/bodkin
through a small animal makes the pelt useless. Use blunt
or barbed for trophies.

Public surface
--------------
    BowKind enum
    ArrowHead enum
    BowProfile dataclass (frozen)
    ShotResult dataclass (frozen)
    HuntingBowRegistry
        .craft(bow_id, owner_id, kind, crafted_at) -> bool
        .resolve_shot(bow_id, arrow, draw_seconds,
                      target_armor_class) -> ShotResult
        .profile_for(kind) -> BowProfile
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class BowKind(str, enum.Enum):
    SHORT_BOW = "short_bow"
    LONGBOW = "longbow"
    COMPOSITE = "composite"
    GREATBOW = "greatbow"


class ArrowHead(str, enum.Enum):
    BLUNT = "blunt"
    BROADHEAD = "broadhead"
    BODKIN = "bodkin"
    POISON_TIP = "poison_tip"
    BARBED = "barbed"


@dataclasses.dataclass(frozen=True)
class BowProfile:
    kind: BowKind
    base_damage: int
    min_draw: int        # seconds
    optimal_draw: int    # seconds
    max_useful_draw: int # past this, falloff
    armor_pierce: int    # subtracted from target AC


_PROFILES: dict[BowKind, BowProfile] = {
    BowKind.SHORT_BOW: BowProfile(
        kind=BowKind.SHORT_BOW,
        base_damage=20, min_draw=1,
        optimal_draw=2, max_useful_draw=4,
        armor_pierce=0,
    ),
    BowKind.LONGBOW: BowProfile(
        kind=BowKind.LONGBOW,
        base_damage=35, min_draw=2,
        optimal_draw=3, max_useful_draw=5,
        armor_pierce=5,
    ),
    BowKind.COMPOSITE: BowProfile(
        kind=BowKind.COMPOSITE,
        base_damage=50, min_draw=2,
        optimal_draw=4, max_useful_draw=7,
        armor_pierce=10,
    ),
    BowKind.GREATBOW: BowProfile(
        kind=BowKind.GREATBOW,
        base_damage=80, min_draw=4,
        optimal_draw=6, max_useful_draw=10,
        armor_pierce=20,
    ),
}

# Arrow head modifiers
_ARROW_DAMAGE_MULT: dict[ArrowHead, float] = {
    ArrowHead.BLUNT: 0.7,
    ArrowHead.BROADHEAD: 1.0,
    ArrowHead.BODKIN: 1.1,
    ArrowHead.POISON_TIP: 0.9,    # initial hit lower; venom carries it
    ArrowHead.BARBED: 1.2,
}

_ARROW_PIERCE_BONUS: dict[ArrowHead, int] = {
    ArrowHead.BLUNT: 0,
    ArrowHead.BROADHEAD: 0,
    ArrowHead.BODKIN: 15,
    ArrowHead.POISON_TIP: 0,
    ArrowHead.BARBED: 0,
}

# Heads that ruin a hide on a small target
_HIDE_RUINING: set[ArrowHead] = {
    ArrowHead.BROADHEAD, ArrowHead.BODKIN, ArrowHead.BARBED,
}

# Heads that often break inside the kill
_FRAGILE: set[ArrowHead] = {ArrowHead.BARBED, ArrowHead.POISON_TIP}


@dataclasses.dataclass
class HuntingBow:
    bow_id: str
    owner_id: str
    kind: BowKind
    crafted_at: int


@dataclasses.dataclass(frozen=True)
class ShotResult:
    damage: int
    broke_arrow: bool
    ruined_hide: bool


@dataclasses.dataclass
class HuntingBowRegistry:
    _bows: dict[str, HuntingBow] = dataclasses.field(
        default_factory=dict,
    )

    def craft(
        self, *, bow_id: str, owner_id: str,
        kind: BowKind, crafted_at: int,
    ) -> bool:
        if not bow_id or not owner_id:
            return False
        if bow_id in self._bows:
            return False
        self._bows[bow_id] = HuntingBow(
            bow_id=bow_id, owner_id=owner_id,
            kind=kind, crafted_at=crafted_at,
        )
        return True

    def profile_for(self, *, kind: BowKind) -> BowProfile:
        return _PROFILES[kind]

    def resolve_shot(
        self, *, bow_id: str, arrow: ArrowHead,
        draw_seconds: int, target_armor_class: int,
        target_is_small: bool = False,
    ) -> t.Optional[ShotResult]:
        b = self._bows.get(bow_id)
        if b is None:
            return None
        prof = _PROFILES[b.kind]
        # draw curve: weak / sweet / falloff
        if draw_seconds < prof.min_draw:
            draw_factor = 0.5
        elif draw_seconds <= prof.optimal_draw:
            draw_factor = 1.0
        elif draw_seconds <= prof.max_useful_draw:
            # linear falloff from 1.0 to 0.6
            span = prof.max_useful_draw - prof.optimal_draw
            over = draw_seconds - prof.optimal_draw
            draw_factor = 1.0 - 0.4 * (over / max(span, 1))
        else:
            draw_factor = 0.4  # arms shaking, way overheld
        dmg = prof.base_damage * _ARROW_DAMAGE_MULT[arrow] \
              * draw_factor
        # armor pierce reduces effective AC; remaining AC
        # subtracts from damage (floor at 1)
        pierce = prof.armor_pierce + _ARROW_PIERCE_BONUS[arrow]
        ac = target_armor_class - pierce
        if ac < 0:
            ac = 0
        final = int(dmg) - ac
        if final < 1:
            final = 1
        ruined = target_is_small and arrow in _HIDE_RUINING
        broke = arrow in _FRAGILE
        return ShotResult(
            damage=final, broke_arrow=broke,
            ruined_hide=ruined,
        )

    def get(self, *, bow_id: str) -> t.Optional[HuntingBow]:
        return self._bows.get(bow_id)

    def total_bows(self) -> int:
        return len(self._bows)


__all__ = [
    "BowKind", "ArrowHead", "BowProfile",
    "HuntingBow", "ShotResult", "HuntingBowRegistry",
]
