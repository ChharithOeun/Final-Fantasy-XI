"""Records of Eminence — daily and weekly objectives + sparks.

Players activate up to 30 objectives at a time. Each objective
tracks progress (kill 30 mobs of family X, complete a Genkai, etc).
Completing an objective awards Sparks of Eminence (currency) and
adds a permanent achievement flag.

Reset cadence:
  DAILY  - resets at the next daily-reset tick
  WEEKLY - resets at the next weekly-reset tick
  ONE_OFF - never resets (one completion ever)

Public surface
--------------
    Cadence enum
    Objective immutable spec
    PlayerRoeTracker per-player
        .activate(objective_id)
        .progress(objective_id, amount)
        .complete_if_ready(objective_id, now_tick) -> CompleteResult
        .daily_reset / .weekly_reset
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Cadence(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    ONE_OFF = "one_off"


@dataclasses.dataclass(frozen=True)
class Objective:
    objective_id: str
    name: str
    cadence: Cadence
    target_count: int                    # how many to complete
    sparks_reward: int                   # currency gained
    description: str = ""


# Sample catalog
ROE_CATALOG: tuple[Objective, ...] = (
    Objective("daily_kill_orcs", "Cull the Orcs",
              cadence=Cadence.DAILY,
              target_count=30, sparks_reward=300),
    Objective("daily_skillchain", "Practice Skillchains",
              cadence=Cadence.DAILY,
              target_count=10, sparks_reward=200),
    Objective("weekly_genkai_progress",
              "Master Trial Progress",
              cadence=Cadence.WEEKLY,
              target_count=1, sparks_reward=2000),
    Objective("oneoff_first_genkai", "Limit Break I",
              cadence=Cadence.ONE_OFF,
              target_count=1, sparks_reward=5000),
    Objective("oneoff_first_av_kill",
              "Slay an Aerial Veil",
              cadence=Cadence.ONE_OFF,
              target_count=1, sparks_reward=3000),
)

ROE_BY_ID: dict[str, Objective] = {o.objective_id: o for o in ROE_CATALOG}

MAX_ACTIVE_OBJECTIVES = 30


@dataclasses.dataclass
class _ProgressEntry:
    progress: int = 0
    completed_at_tick: t.Optional[int] = None


@dataclasses.dataclass(frozen=True)
class CompleteResult:
    accepted: bool
    objective_id: str
    sparks_awarded: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerRoeTracker:
    player_id: str
    sparks: int = 0
    _active: dict[str, _ProgressEntry] = dataclasses.field(
        default_factory=dict, repr=False,
    )
    _completed_oneoff: set[str] = dataclasses.field(
        default_factory=set, repr=False,
    )

    def activate(self, *, objective_id: str) -> bool:
        if objective_id not in ROE_BY_ID:
            return False
        if objective_id in self._completed_oneoff:
            return False    # already done forever
        if objective_id in self._active:
            return False    # already active
        if len(self._active) >= MAX_ACTIVE_OBJECTIVES:
            return False
        self._active[objective_id] = _ProgressEntry()
        return True

    def progress(self, *, objective_id: str, amount: int = 1) -> int:
        """Add progress. Returns new total. No-op if not active."""
        if amount < 0:
            raise ValueError("amount must be >= 0")
        e = self._active.get(objective_id)
        if e is None or e.completed_at_tick is not None:
            return 0
        e.progress += amount
        return e.progress

    def is_ready(self, objective_id: str) -> bool:
        e = self._active.get(objective_id)
        if e is None or e.completed_at_tick is not None:
            return False
        obj = ROE_BY_ID[objective_id]
        return e.progress >= obj.target_count

    def complete_if_ready(
        self, *, objective_id: str, now_tick: int,
    ) -> CompleteResult:
        if objective_id not in self._active:
            return CompleteResult(False, objective_id, reason="not active")
        if not self.is_ready(objective_id):
            return CompleteResult(False, objective_id, reason="not ready")
        obj = ROE_BY_ID[objective_id]
        e = self._active[objective_id]
        e.completed_at_tick = now_tick
        self.sparks += obj.sparks_reward
        if obj.cadence == Cadence.ONE_OFF:
            self._completed_oneoff.add(objective_id)
            del self._active[objective_id]
        return CompleteResult(
            accepted=True,
            objective_id=objective_id,
            sparks_awarded=obj.sparks_reward,
        )

    def daily_reset(self) -> int:
        """Wipe progress on DAILY objectives. Returns count cleared."""
        count = 0
        for oid in list(self._active.keys()):
            obj = ROE_BY_ID[oid]
            if obj.cadence == Cadence.DAILY:
                self._active[oid] = _ProgressEntry()
                count += 1
        return count

    def weekly_reset(self) -> int:
        count = 0
        for oid in list(self._active.keys()):
            obj = ROE_BY_ID[oid]
            if obj.cadence == Cadence.WEEKLY:
                self._active[oid] = _ProgressEntry()
                count += 1
        return count

    def active_count(self) -> int:
        return len(self._active)


__all__ = [
    "Cadence", "Objective",
    "ROE_CATALOG", "ROE_BY_ID",
    "MAX_ACTIVE_OBJECTIVES",
    "CompleteResult", "PlayerRoeTracker",
]
