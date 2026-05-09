"""Tests for adventurers_guild."""
from __future__ import annotations

from server.adventurers_guild import (
    AdventurersGuildSystem, JobKind, JobState,
)


def _post(
    s: AdventurersGuildSystem, reward: int = 1000,
) -> str:
    return s.post_job(
        poster_id="naji", kind=JobKind.CRAFT_ORDER,
        description="Forge me a Mythril Sword",
        reward_gil=reward, posted_day=10,
        deadline_day=20,
    )


def test_post_happy():
    s = AdventurersGuildSystem()
    jid = _post(s)
    assert jid is not None


def test_post_below_min_reward():
    s = AdventurersGuildSystem()
    assert s.post_job(
        poster_id="x", kind=JobKind.CRAFT_ORDER,
        description="d", reward_gil=50,
        posted_day=10, deadline_day=20,
    ) is None


def test_post_deadline_before_posted():
    s = AdventurersGuildSystem()
    assert s.post_job(
        poster_id="x", kind=JobKind.CRAFT_ORDER,
        description="d", reward_gil=1000,
        posted_day=10, deadline_day=5,
    ) is None


def test_post_empty_poster():
    s = AdventurersGuildSystem()
    assert s.post_job(
        poster_id="", kind=JobKind.CRAFT_ORDER,
        description="d", reward_gil=1000,
        posted_day=10, deadline_day=20,
    ) is None


def test_post_empty_description():
    s = AdventurersGuildSystem()
    assert s.post_job(
        poster_id="x", kind=JobKind.CRAFT_ORDER,
        description="", reward_gil=1000,
        posted_day=10, deadline_day=20,
    ) is None


def test_listing_fee_5pct():
    s = AdventurersGuildSystem()
    jid = _post(s, reward=1000)
    j = s.job(job_id=jid)
    assert j.listing_fee_gil == 50


def test_total_escrow_includes_fee():
    s = AdventurersGuildSystem()
    jid = _post(s, reward=1000)
    assert s.total_escrow_paid(job_id=jid) == 1050


def test_accept_happy():
    s = AdventurersGuildSystem()
    jid = _post(s)
    assert s.accept_job(
        job_id=jid, accepter_id="bob",
    ) is True


def test_accept_self_blocked():
    s = AdventurersGuildSystem()
    jid = _post(s)
    assert s.accept_job(
        job_id=jid, accepter_id="naji",
    ) is False


def test_accept_double_blocked():
    s = AdventurersGuildSystem()
    jid = _post(s)
    s.accept_job(job_id=jid, accepter_id="bob")
    assert s.accept_job(
        job_id=jid, accepter_id="cara",
    ) is False


def test_complete_happy_pays_95pct():
    s = AdventurersGuildSystem()
    jid = _post(s, reward=1000)
    s.accept_job(job_id=jid, accepter_id="bob")
    payout = s.complete_job(
        job_id=jid, completed_day=15,
    )
    # reward 1000 - finders fee 5% = 950
    assert payout == 950


def test_complete_guild_revenue():
    s = AdventurersGuildSystem()
    jid = _post(s, reward=1000)
    s.accept_job(job_id=jid, accepter_id="bob")
    s.complete_job(job_id=jid, completed_day=15)
    j = s.job(job_id=jid)
    # listing 50 + finders 50 = 100
    assert j.guild_revenue_gil == 100


def test_complete_before_accept_blocked():
    s = AdventurersGuildSystem()
    jid = _post(s)
    assert s.complete_job(
        job_id=jid, completed_day=15,
    ) is None


def test_complete_past_deadline_blocked():
    s = AdventurersGuildSystem()
    jid = _post(s)
    s.accept_job(job_id=jid, accepter_id="bob")
    assert s.complete_job(
        job_id=jid, completed_day=25,
    ) is None


def test_expire_happy_refunds_reward():
    s = AdventurersGuildSystem()
    jid = _post(s, reward=1000)
    refund = s.expire_job(
        job_id=jid, current_day=21,
    )
    assert refund == 1000


def test_expire_keeps_listing_fee_in_guild():
    s = AdventurersGuildSystem()
    jid = _post(s, reward=1000)
    s.expire_job(job_id=jid, current_day=21)
    assert s.job(
        job_id=jid,
    ).guild_revenue_gil == 50


def test_expire_before_deadline_blocked():
    s = AdventurersGuildSystem()
    jid = _post(s)
    assert s.expire_job(
        job_id=jid, current_day=15,
    ) is None


def test_cancel_happy():
    s = AdventurersGuildSystem()
    jid = _post(s, reward=1000)
    refund = s.cancel_job(
        job_id=jid, poster_id="naji",
    )
    assert refund == 1000


def test_cancel_keeps_listing_fee():
    s = AdventurersGuildSystem()
    jid = _post(s, reward=1000)
    s.cancel_job(job_id=jid, poster_id="naji")
    assert s.job(
        job_id=jid,
    ).guild_revenue_gil == 50


def test_cancel_after_accept_blocked():
    s = AdventurersGuildSystem()
    jid = _post(s)
    s.accept_job(job_id=jid, accepter_id="bob")
    assert s.cancel_job(
        job_id=jid, poster_id="naji",
    ) is None


def test_cancel_wrong_poster_blocked():
    s = AdventurersGuildSystem()
    jid = _post(s)
    assert s.cancel_job(
        job_id=jid, poster_id="bob",
    ) is None


def test_open_jobs_by_kind_filters():
    s = AdventurersGuildSystem()
    a = _post(s)  # craft
    b = s.post_job(
        poster_id="naji", kind=JobKind.POWER_LEVEL,
        description="run me to 50", reward_gil=2000,
        posted_day=10, deadline_day=20,
    )
    s.accept_job(job_id=a, accepter_id="bob")
    crafts = s.open_jobs_by_kind(
        kind=JobKind.CRAFT_ORDER,
    )
    pls = s.open_jobs_by_kind(
        kind=JobKind.POWER_LEVEL,
    )
    # a is now ACCEPTED so not in open_jobs
    assert len(crafts) == 0
    assert len(pls) == 1


def test_jobs_by_poster_and_completer():
    s = AdventurersGuildSystem()
    a = _post(s)
    s.accept_job(job_id=a, accepter_id="bob")
    s.complete_job(job_id=a, completed_day=15)
    b = _post(s)
    assert len(s.jobs_by_poster(poster_id="naji")) == 2
    assert len(
        s.jobs_by_completer(completer_id="bob"),
    ) == 1


def test_unknown_job():
    s = AdventurersGuildSystem()
    assert s.job(job_id="ghost") is None


def test_enum_counts():
    assert len(list(JobKind)) == 5
    assert len(list(JobState)) == 5
