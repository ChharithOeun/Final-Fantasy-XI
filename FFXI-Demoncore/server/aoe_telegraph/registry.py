"""Telegraph lifecycle + visibility rules + reaction-window helpers.

State machine:
    TARGETING - preview shape; visible only to caster (faction-tinted)
    ACTIVE    - cast started; visible to allies in range; if caster is
                a player/ally, also visible to enemies in PvP. If caster
                is an enemy boss/mob, the active telegraph is NOT
                visible to players (intentional skill ceiling).
    LANDING   - cast complete, applying damage to entities still inside
    CANCELED  - caster aborted before cast started
    INTERRUPTED - cast interrupted mid-cast (no damage)

Visibility resolution is faction-aware:
    Caster faction "player_party" / "ally_npc":
        TARGETING -> caster only
        ACTIVE    -> all observers in range
    Caster faction "enemy" / "monster_party":
        TARGETING -> caster only (server-side; never to players)
        ACTIVE    -> NPCs see it for mood propagation; players don't
                     see the decal — they read the wind-up animation
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from .geometry import (
    TelegraphShape,
    point_inside_telegraph,
)


class TelegraphState(str, enum.Enum):
    TARGETING = "targeting"
    ACTIVE = "active"
    LANDING = "landing"
    CANCELED = "canceled"
    INTERRUPTED = "interrupted"


# Caster factions that broadcast their active telegraph to players.
# Enemy factions don't — players read the animation instead.
PLAYER_VISIBLE_CASTER_FACTIONS = frozenset({"player_party", "ally_npc"})


@dataclasses.dataclass
class TelegraphSpec:
    """The static description of a spell/ability's AOE shape."""
    spell_id: str
    shape: TelegraphShape
    element: str = "physical"
    radius_cm: t.Optional[float] = None
    inner_radius_cm: t.Optional[float] = None
    angle_deg: t.Optional[float] = None
    length_cm: t.Optional[float] = None
    polygon: t.Optional[list[tuple[float, float]]] = None


@dataclasses.dataclass
class TelegraphInstance:
    """A live telegraph in the world."""
    instance_id: str
    spec: TelegraphSpec
    caster_id: str
    caster_faction: str            # "player_party" / "ally_npc" /
                                    # "enemy" / "monster_party"
    target_position: tuple[float, float]
    facing_deg: float = 0.0
    state: TelegraphState = TelegraphState.TARGETING
    cast_started_at: t.Optional[float] = None
    cast_duration: float = 0.0     # seconds; 0 for instant

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def fill_pct(self, *, now: float) -> float:
        """0 .. 1 progress through the cast bar. Returns 0 outside
        the ACTIVE window."""
        if self.state != TelegraphState.ACTIVE:
            return 0.0
        if self.cast_started_at is None or self.cast_duration <= 0:
            return 1.0
        elapsed = now - self.cast_started_at
        return max(0.0, min(1.0, elapsed / self.cast_duration))

    def land_at(self) -> t.Optional[float]:
        """Server-time at which this cast lands. None if not yet ACTIVE."""
        if self.cast_started_at is None:
            return None
        return self.cast_started_at + self.cast_duration

    def contains(self, point: tuple[float, float]) -> bool:
        """Geometric containment check using the spec's shape params."""
        return point_inside_telegraph(
            shape=self.spec.shape,
            origin=self.target_position,
            point=point,
            radius_cm=self.spec.radius_cm,
            inner_radius_cm=self.spec.inner_radius_cm,
            length_cm=self.spec.length_cm,
            angle_deg=self.spec.angle_deg,
            facing_deg=self.facing_deg,
            polygon=self.spec.polygon,
        )


