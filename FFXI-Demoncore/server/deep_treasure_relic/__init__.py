"""Deep treasure relic — rare relic-grade salvage from wrecks.

Most wrecks in the missing_ship_registry yield ordinary
cargo. A handful — those resting in the abyss biomes — are
RELIC WRECKS: hulls of long-lost ships from older eras
(Empyrean traders, Sunken Crown flagship variants, etc.)
that occasionally yield relic-grade item drops.

We don't replace missing_ship_registry's cargo loop. Instead
we publish a SECOND, RARE inventory layer over the same
wrecks: a relic_inventory keyed by ship_id with a small
pool of RELIC_PIECES. Salvaging a relic wreck rolls against
the player's diver_skill + a TH-style modifier; on success
they get one piece.

Relic grades:
  AMBER     - lvl 75-99 historic relics (common pool)
  GOLD      - lvl 119 era pieces
  ABYSSAL   - the very rarest; require ABYSS_PERMIT diver

Each relic wreck has a CAPACITY (how many pieces it can
ever yield before being EXHAUSTED). After exhaustion, the
wreck still drops normal cargo but no more relic rolls
succeed.

Public surface
--------------
    RelicGrade enum   AMBER / GOLD / ABYSSAL
    RelicWreckProfile dataclass
    RelicRoll dataclass
    DeepTreasureRelic
        .seed_wreck(ship_id, grade, capacity)
        .roll(ship_id, diver_skill, treasure_hunter, has_abyss)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class RelicGrade(str, enum.Enum):
    AMBER = "amber"
    GOLD = "gold"
    ABYSSAL = "abyssal"


# success threshold for a roll (player_skill + TH bonus)
_GRADE_DIFFICULTY: dict[RelicGrade, int] = {
    RelicGrade.AMBER: 60,
    RelicGrade.GOLD: 120,
    RelicGrade.ABYSSAL: 200,
}


@dataclasses.dataclass
class RelicWreckProfile:
    ship_id: str
    grade: RelicGrade
    capacity_remaining: int


@dataclasses.dataclass(frozen=True)
class RelicRoll:
    accepted: bool
    ship_id: str
    grade: t.Optional[RelicGrade] = None
    piece_index: int = 0
    exhausted: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class DeepTreasureRelic:
    _wrecks: dict[str, RelicWreckProfile] = dataclasses.field(
        default_factory=dict,
    )
    _rolls_taken: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )

    def seed_wreck(
        self, *, ship_id: str,
        grade: RelicGrade,
        capacity: int,
    ) -> bool:
        if not ship_id or capacity <= 0:
            return False
        if ship_id in self._wrecks:
            return False
        if grade not in _GRADE_DIFFICULTY:
            return False
        self._wrecks[ship_id] = RelicWreckProfile(
            ship_id=ship_id,
            grade=grade,
            capacity_remaining=capacity,
        )
        return True

    def roll(
        self, *, ship_id: str,
        diver_skill: int,
        treasure_hunter: int,
        has_abyss_permit: bool,
    ) -> RelicRoll:
        wreck = self._wrecks.get(ship_id)
        if wreck is None:
            return RelicRoll(False, ship_id, reason="unknown wreck")
        if diver_skill < 0 or treasure_hunter < 0:
            return RelicRoll(False, ship_id, reason="bad metrics")
        if wreck.capacity_remaining <= 0:
            return RelicRoll(
                False, ship_id, exhausted=True,
                reason="exhausted",
            )
        # ABYSSAL grade requires ABYSS_PERMIT
        if wreck.grade == RelicGrade.ABYSSAL and not has_abyss_permit:
            return RelicRoll(
                False, ship_id, reason="abyss permit required",
            )
        threshold = _GRADE_DIFFICULTY[wreck.grade]
        # TH adds 10 per tier (small but real)
        score = diver_skill + (treasure_hunter * 10)
        if score < threshold:
            return RelicRoll(
                False, ship_id, reason="failed roll",
            )
        # success
        wreck.capacity_remaining -= 1
        idx = self._rolls_taken.get(ship_id, 0) + 1
        self._rolls_taken[ship_id] = idx
        exhausted_now = wreck.capacity_remaining == 0
        return RelicRoll(
            accepted=True,
            ship_id=ship_id,
            grade=wreck.grade,
            piece_index=idx,
            exhausted=exhausted_now,
        )

    def remaining_capacity(self, *, ship_id: str) -> int:
        wreck = self._wrecks.get(ship_id)
        return wreck.capacity_remaining if wreck else 0


__all__ = [
    "RelicGrade", "RelicWreckProfile", "RelicRoll",
    "DeepTreasureRelic",
]
