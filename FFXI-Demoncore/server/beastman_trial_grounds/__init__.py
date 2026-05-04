"""Beastman trial grounds — BCNM-equivalent tiered battlefields.

The shadow-side counterpart to FFXI's BCNM/ENM/KSNM ecosystem.
Each TRIAL is a sealed battlefield with a TIER (T1-T4) gate, a
PARTY_SIZE cap (commonly 3 or 6), an entry KEY ITEM trade, and
a cooldown after a successful clear.

Players present at clear roll for a CHEST OF DROPS (each loot
slot rolled independently). Failed attempts still consume the
key item — encouraging serious tries.

Public surface
--------------
    TrialTier enum    T1 / T2 / T3 / T4
    TrialState enum   STAGED / IN_PROGRESS / VICTORY / DEFEAT
                      / COOLDOWN
    Trial dataclass
    TrialAttempt dataclass
    StartResult / ClearResult / DropResult dataclasses
    BeastmanTrialGrounds
        .register_trial(trial_id, tier, party_max, key_item_id,
                        cooldown_hours, drops)
        .start(trial_id, party_ids, now_seconds, key_item_held)
        .resolve(trial_id, victory, now_seconds)
        .roll_drop(trial_id, slot_index, roll_pct)
        .state_for(trial_id, now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TrialTier(str, enum.Enum):
    T1 = "tier_1"
    T2 = "tier_2"
    T3 = "tier_3"
    T4 = "tier_4"


class TrialState(str, enum.Enum):
    STAGED = "staged"
    IN_PROGRESS = "in_progress"
    VICTORY = "victory"
    DEFEAT = "defeat"
    COOLDOWN = "cooldown"


@dataclasses.dataclass(frozen=True)
class DropSlot:
    item_id: str
    base_drop_pct: int   # 0..100


@dataclasses.dataclass
class Trial:
    trial_id: str
    tier: TrialTier
    party_max: int
    key_item_id: str
    cooldown_seconds: int
    drops: tuple[DropSlot, ...]
    state: TrialState = TrialState.STAGED
    started_at: t.Optional[int] = None
    resolved_at: t.Optional[int] = None
    last_party: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class StartResult:
    accepted: bool
    trial_id: str
    state: TrialState
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ClearResult:
    accepted: bool
    trial_id: str
    state: TrialState
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class DropResult:
    accepted: bool
    item_id: str = ""
    dropped: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanTrialGrounds:
    _trials: dict[str, Trial] = dataclasses.field(default_factory=dict)

    def register_trial(
        self, *, trial_id: str,
        tier: TrialTier,
        party_max: int,
        key_item_id: str,
        cooldown_hours: int,
        drops: tuple[DropSlot, ...],
    ) -> t.Optional[Trial]:
        if trial_id in self._trials:
            return None
        if not (1 <= party_max <= 18):
            return None
        if cooldown_hours <= 0:
            return None
        if not key_item_id:
            return None
        for d in drops:
            if not (0 <= d.base_drop_pct <= 100):
                return None
        t_obj = Trial(
            trial_id=trial_id, tier=tier,
            party_max=party_max,
            key_item_id=key_item_id,
            cooldown_seconds=cooldown_hours * 3600,
            drops=tuple(drops),
        )
        self._trials[trial_id] = t_obj
        return t_obj

    def start(
        self, *, trial_id: str,
        party_ids: tuple[str, ...],
        key_item_held: bool,
        now_seconds: int,
    ) -> StartResult:
        t_obj = self._trials.get(trial_id)
        if t_obj is None:
            return StartResult(
                False, trial_id, TrialState.STAGED,
                reason="unknown trial",
            )
        if not key_item_held:
            return StartResult(
                False, trial_id, t_obj.state,
                reason="key item not held",
            )
        if not party_ids or len(party_ids) > t_obj.party_max:
            return StartResult(
                False, trial_id, t_obj.state,
                reason="party size invalid",
            )
        # cooldown check
        if t_obj.state == TrialState.COOLDOWN:
            if (
                t_obj.resolved_at is not None
                and now_seconds < t_obj.resolved_at + t_obj.cooldown_seconds
            ):
                return StartResult(
                    False, trial_id, t_obj.state,
                    reason="cooldown active",
                )
            t_obj.state = TrialState.STAGED
        if t_obj.state == TrialState.IN_PROGRESS:
            return StartResult(
                False, trial_id, t_obj.state,
                reason="already running",
            )
        t_obj.state = TrialState.IN_PROGRESS
        t_obj.started_at = now_seconds
        t_obj.last_party = tuple(party_ids)
        return StartResult(
            accepted=True, trial_id=trial_id,
            state=t_obj.state,
        )

    def resolve(
        self, *, trial_id: str,
        victory: bool, now_seconds: int,
    ) -> ClearResult:
        t_obj = self._trials.get(trial_id)
        if t_obj is None:
            return ClearResult(
                False, trial_id, TrialState.STAGED,
                reason="unknown trial",
            )
        if t_obj.state != TrialState.IN_PROGRESS:
            return ClearResult(
                False, trial_id, t_obj.state,
                reason="not in progress",
            )
        t_obj.resolved_at = now_seconds
        if victory:
            t_obj.state = TrialState.VICTORY
        else:
            t_obj.state = TrialState.DEFEAT
        # Roll into cooldown either way
        t_obj.state = TrialState.COOLDOWN
        return ClearResult(
            accepted=True, trial_id=trial_id,
            state=TrialState.VICTORY if victory else TrialState.DEFEAT,
        )

    def roll_drop(
        self, *, trial_id: str,
        slot_index: int, roll_pct: int,
    ) -> DropResult:
        t_obj = self._trials.get(trial_id)
        if t_obj is None:
            return DropResult(
                False, reason="unknown trial",
            )
        if t_obj.state != TrialState.COOLDOWN:
            return DropResult(
                False, reason="no recent clear",
            )
        if not (0 <= roll_pct <= 100):
            return DropResult(False, reason="invalid roll")
        if not (0 <= slot_index < len(t_obj.drops)):
            return DropResult(False, reason="bad slot")
        d = t_obj.drops[slot_index]
        return DropResult(
            accepted=True, item_id=d.item_id,
            dropped=roll_pct < d.base_drop_pct,
        )

    def state_for(
        self, *, trial_id: str, now_seconds: int,
    ) -> TrialState:
        t_obj = self._trials.get(trial_id)
        if t_obj is None:
            return TrialState.STAGED
        if (
            t_obj.state == TrialState.COOLDOWN
            and t_obj.resolved_at is not None
            and now_seconds >= t_obj.resolved_at + t_obj.cooldown_seconds
        ):
            t_obj.state = TrialState.STAGED
        return t_obj.state

    def total_trials(self) -> int:
        return len(self._trials)


__all__ = [
    "TrialTier", "TrialState",
    "DropSlot", "Trial",
    "StartResult", "ClearResult", "DropResult",
    "BeastmanTrialGrounds",
]
