"""Beastmen faction AI — autonomous tribal politics.

Each canonical FFXI beastmen tribe runs its own faction-level AI
agent that decides:

* How aggressively the tribe pushes into adjacent zones
* Whether to declare war on a player nation, an NPC nation, or
  another beastmen tribe
* Whether to ally with another tribe, broker peace, or fortify
* How much manpower to commit to siege_system raids vs.
  defensive fortification
* Which captives to ransom / sacrifice / convert into agents

The tribe-level AI doesn't move individual mobs — that's still
the per-mob entity AI. Tribes set STRATEGIC posture; mobs and
NM warlords execute. The interface is a "stance" each tribe
publishes (CONTAIN / RAID / WAR / FORTIFY / RETREAT) plus a
threat-priority ranking that flows into siege_system and
encounter_gen.

Tribes
------
Demoncore uses the canonical FFXI roster:
    ORC, QUADAV, YAGUDO, GOBLIN, SAHAGIN, TONBERRY,
    ANTICA, MAMOOL_JA, TROLL, LAMIA, MERROW

Public surface
--------------
    BeastmenTribe enum (the 11 tribes)
    Stance enum (CONTAIN / RAID / WAR / FORTIFY / RETREAT)
    DiplomaticStance enum (HOSTILE / WARY / NEUTRAL / ALLIED)
    FactionAIState dataclass — current AI snapshot per tribe
    FactionAIRegistry — registry of all 11 tribes
        .post_stance(tribe, stance) — AI commits to a stance
        .declare_war(tribe, target) / .broker_peace(...)
        .threat_ranking(tribe) — ordered list of who they hate most
        .commit_force(tribe, raid_target, troop_count) — feeds siege_system
        .stance_for(tribe), .summary()

Doctrine
--------
The faction AI is just exposing INTENT. The actual mob spawns
that come from a "RAID" stance happen via siege_system /
encounter_gen / npc_progression. This module is the planning
layer the orchestrator hangs the strategic agents off of.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class BeastmenTribe(str, enum.Enum):
    ORC = "orc"
    QUADAV = "quadav"
    YAGUDO = "yagudo"
    GOBLIN = "goblin"
    SAHAGIN = "sahagin"
    TONBERRY = "tonberry"
    ANTICA = "antica"
    MAMOOL_JA = "mamool_ja"
    TROLL = "troll"
    LAMIA = "lamia"
    MERROW = "merrow"


class Stance(str, enum.Enum):
    """How the tribe is currently posturing toward the world."""
    CONTAIN = "contain"      # default — patrol, hold ground
    RAID = "raid"            # send small parties out; xp fodder
    WAR = "war"              # full siege escalation, big spawns
    FORTIFY = "fortify"      # bunker down, repair walls, breed
    RETREAT = "retreat"      # pull back to homeland, lick wounds


class DiplomaticStance(str, enum.Enum):
    """How a tribe feels about another faction (player nation,
    NPC nation, or another tribe)."""
    HOSTILE = "hostile"
    WARY = "wary"
    NEUTRAL = "neutral"
    ALLIED = "allied"


# Player nations (target candidates for diplomatic stance).
class PlayerNation(str, enum.Enum):
    BASTOK = "bastok"
    SAN_DORIA = "san_doria"
    WINDURST = "windurst"
    JEUNO = "jeuno"


@dataclasses.dataclass
class CommittedForce:
    """A unit of force the tribe AI has dispatched somewhere."""
    target_zone_id: str
    troop_count: int
    committed_at_seconds: float
    notes: str = ""


@dataclasses.dataclass
class FactionAIState:
    """Live snapshot of a tribe's strategic posture."""
    tribe: BeastmenTribe
    stance: Stance = Stance.CONTAIN
    diplomatic: dict[
        t.Union[BeastmenTribe, PlayerNation], DiplomaticStance,
    ] = dataclasses.field(default_factory=dict)
    threat_priority: list[
        t.Union[BeastmenTribe, PlayerNation],
    ] = dataclasses.field(default_factory=list)
    committed_forces: list[CommittedForce] = dataclasses.field(
        default_factory=list,
    )
    last_decision_at_seconds: float = 0.0

    def stance_toward(
        self,
        target: t.Union[BeastmenTribe, PlayerNation],
    ) -> DiplomaticStance:
        return self.diplomatic.get(target, DiplomaticStance.NEUTRAL)


@dataclasses.dataclass(frozen=True)
class StanceResult:
    accepted: bool
    new_stance: t.Optional[Stance] = None
    reason: t.Optional[str] = None


