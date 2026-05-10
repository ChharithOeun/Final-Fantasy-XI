"""Crowd director — ambient crowd life.

Spawns and despawns CrowdAgents per zone to hit a density
target, schedules waypoint motion, repels agents below a
minimum social distance, makes them aware of the player
when nearby (delegating eye contact to eye_animation), and
runs short-lived conversation pods of 2-4 NPCs.

Density targets are zone-driven: Bastok Markets 40, North
Gustaberg 8, Crawler's Nest 0. ``populate_zone(zone_id,
density_target)`` spawns the diff between current and
target counts using sequential agent ids.

Anti-clumping: ``MIN_SOCIAL_DISTANCE_M`` (1.2 m for general,
0.5 m for conversation pods). The repulsion is a single-
step nudge of magnitude ``REPEL_NUDGE_M`` away from the
nearest other agent — runs every tick.

Player awareness: agents within ``PLAYER_AWARE_RADIUS_M``
(4 m) flip ``is_player_aware`` and (if an EyeAnimationSystem
is wired) make eye contact. Greeting policy varies by
archetype: vendors and idlers wave / nod, guards stay
stoic, kids sidle away.

Conversation pods spawn at a fixed position with N members
arrayed in a small circle; pod_lifetime_s = 30 by default.
``tick`` ages the pods and breaks them apart on expiry.

Public surface
--------------
    Archetype enum
    GreetPolicy enum
    CrowdAgent dataclass
    CrowdDirector
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


class Archetype(enum.Enum):
    VENDOR_BUSY = "vendor_busy"
    CIVILIAN_PURPOSEFUL = "civilian_purposeful"
    GUARD_PATROL = "guard_patrol"
    CONVERSATION_POD_MEMBER = "conversation_pod_member"
    IDLER_LEAN = "idler_lean"
    IDLER_SIT = "idler_sit"
    IDLER_SMOKE = "idler_smoke"
    IDLER_DRINK = "idler_drink"
    CHILD_PLAY = "child_play"
    MERCHANT_HAGGLE = "merchant_haggle"


class GreetPolicy(enum.Enum):
    WAVE = "wave"
    NOD = "nod"
    STOIC = "stoic"
    SIDLE_AWAY = "sidle_away"


_GREET_BY_ARCHETYPE: dict[Archetype, GreetPolicy] = {
    Archetype.VENDOR_BUSY: GreetPolicy.WAVE,
    Archetype.MERCHANT_HAGGLE: GreetPolicy.WAVE,
    Archetype.CIVILIAN_PURPOSEFUL: GreetPolicy.NOD,
    Archetype.GUARD_PATROL: GreetPolicy.STOIC,
    Archetype.CONVERSATION_POD_MEMBER: GreetPolicy.NOD,
    Archetype.IDLER_LEAN: GreetPolicy.NOD,
    Archetype.IDLER_SIT: GreetPolicy.NOD,
    Archetype.IDLER_SMOKE: GreetPolicy.STOIC,
    Archetype.IDLER_DRINK: GreetPolicy.WAVE,
    Archetype.CHILD_PLAY: GreetPolicy.SIDLE_AWAY,
}


MIN_SOCIAL_DISTANCE_M: float = 1.2
MIN_POD_DISTANCE_M: float = 0.5
PLAYER_AWARE_RADIUS_M: float = 4.0
REPEL_NUDGE_M: float = 0.05


@dataclasses.dataclass
class CrowdAgent:
    agent_id: str
    npc_id: str
    zone_id: str
    archetype: Archetype
    home_pos_xyz: tuple[float, float, float]
    current_pos_xyz: tuple[float, float, float]
    schedule: tuple[
        tuple[float, tuple[float, float, float]], ...
    ] = ()  # (time_s, target_xyz)
    conversation_partner_ids: tuple[str, ...] = ()
    is_player_aware: bool = False
    pod_id: str | None = None
    despawned: bool = False


def _dist(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> float:
    return math.sqrt(
        (a[0] - b[0]) ** 2
        + (a[1] - b[1]) ** 2
        + (a[2] - b[2]) ** 2
    )


@dataclasses.dataclass
class _Pod:
    pod_id: str
    zone_id: str
    member_ids: tuple[str, ...]
    age_s: float = 0.0
    lifetime_s: float = 30.0


@dataclasses.dataclass
class CrowdDirector:
    pod_lifetime_s: float = 30.0
    _agents: dict[str, CrowdAgent] = dataclasses.field(
        default_factory=dict,
    )
    _pods: dict[str, _Pod] = dataclasses.field(
        default_factory=dict,
    )
    _next_agent_seq: int = 1
    _next_pod_seq: int = 1
    # zone_id -> total spawn count history (for stable ids).
    _zone_seq: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )

    # ---- registration ----

    def register_agent(self, agent: CrowdAgent) -> None:
        if not agent.agent_id:
            raise ValueError("agent_id required")
        if agent.agent_id in self._agents:
            raise ValueError(
                f"duplicate agent: {agent.agent_id}",
            )
        self._agents[agent.agent_id] = agent

    def get(self, agent_id: str) -> CrowdAgent:
        if agent_id not in self._agents:
            raise KeyError(f"unknown agent: {agent_id}")
        return self._agents[agent_id]

    def has(self, agent_id: str) -> bool:
        return agent_id in self._agents

    def despawn_agent(self, agent_id: str) -> None:
        # Marking despawned rather than deleting lets pods
        # finish cleanly + tests inspect the historical set.
        a = self.get(agent_id)
        a.despawned = True

    def alive_agents(self) -> tuple[CrowdAgent, ...]:
        return tuple(
            a for a in self._agents.values()
            if not a.despawned
        )

    def agents_in_zone(
        self, zone_id: str,
    ) -> tuple[CrowdAgent, ...]:
        return tuple(
            sorted(
                (
                    a for a in self._agents.values()
                    if a.zone_id == zone_id and not a.despawned
                ),
                key=lambda a: a.agent_id,
            )
        )

    # ---- population control ----

    def populate_zone(
        self,
        zone_id: str,
        density_target: int,
        archetype: Archetype = Archetype.CIVILIAN_PURPOSEFUL,
    ) -> tuple[str, ...]:
        """Spawn (or despawn) agents in zone_id until live
        count == density_target. Returns the agent_ids
        affected (newly-spawned or newly-despawned)."""
        if density_target < 0:
            raise ValueError(
                "density_target must be >= 0",
            )
        live = self.agents_in_zone(zone_id)
        diff = density_target - len(live)
        affected: list[str] = []
        if diff > 0:
            # Spawn new agents.
            for _ in range(diff):
                seq = self._zone_seq.get(zone_id, 0) + 1
                self._zone_seq[zone_id] = seq
                aid = f"{zone_id}:agent_{seq:04d}"
                # Distribute on a coarse grid so initial
                # positions don't all collide.
                offset = (seq * 1.7) % 12.0 - 6.0
                pos = (offset, 0.0, ((seq * 0.9) % 12.0) - 6.0)
                ag = CrowdAgent(
                    agent_id=aid,
                    npc_id=f"npc_{aid}",
                    zone_id=zone_id,
                    archetype=archetype,
                    home_pos_xyz=pos,
                    current_pos_xyz=pos,
                )
                self.register_agent(ag)
                affected.append(aid)
        elif diff < 0:
            # Despawn the highest-id agents first.
            ids = [a.agent_id for a in live]
            ids.sort(reverse=True)
            for aid in ids[:abs(diff)]:
                self.despawn_agent(aid)
                affected.append(aid)
        return tuple(sorted(affected))

    def density_of(self, zone_id: str) -> int:
        return len(self.agents_in_zone(zone_id))

    # ---- conversation pods ----

    def spawn_conversation_pod(
        self,
        zone_id: str,
        position: tuple[float, float, float],
        member_count: int,
    ) -> str:
        if not (2 <= member_count <= 4):
            raise ValueError(
                "member_count must be 2..4",
            )
        pod_id = f"pod_{self._next_pod_seq:05d}"
        self._next_pod_seq += 1
        members: list[str] = []
        for i in range(member_count):
            ang = (math.tau / member_count) * i
            r = 0.6
            pos = (
                position[0] + math.cos(ang) * r,
                position[1],
                position[2] + math.sin(ang) * r,
            )
            seq = self._zone_seq.get(zone_id, 0) + 1
            self._zone_seq[zone_id] = seq
            aid = f"{zone_id}:agent_{seq:04d}"
            ag = CrowdAgent(
                agent_id=aid,
                npc_id=f"npc_{aid}",
                zone_id=zone_id,
                archetype=Archetype.CONVERSATION_POD_MEMBER,
                home_pos_xyz=pos,
                current_pos_xyz=pos,
                pod_id=pod_id,
            )
            self.register_agent(ag)
            members.append(aid)
        # Cross-link the partners.
        member_tup = tuple(members)
        for aid in members:
            self._agents[aid].conversation_partner_ids = (
                tuple(x for x in member_tup if x != aid)
            )
        self._pods[pod_id] = _Pod(
            pod_id=pod_id,
            zone_id=zone_id,
            member_ids=member_tup,
            lifetime_s=self.pod_lifetime_s,
        )
        return pod_id

    def pods_in_zone(self, zone_id: str) -> tuple[str, ...]:
        return tuple(
            sorted(
                pid for pid, p in self._pods.items()
                if p.zone_id == zone_id
            )
        )

    def has_pod(self, pod_id: str) -> bool:
        return pod_id in self._pods

    def pod_age(self, pod_id: str) -> float:
        if pod_id not in self._pods:
            raise KeyError(f"unknown pod: {pod_id}")
        return self._pods[pod_id].age_s

    # ---- awareness ----

    def player_aware_agents(
        self,
        player_pos: tuple[float, float, float],
        radius_m: float = PLAYER_AWARE_RADIUS_M,
    ) -> tuple[CrowdAgent, ...]:
        return tuple(
            a for a in self.alive_agents()
            if _dist(a.current_pos_xyz, player_pos) <= radius_m
        )

    def greet_policy_for(
        self, agent_id: str,
    ) -> GreetPolicy:
        return _GREET_BY_ARCHETYPE[
            self.get(agent_id).archetype
        ]

    # ---- per-tick update ----

    def tick(
        self,
        dt: float,
        player_pos: tuple[float, float, float],
        eye_system: t.Any | None = None,
        player_id: str = "player",
    ) -> dict[str, t.Any]:
        """Advance the crowd simulation. Returns a small
        report dict (despawned_pods, repelled_pairs,
        aware_count) so tests can inspect what changed."""
        if dt <= 0:
            raise ValueError("dt must be > 0")
        report: dict[str, t.Any] = {
            "despawned_pods": [],
            "repelled_pairs": [],
            "aware_count": 0,
        }
        # 1. Player awareness.
        for a in self.alive_agents():
            d = _dist(a.current_pos_xyz, player_pos)
            was_aware = a.is_player_aware
            a.is_player_aware = d <= PLAYER_AWARE_RADIUS_M
            if a.is_player_aware:
                report["aware_count"] += 1
                if eye_system is not None and not was_aware:
                    # Hand off to eye_animation if wired.
                    if hasattr(eye_system, "register_eyes"):
                        try:
                            if not eye_system.has(a.npc_id):
                                eye_system.register_eyes(
                                    a.npc_id,
                                )
                        except (AttributeError, ValueError):
                            pass
                    if hasattr(
                        eye_system, "set_look_target",
                    ):
                        try:
                            eye_system.set_look_target(
                                a.npc_id, player_id,
                            )
                        except (KeyError, AttributeError):
                            pass
        # 2. Anti-clumping repulsion.
        agents = list(self.alive_agents())
        for i, a in enumerate(agents):
            for b in agents[i + 1:]:
                if a.zone_id != b.zone_id:
                    continue
                d = _dist(a.current_pos_xyz, b.current_pos_xyz)
                same_pod = (
                    a.pod_id is not None
                    and a.pod_id == b.pod_id
                )
                threshold = (
                    MIN_POD_DISTANCE_M if same_pod
                    else MIN_SOCIAL_DISTANCE_M
                )
                if d < threshold and d > 0:
                    # Push b away from a.
                    nx = (
                        b.current_pos_xyz[0]
                        - a.current_pos_xyz[0]
                    ) / d
                    nz = (
                        b.current_pos_xyz[2]
                        - a.current_pos_xyz[2]
                    ) / d
                    new_b = (
                        b.current_pos_xyz[0]
                        + nx * REPEL_NUDGE_M,
                        b.current_pos_xyz[1],
                        b.current_pos_xyz[2]
                        + nz * REPEL_NUDGE_M,
                    )
                    b.current_pos_xyz = new_b
                    report["repelled_pairs"].append(
                        (a.agent_id, b.agent_id),
                    )
        # 3. Pod aging + cleanup.
        expired: list[str] = []
        for pod_id, pod in list(self._pods.items()):
            pod.age_s += dt
            if pod.age_s >= pod.lifetime_s:
                expired.append(pod_id)
        for pod_id in expired:
            pod = self._pods.pop(pod_id)
            report["despawned_pods"].append(pod_id)
            for aid in pod.member_ids:
                if aid in self._agents:
                    self._agents[aid].pod_id = None
                    self._agents[aid].conversation_partner_ids = (
                        ()
                    )
        return report

    # ---- diagnostics ----

    def all_zones(self) -> tuple[str, ...]:
        return tuple(
            sorted({
                a.zone_id for a in self._agents.values()
                if not a.despawned
            })
        )


__all__ = [
    "Archetype",
    "GreetPolicy",
    "CrowdAgent",
    "CrowdDirector",
    "MIN_SOCIAL_DISTANCE_M",
    "MIN_POD_DISTANCE_M",
    "PLAYER_AWARE_RADIUS_M",
]
