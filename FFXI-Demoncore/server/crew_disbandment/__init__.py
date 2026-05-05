"""Crew disbandment — formal dissolution + asset distribution.

Disbanding a crew is a captain-only action. It's irreversible
once committed. Three phases:

  PROPOSED   - captain announces; 48h cooling-off window.
               Members are notified; the captain can CANCEL.
  RATIFIED   - 48h elapsed without cancel. Hold cargo +
               ship roster snapshot taken; assets enter
               distribution.
  DISTRIBUTED - assets paid out; charter dissolved.

Asset distribution:
  Hold gil + cargo are distributed by tenure SHARES — each
  member earns 1 share per Vana'diel-week of membership.
  Captain has a flat +5 share bonus regardless of tenure.

Members can BUY OUT their share early (lose any remaining
distribution but get a flat 25% of holdings worth in gil
immediately). Buyout is one-way.

Public surface
--------------
    DisbandStage enum
    DisbandShare dataclass
    DisbandmentResult dataclass
    CrewDisbandment
        .propose(charter_id, captain_id, now_seconds)
        .cancel(charter_id, captain_id, now_seconds)
        .ratify(charter_id, now_seconds)
        .compute_shares(charter_id, members_with_tenure_weeks,
                        captain_id, total_holdings_value) -> dict
        .buyout(charter_id, member_id, total_value, now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class DisbandStage(str, enum.Enum):
    NONE = "none"
    PROPOSED = "proposed"
    RATIFIED = "ratified"
    DISTRIBUTED = "distributed"
    CANCELLED = "cancelled"


COOLING_OFF_SECONDS = 48 * 3_600
CAPTAIN_SHARE_BONUS = 5
BUYOUT_PCT = 25


@dataclasses.dataclass
class _Disband:
    charter_id: str
    captain_id: str
    stage: DisbandStage = DisbandStage.PROPOSED
    proposed_at: int = 0
    ratified_at: t.Optional[int] = None
    bought_out: set[str] = dataclasses.field(default_factory=set)


@dataclasses.dataclass(frozen=True)
class DisbandmentResult:
    accepted: bool
    stage: t.Optional[DisbandStage] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class BuyoutResult:
    accepted: bool
    payout_gil: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class CrewDisbandment:
    _records: dict[str, _Disband] = dataclasses.field(default_factory=dict)

    def propose(
        self, *, charter_id: str,
        captain_id: str,
        now_seconds: int,
    ) -> DisbandmentResult:
        if not charter_id or not captain_id:
            return DisbandmentResult(False, reason="bad ids")
        existing = self._records.get(charter_id)
        if existing is not None and existing.stage in (
            DisbandStage.PROPOSED, DisbandStage.RATIFIED,
        ):
            return DisbandmentResult(
                False, reason="already in disband flow",
            )
        self._records[charter_id] = _Disband(
            charter_id=charter_id,
            captain_id=captain_id,
            stage=DisbandStage.PROPOSED,
            proposed_at=now_seconds,
        )
        return DisbandmentResult(
            accepted=True, stage=DisbandStage.PROPOSED,
        )

    def cancel(
        self, *, charter_id: str,
        captain_id: str,
        now_seconds: int,
    ) -> DisbandmentResult:
        rec = self._records.get(charter_id)
        if rec is None or rec.stage != DisbandStage.PROPOSED:
            return DisbandmentResult(
                False, reason="nothing to cancel",
            )
        if rec.captain_id != captain_id:
            return DisbandmentResult(
                False, reason="not captain",
            )
        if (now_seconds - rec.proposed_at) >= COOLING_OFF_SECONDS:
            return DisbandmentResult(
                False, reason="cooling-off elapsed; cannot cancel",
            )
        rec.stage = DisbandStage.CANCELLED
        return DisbandmentResult(
            accepted=True, stage=DisbandStage.CANCELLED,
        )

    def ratify(
        self, *, charter_id: str, now_seconds: int,
    ) -> DisbandmentResult:
        rec = self._records.get(charter_id)
        if rec is None or rec.stage != DisbandStage.PROPOSED:
            return DisbandmentResult(False, reason="not proposed")
        if (now_seconds - rec.proposed_at) < COOLING_OFF_SECONDS:
            return DisbandmentResult(
                False, reason="cooling-off active",
            )
        rec.stage = DisbandStage.RATIFIED
        rec.ratified_at = now_seconds
        return DisbandmentResult(
            accepted=True, stage=DisbandStage.RATIFIED,
        )

    def compute_shares(
        self, *, charter_id: str,
        members_with_tenure_weeks: dict[str, int],
        captain_id: str,
        total_holdings_value: int,
    ) -> dict[str, int]:
        if total_holdings_value <= 0:
            return {m: 0 for m in members_with_tenure_weeks}
        rec = self._records.get(charter_id)
        # subtract any bought-out members from the share pool
        bought_out = rec.bought_out if rec else set()
        active_members = {
            m: weeks
            for m, weeks in members_with_tenure_weeks.items()
            if m not in bought_out
        }
        total_shares = 0
        per_member: dict[str, int] = {}
        for m, weeks in active_members.items():
            shares = max(0, weeks)
            if m == captain_id:
                shares += CAPTAIN_SHARE_BONUS
            per_member[m] = shares
            total_shares += shares
        if total_shares <= 0:
            return {m: 0 for m in active_members}
        out: dict[str, int] = {}
        for m, shares in per_member.items():
            out[m] = (total_holdings_value * shares) // total_shares
        return out

    def buyout(
        self, *, charter_id: str,
        member_id: str,
        total_value: int,
        now_seconds: int,
    ) -> BuyoutResult:
        rec = self._records.get(charter_id)
        if rec is None or rec.stage != DisbandStage.PROPOSED:
            return BuyoutResult(False, reason="must be proposed")
        if member_id == rec.captain_id:
            return BuyoutResult(
                False, reason="captain cannot buyout",
            )
        if member_id in rec.bought_out:
            return BuyoutResult(False, reason="already bought out")
        if total_value <= 0:
            return BuyoutResult(False, reason="no holdings")
        payout = (total_value * BUYOUT_PCT) // 100
        rec.bought_out.add(member_id)
        return BuyoutResult(
            accepted=True, payout_gil=payout,
        )

    def stage_of(
        self, *, charter_id: str,
    ) -> DisbandStage:
        rec = self._records.get(charter_id)
        return rec.stage if rec else DisbandStage.NONE


__all__ = [
    "DisbandStage", "DisbandmentResult", "BuyoutResult",
    "CrewDisbandment",
    "COOLING_OFF_SECONDS",
    "CAPTAIN_SHARE_BONUS", "BUYOUT_PCT",
]