# Default seed: each tribe starts HOSTILE to its canonical nation
# rival. This is just initial state; the AI mutates it freely.
_DEFAULT_RIVALS: dict[BeastmenTribe, PlayerNation] = {
    BeastmenTribe.ORC: PlayerNation.SAN_DORIA,
    BeastmenTribe.QUADAV: PlayerNation.BASTOK,
    BeastmenTribe.YAGUDO: PlayerNation.WINDURST,
    BeastmenTribe.GOBLIN: PlayerNation.JEUNO,
    BeastmenTribe.SAHAGIN: PlayerNation.SAN_DORIA,
    BeastmenTribe.TONBERRY: PlayerNation.JEUNO,
    BeastmenTribe.ANTICA: PlayerNation.JEUNO,
    BeastmenTribe.MAMOOL_JA: PlayerNation.SAN_DORIA,
    BeastmenTribe.TROLL: PlayerNation.WINDURST,
    BeastmenTribe.LAMIA: PlayerNation.BASTOK,
    BeastmenTribe.MERROW: PlayerNation.BASTOK,
}


@dataclasses.dataclass
class FactionAIRegistry:
    _states: dict[BeastmenTribe, FactionAIState] = dataclasses.field(
        default_factory=dict,
    )

    def __post_init__(self) -> None:
        # Seed every tribe with default rival posture.
        for tribe in BeastmenTribe:
            rival = _DEFAULT_RIVALS[tribe]
            state = FactionAIState(tribe=tribe)
            state.diplomatic[rival] = DiplomaticStance.HOSTILE
            state.threat_priority.append(rival)
            self._states[tribe] = state

    def state_of(self, tribe: BeastmenTribe) -> FactionAIState:
        return self._states[tribe]

    def stance_for(self, tribe: BeastmenTribe) -> Stance:
        return self._states[tribe].stance

    def post_stance(
        self, *, tribe: BeastmenTribe, stance: Stance,
        now_seconds: float = 0.0,
    ) -> StanceResult:
        s = self._states[tribe]
        # Some transitions are nonsensical — RETREAT can't go
        # straight to WAR without first RAID/CONTAIN.
        if s.stance == Stance.RETREAT and stance == Stance.WAR:
            return StanceResult(
                False,
                reason="must reorganize via CONTAIN/RAID before WAR",
            )
        s.stance = stance
        s.last_decision_at_seconds = now_seconds
        return StanceResult(True, new_stance=stance)

    def declare_war(
        self, *, tribe: BeastmenTribe,
        target: t.Union[BeastmenTribe, PlayerNation],
        now_seconds: float = 0.0,
    ) -> StanceResult:
        if tribe == target:
            return StanceResult(False, reason="cannot war self")
        s = self._states[tribe]
        s.diplomatic[target] = DiplomaticStance.HOSTILE
        if target not in s.threat_priority:
            s.threat_priority.insert(0, target)
        else:
            s.threat_priority.remove(target)
            s.threat_priority.insert(0, target)
        s.stance = Stance.WAR
        s.last_decision_at_seconds = now_seconds
        return StanceResult(True, new_stance=Stance.WAR)

    def broker_peace(
        self, *, tribe: BeastmenTribe,
        target: t.Union[BeastmenTribe, PlayerNation],
        new_diplomatic: DiplomaticStance = DiplomaticStance.NEUTRAL,
        now_seconds: float = 0.0,
    ) -> StanceResult:
        s = self._states[tribe]
        s.diplomatic[target] = new_diplomatic
        if target in s.threat_priority:
            s.threat_priority.remove(target)
        if s.stance == Stance.WAR:
            s.stance = Stance.CONTAIN
        s.last_decision_at_seconds = now_seconds
        return StanceResult(True, new_stance=s.stance)

    def threat_ranking(
        self, tribe: BeastmenTribe,
    ) -> tuple[t.Union[BeastmenTribe, PlayerNation], ...]:
        return tuple(self._states[tribe].threat_priority)

    def commit_force(
        self, *, tribe: BeastmenTribe, target_zone_id: str,
        troop_count: int, now_seconds: float = 0.0,
        notes: str = "",
    ) -> CommittedForce:
        force = CommittedForce(
            target_zone_id=target_zone_id,
            troop_count=troop_count,
            committed_at_seconds=now_seconds,
            notes=notes,
        )
        self._states[tribe].committed_forces.append(force)
        return force

    def total_committed_troops(self, tribe: BeastmenTribe) -> int:
        return sum(
            f.troop_count
            for f in self._states[tribe].committed_forces
        )

    def summary(self) -> dict[BeastmenTribe, Stance]:
        return {
            tribe: state.stance
            for tribe, state in self._states.items()
        }

    def tribes_at_war(self) -> tuple[BeastmenTribe, ...]:
        return tuple(
            t for t, s in self._states.items()
            if s.stance == Stance.WAR
        )


__all__ = [
    "BeastmenTribe", "Stance", "DiplomaticStance", "PlayerNation",
    "CommittedForce", "FactionAIState", "StanceResult",
    "FactionAIRegistry",
]
