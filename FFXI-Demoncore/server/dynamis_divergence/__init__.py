"""Dynamis-Divergence — modern Dynamis with Su5 weapon remoulds.

Reimagined Dynamis. 3-wave instance per zone with currency-cap
removed (canonical Dynamis caps your currency drops; D-D
doesn't). Drops include Dynamis-D Currency (used to remould
canonical Relic weapons into Su5-grade Su2/Su3/Su4/Su5 forms).

Public surface
--------------
    DynamisZone enum (sandy/bastok/windy/jeuno/xarcabard/buburimu)
    WaveOutcome dataclass
    DynamisDInstance
        .start(now)
        .complete_wave(wave, mob_count, current_party_score)
        .resolve(now) -> ResolveResult
    Su5Remould
        .input_required_for(rank) -> tuple[str, int]
        .progress_remould(...) -> RemouldResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


WAVES_PER_INSTANCE = 3
TIMER_SECONDS = 60 * 60        # 1-hour run


class DynamisZone(str, enum.Enum):
    SANDORIA = "dynamis_sandoria"
    BASTOK = "dynamis_bastok"
    WINDURST = "dynamis_windurst"
    JEUNO = "dynamis_jeuno"
    XARCABARD = "dynamis_xarcabard"
    BUBURIMU = "dynamis_buburimu"


class InstanceState(str, enum.Enum):
    PRE = "pre"
    ACTIVE = "active"
    RESOLVED = "resolved"
    EXPIRED = "expired"


@dataclasses.dataclass(frozen=True)
class WaveOutcome:
    wave: int
    accepted: bool
    mob_count: int = 0
    score_added: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ResolveResult:
    accepted: bool
    waves_cleared: int = 0
    final_score: int = 0
    currency_awarded: int = 0
    drop_pool: tuple[str, ...] = ()
    reason: t.Optional[str] = None


@dataclasses.dataclass
class DynamisDInstance:
    instance_id: str
    zone: DynamisZone
    state: InstanceState = InstanceState.PRE
    started_at: float = 0.0
    waves_cleared: int = 0
    score: int = 0

    def start(self, *, now_seconds: float) -> bool:
        if self.state != InstanceState.PRE:
            return False
        self.state = InstanceState.ACTIVE
        self.started_at = now_seconds
        return True

    def complete_wave(
        self, *, wave: int, mob_count: int, now_seconds: float,
    ) -> WaveOutcome:
        if self.state != InstanceState.ACTIVE:
            return WaveOutcome(wave, False, reason="not active")
        if wave != self.waves_cleared + 1:
            return WaveOutcome(wave, False, reason="out-of-order wave")
        if wave > WAVES_PER_INSTANCE:
            return WaveOutcome(wave, False, reason="no wave beyond 3")
        if now_seconds - self.started_at > TIMER_SECONDS:
            self.state = InstanceState.EXPIRED
            return WaveOutcome(wave, False, reason="timer expired")
        if mob_count <= 0:
            return WaveOutcome(wave, False, reason="no mobs killed")
        # Score formula: more mobs killed in earlier waves = more
        added = mob_count * (10 + 5 * wave)
        self.score += added
        self.waves_cleared = wave
        return WaveOutcome(
            wave, True, mob_count=mob_count, score_added=added,
        )

    def resolve(self, *, now_seconds: float) -> ResolveResult:
        if self.state == InstanceState.RESOLVED:
            return ResolveResult(False, reason="already resolved")
        if self.state == InstanceState.EXPIRED:
            return ResolveResult(False, reason="run expired")
        if self.state != InstanceState.ACTIVE:
            return ResolveResult(False, reason="not active")
        # Currency from score — uncapped (this is the D-D twist)
        currency = self.score // 5
        # Drop pool scales with waves cleared
        pool = ("dynamis_d_currency",)
        if self.waves_cleared >= 2:
            pool = pool + ("relic_weapon_remould_token",)
        if self.waves_cleared >= 3:
            pool = pool + ("alexandrite_uncapped",
                            "su5_remould_voucher")
        self.state = InstanceState.RESOLVED
        return ResolveResult(
            accepted=True, waves_cleared=self.waves_cleared,
            final_score=self.score, currency_awarded=currency,
            drop_pool=pool,
        )


# -----------------------------------------------------------------------
# Su5 Remould chain
# -----------------------------------------------------------------------

class Su5Rank(str, enum.Enum):
    BASE = "base"        # canonical Relic
    SU2 = "su2"
    SU3 = "su3"
    SU4 = "su4"
    SU5 = "su5"          # capstone


_RANK_ORDER: tuple[Su5Rank, ...] = (
    Su5Rank.BASE, Su5Rank.SU2, Su5Rank.SU3, Su5Rank.SU4, Su5Rank.SU5,
)


_REMOULD_INPUTS: dict[Su5Rank, tuple[str, int]] = {
    Su5Rank.SU2: ("dynamis_d_currency", 50000),
    Su5Rank.SU3: ("dynamis_d_currency", 150000),
    Su5Rank.SU4: ("dynamis_d_currency", 400000),
    Su5Rank.SU5: ("dynamis_d_currency", 1_000_000),
}


def input_required_for(*, target_rank: Su5Rank) -> tuple[str, int]:
    if target_rank == Su5Rank.BASE:
        return ("", 0)
    return _REMOULD_INPUTS[target_rank]


def next_rank_for(*, current: Su5Rank) -> t.Optional[Su5Rank]:
    idx = _RANK_ORDER.index(current)
    if idx + 1 >= len(_RANK_ORDER):
        return None
    return _RANK_ORDER[idx + 1]


@dataclasses.dataclass(frozen=True)
class RemouldResult:
    accepted: bool
    new_rank: t.Optional[Su5Rank] = None
    currency_consumed: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerSu5Remould:
    """Per-weapon remould state."""
    player_id: str
    weapon_id: str
    rank: Su5Rank = Su5Rank.BASE

    def progress_remould(
        self, *, currency_held: int,
    ) -> RemouldResult:
        nxt = next_rank_for(current=self.rank)
        if nxt is None:
            return RemouldResult(False, reason="weapon at Su5 cap")
        item_id, qty = input_required_for(target_rank=nxt)
        if currency_held < qty:
            return RemouldResult(
                False, reason="insufficient currency",
            )
        self.rank = nxt
        return RemouldResult(
            accepted=True, new_rank=nxt, currency_consumed=qty,
        )


__all__ = [
    "WAVES_PER_INSTANCE", "TIMER_SECONDS",
    "DynamisZone", "InstanceState",
    "WaveOutcome", "ResolveResult", "DynamisDInstance",
    "Su5Rank", "RemouldResult", "PlayerSu5Remould",
    "input_required_for", "next_rank_for",
]