class TelegraphRegistry:
    """All live telegraphs in a zone. Caller drives the state machine
    via begin_targeting / commit_cast / cancel / interrupt / complete."""

    def __init__(self) -> None:
        self._by_id: dict[str, TelegraphInstance] = {}
        self._next_seq: int = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def begin_targeting(self,
                          *,
                          spec: TelegraphSpec,
                          caster_id: str,
                          caster_faction: str,
                          target_position: tuple[float, float],
                          facing_deg: float = 0.0,
                          ) -> TelegraphInstance:
        instance_id = self._mint_id()
        instance = TelegraphInstance(
            instance_id=instance_id, spec=spec,
            caster_id=caster_id, caster_faction=caster_faction,
            target_position=target_position,
            facing_deg=facing_deg,
            state=TelegraphState.TARGETING,
        )
        self._by_id[instance_id] = instance
        return instance

    def update_target_position(self,
                                 instance_id: str,
                                 *,
                                 new_position: tuple[float, float],
                                 new_facing_deg: t.Optional[float] = None,
                                 ) -> bool:
        """Re-target during the TARGETING preview. Returns True if
        applied; False if the instance is past TARGETING."""
        instance = self._by_id.get(instance_id)
        if instance is None or instance.state != TelegraphState.TARGETING:
            return False
        instance.target_position = new_position
        if new_facing_deg is not None:
            instance.facing_deg = new_facing_deg
        return True

    def commit_cast(self,
                     instance_id: str,
                     *,
                     cast_duration: float,
                     now: float) -> bool:
        """TARGETING -> ACTIVE. The active telegraph is now broadcast
        per visibility rules. Returns True on success."""
        instance = self._by_id.get(instance_id)
        if instance is None or instance.state != TelegraphState.TARGETING:
            return False
        instance.state = TelegraphState.ACTIVE
        instance.cast_started_at = now
        instance.cast_duration = cast_duration
        return True

    def cancel(self, instance_id: str) -> bool:
        instance = self._by_id.get(instance_id)
        if instance is None:
            return False
        if instance.state == TelegraphState.TARGETING:
            instance.state = TelegraphState.CANCELED
            return True
        return False

    def interrupt(self, instance_id: str) -> bool:
        instance = self._by_id.get(instance_id)
        if instance is None or instance.state != TelegraphState.ACTIVE:
            return False
        instance.state = TelegraphState.INTERRUPTED
        return True

    def complete(self,
                  instance_id: str,
                  *,
                  now: float,
                  candidate_targets: list[tuple[str, tuple[float, float]]],
                  ) -> list[str]:
        """Cast complete. Apply damage to candidates that are still
        inside the telegraph. Returns the list of hit entity ids.

        candidate_targets: list of (entity_id, position).
        """
        instance = self._by_id.get(instance_id)
        if instance is None or instance.state != TelegraphState.ACTIVE:
            return []
        instance.state = TelegraphState.LANDING

        hit: list[str] = []
        for entity_id, pos in candidate_targets:
            if instance.contains(pos):
                hit.append(entity_id)
        return hit

    def get(self, instance_id: str) -> t.Optional[TelegraphInstance]:
        return self._by_id.get(instance_id)

    def prune_terminal(self) -> int:
        """Drop CANCELED / INTERRUPTED / LANDING instances. Returns
        the number removed. Caller invokes per tick to keep the live
        set small."""
        terminal = {TelegraphState.CANCELED,
                     TelegraphState.INTERRUPTED,
                     TelegraphState.LANDING}
        before = len(self._by_id)
        self._by_id = {iid: i for iid, i in self._by_id.items()
                        if i.state not in terminal}
        return before - len(self._by_id)

    # ------------------------------------------------------------------
    # Visibility
    # ------------------------------------------------------------------

    def visible_to_observer(self,
                             *,
                             observer_id: str,
                             observer_faction: str,
                             observer_kind: str = "player",
                             ) -> list[TelegraphInstance]:
        """Return the list of telegraphs visible to this observer per
        the asymmetric visibility rules.

        observer_kind: 'player' | 'npc'. NPCs always see active enemy
                        telegraphs (mood propagation). Players don't
                        see active enemy telegraphs (skill-ceiling
                        intentional).
        """
        out: list[TelegraphInstance] = []
        for instance in self._by_id.values():
            if instance.state == TelegraphState.TARGETING:
                # Preview is caster-only regardless of faction
                if instance.caster_id == observer_id:
                    out.append(instance)
                continue

            if instance.state == TelegraphState.ACTIVE:
                if instance.caster_faction in PLAYER_VISIBLE_CASTER_FACTIONS:
                    # Player/ally cast: visible to all in range (caller
                    # filters by range; we don't track positions here)
                    out.append(instance)
                else:
                    # Enemy cast: only NPCs see the decal (mood). Players
                    # have to read animation. Caster of course sees it.
                    if instance.caster_id == observer_id:
                        out.append(instance)
                    elif observer_kind != "player":
                        out.append(instance)
            # Terminal states: don't render
        return out

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _mint_id(self) -> str:
        self._next_seq += 1
        return f"tg_{self._next_seq:08d}"


# ----------------------------------------------------------------------
# Reaction-window + mood helpers
# ----------------------------------------------------------------------

REACTION_WINDOW_FRACTION = 0.5   # 'half-time rule' from the doc


def reaction_window_seconds(cast_duration: float) -> float:
    """Roughly half the cast time is the reaction window per the doc.
    1.5s cast -> 0.75s window; 3.0s cast -> 1.5s window."""
    if cast_duration <= 0:
        return 0.0
    return cast_duration * REACTION_WINDOW_FRACTION


# Per-archetype mood deltas when an AOE telegraph appears under an NPC.
# Lifted from event_deltas.py extension in the design doc.
NPC_AOE_MOOD_DELTAS: dict[str, list[tuple[str, float]]] = {
    "civilian": [("fearful", +0.4)],
    "soldier":  [("alert", +0.3)],
    "hero":     [("alert", +0.4)],
    "vendor":   [("fearful", +0.3)],
    "guard":    [("alert", +0.3)],
}


def moods_to_emit(observer_archetype: str,
                   *,
                   event: str = "aoe_telegraph_visible_to_self",
                   ) -> list[tuple[str, float]]:
    """Return (mood, delta) pairs for the orchestrator to apply.

    `event` can be 'aoe_telegraph_visible_to_self', 'dodged_aoe', or
    'hit_by_aoe' — the doc specifies a few. We only encode the
    incoming-telegraph case here; the others use the same archetype
    table with sign flips that the orchestrator owns."""
    if event != "aoe_telegraph_visible_to_self":
        return []
    return NPC_AOE_MOOD_DELTAS.get(observer_archetype, [])
