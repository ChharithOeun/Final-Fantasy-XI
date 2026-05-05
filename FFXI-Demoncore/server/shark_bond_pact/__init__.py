"""Shark bond pact — materialize the SHARK_PACT trust ally.

shark_humanoid_arena awards a SHARK_PACT key item when a
player defeats ZAKARA. This module turns that key item into
a callable summon — a SUMMON_SHARK trust ally drawn from
ZAKARA's bloodline. The summon has its own cooldown, a
single underwater-only restriction (won't surface), and a
short combat duration.

Pact scaling:
  Bond grows with each underwater kill the shark assists in.
  bond ranks 1..5 mapped to {pup_strength, action_set,
  duration_seconds_bonus}.
  rank 1: weakest; rank 5: peer NM strength.

Cooldown rule:
  COOLDOWN_SECONDS between summons. One active shark per
  player; resummoning while one exists rejects.

Public surface
--------------
    BondRank enum
    PactStatus dataclass
    SummonResult dataclass
    SharkBondPact
        .grant_pact(player_id, now_seconds)
        .record_assist(player_id, kill_zone_id)
        .summon(player_id, zone_id, now_seconds)
        .recall(player_id, now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class BondRank(int, enum.Enum):
    R1 = 1
    R2 = 2
    R3 = 3
    R4 = 4
    R5 = 5


# how many assists to advance from current rank to next
_ASSIST_GATES: dict[BondRank, int] = {
    BondRank.R1: 5,
    BondRank.R2: 15,
    BondRank.R3: 30,
    BondRank.R4: 60,
    BondRank.R5: 999_999,    # max — never advances
}

# duration bonus per rank (seconds)
_DURATION_BY_RANK: dict[BondRank, int] = {
    BondRank.R1: 60,
    BondRank.R2: 120,
    BondRank.R3: 180,
    BondRank.R4: 240,
    BondRank.R5: 300,
}

COOLDOWN_SECONDS = 10 * 60

# zones the shark can be summoned in. Anything else rejected
# (it's an underwater-only ally).
_UNDERWATER_ZONES = (
    "tideplate_shallows", "kelp_labyrinth",
    "wreckage_graveyard", "abyss_trench",
    "silmaril_sirenhall", "luminous_drift",
    "reef_spire", "coral_caverns", "drowned_void",
)


@dataclasses.dataclass
class PactStatus:
    player_id: str
    has_pact: bool = False
    rank: BondRank = BondRank.R1
    assists: int = 0
    last_summon_at: t.Optional[int] = None
    active_until: t.Optional[int] = None


@dataclasses.dataclass(frozen=True)
class SummonResult:
    accepted: bool
    rank: t.Optional[BondRank] = None
    duration_seconds: int = 0
    expires_at: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class SharkBondPact:
    _pacts: dict[str, PactStatus] = dataclasses.field(default_factory=dict)

    def grant_pact(
        self, *, player_id: str, now_seconds: int,
    ) -> bool:
        if not player_id:
            return False
        existing = self._pacts.get(player_id)
        if existing and existing.has_pact:
            return False
        self._pacts[player_id] = PactStatus(
            player_id=player_id, has_pact=True,
        )
        return True

    def status(self, *, player_id: str) -> t.Optional[PactStatus]:
        return self._pacts.get(player_id)

    def record_assist(
        self, *, player_id: str, kill_zone_id: str,
    ) -> bool:
        rec = self._pacts.get(player_id)
        if rec is None or not rec.has_pact:
            return False
        if kill_zone_id not in _UNDERWATER_ZONES:
            return False
        rec.assists += 1
        # try to advance rank
        gate = _ASSIST_GATES[rec.rank]
        if rec.assists >= gate and rec.rank != BondRank.R5:
            next_value = rec.rank.value + 1
            rec.rank = BondRank(next_value)
            rec.assists = 0   # reset after promotion
        return True

    def summon(
        self, *, player_id: str,
        zone_id: str,
        now_seconds: int,
    ) -> SummonResult:
        rec = self._pacts.get(player_id)
        if rec is None or not rec.has_pact:
            return SummonResult(False, reason="no pact")
        if zone_id not in _UNDERWATER_ZONES:
            return SummonResult(
                False, reason="must summon underwater",
            )
        # active-ally guard
        if (
            rec.active_until is not None
            and now_seconds < rec.active_until
        ):
            return SummonResult(False, reason="already active")
        # cooldown guard
        if (
            rec.last_summon_at is not None
            and now_seconds < rec.last_summon_at + COOLDOWN_SECONDS
        ):
            return SummonResult(False, reason="on cooldown")
        duration = _DURATION_BY_RANK[rec.rank]
        rec.last_summon_at = now_seconds
        rec.active_until = now_seconds + duration
        return SummonResult(
            accepted=True,
            rank=rec.rank,
            duration_seconds=duration,
            expires_at=rec.active_until,
        )

    def recall(
        self, *, player_id: str, now_seconds: int,
    ) -> bool:
        rec = self._pacts.get(player_id)
        if (
            rec is None
            or rec.active_until is None
            or now_seconds >= rec.active_until
        ):
            return False
        rec.active_until = now_seconds
        return True


__all__ = [
    "BondRank", "PactStatus", "SummonResult",
    "SharkBondPact", "COOLDOWN_SECONDS",
]
