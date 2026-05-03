"""Boss adaptation — bosses learn from prior fights.

When a player kills (or wipes against) a boss, the boss
remembers what worked against them and what didn't. Next time
that same player engages, the boss adjusts: resists the spells
that hurt last time, dodges the weapon skill that landed twice,
counters the strategy that won the prior pull.

This is per-(boss_kind, player_id) memory. Across the world, every
named monster has its own grudge book against every PC who's ever
poked it.

Inputs the adapter consumes
---------------------------
    PlayerEngagementOutcome:
        spells_cast_pct      most-used spell schools
        weaponskills_used    set of WS ids
        damage_types_dealt   physical/magic shares
        won_or_lost          did the player win
        seconds_alive        how long the fight ran

Adaptations the boss can layer
------------------------------
    RESIST_BUMP        +X% resist to a magic school
    DODGE_BUMP         +X% evasion against a WS family
    COUNTER_PATTERN    queues a counter-mechanic on engage
    HP_BUFF            stacks HP if too short prior win
    ENRAGE_TIMER_CUT   shortens enrage if prior win was easy

Public surface
--------------
    AdaptationKind enum
    PlayerEngagementOutcome dataclass
    BossAdaptation dataclass
    AdaptationCascade dataclass
    BossAdaptationRegistry
        .record_outcome(boss_kind, player_id, outcome)
        .compute_adaptations(boss_kind, player_id)
        .has_grudge(boss_kind, player_id)
        .reset(boss_kind, player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default cap on stacked adaptations per boss-vs-player.
MAX_ADAPTATIONS_PER_GRUDGE = 6
# Resist/dodge bump magnitudes (percent).
RESIST_BUMP_PCT = 25
DODGE_BUMP_PCT = 20
HP_BUFF_PCT = 15
ENRAGE_CUT_PCT = 20


class AdaptationKind(str, enum.Enum):
    RESIST_BUMP = "resist_bump"
    DODGE_BUMP = "dodge_bump"
    COUNTER_PATTERN = "counter_pattern"
    HP_BUFF = "hp_buff"
    ENRAGE_TIMER_CUT = "enrage_timer_cut"


class MagicSchool(str, enum.Enum):
    FIRE = "fire"
    ICE = "ice"
    WIND = "wind"
    EARTH = "earth"
    LIGHTNING = "lightning"
    WATER = "water"
    LIGHT = "light"
    DARK = "dark"
    HEAL = "heal"
    ENFEEBLE = "enfeeble"


@dataclasses.dataclass(frozen=True)
class PlayerEngagementOutcome:
    """One fight's worth of player behaviour."""
    boss_kind: str
    player_id: str
    won_or_lost: bool                # True if player killed boss
    seconds_alive: int = 0
    # Spell schools used and their share of damage (0..1).
    spell_school_share: t.Mapping[MagicSchool, float] = (
        dataclasses.field(default_factory=dict)
    )
    weaponskills_used: tuple[str, ...] = ()
    physical_dmg_share: float = 0.0  # 0..1
    magic_dmg_share: float = 0.0     # 0..1
    used_pet: bool = False
    used_summon: bool = False


@dataclasses.dataclass(frozen=True)
class BossAdaptation:
    kind: AdaptationKind
    target: str       # what the adaptation counters
    magnitude_pct: int
    note: str = ""


@dataclasses.dataclass(frozen=True)
class AdaptationCascade:
    """All adaptations a boss has stacked vs one player."""
    boss_kind: str
    player_id: str
    adaptations: tuple[BossAdaptation, ...]
    fight_count: int


@dataclasses.dataclass
class _GrudgeBook:
    """Internal accumulator of a single (boss, player) history."""
    fights: list[PlayerEngagementOutcome] = dataclasses.field(
        default_factory=list,
    )

    def record(self, outcome: PlayerEngagementOutcome) -> None:
        self.fights.append(outcome)

    def fight_count(self) -> int:
        return len(self.fights)

    def player_win_count(self) -> int:
        return sum(1 for f in self.fights if f.won_or_lost)

    def dominant_spell_school(
        self,
    ) -> t.Optional[tuple[MagicSchool, float]]:
        agg: dict[MagicSchool, float] = {}
        for f in self.fights:
            for school, share in f.spell_school_share.items():
                agg[school] = agg.get(school, 0.0) + share
        if not agg:
            return None
        best = max(agg.items(), key=lambda kv: kv[1])
        # Normalize by fight count
        return (best[0], best[1] / max(1, len(self.fights)))

    def repeated_weaponskills(self) -> list[str]:
        counts: dict[str, int] = {}
        for f in self.fights:
            for ws in f.weaponskills_used:
                counts[ws] = counts.get(ws, 0) + 1
        return [ws for ws, n in counts.items() if n >= 2]

    def average_seconds_alive(self) -> float:
        if not self.fights:
            return 0.0
        return sum(
            f.seconds_alive for f in self.fights
        ) / len(self.fights)

    def physical_lean(self) -> bool:
        if not self.fights:
            return False
        avg_phys = sum(
            f.physical_dmg_share for f in self.fights
        ) / len(self.fights)
        return avg_phys >= 0.6

    def magic_lean(self) -> bool:
        if not self.fights:
            return False
        avg_mag = sum(
            f.magic_dmg_share for f in self.fights
        ) / len(self.fights)
        return avg_mag >= 0.6


