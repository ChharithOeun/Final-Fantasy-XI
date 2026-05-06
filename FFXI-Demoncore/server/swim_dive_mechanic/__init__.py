"""Swim & dive mechanic — underwater navigation under fire.

When ICE_BREAK or DAM_BURST drops a player into water,
the world doesn't go on without them — it punishes them
with breath, depth, and the puzzle of finding their way
back up. This module is a per-player swim session with:

    breath_seconds      countdown — runs out → drowning
                        damage tick
    swim_speed_yalms    per-second movement; capped by
                        equipment weight & swim skill
    current_depth_band  0..4 deeper-than-surface
    target_climb_outs   feature_ids that act as exits
                        (broken ice hole, surfaced
                        platform, ladder)

Updates per server tick:
    .tick(player_id, dt_seconds, now_seconds)
    .ascend(player_id, yalms)
    .descend(player_id, yalms)
    .grasp_climb_out(player_id, climb_out_id) -> ClimbResult

Counter buffs (from environmental_counter_effects):
    SWIMMING_SKILL          → +20% swim_speed, -25% breath drain
    COLD_RESIST             → -50% Frost Sleep penalty
    WATER_WALK              → end session immediately
                              (treats water as walkable)

Drowning damage scales with how many seconds past
breath_seconds=0 you are. After
DROWN_LETHAL_SECONDS, the player is KO'd.

Public surface
--------------
    SwimSessionStatus enum
    ClimbOut dataclass (frozen)
    SwimSession dataclass (mutable)
    ClimbResult dataclass (frozen)
    SwimDiveMechanic
        .start_session(player_id, breath_seconds,
                       starting_depth, climb_outs,
                       has_swimming_skill, has_water_walk)
        .tick(player_id, dt_seconds, now_seconds) -> tick info
        .ascend(player_id, yalms)
        .descend(player_id, yalms)
        .grasp_climb_out(player_id, climb_out_id) -> ClimbResult
        .session(player_id) -> Optional[SwimSession]
        .end_session(player_id, reason)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SwimSessionStatus(str, enum.Enum):
    ACTIVE = "active"
    SURFACED = "surfaced"
    DROWNED = "drowned"
    EVACUATED = "evacuated"   # water_walk insta-end


# Tuning knobs
DEFAULT_BREATH_SECONDS = 60
BREATH_DRAIN_PER_SECOND = 1
SWIMMING_SKILL_DRAIN_REDUCTION = 0.75   # 25% less drain
SWIMMING_SKILL_SPEED_BONUS = 1.20       # 20% faster
DEFAULT_SWIM_SPEED_YALMS = 4
DROWN_DPS_BASE = 50
DROWN_DPS_PER_SECOND_OVERTIME = 25
DROWN_LETHAL_SECONDS = 12   # past 0 breath, KO at +12s
ASCEND_BAND_THRESHOLD_YALMS = 5  # cumulative ascent to climb 1 band


@dataclasses.dataclass(frozen=True)
class ClimbOut:
    climb_out_id: str
    band_at_top: int        # what depth_band reaching this exits to
    requires_band: int      # player must be at this depth or shallower
    label: str = ""


@dataclasses.dataclass
class SwimSession:
    player_id: str
    breath_seconds: float
    breath_max: float
    swim_speed_yalms: int
    current_depth_band: int
    climb_outs: list[ClimbOut]
    has_swimming_skill: bool
    has_water_walk: bool
    status: SwimSessionStatus = SwimSessionStatus.ACTIVE
    overtime_seconds: float = 0.0
    last_tick_at: int = 0
    accumulated_ascent: float = 0.0


@dataclasses.dataclass(frozen=True)
class TickResult:
    breath_remaining: float
    drowning_damage: int
    status: SwimSessionStatus
    depth_band: int


@dataclasses.dataclass(frozen=True)
class ClimbResult:
    accepted: bool
    surfaced: bool = False
    new_band: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class SwimDiveMechanic:
    _sessions: dict[str, SwimSession] = dataclasses.field(default_factory=dict)

    def start_session(
        self, *, player_id: str,
        breath_seconds: int = DEFAULT_BREATH_SECONDS,
        starting_depth: int = 1,
        climb_outs: t.Iterable[ClimbOut] = (),
        has_swimming_skill: bool = False,
        has_water_walk: bool = False,
        now_seconds: int = 0,
    ) -> bool:
        if not player_id or breath_seconds <= 0:
            return False
        if player_id in self._sessions:
            return False
        if has_water_walk:
            # short-circuit: never enters
            self._sessions[player_id] = SwimSession(
                player_id=player_id,
                breath_seconds=breath_seconds,
                breath_max=breath_seconds,
                swim_speed_yalms=DEFAULT_SWIM_SPEED_YALMS,
                current_depth_band=0,
                climb_outs=list(climb_outs),
                has_swimming_skill=has_swimming_skill,
                has_water_walk=True,
                status=SwimSessionStatus.EVACUATED,
                last_tick_at=now_seconds,
            )
            return True
        spd = DEFAULT_SWIM_SPEED_YALMS
        if has_swimming_skill:
            spd = int(spd * SWIMMING_SKILL_SPEED_BONUS)
        self._sessions[player_id] = SwimSession(
            player_id=player_id,
            breath_seconds=breath_seconds,
            breath_max=breath_seconds,
            swim_speed_yalms=spd,
            current_depth_band=max(0, starting_depth),
            climb_outs=list(climb_outs),
            has_swimming_skill=has_swimming_skill,
            has_water_walk=False,
            last_tick_at=now_seconds,
        )
        return True

    def tick(
        self, *, player_id: str, dt_seconds: float,
        now_seconds: int,
    ) -> t.Optional[TickResult]:
        s = self._sessions.get(player_id)
        if s is None or s.status != SwimSessionStatus.ACTIVE:
            return None
        if dt_seconds <= 0:
            return TickResult(
                breath_remaining=s.breath_seconds,
                drowning_damage=0, status=s.status,
                depth_band=s.current_depth_band,
            )
        drain = BREATH_DRAIN_PER_SECOND * dt_seconds
        if s.has_swimming_skill:
            drain *= SWIMMING_SKILL_DRAIN_REDUCTION
        s.breath_seconds = max(0.0, s.breath_seconds - drain)
        damage = 0
        if s.breath_seconds == 0:
            s.overtime_seconds += dt_seconds
            tick_dps = DROWN_DPS_BASE + int(
                DROWN_DPS_PER_SECOND_OVERTIME * s.overtime_seconds
            )
            damage = int(tick_dps * dt_seconds)
            if s.overtime_seconds >= DROWN_LETHAL_SECONDS:
                s.status = SwimSessionStatus.DROWNED
        s.last_tick_at = now_seconds
        return TickResult(
            breath_remaining=s.breath_seconds,
            drowning_damage=damage,
            status=s.status,
            depth_band=s.current_depth_band,
        )

    def ascend(self, *, player_id: str, yalms: int) -> bool:
        s = self._sessions.get(player_id)
        if s is None or s.status != SwimSessionStatus.ACTIVE:
            return False
        if yalms <= 0:
            return False
        s.accumulated_ascent += yalms
        while (s.accumulated_ascent >= ASCEND_BAND_THRESHOLD_YALMS
               and s.current_depth_band > 0):
            s.accumulated_ascent -= ASCEND_BAND_THRESHOLD_YALMS
            s.current_depth_band -= 1
        return True

    def descend(self, *, player_id: str, yalms: int) -> bool:
        s = self._sessions.get(player_id)
        if s is None or s.status != SwimSessionStatus.ACTIVE:
            return False
        if yalms <= 0:
            return False
        s.current_depth_band = min(4, s.current_depth_band + 1)
        s.accumulated_ascent = 0.0
        return True

    def grasp_climb_out(
        self, *, player_id: str, climb_out_id: str,
    ) -> ClimbResult:
        s = self._sessions.get(player_id)
        if s is None:
            return ClimbResult(False, reason="no session")
        if s.status != SwimSessionStatus.ACTIVE:
            return ClimbResult(False, reason="session inactive")
        co = next(
            (c for c in s.climb_outs if c.climb_out_id == climb_out_id),
            None,
        )
        if co is None:
            return ClimbResult(False, reason="unknown climb out")
        if s.current_depth_band > co.requires_band:
            return ClimbResult(False, reason="too deep for this exit")
        s.status = SwimSessionStatus.SURFACED
        return ClimbResult(
            accepted=True, surfaced=True, new_band=co.band_at_top,
        )

    def session(self, *, player_id: str) -> t.Optional[SwimSession]:
        return self._sessions.get(player_id)

    def end_session(
        self, *, player_id: str, reason: str = "manual",
    ) -> bool:
        if player_id in self._sessions:
            del self._sessions[player_id]
            return True
        return False


__all__ = [
    "SwimSessionStatus", "ClimbOut", "SwimSession",
    "TickResult", "ClimbResult", "SwimDiveMechanic",
    "DEFAULT_BREATH_SECONDS", "BREATH_DRAIN_PER_SECOND",
    "SWIMMING_SKILL_DRAIN_REDUCTION",
    "SWIMMING_SKILL_SPEED_BONUS",
    "DEFAULT_SWIM_SPEED_YALMS",
    "DROWN_DPS_BASE", "DROWN_DPS_PER_SECOND_OVERTIME",
    "DROWN_LETHAL_SECONDS",
    "ASCEND_BAND_THRESHOLD_YALMS",
]
