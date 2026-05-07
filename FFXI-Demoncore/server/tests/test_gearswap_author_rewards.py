"""Tests for gearswap_author_rewards."""
from __future__ import annotations

from server.gearswap_adopt import AdoptMode, GearswapAdopt
from server.gearswap_author_rewards import (
    GearswapAuthorRewards,
)
from server.gearswap_publisher import GearswapPublisher
from server.gearswap_rating import GearswapRating, Thumb


def _seed():
    p = GearswapPublisher()
    p.set_mentor_status(
        author_id="chharith", is_mentor=True,
        display_name="Chharith",
    )
    pid = p.publish(
        author_id="chharith", job="RDM",
        addon_id="rdm_chharith", lua_source="-- v1",
        reputation_snapshot=80, hours_played_on_job=500,
        published_at=1000,
    )
    a = GearswapAdopt(_publisher=p)
    r = GearswapRating()
    rw = GearswapAuthorRewards(
        _publisher=p, _adopt=a, _rating=r,
    )
    return p, a, r, rw, pid


def _adopt_n(a, pid, n, start=2000):
    for i in range(n):
        a.adopt(
            player_id=f"p{i}", publish_id=pid,
            mode=AdoptMode.USE_AS_IS, adopted_at=start + i,
        )


def test_no_rewards_below_first_tier():
    _, a, _, rw, pid = _seed()
    _adopt_n(a, pid, 5)
    out = rw.check_publish(publish_id=pid)
    assert out == []


def test_first_tier_at_10():
    _, a, _, rw, pid = _seed()
    _adopt_n(a, pid, 10)
    out = rw.check_publish(publish_id=pid)
    assert len(out) == 1
    assert out[0].threshold == 10
    assert out[0].title_awarded == "Mentor's Voice"
    assert out[0].gil_paid == 1000


def test_skips_paid_tier():
    _, a, _, rw, pid = _seed()
    _adopt_n(a, pid, 10)
    rw.check_publish(publish_id=pid)
    # Adopt a few more, still below 50 — no new payout
    _adopt_n(a, pid, 5, start=3000)
    out = rw.check_publish(publish_id=pid)
    assert out == []


def test_multiple_tiers_in_one_check():
    _, a, _, rw, pid = _seed()
    _adopt_n(a, pid, 200)
    out = rw.check_publish(publish_id=pid)
    # 10, 50, 200 = 3 events
    assert len(out) == 3
    assert {ev.threshold for ev in out} == {10, 50, 200}


def test_total_gil_earned():
    _, a, _, rw, pid = _seed()
    _adopt_n(a, pid, 50)
    rw.check_publish(publish_id=pid)
    # tier 10 (1000) + tier 50 (5000) = 6000
    assert rw.total_gil_earned(author_id="chharith") == 6000


def test_titles_earned_sorted():
    _, a, _, rw, pid = _seed()
    _adopt_n(a, pid, 200)
    rw.check_publish(publish_id=pid)
    titles = rw.titles_earned(author_id="chharith")
    assert titles == [
        "Mentor's Voice",
        "Heard in Whispers",
        "Spoken in Marketplaces",
    ]


def test_events_for_author():
    _, a, _, rw, pid = _seed()
    _adopt_n(a, pid, 10)
    rw.check_publish(publish_id=pid)
    out = rw.events_for(author_id="chharith")
    assert len(out) == 1


def test_events_for_unknown_empty():
    _, a, _, rw, pid = _seed()
    _adopt_n(a, pid, 10)
    rw.check_publish(publish_id=pid)
    assert rw.events_for(author_id="ghost") == []


def test_unknown_publish_no_events():
    _, _, _, rw, _ = _seed()
    assert rw.check_publish(publish_id="ghost") == []


def test_negative_net_thumbs_blocks_payout():
    _, a, r, rw, pid = _seed()
    _adopt_n(a, pid, 10)
    # Crush the build
    for i in range(5):
        r.rate(
            player_id=f"d{i}", publish_id=pid,
            thumb=Thumb.DOWN,
        )
    out = rw.check_publish(publish_id=pid)
    assert out == []
    assert rw.total_gil_earned(author_id="chharith") == 0


def test_negative_net_can_recover_later():
    """If the build's reputation recovers, payouts catch up."""
    _, a, r, rw, pid = _seed()
    _adopt_n(a, pid, 10)
    for i in range(5):
        r.rate(
            player_id=f"d{i}", publish_id=pid,
            thumb=Thumb.DOWN,
        )
    rw.check_publish(publish_id=pid)
    # Now community changes their mind
    for d in range(5):
        r.un_rate(player_id=f"d{d}", publish_id=pid)
    for i in range(8):
        r.rate(
            player_id=f"u{i}", publish_id=pid, thumb=Thumb.UP,
        )
    out = rw.check_publish(publish_id=pid)
    assert len(out) == 1
    assert out[0].threshold == 10


def test_unlisted_publish_keeps_paid_rewards():
    """Once paid, unlist doesn't claw back."""
    p, a, _, rw, pid = _seed()
    _adopt_n(a, pid, 10)
    rw.check_publish(publish_id=pid)
    p.unlist(author_id="chharith", publish_id=pid)
    # Pre-existing earnings stay
    assert rw.total_gil_earned(author_id="chharith") == 1000
    titles = rw.titles_earned(author_id="chharith")
    assert "Mentor's Voice" in titles


def test_revoked_still_no_clawback():
    p, a, _, rw, pid = _seed()
    _adopt_n(a, pid, 10)
    rw.check_publish(publish_id=pid)
    p.revoke(publish_id=pid, reason="exploit")
    assert rw.total_gil_earned(author_id="chharith") == 1000


def test_fame_tiers_table_5_entries():
    assert len(GearswapAuthorRewards.fame_tiers()) == 5


def test_fame_tier_thresholds_strict_ascending():
    tiers = GearswapAuthorRewards.fame_tiers()
    for a, b in zip(tiers, tiers[1:]):
        assert a.threshold < b.threshold


def test_idempotent_repeated_check():
    """Calling check_publish at the same adoption count
    twice does not double-pay."""
    _, a, _, rw, pid = _seed()
    _adopt_n(a, pid, 50)
    rw.check_publish(publish_id=pid)
    out = rw.check_publish(publish_id=pid)
    assert out == []
    assert rw.total_gil_earned(author_id="chharith") == 6000


def test_multi_publish_per_author():
    p, a, _, rw, pid = _seed()
    pid2 = p.publish(
        author_id="chharith", job="BLM",
        addon_id="blm_chharith", lua_source="-- v1",
        reputation_snapshot=80, hours_played_on_job=300,
        published_at=2000,
    )
    _adopt_n(a, pid, 10)
    _adopt_n(a, pid2, 10, start=10_000)
    rw.check_publish(publish_id=pid)
    rw.check_publish(publish_id=pid2)
    # Both publishes pay out independently
    assert rw.total_gil_earned(author_id="chharith") == 2000
