"""Mob sapience threshold — long-survivors ascend.

A mob that has KILLED enough players, SURVIVED enough days,
EATEN enough corpses, and AVOIDED death from a predator long
enough begins to think. The world records its name. Other NPCs
start referring to it. Eventually it can be promoted to a
named NM, and beyond that to a full NPC-tier AI agent (using
entity_ai_binding).

This is the difference between "another orc" and "Brokenfang the
Orc Champion who has fed on twenty adventurers". It is a
PERMANENT promotion — the mob keeps its earned identity even if
the population it came from migrates or dies out.

Three sapience tiers
--------------------
    BEAST_OF_NOTE        ~10 score   gets a name + simple bark
    NM_TIER              ~50 score   becomes a named NM, drops loot
    NPC_TIER             ~200 score  full AI agent, faction-aligned

Public surface
--------------
    SapienceTier enum
    SapienceEvent dataclass
    MobLifeRecord dataclass
    MobSapienceThreshold
        .observe_mob(mob_uid, mob_kind)
        .record_event(mob_uid, event)
        .check_promotion(mob_uid) -> Optional[promotion]
        .tier_for(mob_uid)
        .ascended() -> all mobs that crossed BEAST_OF_NOTE
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Tier thresholds.
BEAST_OF_NOTE_THRESHOLD = 10
NM_TIER_THRESHOLD = 50
NPC_TIER_THRESHOLD = 200


class SapienceTier(str, enum.Enum):
    UNREMARKABLE = "unremarkable"
    BEAST_OF_NOTE = "beast_of_note"
    NM_TIER = "nm_tier"
    NPC_TIER = "npc_tier"


class SapienceEventKind(str, enum.Enum):
    KILLED_PLAYER = "killed_player"
    SURVIVED_DAY = "survived_day"
    ATE_CORPSE = "ate_corpse"
    EVADED_BOSS = "evaded_boss"
    DRANK_FROM_SHRINE = "drank_from_shrine"
    LED_PACK_KILL = "led_pack_kill"


# Per-event score grants.
SCORE_PER_EVENT: dict[SapienceEventKind, int] = {
    SapienceEventKind.KILLED_PLAYER: 5,
    SapienceEventKind.SURVIVED_DAY: 1,
    SapienceEventKind.ATE_CORPSE: 1,
    SapienceEventKind.EVADED_BOSS: 8,
    SapienceEventKind.DRANK_FROM_SHRINE: 20,
    SapienceEventKind.LED_PACK_KILL: 6,
}


@dataclasses.dataclass(frozen=True)
class SapienceEvent:
    kind: SapienceEventKind
    note: str = ""
    at_seconds: float = 0.0


@dataclasses.dataclass
class MobLifeRecord:
    mob_uid: str
    mob_kind: str
    sapience_score: int = 0
    tier: SapienceTier = SapienceTier.UNREMARKABLE
    earned_name: str = ""
    times_promoted: int = 0
    last_event_seconds: float = 0.0


@dataclasses.dataclass(frozen=True)
class SapienceAscension:
    """A mob just crossed a threshold."""
    mob_uid: str
    mob_kind: str
    old_tier: SapienceTier
    new_tier: SapienceTier
    earned_name: str
    note: str = ""


def _tier_for_score(score: int) -> SapienceTier:
    if score >= NPC_TIER_THRESHOLD:
        return SapienceTier.NPC_TIER
    if score >= NM_TIER_THRESHOLD:
        return SapienceTier.NM_TIER
    if score >= BEAST_OF_NOTE_THRESHOLD:
        return SapienceTier.BEAST_OF_NOTE
    return SapienceTier.UNREMARKABLE


# Quick deterministic name palette per mob kind.
_NAME_PREFIXES_BY_KIND: dict[str, tuple[str, ...]] = {
    "orc": ("Broken", "Iron", "Black", "Gore"),
    "goblin": ("Sneak", "Rust", "Coin", "Patchy"),
    "tiger": ("Stripe", "Fang", "Snow", "Flame"),
    "bee": ("Stinger", "Honey", "Sun", "Wing"),
    "wyvern": ("Storm", "Cinder", "Bone", "Pale"),
    "skeleton": ("Brittle", "Hollow", "Rusted", "Grim"),
}
_NAME_SUFFIXES_BY_KIND: dict[str, tuple[str, ...]] = {
    "orc": ("fang", "skull", "claw", "axe"),
    "goblin": ("ear", "thumb", "snout", "snicker"),
    "tiger": ("paw", "tail", "eye", "tooth"),
    "bee": ("buzz", "hive", "wing", "queen"),
    "wyvern": ("scale", "wing", "claw", "breath"),
    "skeleton": ("rib", "knee", "knuckle", "spine"),
}


def _earn_name(*, mob_kind: str, mob_uid: str) -> str:
    prefixes = _NAME_PREFIXES_BY_KIND.get(
        mob_kind, ("Old", "Wild", "Greater", "Lesser"),
    )
    suffixes = _NAME_SUFFIXES_BY_KIND.get(
        mob_kind, ("foot", "fang", "eye", "skin"),
    )
    # Deterministic by uid hash so re-promotions are stable
    h = abs(hash(mob_uid))
    p = prefixes[h % len(prefixes)]
    s = suffixes[(h // len(prefixes)) % len(suffixes)]
    return f"{p}{s}"


@dataclasses.dataclass
class MobSapienceThreshold:
    _records: dict[str, MobLifeRecord] = dataclasses.field(
        default_factory=dict,
    )

    def observe_mob(
        self, *, mob_uid: str, mob_kind: str,
    ) -> t.Optional[MobLifeRecord]:
        if mob_uid in self._records:
            return None
        rec = MobLifeRecord(
            mob_uid=mob_uid, mob_kind=mob_kind,
        )
        self._records[mob_uid] = rec
        return rec

    def record_event(
        self, *, mob_uid: str, event: SapienceEvent,
    ) -> t.Optional[int]:
        rec = self._records.get(mob_uid)
        if rec is None:
            return None
        rec.sapience_score += SCORE_PER_EVENT[event.kind]
        rec.last_event_seconds = event.at_seconds
        return rec.sapience_score

    def tier_for(
        self, mob_uid: str,
    ) -> t.Optional[SapienceTier]:
        rec = self._records.get(mob_uid)
        if rec is None:
            return None
        return rec.tier

    def check_promotion(
        self, *, mob_uid: str,
    ) -> t.Optional[SapienceAscension]:
        rec = self._records.get(mob_uid)
        if rec is None:
            return None
        new_tier = _tier_for_score(rec.sapience_score)
        if new_tier == rec.tier:
            return None
        old_tier = rec.tier
        rec.tier = new_tier
        rec.times_promoted += 1
        if (
            old_tier == SapienceTier.UNREMARKABLE
            and not rec.earned_name
        ):
            rec.earned_name = _earn_name(
                mob_kind=rec.mob_kind, mob_uid=rec.mob_uid,
            )
        return SapienceAscension(
            mob_uid=rec.mob_uid, mob_kind=rec.mob_kind,
            old_tier=old_tier, new_tier=new_tier,
            earned_name=rec.earned_name,
        )

    def ascended(
        self,
    ) -> tuple[MobLifeRecord, ...]:
        return tuple(
            r for r in self._records.values()
            if r.tier != SapienceTier.UNREMARKABLE
        )

    def total_observed(self) -> int:
        return len(self._records)


__all__ = [
    "BEAST_OF_NOTE_THRESHOLD",
    "NM_TIER_THRESHOLD",
    "NPC_TIER_THRESHOLD",
    "SapienceTier", "SapienceEventKind",
    "SapienceEvent", "MobLifeRecord",
    "SapienceAscension", "MobSapienceThreshold",
]