@dataclasses.dataclass
class BossAdaptationRegistry:
    max_adaptations_per_grudge: int = MAX_ADAPTATIONS_PER_GRUDGE
    quick_kill_threshold_seconds: int = 60
    _books: dict[tuple[str, str], _GrudgeBook] = (
        dataclasses.field(default_factory=dict)
    )

    def record_outcome(
        self, *, outcome: PlayerEngagementOutcome,
    ) -> None:
        key = (outcome.boss_kind, outcome.player_id)
        book = self._books.setdefault(key, _GrudgeBook())
        book.record(outcome)

    def has_grudge(
        self, *, boss_kind: str, player_id: str,
    ) -> bool:
        return (boss_kind, player_id) in self._books

    def reset(
        self, *, boss_kind: str, player_id: str,
    ) -> bool:
        key = (boss_kind, player_id)
        if key not in self._books:
            return False
        del self._books[key]
        return True

    def compute_adaptations(
        self, *, boss_kind: str, player_id: str,
    ) -> AdaptationCascade:
        book = self._books.get((boss_kind, player_id))
        if book is None:
            return AdaptationCascade(
                boss_kind=boss_kind, player_id=player_id,
                adaptations=(), fight_count=0,
            )

        adaptations: list[BossAdaptation] = []

        # Magic school resist
        dominant = book.dominant_spell_school()
        if dominant is not None and dominant[1] >= 0.30:
            adaptations.append(BossAdaptation(
                kind=AdaptationKind.RESIST_BUMP,
                target=dominant[0].value,
                magnitude_pct=RESIST_BUMP_PCT,
                note=f"learned to resist {dominant[0].value}",
            ))

        # WS dodge
        for ws in book.repeated_weaponskills():
            adaptations.append(BossAdaptation(
                kind=AdaptationKind.DODGE_BUMP,
                target=ws,
                magnitude_pct=DODGE_BUMP_PCT,
                note=f"sidesteps {ws}",
            ))

        # Counter-pattern: physical-heavy lean
        if book.physical_lean():
            adaptations.append(BossAdaptation(
                kind=AdaptationKind.COUNTER_PATTERN,
                target="physical_team",
                magnitude_pct=0,
                note="opens with knockback to scatter melee",
            ))
        if book.magic_lean():
            adaptations.append(BossAdaptation(
                kind=AdaptationKind.COUNTER_PATTERN,
                target="caster_team",
                magnitude_pct=0,
                note="opens with silence-cone vs caster line",
            ))

        # HP buff if player won quickly
        if (
            book.player_win_count() > 0
            and book.average_seconds_alive()
            < self.quick_kill_threshold_seconds
        ):
            adaptations.append(BossAdaptation(
                kind=AdaptationKind.HP_BUFF,
                target="self",
                magnitude_pct=HP_BUFF_PCT,
                note="bulks up after being one-shot",
            ))

        # Enrage cut after multiple wins
        if book.player_win_count() >= 2:
            adaptations.append(BossAdaptation(
                kind=AdaptationKind.ENRAGE_TIMER_CUT,
                target="enrage",
                magnitude_pct=ENRAGE_CUT_PCT,
                note="cuts enrage timer to deny farming",
            ))

        capped = adaptations[: self.max_adaptations_per_grudge]
        return AdaptationCascade(
            boss_kind=boss_kind, player_id=player_id,
            adaptations=tuple(capped),
            fight_count=book.fight_count(),
        )

    def total_grudges(self) -> int:
        return len(self._books)


__all__ = [
    "MAX_ADAPTATIONS_PER_GRUDGE",
    "RESIST_BUMP_PCT", "DODGE_BUMP_PCT",
    "HP_BUFF_PCT", "ENRAGE_CUT_PCT",
    "AdaptationKind", "MagicSchool",
    "PlayerEngagementOutcome", "BossAdaptation",
    "AdaptationCascade", "BossAdaptationRegistry",
]
