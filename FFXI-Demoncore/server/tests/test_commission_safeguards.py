"""Tests for commission_safeguards."""
from __future__ import annotations

from server.commission_safeguards import (
    SafeguardSystem,
    MAX_OPEN_JOBS_PER_POSTER,
    MAX_ACCEPTED_JOBS_PER_COMPLETER,
    MAX_BOUNTIES_PER_TARGET,
    BOUNTY_PERIOD_SPENDING_CAP_GIL,
    MIN_ACCOUNT_AGE_DAYS,
)


def _setup(s: SafeguardSystem, day: int = 0) -> None:
    s.register_account(
        account_id="naji", created_day=day,
    )
    s.register_account(
        account_id="bob", created_day=day,
    )


def test_register_account_happy():
    s = SafeguardSystem()
    assert s.register_account(
        account_id="x", created_day=0,
    ) is True


def test_register_duplicate_blocked():
    s = SafeguardSystem()
    s.register_account(account_id="x", created_day=0)
    assert s.register_account(
        account_id="x", created_day=0,
    ) is False


def test_register_empty_id_blocked():
    s = SafeguardSystem()
    assert s.register_account(
        account_id="", created_day=0,
    ) is False


def test_can_post_job_unknown_blocked():
    s = SafeguardSystem()
    assert s.can_post_job(
        poster_id="ghost",
    ) is False


def test_record_job_posted_increments():
    s = SafeguardSystem()
    _setup(s)
    s.record_job_posted(poster_id="naji")
    s.record_job_posted(poster_id="naji")
    assert s.open_jobs_count(poster_id="naji") == 2


def test_max_open_jobs_blocks():
    s = SafeguardSystem()
    _setup(s)
    for _ in range(MAX_OPEN_JOBS_PER_POSTER):
        s.record_job_posted(poster_id="naji")
    assert s.can_post_job(poster_id="naji") is False
    assert s.record_job_posted(
        poster_id="naji",
    ) is False


def test_record_job_closed_decrements():
    s = SafeguardSystem()
    _setup(s)
    s.record_job_posted(poster_id="naji")
    s.record_job_closed(poster_id="naji")
    assert s.open_jobs_count(poster_id="naji") == 0


def test_max_accepted_jobs_blocks():
    s = SafeguardSystem()
    _setup(s)
    for _ in range(MAX_ACCEPTED_JOBS_PER_COMPLETER):
        s.record_job_accepted(completer_id="bob")
    assert s.can_accept_job(
        completer_id="bob",
    ) is False
    assert s.record_job_accepted(
        completer_id="bob",
    ) is False


def test_record_job_finished_decrements():
    s = SafeguardSystem()
    _setup(s)
    s.record_job_accepted(completer_id="bob")
    s.record_job_finished(completer_id="bob")
    assert s.accepted_jobs_count(
        completer_id="bob",
    ) == 0


def test_can_post_bounty_account_age_gate():
    s = SafeguardSystem()
    s.register_account(
        account_id="newbie", created_day=10,
    )
    # Day 12 — only 2 days old, gate is 7
    assert s.can_post_bounty(
        poster_id="newbie", target_id="bob",
        reward_gil=5000, current_day=12,
    ) is False


def test_can_post_bounty_account_age_passes():
    s = SafeguardSystem()
    s.register_account(
        account_id="naji", created_day=0,
    )
    assert s.can_post_bounty(
        poster_id="naji", target_id="bob",
        reward_gil=5000, current_day=10,
    ) is True


def test_pile_on_cap():
    s = SafeguardSystem()
    s.register_account(
        account_id="p1", created_day=0,
    )
    s.register_account(
        account_id="p2", created_day=0,
    )
    s.register_account(
        account_id="p3", created_day=0,
    )
    s.register_account(
        account_id="p4", created_day=0,
    )
    # 3 distinct posters bounty same target
    s.record_bounty_posted(
        poster_id="p1", target_id="volker",
        reward_gil=5000, posted_day=10,
    )
    s.record_bounty_posted(
        poster_id="p2", target_id="volker",
        reward_gil=5000, posted_day=10,
    )
    s.record_bounty_posted(
        poster_id="p3", target_id="volker",
        reward_gil=5000, posted_day=10,
    )
    # 4th attempt blocked by pile-on cap
    assert s.can_post_bounty(
        poster_id="p4", target_id="volker",
        reward_gil=5000, current_day=10,
    ) is False


