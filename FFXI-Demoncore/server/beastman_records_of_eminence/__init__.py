"""Beastman records of eminence — daily/weekly objectives.

The beastman-side counterpart to FFXI Records of Eminence. Each
player can ACTIVATE a curated set of objectives at any time;
progress accrues and rewards drop on completion. Different
CADENCES reset on different schedules:

  DAILY    - resets at JST 00:00 (60s in test seconds)
  WEEKLY   - resets every 7 days
  CAMPAIGN - persistent until completed (no reset)

A player can have at most a fixed number active per cadence
(8 daily, 4 weekly, 12 campaign) — same approximate caps as
hume RoE.

Public surface
--------------
    Cadence enum
    Eminence dataclass
    BeastmanRecordsOfEminence
        .register_objective(obj_id, cadence, target_count,
                            sparks_reward, gil_reward,
                            description)
        .activate(player_id, obj_id, now_seconds)
        .progress(player_id, obj_id, increment)
        .claim(player_id, obj_id, now_seconds)
        .reset_due(player_id, now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Cadence(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    CAMPAIGN = "campaign"


_CAP_BY_CADENCE: dict[Cadence, int] = {
    Cadence.DAILY: 8,
    Cadence.WEEKLY: 4,
    Cadence.CAMPAIGN: 12,
}

_RESET_SECONDS: dict[Cadence, int] = {
    Cadence.DAILY: 86_400,
    Cadence.WEEKLY: 7 * 86_400,
    Cadence.CAMPAIGN: 0,   # never resets
}


@dataclasses.dataclass(frozen=True)
class Eminence:
    obj_id: str
    cadence: Cadence
    target_count: int
    sparks_reward: int
    gil_reward: int
    description: str = ""


@dataclasses.dataclass
class _PlayerObjective:
    obj_id: str
    cadence: Cadence
    activated_at: int
    progress: int = 0
    claimed: bool = False


@dataclasses.dataclass(frozen=True)
class ActivateResult:
    accepted: bool
    obj_id: str
    cadence: Cadence
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ProgressResult:
    accepted: bool
    obj_id: str
    progress: int
    target: int
    completed: bool
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ClaimResult:
    accepted: bool
    obj_id: str
    sparks_awarded: int = 0
    gil_awarded: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanRecordsOfEminence:
    _catalog: dict[str, Eminence] = dataclasses.field(
        default_factory=dict,
    )
    _active: dict[
        tuple[str, str], _PlayerObjective,
    ] = dataclasses.field(default_factory=dict)

    def register_objective(
        self, *, obj_id: str,
        cadence: Cadence,
        target_count: int,
        sparks_reward: int,
        gil_reward: int,
        description: str = "",
    ) -> t.Optional[Eminence]:
        if obj_id in self._catalog:
            return None
        if target_count <= 0:
            return None
        if sparks_reward < 0 or gil_reward < 0:
            return None
        e = Eminence(
            obj_id=obj_id, cadence=cadence,
            target_count=target_count,
            sparks_reward=sparks_reward,
            gil_reward=gil_reward,
            description=description,
        )
        self._catalog[obj_id] = e
        return e

    def _active_for_player(
        self, player_id: str, cadence: Cadence,
    ) -> list[_PlayerObjective]:
        return [
            po for (pid, _oid), po in self._active.items()
            if pid == player_id and po.cadence == cadence
        ]

    def activate(
        self, *, player_id: str,
        obj_id: str,
        now_seconds: int,
    ) -> ActivateResult:
        e = self._catalog.get(obj_id)
        if e is None:
            return ActivateResult(
                False, obj_id, Cadence.DAILY,
                reason="unknown objective",
            )
        key = (player_id, obj_id)
        if key in self._active:
            return ActivateResult(
                False, obj_id, e.cadence,
                reason="already active",
            )
        active = self._active_for_player(player_id, e.cadence)
        cap = _CAP_BY_CADENCE[e.cadence]
        if len(active) >= cap:
            return ActivateResult(
                False, obj_id, e.cadence,
                reason="cadence cap reached",
            )
        self._active[key] = _PlayerObjective(
            obj_id=obj_id,
            cadence=e.cadence,
            activated_at=now_seconds,
        )
        return ActivateResult(
            accepted=True, obj_id=obj_id, cadence=e.cadence,
        )

    def progress(
        self, *, player_id: str,
        obj_id: str,
        increment: int,
    ) -> ProgressResult:
        e = self._catalog.get(obj_id)
        po = self._active.get((player_id, obj_id))
        if e is None or po is None:
            return ProgressResult(
                False, obj_id, 0, 0, False,
                reason="not active for player",
            )
        if increment <= 0:
            return ProgressResult(
                False, obj_id, po.progress, e.target_count, False,
                reason="non-positive increment",
            )
        if po.claimed:
            return ProgressResult(
                False, obj_id, po.progress, e.target_count,
                completed=True,
                reason="already claimed",
            )
        po.progress = min(po.progress + increment, e.target_count)
        completed = po.progress >= e.target_count
        return ProgressResult(
            accepted=True, obj_id=obj_id,
            progress=po.progress,
            target=e.target_count,
            completed=completed,
        )

    def claim(
        self, *, player_id: str,
        obj_id: str,
        now_seconds: int,
    ) -> ClaimResult:
        e = self._catalog.get(obj_id)
        po = self._active.get((player_id, obj_id))
        if e is None or po is None:
            return ClaimResult(
                False, obj_id, reason="not active",
            )
        if po.claimed:
            return ClaimResult(
                False, obj_id, reason="already claimed",
            )
        if po.progress < e.target_count:
            return ClaimResult(
                False, obj_id, reason="not complete",
            )
        po.claimed = True
        # Daily/weekly automatically deactivate at next reset.
        # Campaigns are removed immediately on claim.
        if e.cadence == Cadence.CAMPAIGN:
            self._active.pop((player_id, obj_id), None)
        return ClaimResult(
            accepted=True, obj_id=obj_id,
            sparks_awarded=e.sparks_reward,
            gil_awarded=e.gil_reward,
        )

    def reset_due(
        self, *, player_id: str, now_seconds: int,
    ) -> int:
        """Reset daily/weekly objectives whose window has elapsed.
        Returns count reset."""
        reset_count = 0
        keys_to_drop: list[tuple[str, str]] = []
        for (pid, oid), po in list(self._active.items()):
            if pid != player_id:
                continue
            window = _RESET_SECONDS[po.cadence]
            if window == 0:
                continue
            if now_seconds - po.activated_at >= window:
                keys_to_drop.append((pid, oid))
        for k in keys_to_drop:
            self._active.pop(k, None)
            reset_count += 1
        return reset_count

    def active_count(
        self, *, player_id: str, cadence: Cadence,
    ) -> int:
        return len(self._active_for_player(player_id, cadence))

    def total_objectives(self) -> int:
        return len(self._catalog)


__all__ = [
    "Cadence", "Eminence",
    "ActivateResult", "ProgressResult", "ClaimResult",
    "BeastmanRecordsOfEminence",
]
