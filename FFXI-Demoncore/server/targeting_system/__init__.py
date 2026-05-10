"""Targeting system — tab-target, lock-on, AOE placement,
sub-target chain.

FFXI shipped with tab-target only — press tab, cycle the
nearest enemy, lock on. Modern action games layer
ground-targeted reticles, cone-facing, and friendly tab
on top. This module is the single decision-maker for "what
am I targeting right now?"

Tab cycling sorts candidates by camera-screen-distance:
the enemy closest to screen-center is "next" because that
matches what the player's looking at. Lock holds until
manually released, target dies, target unloads, or target
moves out of range. Friendly tab cycles party members and
nearby friendly NPCs (for cures and buffs).

AOE placement comes in two forms — ground (the reticle
clamps to a valid surface within max_range_m, e.g. you
can't place fire-IV halfway up a cliff face) and cone
(uses player_facing + arc_deg to define a wedge in front).

Sub-target chain handles abilities that hit your main but
spawn a follow-up on a different mob — DRG Penta Thrust
into Jump on a flanker. The next ability checks the
sub-target before the main; if the sub is set and live, it
takes precedence.

Public surface
--------------
    TargetingMode enum
    TargetFilter enum
    TargetCandidate dataclass (frozen)
    AOEPlacement dataclass (frozen)
    TargeterState dataclass
    TargetingSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TargetingMode(enum.Enum):
    NONE = "none"
    TAB_TARGET_NEAREST = "tab_target_nearest"
    TAB_TARGET_LOCK = "tab_target_lock"
    AOE_GROUND_PLACE = "aoe_ground_place"
    AOE_CONE_FACING = "aoe_cone_facing"
    FRIENDLY_TAB = "friendly_tab"
    SUB_TARGET_CHAIN = "sub_target_chain"
    SPECIFIC_NPC_ID = "specific_npc_id"


class TargetFilter(enum.Enum):
    FRIENDLY = "friendly"
    ENEMY = "enemy"
    NEUTRAL = "neutral"
    NM = "nm"
    BOSS = "boss"
    DESTRUCTIBLE = "destructible"


@dataclasses.dataclass(frozen=True)
class TargetCandidate:
    target_id: str
    filter_kind: TargetFilter
    distance_m: float
    screen_distance_px: float
    is_alive: bool = True
    is_loaded: bool = True


@dataclasses.dataclass(frozen=True)
class AOEPlacement:
    player_id: str
    ground_pos: tuple[float, float, float]
    is_valid: bool
    reason: str


@dataclasses.dataclass
class TargeterState:
    player_id: str
    mode: TargetingMode = TargetingMode.NONE
    current_target: str = ""
    sub_target: str = ""
    locked: bool = False
    last_filter: TargetFilter | None = None


@dataclasses.dataclass
class TargetingSystem:
    _states: dict[str, TargeterState] = dataclasses.field(
        default_factory=dict,
    )
    _target_of_targets: dict[
        str, str,
    ] = dataclasses.field(default_factory=dict)

    # ---------------------------------------------- register
    def register_targeter(self, player_id: str) -> TargeterState:
        if not player_id:
            raise ValueError("player_id required")
        if player_id in self._states:
            raise ValueError(
                f"duplicate player_id: {player_id}",
            )
        st = TargeterState(player_id=player_id)
        self._states[player_id] = st
        return st

    def state_of(self, player_id: str) -> TargeterState:
        if player_id not in self._states:
            raise KeyError(f"unknown player_id: {player_id}")
        return self._states[player_id]

    def targeter_count(self) -> int:
        return len(self._states)

    # ---------------------------------------------- mode
    def set_mode(
        self, player_id: str, mode: TargetingMode,
    ) -> TargeterState:
        st = self.state_of(player_id)
        st.mode = mode
        if mode == TargetingMode.TAB_TARGET_LOCK:
            st.locked = True
        elif mode == TargetingMode.NONE:
            st.locked = False
        return st

    # ---------------------------------------------- tab
    def tab_target(
        self,
        player_id: str,
        current_target: str,
        candidates: t.Sequence[TargetCandidate],
        radius_m: float,
        filter_kinds: t.Iterable[TargetFilter] | None = None,
    ) -> str:
        """Cycle through candidates within radius_m,
        filtered by filter_kinds (default = ENEMY).
        Returns the next target_id, or '' if none in range.
        """
        if radius_m < 0:
            raise ValueError("radius_m must be >= 0")
        st = self.state_of(player_id)
        kinds = (
            set(filter_kinds)
            if filter_kinds is not None
            else {TargetFilter.ENEMY}
        )
        # Filter to live, loaded, in-range, matching kind
        eligible = [
            c for c in candidates
            if c.is_alive and c.is_loaded
            and c.distance_m <= radius_m
            and c.filter_kind in kinds
        ]
        if not eligible:
            return ""
        # Sort by screen-center distance ascending,
        # then by target_id for determinism
        eligible.sort(
            key=lambda c: (c.screen_distance_px, c.target_id),
        )
        # If current target is in eligible, pick the next
        # one in cycle order
        ids = [c.target_id for c in eligible]
        if current_target in ids:
            idx = ids.index(current_target)
            nxt = ids[(idx + 1) % len(ids)]
        else:
            nxt = ids[0]
        st.current_target = nxt
        return nxt

    def friendly_tab(
        self,
        player_id: str,
        current_target: str,
        candidates: t.Sequence[TargetCandidate],
        radius_m: float,
    ) -> str:
        return self.tab_target(
            player_id, current_target, candidates, radius_m,
            filter_kinds={TargetFilter.FRIENDLY},
        )

    def lock_target(
        self, player_id: str, target_id: str,
    ) -> TargeterState:
        st = self.state_of(player_id)
        st.current_target = target_id
        st.locked = True
        st.mode = TargetingMode.TAB_TARGET_LOCK
        return st

    def release_lock(self, player_id: str) -> TargeterState:
        st = self.state_of(player_id)
        st.locked = False
        if st.mode == TargetingMode.TAB_TARGET_LOCK:
            st.mode = TargetingMode.TAB_TARGET_NEAREST
        return st

    def is_locked(self, player_id: str) -> bool:
        return self.state_of(player_id).locked

    # ---------------------------------------------- range
    def out_of_range(
        self,
        player_id: str,
        target_id: str,
        candidates: t.Sequence[TargetCandidate],
        range_m: float,
    ) -> bool:
        for c in candidates:
            if c.target_id == target_id:
                if (
                    not c.is_alive or not c.is_loaded
                    or c.distance_m > range_m
                ):
                    return True
                return False
        return True

    # ---------------------------------------------- AOE
    def place_aoe(
        self,
        player_id: str,
        ground_pos: tuple[float, float, float],
        max_range_m: float,
        player_pos: tuple[float, float, float],
        valid_surfaces_predicate: t.Callable[
            [tuple[float, float, float]], bool,
        ],
    ) -> AOEPlacement:
        if max_range_m < 0:
            raise ValueError("max_range_m must be >= 0")
        # Distance from player to ground_pos (XZ-plane)
        dx = ground_pos[0] - player_pos[0]
        dz = ground_pos[2] - player_pos[2]
        dist = (dx * dx + dz * dz) ** 0.5
        if dist > max_range_m:
            return AOEPlacement(
                player_id=player_id,
                ground_pos=ground_pos,
                is_valid=False,
                reason="out_of_range",
            )
        if not valid_surfaces_predicate(ground_pos):
            return AOEPlacement(
                player_id=player_id,
                ground_pos=ground_pos,
                is_valid=False,
                reason="invalid_surface",
            )
        return AOEPlacement(
            player_id=player_id,
            ground_pos=ground_pos,
            is_valid=True,
            reason="ok",
        )

    def cone_targets(
        self,
        player_pos: tuple[float, float, float],
        player_facing_deg: float,
        arc_deg: float,
        max_range_m: float,
        candidates: t.Sequence[TargetCandidate],
        candidate_positions: t.Mapping[
            str, tuple[float, float, float],
        ],
    ) -> tuple[str, ...]:
        if arc_deg < 0 or arc_deg > 360:
            raise ValueError("arc_deg must be in [0, 360]")
        import math
        half = arc_deg / 2.0
        facing_rad = math.radians(player_facing_deg)
        fx, fz = math.sin(facing_rad), math.cos(facing_rad)
        out: list[str] = []
        for c in candidates:
            if not c.is_alive or not c.is_loaded:
                continue
            if c.target_id not in candidate_positions:
                continue
            tp = candidate_positions[c.target_id]
            dx = tp[0] - player_pos[0]
            dz = tp[2] - player_pos[2]
            dist = (dx * dx + dz * dz) ** 0.5
            if dist > max_range_m or dist == 0:
                continue
            # cosine of angle between facing and (dx,dz)
            cos_ang = (fx * dx + fz * dz) / dist
            cos_ang = max(-1.0, min(1.0, cos_ang))
            ang_deg = math.degrees(math.acos(cos_ang))
            if ang_deg <= half:
                out.append(c.target_id)
        return tuple(sorted(out))

    # ---------------------------------------------- sub-target
    def set_sub_target(
        self, player_id: str, target_id: str,
    ) -> TargeterState:
        st = self.state_of(player_id)
        st.sub_target = target_id
        return st

    def clear_sub_target(self, player_id: str) -> TargeterState:
        st = self.state_of(player_id)
        st.sub_target = ""
        return st

    def clear_target(self, player_id: str) -> TargeterState:
        st = self.state_of(player_id)
        st.current_target = ""
        st.sub_target = ""
        st.locked = False
        return st

    # ---------------------------------------------- target-of-target
    def update_target_of_target(
        self, target_id: str, what_they_target: str,
    ) -> None:
        self._target_of_targets[target_id] = what_they_target

    def target_of_target(
        self, player_id: str, target_id: str,
    ) -> str:
        return self._target_of_targets.get(target_id, "")


__all__ = [
    "TargetingMode",
    "TargetFilter",
    "TargetCandidate",
    "AOEPlacement",
    "TargeterState",
    "TargetingSystem",
]
