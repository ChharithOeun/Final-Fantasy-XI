"""DPS meter — rolling damage/heal/taken metrics.

Per-player rolling-30-second window for:
  DAMAGE_OUT       outgoing damage
  HEAL_OUT         outgoing heals
  DAMAGE_TAKEN     incoming damage
  THREAT           sum of damage_out + heal_out (rough hate proxy)

The meter exposes per-player rates AND a party rollup so the
party UI can show "who's pulling weight" without blaming.

Public surface
--------------
    EventKind enum
    CombatEvent dataclass
    PlayerSnapshot dataclass
    PartyRollup dataclass
    DPSMeter
        .record(player_id, kind, amount, at_seconds)
        .snapshot_for(player_id, now_seconds, window_seconds)
        .party_rollup(member_ids, now_seconds)
        .reset(player_id) — wipe (e.g. after a wipe)
"""
from __future__ import annotations

import collections
import dataclasses
import enum
import typing as t


# Default rolling window for "current DPS" reports.
DEFAULT_WINDOW_SECONDS = 30.0
# Per-player ring buffer cap.
MAX_EVENTS_PER_PLAYER = 1024


class EventKind(str, enum.Enum):
    DAMAGE_OUT = "damage_out"
    HEAL_OUT = "heal_out"
    DAMAGE_TAKEN = "damage_taken"


@dataclasses.dataclass(frozen=True)
class CombatEvent:
    kind: EventKind
    amount: int
    at_seconds: float


@dataclasses.dataclass(frozen=True)
class PlayerSnapshot:
    player_id: str
    window_seconds: float
    damage_out: int
    heal_out: int
    damage_taken: int
    dps: float
    hps: float
    dtps: float
    threat: float          # damage_out + heal_out per second
    sample_count: int


@dataclasses.dataclass(frozen=True)
class PartyRollup:
    window_seconds: float
    members: tuple[PlayerSnapshot, ...]
    total_dps: float
    total_hps: float
    total_dtps: float


@dataclasses.dataclass
class DPSMeter:
    default_window: float = DEFAULT_WINDOW_SECONDS
    max_events: int = MAX_EVENTS_PER_PLAYER
    _events: dict[
        str, collections.deque,
    ] = dataclasses.field(default_factory=dict)

    def record(
        self, *, player_id: str, kind: EventKind,
        amount: int, at_seconds: float,
    ) -> bool:
        if amount <= 0:
            return False
        buf = self._events.get(player_id)
        if buf is None:
            buf = collections.deque(maxlen=self.max_events)
            self._events[player_id] = buf
        buf.append(CombatEvent(
            kind=kind, amount=amount,
            at_seconds=at_seconds,
        ))
        return True

    def _aggregate_window(
        self, *, player_id: str, now_seconds: float,
        window_seconds: float,
    ) -> tuple[int, int, int, int]:
        """Returns (damage_out, heal_out, damage_taken, sample_count)."""
        buf = self._events.get(player_id)
        if buf is None:
            return 0, 0, 0, 0
        cutoff = now_seconds - window_seconds
        d_out = h_out = d_in = 0
        n = 0
        for ev in buf:
            if ev.at_seconds < cutoff:
                continue
            if ev.at_seconds > now_seconds:
                continue
            if ev.kind == EventKind.DAMAGE_OUT:
                d_out += ev.amount
            elif ev.kind == EventKind.HEAL_OUT:
                h_out += ev.amount
            elif ev.kind == EventKind.DAMAGE_TAKEN:
                d_in += ev.amount
            n += 1
        return d_out, h_out, d_in, n

    def snapshot_for(
        self, *, player_id: str, now_seconds: float,
        window_seconds: t.Optional[float] = None,
    ) -> PlayerSnapshot:
        win = (
            window_seconds
            if window_seconds is not None
            else self.default_window
        )
        if win <= 0:
            win = self.default_window
        d_out, h_out, d_in, n = self._aggregate_window(
            player_id=player_id,
            now_seconds=now_seconds,
            window_seconds=win,
        )
        dps = d_out / win
        hps = h_out / win
        dtps = d_in / win
        threat = (d_out + h_out) / win
        return PlayerSnapshot(
            player_id=player_id,
            window_seconds=win,
            damage_out=d_out,
            heal_out=h_out,
            damage_taken=d_in,
            dps=dps, hps=hps, dtps=dtps,
            threat=threat,
            sample_count=n,
        )

    def party_rollup(
        self, *, member_ids: tuple[str, ...],
        now_seconds: float,
        window_seconds: t.Optional[float] = None,
    ) -> PartyRollup:
        win = (
            window_seconds
            if window_seconds is not None
            else self.default_window
        )
        snaps = tuple(
            self.snapshot_for(
                player_id=mid,
                now_seconds=now_seconds,
                window_seconds=win,
            )
            for mid in member_ids
        )
        total_dps = sum(s.dps for s in snaps)
        total_hps = sum(s.hps for s in snaps)
        total_dtps = sum(s.dtps for s in snaps)
        return PartyRollup(
            window_seconds=win,
            members=snaps,
            total_dps=total_dps,
            total_hps=total_hps,
            total_dtps=total_dtps,
        )

    def reset(self, *, player_id: str) -> bool:
        return self._events.pop(player_id, None) is not None

    def reset_all(self) -> int:
        n = len(self._events)
        self._events.clear()
        return n

    def total_players_tracked(self) -> int:
        return len(self._events)


__all__ = [
    "DEFAULT_WINDOW_SECONDS",
    "MAX_EVENTS_PER_PLAYER",
    "EventKind",
    "CombatEvent", "PlayerSnapshot", "PartyRollup",
    "DPSMeter",
]
