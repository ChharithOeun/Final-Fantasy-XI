"""Death recap — post-mortem damage breakdown.

When a player dies, the renderer brings up a RECAP card showing
exactly what killed them: the last N damage events with sources,
damage types, mitigation that fired (or didn't), and a
diagnosed CAUSE_OF_DEATH (one of: KILLING_BLOW_OVERFLOW,
DOT_TICK, BURST_COMBO, ENRAGE_TIMER, FALL_DAMAGE).

Distinct from death_replay_cam (the rolling buffer for
permadeath review). death_recap is the IMMEDIATE death summary —
shorter window, tighter focus on what to do differently next
time.

Public surface
--------------
    DamageType enum
    MitigationKind enum
    DamageEvent dataclass
    CauseOfDeath enum
    DeathRecap dataclass
    DeathRecapSystem
        .record_damage(player_id, source_id, dmg_type, amount,
                       mitigation_applied, hp_after, at_seconds)
        .compose_recap(player_id, killing_blow_at) -> DeathRecap
        .reset(player_id)
"""
from __future__ import annotations

import collections
import dataclasses
import enum
import typing as t


# Default rolling window before death (seconds).
DEFAULT_RECAP_WINDOW = 10.0
# Cap on captured events per player.
MAX_EVENTS_PER_PLAYER = 64


class DamageType(str, enum.Enum):
    PHYSICAL = "physical"
    MAGIC = "magic"
    BREATH = "breath"
    DOT = "dot"
    FALL = "fall"
    DROWN = "drown"
    ENVIRONMENTAL = "environmental"


class MitigationKind(str, enum.Enum):
    NONE = "none"
    STONESKIN = "stoneskin"
    PROTECT = "protect"
    SHELL = "shell"
    PHALANX = "phalanx"
    PARRY = "parry"
    BLOCK = "block"
    DODGE = "dodge"
    INTERVENED = "intervened"


class CauseOfDeath(str, enum.Enum):
    KILLING_BLOW_OVERFLOW = "killing_blow_overflow"
    DOT_TICK = "dot_tick"
    BURST_COMBO = "burst_combo"
    ENRAGE_TIMER = "enrage_timer"
    FALL_DAMAGE = "fall_damage"
    UNKNOWN = "unknown"


@dataclasses.dataclass(frozen=True)
class DamageEvent:
    source_id: str
    dmg_type: DamageType
    amount: int
    mitigation: MitigationKind
    hp_after: int
    at_seconds: float


@dataclasses.dataclass(frozen=True)
class DeathRecap:
    player_id: str
    killing_blow_at_seconds: float
    cause: CauseOfDeath
    killer_id: t.Optional[str]
    events: tuple[DamageEvent, ...]
    total_damage: int
    burst_window_total: int        # damage in last 3 seconds
    longest_no_mitigation_streak: int


@dataclasses.dataclass
class DeathRecapSystem:
    recap_window: float = DEFAULT_RECAP_WINDOW
    max_events: int = MAX_EVENTS_PER_PLAYER
    _events: dict[
        str, collections.deque,
    ] = dataclasses.field(default_factory=dict)

    def record_damage(
        self, *, player_id: str, source_id: str,
        dmg_type: DamageType, amount: int,
        mitigation: MitigationKind = MitigationKind.NONE,
        hp_after: int = 0,
        at_seconds: float = 0.0,
    ) -> bool:
        if amount < 0:
            return False
        buf = self._events.get(player_id)
        if buf is None:
            buf = collections.deque(maxlen=self.max_events)
            self._events[player_id] = buf
        buf.append(DamageEvent(
            source_id=source_id, dmg_type=dmg_type,
            amount=amount, mitigation=mitigation,
            hp_after=max(0, hp_after),
            at_seconds=at_seconds,
        ))
        return True

    def _diagnose(
        self, events: list[DamageEvent],
        killing_blow_at: float,
    ) -> tuple[CauseOfDeath, t.Optional[str]]:
        if not events:
            return (CauseOfDeath.UNKNOWN, None)
        last = events[-1]
        # Fall damage trumps everything if the last hit was a fall
        if last.dmg_type == DamageType.FALL:
            return (CauseOfDeath.FALL_DAMAGE, last.source_id)
        # DOT tick if the last hit was a DOT and was small
        if (
            last.dmg_type == DamageType.DOT
            and last.amount < 200
        ):
            return (CauseOfDeath.DOT_TICK, last.source_id)
        # Burst combo: 3+ events landed in the final 3 seconds
        burst = [
            e for e in events
            if killing_blow_at - e.at_seconds <= 3.0
        ]
        if len(burst) >= 3:
            return (
                CauseOfDeath.BURST_COMBO,
                last.source_id,
            )
        # Killing blow overflow if the last hit was huge
        if last.amount >= 1000:
            return (
                CauseOfDeath.KILLING_BLOW_OVERFLOW,
                last.source_id,
            )
        return (CauseOfDeath.UNKNOWN, last.source_id)

    def compose_recap(
        self, *, player_id: str,
        killing_blow_at_seconds: float,
    ) -> t.Optional[DeathRecap]:
        buf = self._events.get(player_id)
        if not buf:
            return None
        # Filter to events within the recap window
        cutoff = killing_blow_at_seconds - self.recap_window
        events = [
            e for e in buf
            if e.at_seconds >= cutoff
            and e.at_seconds <= killing_blow_at_seconds
        ]
        if not events:
            return None
        cause, killer = self._diagnose(
            events, killing_blow_at_seconds,
        )
        total = sum(e.amount for e in events)
        burst_total = sum(
            e.amount for e in events
            if killing_blow_at_seconds - e.at_seconds <= 3.0
        )
        # Streak of consecutive unmitigated hits
        max_streak = 0
        cur = 0
        for e in events:
            if e.mitigation == MitigationKind.NONE:
                cur += 1
                max_streak = max(max_streak, cur)
            else:
                cur = 0
        return DeathRecap(
            player_id=player_id,
            killing_blow_at_seconds=(
                killing_blow_at_seconds
            ),
            cause=cause,
            killer_id=killer,
            events=tuple(events),
            total_damage=total,
            burst_window_total=burst_total,
            longest_no_mitigation_streak=max_streak,
        )

    def reset(
        self, *, player_id: str,
    ) -> bool:
        return self._events.pop(player_id, None) is not None

    def total_players_tracked(self) -> int:
        return len(self._events)


__all__ = [
    "DEFAULT_RECAP_WINDOW", "MAX_EVENTS_PER_PLAYER",
    "DamageType", "MitigationKind", "CauseOfDeath",
    "DamageEvent", "DeathRecap",
    "DeathRecapSystem",
]
