"""Net party sync — party state replication across the wire.

party_system owns the *membership* — who's in, who's leader,
who got kicked. This module owns the *replication* — HP/MP/
TP, position, status effects, current target, the
following-the-leader chain, and the auto-formation slots
the tank should be 8m forward of group center.

The wire rule: 5Hz inside the same zone (positions matter,
buff bars update smoothly), 1Hz cross-zone (your party
healer is in Sandy, you're in Bastok — you still see her
HP bar, you don't see her on your minimap).

Follow-the-leader is the canonical "I'll AFK and let my
party drag me" pattern. set_following(member, leader)
overrides the member's movement input — pathfind toward
leader, leave (re-engage normal input) when distance
exceeds following_radius (default 5m). break_follow on
combat engage, hard input, or zone-cross.

Auto-formation: TANK 8m forward of group center, HEAL 8m
behind, DD 4m left/right of leader, SUPPORT/UTILITY behind
DD. Formation is per-party opt-in; off by default because
sandbox.

Public surface
--------------
    PartyMemberRole enum
    PartyMemberState dataclass (frozen)
    PartySyncPayload dataclass (frozen)
    NetPartySyncSystem
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


# Hz rates by zone-match.
SYNC_HZ_SAME_ZONE = 5.0
SYNC_HZ_CROSS_ZONE = 1.0

# Follow-the-leader defaults.
DEFAULT_FOLLOWING_RADIUS_M = 5.0

# Formation offsets (meters).
TANK_FORWARD_M = 8.0
HEAL_BACK_M = 8.0
DD_FLANK_M = 4.0


class PartyMemberRole(enum.Enum):
    TANK = "tank"
    HEAL = "heal"
    DD = "dd"
    SUPPORT = "support"
    UTILITY = "utility"


@dataclasses.dataclass(frozen=True)
class PartyMemberState:
    player_id: str
    hp_pct: float
    mp_pct: float
    tp: int
    zone_id: str
    position_xyz: tuple[float, float, float]
    status_effects_bitmap: int
    current_target_id: str
    is_pulling: bool
    role: PartyMemberRole


@dataclasses.dataclass(frozen=True)
class PartySyncPayload:
    party_id: str
    viewer_id: str
    is_full: bool  # True = same zone full state; False = cross-zone summary
    members: tuple[PartyMemberState, ...]


@dataclasses.dataclass
class _PartyRecord:
    party_id: str
    leader_id: str
    members: dict[str, PartyMemberState] = dataclasses.field(
        default_factory=dict,
    )
    formation_enabled: bool = False


@dataclasses.dataclass
class NetPartySyncSystem:
    _parties: dict[str, _PartyRecord] = dataclasses.field(
        default_factory=dict,
    )
    # player_id -> party_id.
    _player_to_party: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )
    # follower_id -> leader_id.
    _following: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )
    # per-party following radius override.
    _following_radius: dict[str, float] = dataclasses.field(
        default_factory=dict,
    )

    # ---------------------------------------------- parties
    def register_party(
        self,
        party_id: str,
        leader_id: str,
    ) -> None:
        if not party_id:
            raise ValueError("party_id required")
        if party_id in self._parties:
            raise ValueError(f"duplicate party: {party_id}")
        if not leader_id:
            raise ValueError("leader_id required")
        self._parties[party_id] = _PartyRecord(
            party_id=party_id, leader_id=leader_id,
        )

    def party_count(self) -> int:
        return len(self._parties)

    def leader_of(self, party_id: str) -> str:
        return self._parties[party_id].leader_id

    def set_formation_enabled(
        self, party_id: str, enabled: bool,
    ) -> None:
        self._parties[party_id].formation_enabled = enabled

    def formation_enabled(self, party_id: str) -> bool:
        return self._parties[party_id].formation_enabled

    # ---------------------------------------------- members
    def update_member_state(
        self,
        party_id: str,
        state: PartyMemberState,
    ) -> None:
        if party_id not in self._parties:
            raise KeyError(f"unknown party: {party_id}")
        if not (0.0 <= state.hp_pct <= 1.0):
            raise ValueError("hp_pct must be in [0,1]")
        if not (0.0 <= state.mp_pct <= 1.0):
            raise ValueError("mp_pct must be in [0,1]")
        rec = self._parties[party_id]
        rec.members[state.player_id] = state
        self._player_to_party[state.player_id] = party_id

    def member_state(
        self, party_id: str, player_id: str,
    ) -> PartyMemberState:
        return self._parties[party_id].members[player_id]

    def member_count(self, party_id: str) -> int:
        return len(self._parties[party_id].members)

    # ---------------------------------------------- sync
    def sync_payload_for(
        self,
        party_id: str,
        viewer_id: str,
        zone_match: bool,
    ) -> PartySyncPayload:
        if party_id not in self._parties:
            raise KeyError(f"unknown party: {party_id}")
        rec = self._parties[party_id]
        if zone_match:
            # Full state.
            return PartySyncPayload(
                party_id=party_id,
                viewer_id=viewer_id,
                is_full=True,
                members=tuple(rec.members.values()),
            )
        # Cross-zone: strip position to (0,0,0) and current_target_id,
        # but keep HP/MP/TP/zone/role/status.
        slim = tuple(
            dataclasses.replace(
                m,
                position_xyz=(0.0, 0.0, 0.0),
                current_target_id="",
            )
            for m in rec.members.values()
        )
        return PartySyncPayload(
            party_id=party_id,
            viewer_id=viewer_id,
            is_full=False,
            members=slim,
        )

    def sync_hz(self, zone_match: bool) -> float:
        return SYNC_HZ_SAME_ZONE if zone_match else SYNC_HZ_CROSS_ZONE

    # ---------------------------------------------- follow
    def set_following(
        self,
        player_id: str,
        leader_id: str,
    ) -> None:
        if not player_id or not leader_id:
            raise ValueError("ids required")
        if player_id == leader_id:
            raise ValueError("cannot follow self")
        self._following[player_id] = leader_id

    def clear_following(self, player_id: str) -> None:
        self._following.pop(player_id, None)

    def following_of(self, player_id: str) -> str:
        return self._following.get(player_id, "")

    def set_following_radius(
        self, party_id: str, radius_m: float,
    ) -> None:
        if radius_m <= 0:
            raise ValueError("radius_m must be > 0")
        self._following_radius[party_id] = radius_m

    def following_radius(self, party_id: str) -> float:
        return self._following_radius.get(
            party_id, DEFAULT_FOLLOWING_RADIUS_M,
        )

    def should_break_follow(
        self,
        player_id: str,
        distance_to_leader_m: float,
    ) -> bool:
        if self._following.get(player_id, "") == "":
            return False
        party_id = self._player_to_party.get(player_id, "")
        if not party_id:
            return True
        radius = self.following_radius(party_id)
        # Re-engage pathfinding once outside radius.
        return distance_to_leader_m > radius

    # ---------------------------------------------- formation
    def _group_center(
        self, rec: _PartyRecord,
    ) -> tuple[float, float, float]:
        if not rec.members:
            return (0.0, 0.0, 0.0)
        xs = [m.position_xyz[0] for m in rec.members.values()]
        ys = [m.position_xyz[1] for m in rec.members.values()]
        zs = [m.position_xyz[2] for m in rec.members.values()]
        n = len(rec.members)
        return (sum(xs) / n, sum(ys) / n, sum(zs) / n)

    def formation_target_for(
        self,
        player_id: str,
        party_id: str,
        leader_facing_deg: float = 0.0,
    ) -> tuple[float, float, float]:
        """Compute the formation slot for player_id.

        leader_facing_deg defines the forward axis (0 deg =
        +X). Returns the world-space target position the
        player should pathfind toward."""
        if party_id not in self._parties:
            raise KeyError(f"unknown party: {party_id}")
        rec = self._parties[party_id]
        if player_id not in rec.members:
            raise KeyError(f"unknown member: {player_id}")
        if not rec.formation_enabled:
            # Formation disabled — return member's own position
            # (no override).
            return rec.members[player_id].position_xyz
        center = self._group_center(rec)
        role = rec.members[player_id].role
        rad = math.radians(leader_facing_deg)
        fx = math.cos(rad)
        fz = math.sin(rad)
        # Right vector (perpendicular).
        rx = -math.sin(rad)
        rz = math.cos(rad)
        if role == PartyMemberRole.TANK:
            dx = fx * TANK_FORWARD_M
            dz = fz * TANK_FORWARD_M
        elif role == PartyMemberRole.HEAL:
            dx = -fx * HEAL_BACK_M
            dz = -fz * HEAL_BACK_M
        elif role == PartyMemberRole.DD:
            # Stable left/right by member id parity.
            side = 1.0 if (
                hash(player_id) % 2 == 0
            ) else -1.0
            dx = rx * DD_FLANK_M * side
            dz = rz * DD_FLANK_M * side
        elif role == PartyMemberRole.SUPPORT:
            dx = -fx * (HEAL_BACK_M * 0.6)
            dz = -fz * (HEAL_BACK_M * 0.6)
        else:  # UTILITY
            dx = -fx * (HEAL_BACK_M * 0.3) + rx * DD_FLANK_M
            dz = -fz * (HEAL_BACK_M * 0.3) + rz * DD_FLANK_M
        return (center[0] + dx, center[1], center[2] + dz)

    # ---------------------------------------------- summary
    def party_health_summary(
        self, party_id: str,
    ) -> tuple[tuple[str, float, float, int], ...]:
        """Returns ordered (player_id, hp_pct, mp_pct, tp)
        tuples — for HUD party frame rendering. Order is
        leader first, then by player_id."""
        if party_id not in self._parties:
            raise KeyError(f"unknown party: {party_id}")
        rec = self._parties[party_id]
        ms = rec.members
        order = sorted(
            ms.keys(),
            key=lambda pid: (pid != rec.leader_id, pid),
        )
        return tuple(
            (pid, ms[pid].hp_pct, ms[pid].mp_pct, ms[pid].tp)
            for pid in order
        )


__all__ = [
    "PartyMemberRole",
    "PartyMemberState",
    "PartySyncPayload",
    "NetPartySyncSystem",
    "SYNC_HZ_SAME_ZONE",
    "SYNC_HZ_CROSS_ZONE",
    "DEFAULT_FOLLOWING_RADIUS_M",
    "TANK_FORWARD_M",
    "HEAL_BACK_M",
    "DD_FLANK_M",
]
