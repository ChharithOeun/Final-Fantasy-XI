"""Mercenary reputation — per-kind completer reputation.

Each completer accumulates a reputation score per JobKind they
take on. Successful completions add +10, disputes that the
completer loses subtract 5, expirations they walked away from
subtract 2. Reputation thresholds map to ranks: NOVICE,
JOURNEYMAN, EXPERT, MASTER. Posters querying the guild can see
a completer's per-kind track record before accepting their bid
on a job — long-running carriers won't get hired for craft
orders, even if they're cheap.

Public surface
--------------
    JobKind enum (mirrored from adventurers_guild)
    Outcome enum
    Rank enum
    Completion dataclass (frozen)
    MercenaryReputationSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_RANK_THRESHOLDS = (
    (0, "novice"),
    (50, "journeyman"),
    (100, "expert"),
    (250, "master"),
)

_DELTA_SUCCESS = 10
_DELTA_DISPUTE_LOSS = -5
_DELTA_EXPIRY = -2


class JobKind(str, enum.Enum):
    CRAFT_ORDER = "craft_order"
    POWER_LEVEL = "power_level"
    CONTENT_CARRY = "content_carry"
    DELIVERY = "delivery"
    ESCORT = "escort"
    BOUNTY = "bounty"


class Outcome(str, enum.Enum):
    SUCCESS = "success"
    DISPUTE_LOSS = "dispute_loss"
    EXPIRY = "expiry"


class Rank(str, enum.Enum):
    NOVICE = "novice"
    JOURNEYMAN = "journeyman"
    EXPERT = "expert"
    MASTER = "master"


@dataclasses.dataclass(frozen=True)
class Completion:
    completion_id: str
    completer_id: str
    kind: JobKind
    outcome: Outcome
    delta: int
    recorded_day: int


def _rank_for_score(score: int) -> Rank:
    label = "novice"
    for thresh, name in _RANK_THRESHOLDS:
        if score >= thresh:
            label = name
    return Rank(label)


@dataclasses.dataclass
class MercenaryReputationSystem:
    _completions: dict[str, Completion] = (
        dataclasses.field(default_factory=dict)
    )
    _scores: dict[tuple[str, str], int] = (
        dataclasses.field(default_factory=dict)
    )
    _next: int = 1

    def record_completion(
        self, *, completer_id: str, kind: JobKind,
        outcome: Outcome, recorded_day: int,
    ) -> t.Optional[str]:
        if not completer_id:
            return None
        if recorded_day < 0:
            return None
        if outcome == Outcome.SUCCESS:
            delta = _DELTA_SUCCESS
        elif outcome == Outcome.DISPUTE_LOSS:
            delta = _DELTA_DISPUTE_LOSS
        else:
            delta = _DELTA_EXPIRY
        cid = f"comp_{self._next}"
        self._next += 1
        self._completions[cid] = Completion(
            completion_id=cid,
            completer_id=completer_id, kind=kind,
            outcome=outcome, delta=delta,
            recorded_day=recorded_day,
        )
        key = (completer_id, kind.value)
        self._scores[key] = max(
            0, self._scores.get(key, 0) + delta,
        )
        return cid

    def reputation(
        self, *, completer_id: str, kind: JobKind,
    ) -> int:
        return self._scores.get(
            (completer_id, kind.value), 0,
        )

    def rank(
        self, *, completer_id: str, kind: JobKind,
    ) -> Rank:
        return _rank_for_score(
            self.reputation(
                completer_id=completer_id, kind=kind,
            ),
        )

    def overall_reputation(
        self, *, completer_id: str,
    ) -> int:
        return sum(
            v for (cid, _k), v in self._scores.items()
            if cid == completer_id
        )

    def completions_by_completer(
        self, *, completer_id: str,
    ) -> list[Completion]:
        return [
            c for c in self._completions.values()
            if c.completer_id == completer_id
        ]

    def completion(
        self, *, completion_id: str,
    ) -> t.Optional[Completion]:
        return self._completions.get(completion_id)


__all__ = [
    "JobKind", "Outcome", "Rank", "Completion",
    "MercenaryReputationSystem",
]
