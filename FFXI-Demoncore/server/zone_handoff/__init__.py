"""Zone handoff — invisible inter-zone transitions.

In retail FFXI, every zone change is a load screen. In Demoncore
the player walks across a boundary and the next zone is already
streaming. This module computes the hand-off:

  - When player_pos enters the *prefetch zone* of a boundary
    (predicted_distance_remaining_m / velocity = prefetch_eta_s),
    request the target zone's tiles to start LOADING.
  - When player_pos crosses the boundary volume, swap their
    zone assignment.
  - Cross-zone state continuity is preserved by emitting a
    HandoffEvent that other systems (aggro_system, mob_respawn,
    weather_zone_state, time-of-day) listen to. Their state is
    *not* reset.
  - NPCs mid-pursuit (Fomor, beastmen) carry their session_id
    across — the boundary is purely a tag change for them.
  - Multiplayer: client predicts the crossing for smooth motion;
    server holds authoritative position.

If prefetch fails (network/disk error), gracefully apply a small
(default 200 ms) hitch rather than fall back to a load screen.

Public surface
--------------
    HandoffOutcome enum
    ZoneBoundary dataclass (frozen)
    HandoffDecision dataclass (frozen)
    PursuingNpc dataclass (frozen)
    ZoneHandoffSystem
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


class HandoffOutcome(enum.Enum):
    NO_ACTION = "no_action"
    PREFETCH = "prefetch"
    CROSS = "cross"
    HITCH = "hitch"


@dataclasses.dataclass(frozen=True)
class ZoneBoundary:
    boundary_id: str
    zone_a_id: str
    zone_b_id: str
    transition_volume_min: tuple[float, float, float]
    transition_volume_max: tuple[float, float, float]
    prefetch_distance_m: float = 200.0
    predicted_player_velocity_kmh: float = 18.0


@dataclasses.dataclass(frozen=True)
class HandoffDecision:
    boundary_id: str
    outcome: HandoffOutcome
    target_zone_id: t.Optional[str]
    eta_seconds: float
    hitch_ms: int = 0


@dataclasses.dataclass(frozen=True)
class PursuingNpc:
    """An NPC currently chasing the player and about to cross
    a boundary along with them."""
    npc_id: str
    session_id: str
    family: str
    current_zone_id: str
    target_player_id: str


def _kmh_to_ms(v_kmh: float) -> float:
    return v_kmh * 1000.0 / 3600.0


def _point_in_volume(
    p: tuple[float, float, float],
    mn: tuple[float, float, float],
    mx: tuple[float, float, float],
) -> bool:
    return (
        mn[0] <= p[0] <= mx[0]
        and mn[1] <= p[1] <= mx[1]
        and mn[2] <= p[2] <= mx[2]
    )


def _boundary_center(
    b: ZoneBoundary,
) -> tuple[float, float, float]:
    mn = b.transition_volume_min
    mx = b.transition_volume_max
    return (
        (mn[0] + mx[0]) * 0.5,
        (mn[1] + mx[1]) * 0.5,
        (mn[2] + mx[2]) * 0.5,
    )


def _dist(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> float:
    return math.sqrt(
        (a[0] - b[0]) ** 2
        + (a[1] - b[1]) ** 2
        + (a[2] - b[2]) ** 2
    )


def is_within_handoff_window(
    player_pos: tuple[float, float, float],
    boundary: ZoneBoundary,
) -> bool:
    """True if the player is inside the prefetch ring of this
    boundary (or already inside the volume)."""
    if _point_in_volume(
        player_pos,
        boundary.transition_volume_min,
        boundary.transition_volume_max,
    ):
        return True
    d = _dist(player_pos, _boundary_center(boundary))
    return d <= boundary.prefetch_distance_m


def prefetch_eta_s(
    player_pos: tuple[float, float, float],
    velocity_kmh: float,
    target_boundary: ZoneBoundary,
) -> float:
    """Seconds until the player reaches the boundary at the
    given velocity. Returns 0 if already inside the volume.
    Returns +inf if velocity is zero."""
    if _point_in_volume(
        player_pos,
        target_boundary.transition_volume_min,
        target_boundary.transition_volume_max,
    ):
        return 0.0
    if velocity_kmh <= 0.0:
        return float("inf")
    d = _dist(player_pos, _boundary_center(target_boundary))
    return round(d / _kmh_to_ms(velocity_kmh), 4)


@dataclasses.dataclass
class ZoneHandoffSystem:
    """In-memory boundary book + handoff decisions."""
    default_hitch_ms: int = 200
    _boundaries: dict[str, ZoneBoundary] = dataclasses.field(
        default_factory=dict,
    )
    _prefetched: set[tuple[str, str]] = dataclasses.field(
        default_factory=set,
    )  # (boundary_id, target_zone_id) — has prefetch already fired
    _prefetch_ok: dict[str, bool] = dataclasses.field(
        default_factory=dict,
    )  # boundary_id -> last prefetch success flag (default True)
    _pursuing: dict[str, list[PursuingNpc]] = dataclasses.field(
        default_factory=dict,
    )  # boundary_id -> list of NPCs

    def register_boundary(self, boundary: ZoneBoundary) -> None:
        if not boundary.boundary_id:
            raise ValueError("boundary_id required")
        if boundary.zone_a_id == boundary.zone_b_id:
            raise ValueError("zone_a_id and zone_b_id must differ")
        if boundary.prefetch_distance_m <= 0:
            raise ValueError("prefetch_distance_m must be positive")
        for i in range(3):
            if (
                boundary.transition_volume_min[i]
                > boundary.transition_volume_max[i]
            ):
                raise ValueError(
                    "transition_volume_min must be <= max",
                )
        self._boundaries[boundary.boundary_id] = boundary
        self._prefetch_ok.setdefault(boundary.boundary_id, True)

    def get_boundary(self, boundary_id: str) -> ZoneBoundary:
        if boundary_id not in self._boundaries:
            raise KeyError(f"unknown boundary: {boundary_id}")
        return self._boundaries[boundary_id]

    def all_boundaries(self) -> tuple[ZoneBoundary, ...]:
        return tuple(self._boundaries.values())

    def boundaries_for_zone(
        self, zone_id: str,
    ) -> tuple[ZoneBoundary, ...]:
        return tuple(
            b for b in self._boundaries.values()
            if zone_id in (b.zone_a_id, b.zone_b_id)
        )

    def set_prefetch_outcome(
        self, boundary_id: str, success: bool,
    ) -> None:
        """Test/diagnostic hook to simulate a prefetch failure."""
        if boundary_id not in self._boundaries:
            raise KeyError(f"unknown boundary: {boundary_id}")
        self._prefetch_ok[boundary_id] = success

    def register_pursuing_npc(
        self, boundary_id: str, npc: PursuingNpc,
    ) -> None:
        if boundary_id not in self._boundaries:
            raise KeyError(f"unknown boundary: {boundary_id}")
        self._pursuing.setdefault(boundary_id, []).append(npc)

    def pursuing_npcs_to_handoff(
        self, boundary_id: str,
    ) -> tuple[PursuingNpc, ...]:
        if boundary_id not in self._boundaries:
            raise KeyError(f"unknown boundary: {boundary_id}")
        return tuple(self._pursuing.get(boundary_id, ()))

    def _target_zone(
        self, boundary: ZoneBoundary, current_zone: str,
    ) -> t.Optional[str]:
        if current_zone == boundary.zone_a_id:
            return boundary.zone_b_id
        if current_zone == boundary.zone_b_id:
            return boundary.zone_a_id
        return None

    def handoff_for(
        self,
        player_pos: tuple[float, float, float],
        velocity_kmh: float,
        current_zone: str,
    ) -> tuple[HandoffDecision, ...]:
        """Returns one HandoffDecision per boundary touching the
        current zone. Most are NO_ACTION; the interesting ones
        are PREFETCH (we should start streaming target zone),
        CROSS (player just entered the volume — swap zones),
        or HITCH (prefetch failed; brief stall to recover)."""
        decisions: list[HandoffDecision] = []
        for b in self._boundaries.values():
            target = self._target_zone(b, current_zone)
            if target is None:
                continue
            if _point_in_volume(
                player_pos,
                b.transition_volume_min,
                b.transition_volume_max,
            ):
                key = (b.boundary_id, target)
                if not self._prefetch_ok.get(b.boundary_id, True):
                    decisions.append(HandoffDecision(
                        boundary_id=b.boundary_id,
                        outcome=HandoffOutcome.HITCH,
                        target_zone_id=target,
                        eta_seconds=0.0,
                        hitch_ms=self.default_hitch_ms,
                    ))
                else:
                    decisions.append(HandoffDecision(
                        boundary_id=b.boundary_id,
                        outcome=HandoffOutcome.CROSS,
                        target_zone_id=target,
                        eta_seconds=0.0,
                    ))
                self._prefetched.add(key)
            elif is_within_handoff_window(player_pos, b):
                eta = prefetch_eta_s(
                    player_pos, velocity_kmh, b,
                )
                decisions.append(HandoffDecision(
                    boundary_id=b.boundary_id,
                    outcome=HandoffOutcome.PREFETCH,
                    target_zone_id=target,
                    eta_seconds=eta,
                ))
                self._prefetched.add((b.boundary_id, target))
            else:
                decisions.append(HandoffDecision(
                    boundary_id=b.boundary_id,
                    outcome=HandoffOutcome.NO_ACTION,
                    target_zone_id=target,
                    eta_seconds=float("inf"),
                ))
        decisions.sort(key=lambda d: d.boundary_id)
        return tuple(decisions)

    def has_prefetched(
        self, boundary_id: str, target_zone_id: str,
    ) -> bool:
        return (boundary_id, target_zone_id) in self._prefetched


__all__ = [
    "HandoffOutcome",
    "ZoneBoundary",
    "HandoffDecision",
    "PursuingNpc",
    "ZoneHandoffSystem",
    "is_within_handoff_window",
    "prefetch_eta_s",
]
