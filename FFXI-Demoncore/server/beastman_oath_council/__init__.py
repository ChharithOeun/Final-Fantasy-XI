"""Beastman oath council — formal city oath system.

Each beastman city's GOVERNING COUNCIL administers OATHS that
players take to bind themselves to obligations in exchange for
city standing and access to council-only services.

An oath has:
  - oath_id, city, kind (LOYALTY / VENGEANCE / SECRECY / TRIBUTE)
  - duration_days
  - obligation_payload (e.g., "kill 25 hume soldiers per week")
  - reward_standing (granted on completion)
  - break_penalty_standing (deducted if broken)

A player can hold at most ONE oath per city at a time. Oaths
PROGRESS via report_obligation. break_oath ends it early with
the penalty applied.

Public surface
--------------
    OathKind enum
    OathState enum    ACTIVE / FULFILLED / BROKEN
    Oath dataclass
    BeastmanOathCouncil
        .register_oath(oath_id, city, kind, duration_days,
                       obligation_threshold, reward_standing,
                       break_penalty)
        .swear(player_id, oath_id, now_day)
        .report_obligation(player_id, oath_id, increment)
        .complete(player_id, oath_id, now_day)
        .break_oath(player_id, oath_id, now_day)
        .active_oath_for(player_id, city)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class OathKind(str, enum.Enum):
    LOYALTY = "loyalty"
    VENGEANCE = "vengeance"
    SECRECY = "secrecy"
    TRIBUTE = "tribute"


class OathState(str, enum.Enum):
    ACTIVE = "active"
    FULFILLED = "fulfilled"
    BROKEN = "broken"


class CouncilCity(str, enum.Enum):
    OZTROJA = "oztroja"
    PALBOROUGH = "palborough"
    HALVUNG = "halvung"
    ARRAPAGO = "arrapago"


@dataclasses.dataclass(frozen=True)
class Oath:
    oath_id: str
    city: CouncilCity
    kind: OathKind
    duration_days: int
    obligation_threshold: int
    reward_standing: int
    break_penalty: int


@dataclasses.dataclass
class _PlayerOath:
    oath_id: str
    sworn_at_day: int
    progress: int = 0
    state: OathState = OathState.ACTIVE


@dataclasses.dataclass(frozen=True)
class SwearResult:
    accepted: bool
    oath_id: str
    state: OathState
    expires_at_day: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ReportResult:
    accepted: bool
    oath_id: str
    progress: int
    threshold: int
    fulfilled: bool
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class CompleteResult:
    accepted: bool
    oath_id: str
    standing_awarded: int
    state: OathState
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class BreakResult:
    accepted: bool
    oath_id: str
    standing_penalty: int
    state: OathState
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanOathCouncil:
    _oaths: dict[str, Oath] = dataclasses.field(default_factory=dict)
    _sworn: dict[
        tuple[str, CouncilCity], _PlayerOath,
    ] = dataclasses.field(default_factory=dict)

    def register_oath(
        self, *, oath_id: str,
        city: CouncilCity,
        kind: OathKind,
        duration_days: int,
        obligation_threshold: int,
        reward_standing: int,
        break_penalty: int,
    ) -> t.Optional[Oath]:
        if oath_id in self._oaths:
            return None
        if duration_days <= 0:
            return None
        if obligation_threshold <= 0:
            return None
        if reward_standing < 0 or break_penalty < 0:
            return None
        o = Oath(
            oath_id=oath_id, city=city, kind=kind,
            duration_days=duration_days,
            obligation_threshold=obligation_threshold,
            reward_standing=reward_standing,
            break_penalty=break_penalty,
        )
        self._oaths[oath_id] = o
        return o

    def swear(
        self, *, player_id: str,
        oath_id: str,
        now_day: int,
    ) -> SwearResult:
        o = self._oaths.get(oath_id)
        if o is None:
            return SwearResult(
                False, oath_id, OathState.BROKEN,
                reason="unknown oath",
            )
        key = (player_id, o.city)
        existing = self._sworn.get(key)
        if existing is not None and existing.state == OathState.ACTIVE:
            return SwearResult(
                False, oath_id, existing.state,
                reason="already sworn to a city oath",
            )
        self._sworn[key] = _PlayerOath(
            oath_id=oath_id,
            sworn_at_day=now_day,
        )
        return SwearResult(
            accepted=True,
            oath_id=oath_id,
            state=OathState.ACTIVE,
            expires_at_day=now_day + o.duration_days,
        )

    def _find_active(
        self, player_id: str, oath_id: str,
    ) -> t.Optional[tuple[CouncilCity, _PlayerOath, Oath]]:
        o = self._oaths.get(oath_id)
        if o is None:
            return None
        po = self._sworn.get((player_id, o.city))
        if po is None or po.oath_id != oath_id:
            return None
        return (o.city, po, o)

    def report_obligation(
        self, *, player_id: str,
        oath_id: str,
        increment: int,
    ) -> ReportResult:
        f = self._find_active(player_id, oath_id)
        if f is None:
            return ReportResult(
                False, oath_id, 0, 0, False,
                reason="oath not active for player",
            )
        _city, po, o = f
        if po.state != OathState.ACTIVE:
            return ReportResult(
                False, oath_id, po.progress,
                o.obligation_threshold, False,
                reason="oath not active",
            )
        if increment <= 0:
            return ReportResult(
                False, oath_id, po.progress,
                o.obligation_threshold, False,
                reason="non-positive increment",
            )
        po.progress = min(
            po.progress + increment,
            o.obligation_threshold,
        )
        fulfilled = po.progress >= o.obligation_threshold
        return ReportResult(
            accepted=True, oath_id=oath_id,
            progress=po.progress,
            threshold=o.obligation_threshold,
            fulfilled=fulfilled,
        )

    def complete(
        self, *, player_id: str,
        oath_id: str,
        now_day: int,
    ) -> CompleteResult:
        f = self._find_active(player_id, oath_id)
        if f is None:
            return CompleteResult(
                False, oath_id, 0, OathState.BROKEN,
                reason="oath not active",
            )
        city, po, o = f
        if po.state != OathState.ACTIVE:
            return CompleteResult(
                False, oath_id, 0, po.state,
                reason="oath not active",
            )
        if po.progress < o.obligation_threshold:
            return CompleteResult(
                False, oath_id, 0, po.state,
                reason="obligation incomplete",
            )
        if now_day - po.sworn_at_day > o.duration_days:
            po.state = OathState.BROKEN
            return CompleteResult(
                False, oath_id, 0, po.state,
                reason="oath duration elapsed",
            )
        po.state = OathState.FULFILLED
        return CompleteResult(
            accepted=True,
            oath_id=oath_id,
            standing_awarded=o.reward_standing,
            state=po.state,
        )

    def break_oath(
        self, *, player_id: str,
        oath_id: str,
        now_day: int,
    ) -> BreakResult:
        f = self._find_active(player_id, oath_id)
        if f is None:
            return BreakResult(
                False, oath_id, 0, OathState.BROKEN,
                reason="oath not active",
            )
        _city, po, o = f
        if po.state != OathState.ACTIVE:
            return BreakResult(
                False, oath_id, 0, po.state,
                reason="oath not active",
            )
        po.state = OathState.BROKEN
        return BreakResult(
            accepted=True,
            oath_id=oath_id,
            standing_penalty=o.break_penalty,
            state=po.state,
        )

    def active_oath_for(
        self, *, player_id: str, city: CouncilCity,
    ) -> t.Optional[str]:
        po = self._sworn.get((player_id, city))
        if po is None or po.state != OathState.ACTIVE:
            return None
        return po.oath_id

    def total_oaths(self) -> int:
        return len(self._oaths)


__all__ = [
    "OathKind", "OathState", "CouncilCity",
    "Oath",
    "SwearResult", "ReportResult",
    "CompleteResult", "BreakResult",
    "BeastmanOathCouncil",
]
