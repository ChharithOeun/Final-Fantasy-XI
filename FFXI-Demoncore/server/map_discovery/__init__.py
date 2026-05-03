"""Map discovery — per-player fog of war + landmark unlocks.

Players start the game with no maps. They earn map data either
by EXPLORING (visit a zone for the first time, fog clears in
chunks as they walk through it) or by BUYING from a cartographer
NPC who sells regional map sets.

Landmarks are notable POIs (the Star Sibyl's Statue, Galkan
Mining Hall, the Crag of Holla). First visit grants a small
honor reward and unlocks a TITLE.

Public surface
--------------
    DiscoveryMethod enum (EXPLORED / PURCHASED / GIFTED)
    Landmark dataclass
    PlayerMapState
        .visit_zone_chunk(zone, chunk_id, now)
        .has_zone(zone_id) / .chunks_seen(zone_id)
        .visit_landmark(landmark_id) -> bool (True = first time)
        .own_full_map(zone_id) -> bool
        .grant_full_map(zone_id, method)
    MapRegistry — global; holds zone + landmark catalogs
        .register_zone(...) / .register_landmark(...)
        .player(player_id) -> PlayerMapState
        .first_discovery_reward(landmark_id) -> rewards
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default reward grants per first-time landmark discovery.
DEFAULT_FIRST_DISCOVERY_HONOR = 5


class DiscoveryMethod(str, enum.Enum):
    EXPLORED = "explored"
    PURCHASED = "purchased"
    GIFTED = "gifted"


@dataclasses.dataclass(frozen=True)
class ZoneMapDef:
    zone_id: str
    label: str
    total_chunks: int = 16          # NxN grid, common = 4x4 = 16
    purchase_price_gil: int = 5_000
    region: str = ""


@dataclasses.dataclass(frozen=True)
class Landmark:
    landmark_id: str
    label: str
    zone_id: str
    title_id: t.Optional[str] = None
    honor_reward: int = DEFAULT_FIRST_DISCOVERY_HONOR
    notes: str = ""


@dataclasses.dataclass(frozen=True)
class FirstDiscoveryReward:
    accepted: bool
    honor_gained: int = 0
    title_id: t.Optional[str] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerMapState:
    player_id: str
    # zone_id -> set of chunk_ids the player has explored
    _chunks_seen: dict[
        str, set[int],
    ] = dataclasses.field(default_factory=dict)
    # zone_id -> DiscoveryMethod when the FULL map was granted
    _full_maps: dict[
        str, DiscoveryMethod,
    ] = dataclasses.field(default_factory=dict)
    # landmark_id -> first-visit timestamp
    _landmark_visits: dict[
        str, float,
    ] = dataclasses.field(default_factory=dict)

    def visit_zone_chunk(
        self, *, zone_id: str, chunk_id: int,
    ) -> bool:
        """Returns True if this is a NEW chunk for the player."""
        bucket = self._chunks_seen.setdefault(zone_id, set())
        if chunk_id in bucket:
            return False
        bucket.add(chunk_id)
        return True

    def chunks_seen(self, zone_id: str) -> int:
        return len(self._chunks_seen.get(zone_id, set()))

    def has_zone(self, zone_id: str) -> bool:
        """Player either has the full map OR has seen any chunk."""
        if zone_id in self._full_maps:
            return True
        return bool(self._chunks_seen.get(zone_id))

    def own_full_map(self, zone_id: str) -> bool:
        return zone_id in self._full_maps

    def grant_full_map(
        self, *, zone_id: str, method: DiscoveryMethod,
    ) -> None:
        self._full_maps[zone_id] = method

    def visit_landmark(
        self, *, landmark_id: str, now_seconds: float,
    ) -> bool:
        """Returns True if this is the FIRST visit."""
        if landmark_id in self._landmark_visits:
            return False
        self._landmark_visits[landmark_id] = now_seconds
        return True

    def landmarks_visited(self) -> tuple[str, ...]:
        return tuple(self._landmark_visits.keys())

    def total_zones_seen(self) -> int:
        return len(set(self._chunks_seen) | set(self._full_maps))


@dataclasses.dataclass
class MapRegistry:
    _zones: dict[str, ZoneMapDef] = dataclasses.field(
        default_factory=dict,
    )
    _landmarks: dict[str, Landmark] = dataclasses.field(
        default_factory=dict,
    )
    _players: dict[str, PlayerMapState] = dataclasses.field(
        default_factory=dict,
    )

    def register_zone(self, zone: ZoneMapDef) -> ZoneMapDef:
        if zone.total_chunks <= 0:
            raise ValueError("total_chunks must be positive")
        self._zones[zone.zone_id] = zone
        return zone

    def register_landmark(self, lm: Landmark) -> Landmark:
        self._landmarks[lm.landmark_id] = lm
        return lm

    def zone(self, zone_id: str) -> t.Optional[ZoneMapDef]:
        return self._zones.get(zone_id)

    def landmark(
        self, landmark_id: str,
    ) -> t.Optional[Landmark]:
        return self._landmarks.get(landmark_id)

    def landmarks_in_zone(
        self, zone_id: str,
    ) -> tuple[Landmark, ...]:
        return tuple(
            lm for lm in self._landmarks.values()
            if lm.zone_id == zone_id
        )

    def player(self, player_id: str) -> PlayerMapState:
        s = self._players.get(player_id)
        if s is None:
            s = PlayerMapState(player_id=player_id)
            self._players[player_id] = s
        return s

    def first_discovery_reward(
        self, *, player_id: str, landmark_id: str,
        now_seconds: float = 0.0,
    ) -> FirstDiscoveryReward:
        lm = self._landmarks.get(landmark_id)
        if lm is None:
            return FirstDiscoveryReward(
                accepted=False, reason="unknown landmark",
            )
        state = self.player(player_id)
        if not state.visit_landmark(
            landmark_id=landmark_id, now_seconds=now_seconds,
        ):
            return FirstDiscoveryReward(
                accepted=False,
                reason="already visited",
            )
        return FirstDiscoveryReward(
            accepted=True,
            honor_gained=lm.honor_reward,
            title_id=lm.title_id,
        )

    def coverage_pct(
        self, *, player_id: str, zone_id: str,
    ) -> int:
        zone = self._zones.get(zone_id)
        if zone is None:
            return 0
        state = self.player(player_id)
        if state.own_full_map(zone_id):
            return 100
        seen = state.chunks_seen(zone_id)
        return int((seen / zone.total_chunks) * 100)

    def total_zones(self) -> int:
        return len(self._zones)

    def total_landmarks(self) -> int:
        return len(self._landmarks)


__all__ = [
    "DEFAULT_FIRST_DISCOVERY_HONOR",
    "DiscoveryMethod",
    "ZoneMapDef", "Landmark",
    "FirstDiscoveryReward",
    "PlayerMapState", "MapRegistry",
]
