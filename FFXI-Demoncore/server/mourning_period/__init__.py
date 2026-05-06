"""Mourning period — server-wide effects after legendary permadeath.

When a player who held a LEGENDARY or MYTHIC title permadies,
the server enters a mourning period. Flags drop to half-mast,
festival music dampens, certain quests pause, and a small
buff (+5% XP from kills) is granted to all players in
solidarity. The mourning period is a state, not just a flag.

Duration scales with title tier:
    LEGENDARY      3 in-game days
    MYTHIC         7 in-game days
    Special edge   14 in-game days (server-defining figure;
                   set explicitly via begin_mourning(extended=True))

Only one mourning at a time. New mournings either replace
(if higher tier) or extend (if same tier) the current state.
A player who already has an active mourning never gets a
second one stacked.

Public surface
--------------
    MourningSeverity enum
    MourningState dataclass (mutable)
    MourningPeriod
        .begin_mourning(deceased_id, deceased_name,
                        deceased_title_tier, started_at,
                        seconds_per_day, extended=False)
            -> bool
        .is_mourning(now_seconds) -> bool
        .current_state(now_seconds) -> Optional[MourningState]
        .seconds_remaining(now_seconds) -> int
        .seconds_to_xp_bonus_pct(now_seconds) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class MourningSeverity(str, enum.Enum):
    NONE = "none"
    LIGHT = "light"          # 3-day, +5% xp
    HEAVY = "heavy"          # 7-day, +10% xp
    SERVER_DEFINING = "server_defining"   # 14-day, +15% xp


_DURATION_DAYS = {
    MourningSeverity.LIGHT: 3,
    MourningSeverity.HEAVY: 7,
    MourningSeverity.SERVER_DEFINING: 14,
}

_XP_BONUS_PCT = {
    MourningSeverity.NONE: 0,
    MourningSeverity.LIGHT: 5,
    MourningSeverity.HEAVY: 10,
    MourningSeverity.SERVER_DEFINING: 15,
}

_SEVERITY_ORDER = {
    MourningSeverity.NONE: 0,
    MourningSeverity.LIGHT: 1,
    MourningSeverity.HEAVY: 2,
    MourningSeverity.SERVER_DEFINING: 3,
}


@dataclasses.dataclass
class MourningState:
    deceased_id: str
    deceased_name: str
    severity: MourningSeverity
    started_at: int
    ends_at: int


def _severity_for(tier: str, extended: bool) -> MourningSeverity:
    if extended:
        return MourningSeverity.SERVER_DEFINING
    if tier == "mythic":
        return MourningSeverity.HEAVY
    if tier == "legendary":
        return MourningSeverity.LIGHT
    return MourningSeverity.NONE


@dataclasses.dataclass
class MourningPeriod:
    _state: t.Optional[MourningState] = None

    def begin_mourning(
        self, *, deceased_id: str, deceased_name: str,
        deceased_title_tier: str,
        started_at: int, seconds_per_day: int,
        extended: bool = False,
    ) -> bool:
        if not deceased_id or not deceased_name:
            return False
        if seconds_per_day <= 0:
            return False
        sev = _severity_for(deceased_title_tier, extended)
        if sev == MourningSeverity.NONE:
            return False
        # if active state exists, only allow if new tier higher OR same tier
        if self._state is not None and started_at < self._state.ends_at:
            existing_rank = _SEVERITY_ORDER[self._state.severity]
            new_rank = _SEVERITY_ORDER[sev]
            if new_rank < existing_rank:
                return False
            # same or higher → replace (keeps the more poignant figure)
        days = _DURATION_DAYS[sev]
        self._state = MourningState(
            deceased_id=deceased_id,
            deceased_name=deceased_name,
            severity=sev,
            started_at=started_at,
            ends_at=started_at + days * seconds_per_day,
        )
        return True

    def is_mourning(self, *, now_seconds: int) -> bool:
        if self._state is None:
            return False
        return now_seconds < self._state.ends_at

    def current_state(
        self, *, now_seconds: int,
    ) -> t.Optional[MourningState]:
        if not self.is_mourning(now_seconds=now_seconds):
            return None
        return self._state

    def seconds_remaining(self, *, now_seconds: int) -> int:
        if self._state is None:
            return 0
        if now_seconds >= self._state.ends_at:
            return 0
        return self._state.ends_at - now_seconds

    def xp_bonus_pct(self, *, now_seconds: int) -> int:
        state = self.current_state(now_seconds=now_seconds)
        if state is None:
            return 0
        return _XP_BONUS_PCT[state.severity]


__all__ = [
    "MourningSeverity", "MourningState", "MourningPeriod",
]
