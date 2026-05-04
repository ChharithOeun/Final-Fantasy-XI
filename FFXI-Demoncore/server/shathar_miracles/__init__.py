"""Shathar miracles — beastman religion miracle system.

Pledged worshippers of SHATHAR THE OUTCAST who have completed
their pilgrimage can invoke MIRACLES — moments where the
Outcast briefly intervenes. Miracles cost FAITH POINTS,
typically tied to recent worship deeds (offerings, defending
shrines, refusing to abandon kin). Miracles are POTENT but
RARE — long cooldowns, hard prerequisites.

Each miracle has:
* a faith cost
* a per-player cooldown (in-game seconds)
* a tier (LESSER / GREATER / OUTCAST_VOICE)
* a payload — what happens (heal everyone in earshot, drop a
  monolith, paralyze invaders, summon a wraith, etc.)

Public surface
--------------
    MiracleKind enum
    MiracleTier enum
    MiracleDef dataclass
    InvocationResult dataclass
    ShatharMiracles
        .grant_faith(player_id, points)
        .register_miracle(kind, tier, faith_cost, cooldown_seconds)
        .invoke(player_id, kind, now_seconds)
        .faith_points(player_id) -> int
        .next_available_at(player_id, kind) -> Optional[float]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Defaults.
MAX_FAITH_POINTS = 1000


class MiracleTier(str, enum.Enum):
    LESSER = "lesser"
    GREATER = "greater"
    OUTCAST_VOICE = "outcast_voice"


class MiracleKind(str, enum.Enum):
    SHIELD_OF_THE_FORGOTTEN = "shield_of_the_forgotten"
    OUTCASTS_HYMN = "outcasts_hymn"
    BREAKING_OF_THE_VEIL = "breaking_of_the_veil"
    HOLLOW_THRONE_RISE = "hollow_throne_rise"
    THE_NAMING = "the_naming"


@dataclasses.dataclass(frozen=True)
class MiracleDef:
    kind: MiracleKind
    tier: MiracleTier
    faith_cost: int
    cooldown_seconds: float
    label: str = ""


@dataclasses.dataclass(frozen=True)
class InvocationResult:
    accepted: bool
    kind: MiracleKind
    faith_remaining: int = 0
    cooldown_until_seconds: float = 0.0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class _PlayerState:
    player_id: str
    faith_points: int = 0
    cooldowns: dict[
        MiracleKind, float,
    ] = dataclasses.field(default_factory=dict)
    invocations: int = 0


@dataclasses.dataclass
class ShatharMiracles:
    max_faith_points: int = MAX_FAITH_POINTS
    _miracles: dict[
        MiracleKind, MiracleDef,
    ] = dataclasses.field(default_factory=dict)
    _states: dict[str, _PlayerState] = dataclasses.field(
        default_factory=dict,
    )

    def register_miracle(
        self, *, kind: MiracleKind,
        tier: MiracleTier,
        faith_cost: int,
        cooldown_seconds: float,
        label: str = "",
    ) -> t.Optional[MiracleDef]:
        if kind in self._miracles:
            return None
        if faith_cost < 0:
            return None
        if cooldown_seconds < 0:
            return None
        m = MiracleDef(
            kind=kind, tier=tier,
            faith_cost=faith_cost,
            cooldown_seconds=cooldown_seconds,
            label=label or kind.value,
        )
        self._miracles[kind] = m
        return m

    def _state(self, player_id: str) -> _PlayerState:
        st = self._states.get(player_id)
        if st is None:
            st = _PlayerState(player_id=player_id)
            self._states[player_id] = st
        return st

    def grant_faith(
        self, *, player_id: str, points: int,
    ) -> t.Optional[int]:
        if points <= 0:
            return None
        st = self._state(player_id)
        st.faith_points = min(
            self.max_faith_points,
            st.faith_points + points,
        )
        return st.faith_points

    def faith_points(
        self, *, player_id: str,
    ) -> int:
        return self._state(player_id).faith_points

    def next_available_at(
        self, *, player_id: str,
        kind: MiracleKind,
    ) -> t.Optional[float]:
        st = self._states.get(player_id)
        if st is None:
            return None
        return st.cooldowns.get(kind)

    def invoke(
        self, *, player_id: str,
        kind: MiracleKind,
        now_seconds: float = 0.0,
    ) -> InvocationResult:
        m = self._miracles.get(kind)
        if m is None:
            return InvocationResult(
                False, kind=kind,
                reason="miracle not registered",
            )
        st = self._state(player_id)
        cd_until = st.cooldowns.get(kind, 0.0)
        if now_seconds < cd_until:
            return InvocationResult(
                False, kind=kind,
                faith_remaining=st.faith_points,
                cooldown_until_seconds=cd_until,
                reason="on cooldown",
            )
        if st.faith_points < m.faith_cost:
            return InvocationResult(
                False, kind=kind,
                faith_remaining=st.faith_points,
                cooldown_until_seconds=cd_until,
                reason="insufficient faith",
            )
        st.faith_points -= m.faith_cost
        next_avail = now_seconds + m.cooldown_seconds
        st.cooldowns[kind] = next_avail
        st.invocations += 1
        return InvocationResult(
            accepted=True, kind=kind,
            faith_remaining=st.faith_points,
            cooldown_until_seconds=next_avail,
        )

    def total_miracles(self) -> int:
        return len(self._miracles)

    def total_invocations(
        self, *, player_id: str,
    ) -> int:
        st = self._states.get(player_id)
        return st.invocations if st else 0


__all__ = [
    "MAX_FAITH_POINTS",
    "MiracleKind", "MiracleTier",
    "MiracleDef", "InvocationResult",
    "ShatharMiracles",
]
