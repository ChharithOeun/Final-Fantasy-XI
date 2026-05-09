"""Adventurers' Guild — central job board and escrow.

Any player (or NPC) can post a job to the guild. The guild
collects the reward + listing fee up front and holds them in
escrow. A completer accepts the job, fulfills it, and the
guild pays out the reward minus a finder's fee on completion.
Unfulfilled jobs expire after their deadline; cancelations
refund the reward (but the listing fee is the cost of
advertising and stays with the guild).

Five generic job kinds:
    CRAFT_ORDER    poster wants an item crafted
    POWER_LEVEL    poster wants XP help in a zone
    CONTENT_CARRY  poster wants help clearing instance
    DELIVERY       poster wants an item delivered
    ESCORT         poster wants safe passage to a zone

Bounty contracts go through bounty_contracts/ — they carry
hostile-target safeguards that don't apply here.

Lifecycle
    POSTED      escrow held, accepting takers
    ACCEPTED    a completer took it
    COMPLETED   delivered, paid out, guild pocketed fees
    EXPIRED     deadline passed unfulfilled
    CANCELED    poster pulled the listing (loses listing fee)

Public surface
--------------
    JobKind enum
    JobState enum
    Job dataclass (frozen)
    AdventurersGuildSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_LISTING_FEE_PCT = 5     # of reward, kept by guild always
_FINDERS_FEE_PCT = 5     # of reward, deducted from payout
_MIN_REWARD = 100


class JobKind(str, enum.Enum):
    CRAFT_ORDER = "craft_order"
    POWER_LEVEL = "power_level"
    CONTENT_CARRY = "content_carry"
    DELIVERY = "delivery"
    ESCORT = "escort"


class JobState(str, enum.Enum):
    POSTED = "posted"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELED = "canceled"


@dataclasses.dataclass(frozen=True)
class Job:
    job_id: str
    poster_id: str
    kind: JobKind
    description: str
    reward_gil: int
    listing_fee_gil: int
    state: JobState
    accepted_by: str
    posted_day: int
    deadline_day: int
    payout_gil: int          # paid to completer on COMPLETED
    guild_revenue_gil: int


@dataclasses.dataclass
class AdventurersGuildSystem:
    _jobs: dict[str, Job] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def post_job(
        self, *, poster_id: str, kind: JobKind,
        description: str, reward_gil: int,
        posted_day: int, deadline_day: int,
    ) -> t.Optional[str]:
        if not poster_id or not description:
            return None
        if reward_gil < _MIN_REWARD:
            return None
        if posted_day < 0:
            return None
        if deadline_day <= posted_day:
            return None
        listing_fee = (
            reward_gil * _LISTING_FEE_PCT // 100
        )
        jid = f"job_{self._next}"
        self._next += 1
        self._jobs[jid] = Job(
            job_id=jid, poster_id=poster_id, kind=kind,
            description=description,
            reward_gil=reward_gil,
            listing_fee_gil=listing_fee,
            state=JobState.POSTED, accepted_by="",
            posted_day=posted_day,
            deadline_day=deadline_day,
            payout_gil=0, guild_revenue_gil=0,
        )
        return jid

    def total_escrow_paid(
        self, *, job_id: str,
    ) -> int:
        """How much the poster paid into escrow when
        posting (reward + listing fee)."""
        j = self._jobs.get(job_id)
        if j is None:
            return 0
        return j.reward_gil + j.listing_fee_gil

    def accept_job(
        self, *, job_id: str, accepter_id: str,
    ) -> bool:
        if job_id not in self._jobs:
            return False
        j = self._jobs[job_id]
        if j.state != JobState.POSTED:
            return False
        if not accepter_id:
            return False
        if accepter_id == j.poster_id:
            return False
        self._jobs[job_id] = dataclasses.replace(
            j, state=JobState.ACCEPTED,
            accepted_by=accepter_id,
        )
        return True

    def complete_job(
        self, *, job_id: str, completed_day: int,
    ) -> t.Optional[int]:
        """Pay out. Returns gil paid to completer.
        Guild keeps listing_fee + finders_fee.
        """
        if job_id not in self._jobs:
            return None
        j = self._jobs[job_id]
        if j.state != JobState.ACCEPTED:
            return None
        if completed_day < j.posted_day:
            return None
        if completed_day > j.deadline_day:
            return None
        finders_fee = (
            j.reward_gil * _FINDERS_FEE_PCT // 100
        )
        payout = j.reward_gil - finders_fee
        revenue = j.listing_fee_gil + finders_fee
        self._jobs[job_id] = dataclasses.replace(
            j, state=JobState.COMPLETED,
            payout_gil=payout,
            guild_revenue_gil=revenue,
        )
        return payout

    def expire_job(
        self, *, job_id: str, current_day: int,
    ) -> t.Optional[int]:
        """Mark expired. Refunds reward to poster.
        Listing fee stays with guild. Returns refund.
        """
        if job_id not in self._jobs:
            return None
        j = self._jobs[job_id]
        if j.state not in (
            JobState.POSTED, JobState.ACCEPTED,
        ):
            return None
        if current_day <= j.deadline_day:
            return None
        self._jobs[job_id] = dataclasses.replace(
            j, state=JobState.EXPIRED,
            guild_revenue_gil=j.listing_fee_gil,
        )
        return j.reward_gil

    def cancel_job(
        self, *, job_id: str, poster_id: str,
    ) -> t.Optional[int]:
        """Poster pulls listing. Only allowed when
        not yet ACCEPTED. Refund = reward; listing
        fee stays with guild. Returns refund.
        """
        if job_id not in self._jobs:
            return None
        j = self._jobs[job_id]
        if j.state != JobState.POSTED:
            return None
        if j.poster_id != poster_id:
            return None
        self._jobs[job_id] = dataclasses.replace(
            j, state=JobState.CANCELED,
            guild_revenue_gil=j.listing_fee_gil,
        )
        return j.reward_gil

    def job(self, *, job_id: str) -> t.Optional[Job]:
        return self._jobs.get(job_id)

    def open_jobs_by_kind(
        self, *, kind: JobKind,
    ) -> list[Job]:
        return [
            j for j in self._jobs.values()
            if j.kind == kind and j.state == JobState.POSTED
        ]

    def jobs_by_poster(
        self, *, poster_id: str,
    ) -> list[Job]:
        return [
            j for j in self._jobs.values()
            if j.poster_id == poster_id
        ]

    def jobs_by_completer(
        self, *, completer_id: str,
    ) -> list[Job]:
        return [
            j for j in self._jobs.values()
            if j.accepted_by == completer_id
        ]


__all__ = [
    "JobKind", "JobState", "Job",
    "AdventurersGuildSystem",
]
