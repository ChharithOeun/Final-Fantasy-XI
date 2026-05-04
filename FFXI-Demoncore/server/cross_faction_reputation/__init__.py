"""Cross-faction reputation — bridges hume and beastman sides.

A hume player who quietly does jobs for beastmen earns a SHADOW
REPUTATION on each beastman faction. A beastman player likewise
can earn a CIVIL REPUTATION on hume nations through honest
trade and refused conflict.

The mechanic is symmetric. Each player has, per (own_faction,
target_faction), a -1000..+1000 score. Quest completions
adjust it; betraying your own side caps the score.

This sits BESIDE the canon faction_reputation: that one tracks
your nation's view of you. cross_faction_reputation tracks the
OPPOSING culture's view.

Public surface
--------------
    SideKind enum    HUME_NATIONS / BEASTMAN
    StandingTier enum  HOSTILE -> NEUTRAL -> ACQUAINTED ->
                        TRUSTED -> EXALTED
    CrossFactionReputation
        .modify(player_id, own_side, target_faction, delta)
        .standing(player_id, target_faction) -> tier
        .points(player_id, target_faction) -> int
        .reset(player_id, target_faction)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Score bounds.
MIN_SCORE = -1000
MAX_SCORE = 1000


class SideKind(str, enum.Enum):
    HUME_NATIONS = "hume_nations"
    BEASTMAN = "beastman"


class StandingTier(str, enum.Enum):
    HOSTILE = "hostile"        # < -300
    NEUTRAL = "neutral"        # -300 .. 99
    ACQUAINTED = "acquainted"  # 100 .. 399
    TRUSTED = "trusted"        # 400 .. 799
    EXALTED = "exalted"        # 800 +


_TIER_THRESHOLDS: tuple[
    tuple[StandingTier, int], ...,
] = (
    (StandingTier.EXALTED, 800),
    (StandingTier.TRUSTED, 400),
    (StandingTier.ACQUAINTED, 100),
    (StandingTier.NEUTRAL, -300),
)


def _tier_for_score(score: int) -> StandingTier:
    for tier, threshold in _TIER_THRESHOLDS:
        if score >= threshold:
            return tier
    return StandingTier.HOSTILE


@dataclasses.dataclass(frozen=True)
class StandingResult:
    accepted: bool
    points: int
    tier: StandingTier
    reason: t.Optional[str] = None


@dataclasses.dataclass
class CrossFactionReputation:
    # (player_id, target_faction) -> score
    _scores: dict[
        tuple[str, str], int,
    ] = dataclasses.field(default_factory=dict)
    # player_id -> own_side
    _player_side: dict[str, SideKind] = dataclasses.field(
        default_factory=dict,
    )

    def declare_side(
        self, *, player_id: str,
        own_side: SideKind,
    ) -> bool:
        if player_id in self._player_side:
            return False
        self._player_side[player_id] = own_side
        return True

    def own_side_for(
        self, player_id: str,
    ) -> t.Optional[SideKind]:
        return self._player_side.get(player_id)

    def modify(
        self, *, player_id: str,
        target_faction: str,
        delta: int,
    ) -> StandingResult:
        if not target_faction:
            return StandingResult(
                False, points=0,
                tier=StandingTier.NEUTRAL,
                reason="empty target faction",
            )
        if player_id not in self._player_side:
            return StandingResult(
                False, points=0,
                tier=StandingTier.NEUTRAL,
                reason="own side not declared",
            )
        if delta == 0:
            score = self._scores.get(
                (player_id, target_faction), 0,
            )
            return StandingResult(
                False, points=score,
                tier=_tier_for_score(score),
                reason="zero delta",
            )
        key = (player_id, target_faction)
        current = self._scores.get(key, 0)
        new_score = max(
            MIN_SCORE, min(MAX_SCORE, current + delta),
        )
        self._scores[key] = new_score
        return StandingResult(
            accepted=True, points=new_score,
            tier=_tier_for_score(new_score),
        )

    def points(
        self, *, player_id: str,
        target_faction: str,
    ) -> int:
        return self._scores.get(
            (player_id, target_faction), 0,
        )

    def standing(
        self, *, player_id: str,
        target_faction: str,
    ) -> StandingTier:
        return _tier_for_score(
            self.points(
                player_id=player_id,
                target_faction=target_faction,
            )
        )

    def reset(
        self, *, player_id: str,
        target_faction: str,
    ) -> bool:
        return self._scores.pop(
            (player_id, target_faction), None,
        ) is not None

    def total_pairs(self) -> int:
        return len(self._scores)

    def total_players(self) -> int:
        return len(self._player_side)


__all__ = [
    "MIN_SCORE", "MAX_SCORE",
    "SideKind", "StandingTier",
    "StandingResult",
    "CrossFactionReputation",
]
