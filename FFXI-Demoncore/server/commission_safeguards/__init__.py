"""Commission safeguards — global rule layer for guild + bounty.

The Adventurers' Guild and bounty_contracts module are
mechanically separate, but they share an abuse surface — without
caps, bad actors could spam thousands of grief contracts. This
module is the registry of global rules that other systems
query before allowing risky actions.

Rules
-----
- MAX_OPEN_JOBS_PER_POSTER: 5 simultaneous open postings.
- MAX_ACCEPTED_JOBS_PER_COMPLETER: 3 active acceptances.
- MAX_BOUNTIES_PER_TARGET: a single target can carry at most
  3 distinct active bounties from different posters at once
  (prevents pile-on grief).
- BOUNTY_PERIOD_SPENDING_CAP_GIL: any single poster cannot
  spend more than 100,000 gil on bounties in a 30-day window.
- ACCOUNT_AGE_BOUNTY_GATE: posters under MIN_ACCOUNT_AGE_DAYS
  (default 7) cannot post bounties at all — anti-throwaway.
- DISPUTE_WINDOW_DAYS: completer has 7 days post-completion
  to file a dispute claiming the poster cheated; vice versa.

This module is pure rule-check / state-tracking. It doesn't
hold escrow itself — it tells the guild and bounty modules
"yes, this poster can post" or "no, they're over a cap".

Public surface
--------------
    SafeguardSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


MAX_OPEN_JOBS_PER_POSTER = 5
MAX_ACCEPTED_JOBS_PER_COMPLETER = 3
MAX_BOUNTIES_PER_TARGET = 3
BOUNTY_PERIOD_SPENDING_CAP_GIL = 100_000
BOUNTY_PERIOD_DAYS = 30
MIN_ACCOUNT_AGE_DAYS = 7
DISPUTE_WINDOW_DAYS = 7


@dataclasses.dataclass(frozen=True)
class SpendRecord:
    poster_id: str
    amount_gil: int
    posted_day: int


@dataclasses.dataclass
class _PState:
    open_jobs: int = 0
    accepted_jobs: int = 0
    spend_log: list[SpendRecord] = dataclasses.field(
        default_factory=list,
    )
    account_created_day: int = 0


@dataclasses.dataclass
class SafeguardSystem:
    _posters: dict[str, _PState] = dataclasses.field(
        default_factory=dict,
    )
    _bounty_target_count: dict[str, int] = (
        dataclasses.field(default_factory=dict)
    )

    def register_account(
        self, *, account_id: str, created_day: int,
    ) -> bool:
        if not account_id:
            return False
        if created_day < 0:
            return False
        if account_id in self._posters:
            return False
        self._posters[account_id] = _PState(
            account_created_day=created_day,
        )
        return True

    def can_post_job(
        self, *, poster_id: str,
    ) -> bool:
        st = self._posters.get(poster_id)
        if st is None:
            return False
        return st.open_jobs < MAX_OPEN_JOBS_PER_POSTER

    def record_job_posted(
        self, *, poster_id: str,
    ) -> bool:
        st = self._posters.get(poster_id)
        if st is None:
            return False
        if st.open_jobs >= MAX_OPEN_JOBS_PER_POSTER:
            return False
        st.open_jobs += 1
        return True

    def record_job_closed(
        self, *, poster_id: str,
    ) -> bool:
        """Job closed = completed/expired/canceled.
        Frees up an open slot."""
        st = self._posters.get(poster_id)
        if st is None:
            return False
        if st.open_jobs <= 0:
            return False
        st.open_jobs -= 1
        return True

    def can_accept_job(
        self, *, completer_id: str,
    ) -> bool:
        st = self._posters.get(completer_id)
        if st is None:
            return False
        return (
            st.accepted_jobs
            < MAX_ACCEPTED_JOBS_PER_COMPLETER
        )

    def record_job_accepted(
        self, *, completer_id: str,
    ) -> bool:
        st = self._posters.get(completer_id)
        if st is None:
            return False
        if (
            st.accepted_jobs
            >= MAX_ACCEPTED_JOBS_PER_COMPLETER
        ):
            return False
        st.accepted_jobs += 1
        return True

    def record_job_finished(
        self, *, completer_id: str,
    ) -> bool:
        st = self._posters.get(completer_id)
        if st is None:
            return False
        if st.accepted_jobs <= 0:
            return False
        st.accepted_jobs -= 1
        return True

    def can_post_bounty(
        self, *, poster_id: str, target_id: str,
        reward_gil: int, current_day: int,
    ) -> bool:
        st = self._posters.get(poster_id)
        if st is None:
            return False
        # Account age gate
        age = current_day - st.account_created_day
        if age < MIN_ACCOUNT_AGE_DAYS:
            return False
        # Pile-on cap
        if (
            self._bounty_target_count.get(target_id, 0)
            >= MAX_BOUNTIES_PER_TARGET
        ):
            return False
        # Period spending cap
        recent_spend = sum(
            r.amount_gil for r in st.spend_log
            if (current_day - r.posted_day)
            < BOUNTY_PERIOD_DAYS
        )
        if (
            recent_spend + reward_gil
            > BOUNTY_PERIOD_SPENDING_CAP_GIL
        ):
            return False
        return True

    def record_bounty_posted(
        self, *, poster_id: str, target_id: str,
        reward_gil: int, posted_day: int,
    ) -> bool:
        if not self.can_post_bounty(
            poster_id=poster_id, target_id=target_id,
            reward_gil=reward_gil,
            current_day=posted_day,
        ):
            return False
        st = self._posters[poster_id]
        st.spend_log.append(
            SpendRecord(
                poster_id=poster_id,
                amount_gil=reward_gil,
                posted_day=posted_day,
            ),
        )
        self._bounty_target_count[target_id] = (
            self._bounty_target_count.get(target_id, 0)
            + 1
        )
        return True

    def record_bounty_closed(
        self, *, target_id: str,
    ) -> bool:
        cnt = self._bounty_target_count.get(target_id, 0)
        if cnt <= 0:
            return False
        self._bounty_target_count[target_id] = cnt - 1
        return True

    def open_jobs_count(
        self, *, poster_id: str,
    ) -> int:
        st = self._posters.get(poster_id)
        return 0 if st is None else st.open_jobs

    def accepted_jobs_count(
        self, *, completer_id: str,
    ) -> int:
        st = self._posters.get(completer_id)
        return 0 if st is None else st.accepted_jobs

    def bounty_target_count(
        self, *, target_id: str,
    ) -> int:
        return self._bounty_target_count.get(
            target_id, 0,
        )

    def recent_bounty_spend(
        self, *, poster_id: str, current_day: int,
    ) -> int:
        st = self._posters.get(poster_id)
        if st is None:
            return 0
        return sum(
            r.amount_gil for r in st.spend_log
            if (current_day - r.posted_day)
            < BOUNTY_PERIOD_DAYS
        )


__all__ = [
    "SafeguardSystem", "SpendRecord",
    "MAX_OPEN_JOBS_PER_POSTER",
    "MAX_ACCEPTED_JOBS_PER_COMPLETER",
    "MAX_BOUNTIES_PER_TARGET",
    "BOUNTY_PERIOD_SPENDING_CAP_GIL",
    "BOUNTY_PERIOD_DAYS",
    "MIN_ACCOUNT_AGE_DAYS",
    "DISPUTE_WINDOW_DAYS",
]
