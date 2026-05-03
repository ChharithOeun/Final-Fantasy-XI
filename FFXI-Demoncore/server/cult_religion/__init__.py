"""Cult & religion — gods, prayers, miracles, heresies.

A player can declare allegiance to a god (canonical FFXI: Altana,
Promathia, plus Demoncore-flavored Forgotten Ones — Caradoc the
Dim Forge, Yulgar the Hollow Throne, Zenith the Open Sky). Faith
rises through PRAYER + DEED + OFFERING; falls through SIN. At
faith tiers, prayers unlock; at top tier rare MIRACLES can fire.

Heretics — players who recently followed a rival god — face a
faith-malus when switching cults. Apostates (who break vow 3+
times) suffer a permanent faith ceiling cut.

Public surface
--------------
    GodKind enum
    PrayerKind enum
    DevotionTier enum
    DevotionRecord dataclass
    PrayerOutcome dataclass
    CultReligionRegistry
        .pledge(player_id, god) -> bool
        .pray(player_id, prayer_kind, faith_cost) -> Outcome
        .offer(player_id, gil_or_item_value) -> int
        .sin(player_id, magnitude, kind) -> bool
        .declare_apostate(player_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Faith bands (0..1000 default).
DEVOTED_TIER_FAITH = 100
FAITHFUL_TIER_FAITH = 300
ZEALOT_TIER_FAITH = 600
SAINT_TIER_FAITH = 900
MAX_FAITH = 1000

# Heretic malus when switching cults (subtracted from new pledge).
HERETIC_MALUS = 100
# Apostate cap reduction per apostasy.
APOSTATE_CEILING_CUT = 200
APOSTATE_THRESHOLD = 3


class GodKind(str, enum.Enum):
    ALTANA = "altana"
    PROMATHIA = "promathia"
    CARADOC = "caradoc"          # Dim Forge — smiths/mages
    YULGAR = "yulgar"            # Hollow Throne — outlaws
    ZENITH = "zenith"            # Open Sky — wanderers/scholars


class PrayerKind(str, enum.Enum):
    BLESSING = "blessing"        # tier 0: small buff
    HEALING_LIGHT = "healing_light"
    GUIDING_STAR = "guiding_star"   # marks NM direction
    BREATH_OF_FORGE = "breath_of_forge"   # crafting buff
    JUDGEMENT = "judgement"      # smite outlaw
    MIRACLE_RESURRECTION = "miracle_resurrection"   # rare


class DevotionTier(str, enum.Enum):
    NONE = "none"
    DEVOTED = "devoted"
    FAITHFUL = "faithful"
    ZEALOT = "zealot"
    SAINT = "saint"


# Faith cost per prayer (default).
_DEFAULT_PRAYER_COSTS: dict[PrayerKind, int] = {
    PrayerKind.BLESSING: 10,
    PrayerKind.HEALING_LIGHT: 30,
    PrayerKind.GUIDING_STAR: 60,
    PrayerKind.BREATH_OF_FORGE: 80,
    PrayerKind.JUDGEMENT: 120,
    PrayerKind.MIRACLE_RESURRECTION: 250,
}


# Required tier per prayer.
_PRAYER_REQUIRED_TIER: dict[PrayerKind, DevotionTier] = {
    PrayerKind.BLESSING: DevotionTier.DEVOTED,
    PrayerKind.HEALING_LIGHT: DevotionTier.FAITHFUL,
    PrayerKind.GUIDING_STAR: DevotionTier.FAITHFUL,
    PrayerKind.BREATH_OF_FORGE: DevotionTier.ZEALOT,
    PrayerKind.JUDGEMENT: DevotionTier.ZEALOT,
    PrayerKind.MIRACLE_RESURRECTION: DevotionTier.SAINT,
}


@dataclasses.dataclass
class DevotionRecord:
    player_id: str
    god: GodKind
    faith: int = 0
    pledged_at_seconds: float = 0.0
    apostate_count: int = 0
    faith_ceiling: int = MAX_FAITH


def _tier_for_faith(faith: int) -> DevotionTier:
    if faith >= SAINT_TIER_FAITH:
        return DevotionTier.SAINT
    if faith >= ZEALOT_TIER_FAITH:
        return DevotionTier.ZEALOT
    if faith >= FAITHFUL_TIER_FAITH:
        return DevotionTier.FAITHFUL
    if faith >= DEVOTED_TIER_FAITH:
        return DevotionTier.DEVOTED
    return DevotionTier.NONE


@dataclasses.dataclass(frozen=True)
class PrayerOutcome:
    accepted: bool
    prayer_kind: t.Optional[PrayerKind] = None
    faith_after: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class CultReligionRegistry:
    _devotions: dict[str, DevotionRecord] = dataclasses.field(
        default_factory=dict,
    )
    _previous_gods: dict[str, GodKind] = dataclasses.field(
        default_factory=dict,
    )

    def pledge(
        self, *, player_id: str, god: GodKind,
        now_seconds: float = 0.0,
    ) -> bool:
        existing = self._devotions.get(player_id)
        if existing is not None:
            if existing.god == god:
                # Re-pledging same god is a no-op success
                return True
            # Switching gods — note as previous, apply heretic malus
            self._previous_gods[player_id] = existing.god
        ceiling = (
            existing.faith_ceiling
            if existing is not None
            else MAX_FAITH
        )
        apostate_count = (
            existing.apostate_count
            if existing is not None
            else 0
        )
        starting_faith = (
            -HERETIC_MALUS
            if existing is not None
            else 0
        )
        # Faith floor at 0
        starting_faith = max(0, starting_faith)
        rec = DevotionRecord(
            player_id=player_id, god=god,
            faith=starting_faith,
            pledged_at_seconds=now_seconds,
            faith_ceiling=ceiling,
            apostate_count=apostate_count,
        )
        self._devotions[player_id] = rec
        return True

    def devotion(
        self, player_id: str,
    ) -> t.Optional[DevotionRecord]:
        return self._devotions.get(player_id)

    def tier_for(
        self, player_id: str,
    ) -> t.Optional[DevotionTier]:
        rec = self._devotions.get(player_id)
        if rec is None:
            return None
        return _tier_for_faith(rec.faith)

    def offer(
        self, *, player_id: str, value: int,
    ) -> t.Optional[int]:
        if value <= 0:
            return None
        rec = self._devotions.get(player_id)
        if rec is None:
            return None
        # Each 100 gil-equivalent = 1 faith
        gain = value // 100
        rec.faith = min(
            rec.faith_ceiling, rec.faith + gain,
        )
        return rec.faith

    def sin(
        self, *, player_id: str, magnitude: int,
    ) -> bool:
        if magnitude <= 0:
            return False
        rec = self._devotions.get(player_id)
        if rec is None:
            return False
        rec.faith = max(0, rec.faith - magnitude)
        return True

    def pray(
        self, *, player_id: str, prayer_kind: PrayerKind,
    ) -> PrayerOutcome:
        rec = self._devotions.get(player_id)
        if rec is None:
            return PrayerOutcome(
                False, reason="player has not pledged",
            )
        required_tier = _PRAYER_REQUIRED_TIER[prayer_kind]
        current_tier = _tier_for_faith(rec.faith)
        if (
            _TIER_RANK[current_tier]
            < _TIER_RANK[required_tier]
        ):
            return PrayerOutcome(
                False, reason="faith tier insufficient",
            )
        cost = _DEFAULT_PRAYER_COSTS[prayer_kind]
        if rec.faith < cost:
            return PrayerOutcome(
                False, reason="faith too low",
            )
        rec.faith -= cost
        return PrayerOutcome(
            accepted=True, prayer_kind=prayer_kind,
            faith_after=rec.faith,
        )

    def declare_apostate(
        self, *, player_id: str,
    ) -> bool:
        rec = self._devotions.get(player_id)
        if rec is None:
            return False
        rec.apostate_count += 1
        rec.faith = 0
        if rec.apostate_count >= APOSTATE_THRESHOLD:
            rec.faith_ceiling = max(
                100,
                rec.faith_ceiling - APOSTATE_CEILING_CUT,
            )
        return True

    def total_devotions(self) -> int:
        return len(self._devotions)


_TIER_RANK: dict[DevotionTier, int] = {
    DevotionTier.NONE: 0,
    DevotionTier.DEVOTED: 1,
    DevotionTier.FAITHFUL: 2,
    DevotionTier.ZEALOT: 3,
    DevotionTier.SAINT: 4,
}


__all__ = [
    "DEVOTED_TIER_FAITH", "FAITHFUL_TIER_FAITH",
    "ZEALOT_TIER_FAITH", "SAINT_TIER_FAITH",
    "MAX_FAITH",
    "HERETIC_MALUS", "APOSTATE_CEILING_CUT",
    "APOSTATE_THRESHOLD",
    "GodKind", "PrayerKind", "DevotionTier",
    "DevotionRecord", "PrayerOutcome",
    "CultReligionRegistry",
]
