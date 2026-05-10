"""Net replication — authoritative server entity replication
with client prediction.

FFXI's retail networking is the classic 2002 model — TCP for
auth + chat, UDP for game traffic, and a fixed-rate broadcast
of everyone-in-zone to everyone-in-zone. That scales to a
6-person party in a quiet field and falls over the moment 30
players pile on Kirin. Modern MMO networking is built on
interest management + replication priority + client
prediction + snapshot interpolation. This module is the
schema and the algorithm for all of those.

The model is borrowed from Quake/CS:GO/Overwatch/Valorant
with the FFXI-specific twist that party + alliance members
get expanded interest radius (you can see your alliance lead
crossing the zone even at 250m because the social link is
the gameplay).

EntityKind enumerates everything the server replicates —
PLAYER, NPC, MOB, PROJECTILE, DROPPED_ITEM,
DESTRUCTIBLE_PROP, ENVIRONMENT_TRIGGER. Snapshot is the
on-wire delta: entity_id + kind + pos + vel + yaw + hp%
+ mp% + tp + status_flags + anim_state + server_tick +
timestamp_ms. The wire format is the same for all entity
kinds — different kinds use different fields, but the
shape is uniform so the deserializer is one path.

Replication priorities are tiered by kind + distance:
LOCAL_PLAYER gets 60Hz (the client owns prediction, server
reconciles), NEARBY_PLAYER 30Hz within 50m / 10Hz 50-200m /
2Hz beyond. MOB_NEARBY 30Hz in combat / 10Hz idle.
PROJECTILE 60Hz (fast-moving, low margin for error).
STATIC entities (DROPPED_ITEM, DESTRUCTIBLE_PROP,
ENVIRONMENT_TRIGGER) only send on state-change.

Relevancy filtering: for each viewer, only entities within
interest_radius_m (default 200m) are sent. Party/alliance
members extend their effective radius because the social
link is the gameplay.

Client prediction: client extrapolates LOCAL_PLAYER and
PROJECTILE positions between server snapshots using last
velocity + the 100ms snapshot interval. Server reconciles
authoritative position on each snapshot; client snaps if
the delta exceeds 50cm (otherwise blend smoothly to
authority over the next 100ms).

Snapshot interpolation: remote entities render 100ms in the
past — the client always has two snapshots bracketing the
current render time and lerps between them. This is the
trick that makes 10Hz remote-entity updates look like 60Hz
smooth motion.

Public surface
--------------
    EntityKind enum
    ReplicationTier enum
    Snapshot dataclass (frozen)
    ReconcileResult dataclass (frozen)
    NetReplicationSystem
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


# Default interest radius (meters) — anything beyond this is
# culled from replication entirely.
DEFAULT_INTEREST_RADIUS_M = 200.0

# Snapshot interpolation buffer — render N ms in the past.
SNAPSHOT_INTERP_DELAY_MS = 100

# Client prediction snap threshold (cm) — if the client's
# predicted position is more than this far from the
# server's authoritative position, snap instead of blend.
PREDICTION_SNAP_DELTA_CM = 50.0

# Party/alliance interest-radius multiplier (members see
# each other at expanded distance).
PARTY_RADIUS_MULTIPLIER = 1.5


class EntityKind(enum.Enum):
    PLAYER = "player"
    NPC = "npc"
    MOB = "mob"
    PROJECTILE = "projectile"
    DROPPED_ITEM = "dropped_item"
    DESTRUCTIBLE_PROP = "destructible_prop"
    ENVIRONMENT_TRIGGER = "environment_trigger"


class ReplicationTier(enum.Enum):
    LOCAL_PLAYER = "local_player"          # 60Hz
    NEARBY_PLAYER_CLOSE = "nearby_close"   # 30Hz within 50m
    NEARBY_PLAYER_MID = "nearby_mid"       # 10Hz 50-200m
    NEARBY_PLAYER_FAR = "nearby_far"       # 2Hz >200m
    MOB_COMBAT = "mob_combat"              # 30Hz
    MOB_IDLE = "mob_idle"                  # 10Hz
    PROJECTILE = "projectile"              # 60Hz
    STATIC_ON_CHANGE = "static_on_change"  # change-only


# Hz per tier.
_HZ_BY_TIER: dict[ReplicationTier, float] = {
    ReplicationTier.LOCAL_PLAYER: 60.0,
    ReplicationTier.NEARBY_PLAYER_CLOSE: 30.0,
    ReplicationTier.NEARBY_PLAYER_MID: 10.0,
    ReplicationTier.NEARBY_PLAYER_FAR: 2.0,
    ReplicationTier.MOB_COMBAT: 30.0,
    ReplicationTier.MOB_IDLE: 10.0,
    ReplicationTier.PROJECTILE: 60.0,
    ReplicationTier.STATIC_ON_CHANGE: 0.0,
}


@dataclasses.dataclass(frozen=True)
class Snapshot:
    entity_id: str
    kind: EntityKind
    position_xyz: tuple[float, float, float]
    velocity_xyz: tuple[float, float, float]
    yaw_deg: float
    hp_pct: float
    mp_pct: float
    tp: int
    status_flags_bitmap: int
    anim_state_id: int
    server_tick: int
    timestamp_ms: int


@dataclasses.dataclass(frozen=True)
class ReconcileResult:
    entity_id: str
    delta_cm: float
    should_snap: bool
    blend_ms: int
    authoritative_position: tuple[float, float, float]


def _distance_m(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    dz = a[2] - b[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)


@dataclasses.dataclass
class NetReplicationSystem:
    # entity_id -> ordered list of snapshots (oldest-first).
    _history: dict[str, list[Snapshot]] = dataclasses.field(
        default_factory=dict,
    )
    # entity_id -> EntityKind (registered).
    _kinds: dict[str, EntityKind] = dataclasses.field(
        default_factory=dict,
    )
    # viewer_id -> interest radius (m).
    _interest: dict[str, float] = dataclasses.field(
        default_factory=dict,
    )
    # viewer_id -> set of "linked" ids (party + alliance).
    _social_links: dict[str, set[str]] = dataclasses.field(
        default_factory=dict,
    )
    # mob entity_id -> bool (in combat?)
    _mob_in_combat: dict[str, bool] = dataclasses.field(
        default_factory=dict,
    )
    # Predicted client positions — last reported by client.
    _client_predicted: dict[
        str, tuple[float, float, float]
    ] = dataclasses.field(default_factory=dict)
    # History cap per entity.
    _max_history: int = 64

    # ---------------------------------------------- register
    def register_entity(
        self,
        entity_id: str,
        kind: EntityKind,
    ) -> None:
        if not entity_id:
            raise ValueError("entity_id required")
        if entity_id in self._kinds:
            raise ValueError(
                f"duplicate entity_id: {entity_id}",
            )
        self._kinds[entity_id] = kind
        self._history[entity_id] = []

    def is_registered(self, entity_id: str) -> bool:
        return entity_id in self._kinds

    def kind_of(self, entity_id: str) -> EntityKind:
        if entity_id not in self._kinds:
            raise KeyError(f"unknown entity: {entity_id}")
        return self._kinds[entity_id]

    def entity_count(self) -> int:
        return len(self._kinds)

    # ---------------------------------------------- snapshots
    def record_snapshot(self, snap: Snapshot) -> None:
        if snap.entity_id not in self._kinds:
            raise KeyError(
                f"unknown entity: {snap.entity_id}",
            )
        if snap.kind != self._kinds[snap.entity_id]:
            raise ValueError(
                "kind mismatch for entity_id",
            )
        hist = self._history[snap.entity_id]
        hist.append(snap)
        # Keep history bounded.
        if len(hist) > self._max_history:
            del hist[: len(hist) - self._max_history]

    def latest_snapshot(self, entity_id: str) -> Snapshot:
        hist = self._history.get(entity_id)
        if not hist:
            raise KeyError(
                f"no snapshots for {entity_id}",
            )
        return hist[-1]

    def history_size(self, entity_id: str) -> int:
        return len(self._history.get(entity_id, []))

    # ---------------------------------------------- interest
    def set_interest_radius(
        self,
        player_id: str,
        radius_m: float,
    ) -> None:
        if radius_m < 0:
            raise ValueError("radius_m must be >= 0")
        self._interest[player_id] = radius_m

    def interest_radius(self, player_id: str) -> float:
        return self._interest.get(
            player_id, DEFAULT_INTEREST_RADIUS_M,
        )

    def link_social(
        self,
        viewer_id: str,
        linked_ids: t.Iterable[str],
    ) -> None:
        s = self._social_links.setdefault(viewer_id, set())
        for lid in linked_ids:
            s.add(lid)

    def clear_social(self, viewer_id: str) -> None:
        self._social_links.pop(viewer_id, None)

    def is_linked(self, viewer_id: str, other_id: str) -> bool:
        return other_id in self._social_links.get(
            viewer_id, set(),
        )

    # ---------------------------------------------- relevancy
    def relevant_entities_for(
        self,
        player_id: str,
        all_entities: t.Iterable[str],
    ) -> list[str]:
        if player_id not in self._history:
            return []
        try:
            viewer_pos = self.latest_snapshot(
                player_id,
            ).position_xyz
        except KeyError:
            return []
        radius = self.interest_radius(player_id)
        linked = self._social_links.get(player_id, set())
        out: list[str] = []
        for eid in all_entities:
            if eid == player_id:
                out.append(eid)
                continue
            if eid not in self._history or not self._history[eid]:
                continue
            other_pos = self._history[eid][-1].position_xyz
            d = _distance_m(viewer_pos, other_pos)
            r = radius
            if eid in linked:
                r = radius * PARTY_RADIUS_MULTIPLIER
            if d <= r:
                out.append(eid)
        return out

    # ---------------------------------------------- rate
    def replication_tier_for(
        self,
        viewer_id: str,
        target_id: str,
        distance_m: float,
        target_kind: EntityKind,
    ) -> ReplicationTier:
        if distance_m < 0:
            raise ValueError("distance_m must be >= 0")
        if viewer_id == target_id and target_kind == EntityKind.PLAYER:
            return ReplicationTier.LOCAL_PLAYER
        if target_kind == EntityKind.PROJECTILE:
            return ReplicationTier.PROJECTILE
        if target_kind == EntityKind.PLAYER:
            if distance_m <= 50.0:
                return ReplicationTier.NEARBY_PLAYER_CLOSE
            if distance_m <= 200.0:
                return ReplicationTier.NEARBY_PLAYER_MID
            return ReplicationTier.NEARBY_PLAYER_FAR
        if target_kind == EntityKind.MOB:
            if self._mob_in_combat.get(target_id, False):
                return ReplicationTier.MOB_COMBAT
            return ReplicationTier.MOB_IDLE
        # NPC, items, props, triggers => on-change.
        return ReplicationTier.STATIC_ON_CHANGE

    def replication_rate_for(
        self,
        viewer_id: str,
        target_id: str,
        distance_m: float,
        target_kind: EntityKind,
    ) -> float:
        tier = self.replication_tier_for(
            viewer_id, target_id, distance_m, target_kind,
        )
        return _HZ_BY_TIER[tier]

    def set_mob_combat(self, mob_id: str, in_combat: bool) -> None:
        self._mob_in_combat[mob_id] = in_combat

    # ---------------------------------------------- prediction
    def predict_position(
        self,
        entity_id: str,
        t_ms_ahead: int,
    ) -> tuple[float, float, float]:
        if t_ms_ahead < 0:
            raise ValueError("t_ms_ahead must be >= 0")
        snap = self.latest_snapshot(entity_id)
        dt = t_ms_ahead / 1000.0
        return (
            snap.position_xyz[0] + snap.velocity_xyz[0] * dt,
            snap.position_xyz[1] + snap.velocity_xyz[1] * dt,
            snap.position_xyz[2] + snap.velocity_xyz[2] * dt,
        )

    def set_client_predicted(
        self,
        entity_id: str,
        pos: tuple[float, float, float],
    ) -> None:
        self._client_predicted[entity_id] = pos

    def reconcile(
        self,
        entity_id: str,
        server_snapshot: Snapshot,
    ) -> ReconcileResult:
        client_pos = self._client_predicted.get(
            entity_id, server_snapshot.position_xyz,
        )
        delta_m = _distance_m(
            client_pos, server_snapshot.position_xyz,
        )
        delta_cm = delta_m * 100.0
        should_snap = delta_cm > PREDICTION_SNAP_DELTA_CM
        blend_ms = 0 if should_snap else 100
        return ReconcileResult(
            entity_id=entity_id,
            delta_cm=delta_cm,
            should_snap=should_snap,
            blend_ms=blend_ms,
            authoritative_position=server_snapshot.position_xyz,
        )

    # ---------------------------------------------- interp
    def snapshot_at(
        self,
        entity_id: str,
        t_ms_past: int,
    ) -> tuple[float, float, float]:
        """Interpolated position at (now - t_ms_past).

        Walks history; finds the two snapshots bracketing
        the target timestamp; linearly interpolates. If
        target is older than the oldest snapshot, returns
        the oldest. If newer than the newest, returns the
        newest (no extrapolation past authority).
        """
        if t_ms_past < 0:
            raise ValueError("t_ms_past must be >= 0")
        hist = self._history.get(entity_id, [])
        if not hist:
            raise KeyError(f"no history for {entity_id}")
        if len(hist) == 1:
            return hist[0].position_xyz
        latest = hist[-1]
        target_ts = latest.timestamp_ms - t_ms_past
        if target_ts >= latest.timestamp_ms:
            return latest.position_xyz
        if target_ts <= hist[0].timestamp_ms:
            return hist[0].position_xyz
        # Find bracket.
        for i in range(len(hist) - 1):
            a = hist[i]
            b = hist[i + 1]
            if a.timestamp_ms <= target_ts <= b.timestamp_ms:
                span = b.timestamp_ms - a.timestamp_ms
                if span <= 0:
                    return a.position_xyz
                u = (target_ts - a.timestamp_ms) / span
                return (
                    a.position_xyz[0]
                    + (b.position_xyz[0] - a.position_xyz[0])
                    * u,
                    a.position_xyz[1]
                    + (b.position_xyz[1] - a.position_xyz[1])
                    * u,
                    a.position_xyz[2]
                    + (b.position_xyz[2] - a.position_xyz[2])
                    * u,
                )
        return latest.position_xyz

    # ---------------------------------------------- helpers
    def prune_history_before(
        self,
        entity_id: str,
        cutoff_ms: int,
    ) -> int:
        hist = self._history.get(entity_id, [])
        keep = [s for s in hist if s.timestamp_ms >= cutoff_ms]
        removed = len(hist) - len(keep)
        self._history[entity_id] = keep
        return removed


__all__ = [
    "EntityKind",
    "ReplicationTier",
    "Snapshot",
    "ReconcileResult",
    "NetReplicationSystem",
    "DEFAULT_INTEREST_RADIUS_M",
    "SNAPSHOT_INTERP_DELAY_MS",
    "PREDICTION_SNAP_DELTA_CM",
    "PARTY_RADIUS_MULTIPLIER",
]