def test_bounty_target_count():
    s = SafeguardSystem()
    s.register_account(account_id="p1", created_day=0)
    s.register_account(account_id="p2", created_day=0)
    s.record_bounty_posted(
        poster_id="p1", target_id="volker",
        reward_gil=5000, posted_day=10,
    )
    s.record_bounty_posted(
        poster_id="p2", target_id="volker",
        reward_gil=5000, posted_day=10,
    )
    assert s.bounty_target_count(
        target_id="volker",
    ) == 2


def test_bounty_closed_decrements_target():
    s = SafeguardSystem()
    s.register_account(account_id="p1", created_day=0)
    s.record_bounty_posted(
        poster_id="p1", target_id="volker",
        reward_gil=5000, posted_day=10,
    )
    s.record_bounty_closed(target_id="volker")
    assert s.bounty_target_count(
        target_id="volker",
    ) == 0


def test_period_spending_cap():
    s = SafeguardSystem()
    s.register_account(
        account_id="whale", created_day=0,
    )
    # Single bounty above cap blocked
    assert s.can_post_bounty(
        poster_id="whale", target_id="bob",
        reward_gil=BOUNTY_PERIOD_SPENDING_CAP_GIL + 1,
        current_day=10,
    ) is False


def test_period_spending_aggregates():
    s = SafeguardSystem()
    s.register_account(
        account_id="whale", created_day=0,
    )
    half = BOUNTY_PERIOD_SPENDING_CAP_GIL // 2
    s.record_bounty_posted(
        poster_id="whale", target_id="t1",
        reward_gil=half, posted_day=10,
    )
    s.record_bounty_posted(
        poster_id="whale", target_id="t2",
        reward_gil=half, posted_day=11,
    )
    # Adding any more pushes over the cap
    assert s.can_post_bounty(
        poster_id="whale", target_id="t3",
        reward_gil=1, current_day=12,
    ) is False


def test_period_spending_resets_after_window():
    s = SafeguardSystem()
    s.register_account(
        account_id="whale", created_day=0,
    )
    s.record_bounty_posted(
        poster_id="whale", target_id="t1",
        reward_gil=BOUNTY_PERIOD_SPENDING_CAP_GIL,
        posted_day=10,
    )
    # 35 days later — outside the 30-day window
    assert s.can_post_bounty(
        poster_id="whale", target_id="t2",
        reward_gil=5000, current_day=45,
    ) is True


def test_recent_bounty_spend_query():
    s = SafeguardSystem()
    s.register_account(account_id="x", created_day=0)
    s.record_bounty_posted(
        poster_id="x", target_id="t",
        reward_gil=10000, posted_day=10,
    )
    assert s.recent_bounty_spend(
        poster_id="x", current_day=15,
    ) == 10000
    assert s.recent_bounty_spend(
        poster_id="x", current_day=50,
    ) == 0


def test_unknown_poster_can_post_returns_false():
    s = SafeguardSystem()
    assert s.can_post_bounty(
        poster_id="ghost", target_id="t",
        reward_gil=5000, current_day=10,
    ) is False


def test_record_blocked_when_capped():
    s = SafeguardSystem()
    s.register_account(account_id="p1", created_day=0)
    s.register_account(account_id="p2", created_day=0)
    s.register_account(account_id="p3", created_day=0)
    s.register_account(account_id="p4", created_day=0)
    for p in ("p1", "p2", "p3"):
        s.record_bounty_posted(
            poster_id=p, target_id="v",
            reward_gil=1000, posted_day=10,
        )
    assert s.record_bounty_posted(
        poster_id="p4", target_id="v",
        reward_gil=1000, posted_day=10,
    ) is False


def test_open_jobs_count_unknown():
    s = SafeguardSystem()
    assert s.open_jobs_count(
        poster_id="ghost",
    ) == 0


def test_recent_spend_unknown():
    s = SafeguardSystem()
    assert s.recent_bounty_spend(
        poster_id="ghost", current_day=10,
    ) == 0


def test_constants_sane():
    assert MAX_OPEN_JOBS_PER_POSTER >= 3
    assert MAX_BOUNTIES_PER_TARGET <= 5
    assert MIN_ACCOUNT_AGE_DAYS >= 1
