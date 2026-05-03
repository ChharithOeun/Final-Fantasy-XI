"""AI plot generator — dynamic story arcs from world state.

Reads the live world state and proposes PLOT HOOKS the
orchestrator can wire into NPC dialogue, faction events, and
dynamic_quest_gen. Distinct from faction_quest_chains (authored
arcs); this module mints fresh hooks based on what's actually
happening RIGHT NOW.

Inputs the generator considers
------------------------------
* faction_tension_pct : 0..100  (war pressure between two factions)
* recent_boss_kills_by_player : list of (boss_id, days_ago)
* outstanding_rumors : how many high-salience rumors are alive
* recent_permadeaths_in_zone : count
* npc_relationship_grief : when a major NPC died, kin in grief

Plot hook kinds
---------------
    REVENGE_ARC          someone wants the boss-killer dealt with
    SUCCESSION_CRISIS    named NPC died, no clear heir
    PROPHECY_AWAKENING   omens imply a buried artifact's stir
    BORDER_INCIDENT      faction-tension event spills into a town
    GRIEVING_ARC         mourning kin offers a quest of farewell
    SCANDAL              high-rep NPC's secret leaks via rumor
    PLAGUE_OUTBREAK      local population unrest
    WANDERING_HERO       a famous PC's fame draws challengers

Public surface
--------------
    PlotHookKind enum
    Urgency enum
    PlotHook dataclass
    WorldStateSnapshot dataclass — inputs
    PlotGenerationResult dataclass
    AIPlotGenerator
        .ingest(snapshot, now)
        .generate(now, max_hooks) -> PlotGenerationResult
        .acknowledge(hook_id) — orchestrator says "I took it"
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default per-tick max hook output.
DEFAULT_MAX_HOOKS_PER_TICK = 5


class PlotHookKind(str, enum.Enum):
    REVENGE_ARC = "revenge_arc"
    SUCCESSION_CRISIS = "succession_crisis"
    PROPHECY_AWAKENING = "prophecy_awakening"
    BORDER_INCIDENT = "border_incident"
    GRIEVING_ARC = "grieving_arc"
    SCANDAL = "scandal"
    PLAGUE_OUTBREAK = "plague_outbreak"
    WANDERING_HERO = "wandering_hero"


class Urgency(str, enum.Enum):
    URGENT = "urgent"          # fire ASAP
    HIGH = "high"
    NORMAL = "normal"
    BACKGROUND = "background"   # for ambient flavor


_URGENCY_ORDER: dict[Urgency, int] = {
    Urgency.URGENT: 0,
    Urgency.HIGH: 1,
    Urgency.NORMAL: 2,
    Urgency.BACKGROUND: 3,
}


@dataclasses.dataclass(frozen=True)
class FactionTension:
    faction_a: str
    faction_b: str
    tension_pct: int             # 0..100; 80+ = imminent skirmish


@dataclasses.dataclass(frozen=True)
class WorldStateSnapshot:
    now_seconds: float = 0.0
    factions_in_tension: tuple[FactionTension, ...] = ()
    recent_boss_kills: tuple[tuple[str, str, int], ...] = ()
    # (player_id, boss_id, days_ago)
    outstanding_high_salience_rumors: int = 0
    recent_permadeaths: tuple[
        tuple[str, str, str], ...,
    ] = ()
    # (name, nation, cause)
    npc_grief_signals: tuple[
        tuple[str, str], ...,
    ] = ()
    # (mourner_npc_id, dead_npc_id)
    famous_player_fame_score: int = 0     # 0..1000
    famous_player_id: t.Optional[str] = None
    # Population unrest signals (e.g. plague rumor density)
    plague_rumors_in_zone: tuple[
        tuple[str, int], ...,
    ] = ()
    # (zone_id, count)


@dataclasses.dataclass(frozen=True)
class PlotHook:
    hook_id: str
    kind: PlotHookKind
    urgency: Urgency
    summary: str
    triggering_actor_id: t.Optional[str] = None
    target_actor_id: t.Optional[str] = None
    payload: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )
    proposed_at_seconds: float = 0.0


@dataclasses.dataclass(frozen=True)
class PlotGenerationResult:
    hooks: tuple[PlotHook, ...]
    skipped_low_urgency: int = 0


@dataclasses.dataclass
class AIPlotGenerator:
    max_hooks_per_tick: int = DEFAULT_MAX_HOOKS_PER_TICK
    fame_threshold_for_wandering_hero: int = 500
    boss_kill_revenge_window_days: int = 14
    tension_threshold_for_border: int = 70
    plague_outbreak_rumor_threshold: int = 4
    _hook_counter: int = 0
    _proposed: dict[str, PlotHook] = dataclasses.field(
        default_factory=dict,
    )
    _acknowledged: set[str] = dataclasses.field(
        default_factory=set,
    )

    def _next_hook_id(self, prefix: str) -> str:
        hid = f"plot_{prefix}_{self._hook_counter}"
        self._hook_counter += 1
        return hid

    def _gen_revenge(
        self, snapshot: WorldStateSnapshot,
    ) -> list[PlotHook]:
        out: list[PlotHook] = []
        for player_id, boss_id, days in snapshot.recent_boss_kills:
            if days > self.boss_kill_revenge_window_days:
                continue
            urgency = (
                Urgency.URGENT if days <= 2 else Urgency.HIGH
            )
            out.append(PlotHook(
                hook_id=self._next_hook_id("rev"),
                kind=PlotHookKind.REVENGE_ARC,
                urgency=urgency,
                summary=(
                    f"{boss_id}'s allies hunt {player_id} "
                    f"for revenge"
                ),
                triggering_actor_id=boss_id,
                target_actor_id=player_id,
                payload={
                    "boss_id": boss_id,
                    "player_id": player_id,
                    "days_ago": str(days),
                },
                proposed_at_seconds=snapshot.now_seconds,
            ))
        return out

    def _gen_succession(
        self, snapshot: WorldStateSnapshot,
    ) -> list[PlotHook]:
        out: list[PlotHook] = []
        for name, nation, cause in snapshot.recent_permadeaths:
            out.append(PlotHook(
                hook_id=self._next_hook_id("succ"),
                kind=PlotHookKind.SUCCESSION_CRISIS,
                urgency=Urgency.HIGH,
                summary=(
                    f"{name} of {nation} is dead — heir wars "
                    "loom"
                ),
                triggering_actor_id=name,
                payload={
                    "name": name, "nation": nation,
                    "cause": cause,
                },
                proposed_at_seconds=snapshot.now_seconds,
            ))
        return out

    def _gen_grieving(
        self, snapshot: WorldStateSnapshot,
    ) -> list[PlotHook]:
        out: list[PlotHook] = []
        for mourner, dead in snapshot.npc_grief_signals:
            out.append(PlotHook(
                hook_id=self._next_hook_id("grief"),
                kind=PlotHookKind.GRIEVING_ARC,
                urgency=Urgency.NORMAL,
                summary=(
                    f"{mourner} mourns {dead} — quest of "
                    "farewell available"
                ),
                triggering_actor_id=mourner,
                target_actor_id=dead,
                payload={
                    "mourner_id": mourner, "dead_id": dead,
                },
                proposed_at_seconds=snapshot.now_seconds,
            ))
        return out

    def _gen_border_incident(
        self, snapshot: WorldStateSnapshot,
    ) -> list[PlotHook]:
        out: list[PlotHook] = []
        for tension in snapshot.factions_in_tension:
            if tension.tension_pct < self.tension_threshold_for_border:
                continue
            out.append(PlotHook(
                hook_id=self._next_hook_id("border"),
                kind=PlotHookKind.BORDER_INCIDENT,
                urgency=(
                    Urgency.URGENT
                    if tension.tension_pct >= 90
                    else Urgency.HIGH
                ),
                summary=(
                    f"{tension.faction_a} skirmishers cross "
                    f"into {tension.faction_b} land"
                ),
                triggering_actor_id=tension.faction_a,
                target_actor_id=tension.faction_b,
                payload={
                    "tension_pct": str(tension.tension_pct),
                },
                proposed_at_seconds=snapshot.now_seconds,
            ))
        return out

    def _gen_scandal(
        self, snapshot: WorldStateSnapshot,
    ) -> list[PlotHook]:
        out: list[PlotHook] = []
        if snapshot.outstanding_high_salience_rumors >= 5:
            out.append(PlotHook(
                hook_id=self._next_hook_id("scandal"),
                kind=PlotHookKind.SCANDAL,
                urgency=Urgency.NORMAL,
                summary=(
                    "rumors swirl — a high-rep NPC's secret "
                    "leaks"
                ),
                payload={
                    "rumor_count": str(
                        snapshot.outstanding_high_salience_rumors,
                    ),
                },
                proposed_at_seconds=snapshot.now_seconds,
            ))
        return out

    def _gen_plague(
        self, snapshot: WorldStateSnapshot,
    ) -> list[PlotHook]:
        out: list[PlotHook] = []
        for zone_id, count in snapshot.plague_rumors_in_zone:
            if count < self.plague_outbreak_rumor_threshold:
                continue
            out.append(PlotHook(
                hook_id=self._next_hook_id("plague"),
                kind=PlotHookKind.PLAGUE_OUTBREAK,
                urgency=(
                    Urgency.URGENT if count >= 8 else Urgency.HIGH
                ),
                summary=(
                    f"plague rumors thick in {zone_id} — "
                    "investigate"
                ),
                payload={"zone_id": zone_id,
                          "rumor_count": str(count)},
                proposed_at_seconds=snapshot.now_seconds,
            ))
        return out

    def _gen_wandering_hero(
        self, snapshot: WorldStateSnapshot,
    ) -> list[PlotHook]:
        if (
            snapshot.famous_player_id is None
            or snapshot.famous_player_fame_score
            < self.fame_threshold_for_wandering_hero
        ):
            return []
        return [PlotHook(
            hook_id=self._next_hook_id("wander"),
            kind=PlotHookKind.WANDERING_HERO,
            urgency=Urgency.NORMAL,
            summary=(
                f"{snapshot.famous_player_id}'s fame draws "
                "challengers"
            ),
            target_actor_id=snapshot.famous_player_id,
            payload={
                "fame": str(
                    snapshot.famous_player_fame_score,
                ),
            },
            proposed_at_seconds=snapshot.now_seconds,
        )]

    def generate(
        self, *, snapshot: WorldStateSnapshot,
    ) -> PlotGenerationResult:
        proposals: list[PlotHook] = []
        proposals.extend(self._gen_revenge(snapshot))
        proposals.extend(self._gen_succession(snapshot))
        proposals.extend(self._gen_grieving(snapshot))
        proposals.extend(self._gen_border_incident(snapshot))
        proposals.extend(self._gen_scandal(snapshot))
        proposals.extend(self._gen_plague(snapshot))
        proposals.extend(self._gen_wandering_hero(snapshot))
        # Sort by urgency, then by triggering time
        proposals.sort(
            key=lambda h: (
                _URGENCY_ORDER[h.urgency],
                h.proposed_at_seconds,
            ),
        )
        # Cap at max_hooks_per_tick
        accepted = proposals[:self.max_hooks_per_tick]
        skipped = len(proposals) - len(accepted)
        for h in accepted:
            self._proposed[h.hook_id] = h
        return PlotGenerationResult(
            hooks=tuple(accepted),
            skipped_low_urgency=skipped,
        )

    def acknowledge(self, *, hook_id: str) -> bool:
        if hook_id not in self._proposed:
            return False
        if hook_id in self._acknowledged:
            return False
        self._acknowledged.add(hook_id)
        return True

    def is_acknowledged(self, hook_id: str) -> bool:
        return hook_id in self._acknowledged

    def total_proposed(self) -> int:
        return len(self._proposed)


__all__ = [
    "DEFAULT_MAX_HOOKS_PER_TICK",
    "PlotHookKind", "Urgency",
    "FactionTension",
    "WorldStateSnapshot", "PlotHook",
    "PlotGenerationResult", "AIPlotGenerator",
]
