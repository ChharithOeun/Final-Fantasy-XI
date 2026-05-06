"""Telegraph reading skill — per-player perception XP.

A boss telegraph (a wind-up animation, a glow, an
audible callout) is the player's chance to dodge,
interrupt, or counter. Players READ telegraphs at
different speeds based on practice. This module is a
per-player skill XP track:

    skill 0..299      NOVICE       — base reaction window
                                       (e.g. boss telegraph
                                       lasts 3.0s; you see it
                                       with 1.0s warning)
    300..599          APPRENTICE   — +0.4s warning, +5%
                                       tag bonus
    600..899          ADEPT        — +0.8s warning, +10%
                                       tag bonus
    900..1199         EXPERT       — +1.2s warning, +15%
                                       tag bonus, "telegraph
                                       prediction" — NEXT-MOVE
                                       hint shown
    1200+             MASTER       — +1.6s warning, +20%
                                       tag bonus, prediction
                                       shows for 2 future moves

XP gain:
    successful dodge of telegraphed AOE      +5
    successful interrupt of telegraphed cast +10
    successful counter of telegraphed melee  +8
    failed (missed) telegraph                +1   (you learn
                                                  from failure)

Skill DECAYS (slowly) without practice — 1 XP/day if the
player hasn't engaged any telegraphed mob in 24h. Caps
at MASTER+1000.

Public surface
--------------
    Tier enum
    TelegraphTier dataclass (frozen)
    TelegraphReadingSkill
        .award_xp(player_id, source, magnitude=1)
        .skill(player_id) -> int
        .tier(player_id) -> Tier
        .warning_bonus_seconds(player_id) -> float
        .tag_bonus_pct(player_id) -> int
        .prediction_count(player_id) -> int
        .decay(player_id, days_since_last_practice)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Tier(str, enum.Enum):
    NOVICE = "novice"
    APPRENTICE = "apprentice"
    ADEPT = "adept"
    EXPERT = "expert"
    MASTER = "master"


class XPSource(str, enum.Enum):
    DODGED_AOE = "dodged_aoe"
    INTERRUPTED_CAST = "interrupted_cast"
    COUNTERED_MELEE = "countered_melee"
    MISSED_TELEGRAPH = "missed_telegraph"


XP_GAIN: dict[XPSource, int] = {
    XPSource.DODGED_AOE: 5,
    XPSource.INTERRUPTED_CAST: 10,
    XPSource.COUNTERED_MELEE: 8,
    XPSource.MISSED_TELEGRAPH: 1,
}

# Tier thresholds (skill_xp >= threshold)
TIER_THRESHOLDS: tuple[tuple[int, Tier], ...] = (
    (1200, Tier.MASTER),
    (900, Tier.EXPERT),
    (600, Tier.ADEPT),
    (300, Tier.APPRENTICE),
    (0, Tier.NOVICE),
)


@dataclasses.dataclass(frozen=True)
class TierProfile:
    tier: Tier
    warning_bonus_seconds: float
    tag_bonus_pct: int
    prediction_count: int


_PROFILES: dict[Tier, TierProfile] = {
    Tier.NOVICE: TierProfile(
        Tier.NOVICE, 0.0, 0, 0,
    ),
    Tier.APPRENTICE: TierProfile(
        Tier.APPRENTICE, 0.4, 5, 0,
    ),
    Tier.ADEPT: TierProfile(
        Tier.ADEPT, 0.8, 10, 0,
    ),
    Tier.EXPERT: TierProfile(
        Tier.EXPERT, 1.2, 15, 1,
    ),
    Tier.MASTER: TierProfile(
        Tier.MASTER, 1.6, 20, 2,
    ),
}


SKILL_CAP = 2200   # MASTER threshold + 1000
XP_DECAY_PER_DAY = 1


@dataclasses.dataclass
class TelegraphReadingSkill:
    _xp: dict[str, int] = dataclasses.field(default_factory=dict)

    def award_xp(
        self, *, player_id: str, source: XPSource,
        magnitude: int = 1,
    ) -> int:
        if not player_id or magnitude <= 0:
            return 0
        gain = XP_GAIN[source] * magnitude
        cur = self._xp.get(player_id, 0)
        new = min(SKILL_CAP, cur + gain)
        self._xp[player_id] = new
        return new - cur

    def skill(self, *, player_id: str) -> int:
        return self._xp.get(player_id, 0)

    def tier(self, *, player_id: str) -> Tier:
        s = self.skill(player_id=player_id)
        for threshold, t_ in TIER_THRESHOLDS:
            if s >= threshold:
                return t_
        return Tier.NOVICE

    def _profile(self, *, player_id: str) -> TierProfile:
        return _PROFILES[self.tier(player_id=player_id)]

    def warning_bonus_seconds(self, *, player_id: str) -> float:
        return self._profile(player_id=player_id).warning_bonus_seconds

    def tag_bonus_pct(self, *, player_id: str) -> int:
        return self._profile(player_id=player_id).tag_bonus_pct

    def prediction_count(self, *, player_id: str) -> int:
        return self._profile(player_id=player_id).prediction_count

    def decay(
        self, *, player_id: str, days_since_last_practice: int,
    ) -> int:
        if days_since_last_practice <= 0 or player_id not in self._xp:
            return 0
        loss = days_since_last_practice * XP_DECAY_PER_DAY
        cur = self._xp[player_id]
        new = max(0, cur - loss)
        self._xp[player_id] = new
        return cur - new


__all__ = [
    "Tier", "XPSource", "TierProfile",
    "TelegraphReadingSkill",
    "XP_GAIN", "TIER_THRESHOLDS", "SKILL_CAP",
    "XP_DECAY_PER_DAY",
]
