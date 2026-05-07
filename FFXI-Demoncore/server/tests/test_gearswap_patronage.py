"""Tests for gearswap_patronage."""
from __future__ import annotations

from server.gearswap_patronage import GearswapPatronage


def test_tip_happy():
    p = GearswapPatronage()
    out = p.tip(
        patron_id="bob", recipient_id="chharith",
        gil_amount=10000, posted_at=1000,
    )
    assert out.success is True
    assert out.record.gil_amount == 10000


def test_tip_blank_patron_blocked():
    p = GearswapPatronage()
    out = p.tip(
        patron_id="", recipient_id="chharith",
        gil_amount=10000, posted_at=1000,
    )
    assert out.success is False
    assert out.reason == "ids_required"


def test_tip_blank_recipient_blocked():
    p = GearswapPatronage()
    out = p.tip(
        patron_id="bob", recipient_id="",
        gil_amount=10000, posted_at=1000,
    )
    assert out.success is False


def test_tip_self_blocked():
    p = GearswapPatronage()
    out = p.tip(
        patron_id="bob", recipient_id="bob",
        gil_amount=10000, posted_at=1000,
    )
    assert out.success is False
    assert out.reason == "self_tip"


def test_tip_below_min_blocked():
    p = GearswapPatronage()
    out = p.tip(
        patron_id="bob", recipient_id="chharith",
        gil_amount=50, posted_at=1000,
    )
    assert out.success is False
    assert out.reason == "below_min"


def test_tip_at_min_allowed():
    p = GearswapPatronage()
    out = p.tip(
        patron_id="bob", recipient_id="chharith",
        gil_amount=100, posted_at=1000,
    )
    assert out.success is True


def test_tip_daily_cap_blocks_over():
    p = GearswapPatronage()
    p.tip(
        patron_id="bob", recipient_id="chharith",
        gil_amount=900_000, posted_at=1000,
    )
    out = p.tip(
        patron_id="bob", recipient_id="chharith",
        gil_amount=200_000, posted_at=1500,
    )
    assert out.success is False
    assert out.reason == "daily_cap_to_recipient"


def test_tip_daily_cap_resets_after_24h():
    p = GearswapPatronage()
    p.tip(
        patron_id="bob", recipient_id="chharith",
        gil_amount=1_000_000, posted_at=1000,
    )
    # 25 hours later, fresh budget
    out = p.tip(
        patron_id="bob", recipient_id="chharith",
        gil_amount=500_000,
        posted_at=1000 + 25 * 3600,
    )
    assert out.success is True


def test_tip_cap_is_per_recipient():
    """Bob can max-tip Chharith AND max-tip Rival in
    the same day."""
    p = GearswapPatronage()
    out1 = p.tip(
        patron_id="bob", recipient_id="chharith",
        gil_amount=1_000_000, posted_at=1000,
    )
    out2 = p.tip(
        patron_id="bob", recipient_id="rival",
        gil_amount=1_000_000, posted_at=1500,
    )
    assert out1.success is True
    assert out2.success is True


def test_tip_with_publish_id():
    p = GearswapPatronage()
    out = p.tip(
        patron_id="bob", recipient_id="chharith",
        gil_amount=10000, publish_id="pub_42",
        posted_at=1000,
    )
    assert out.record.publish_id == "pub_42"


def test_total_gil_received():
    p = GearswapPatronage()
    p.tip(
        patron_id="bob", recipient_id="chharith",
        gil_amount=10000, posted_at=1000,
    )
    p.tip(
        patron_id="cara", recipient_id="chharith",
        gil_amount=5000, posted_at=2000,
    )
    assert p.total_gil_received(
        recipient_id="chharith",
    ) == 15000


def test_total_gil_given():
    p = GearswapPatronage()
    p.tip(
        patron_id="bob", recipient_id="chharith",
        gil_amount=10000, posted_at=1000,
    )
    p.tip(
        patron_id="bob", recipient_id="rival",
        gil_amount=3000, posted_at=2000,
    )
    assert p.total_gil_given(patron_id="bob") == 13000


def test_top_patrons_sorted():
    p = GearswapPatronage()
    p.tip(
        patron_id="bob", recipient_id="chharith",
        gil_amount=5000, posted_at=1000,
    )
    p.tip(
        patron_id="cara", recipient_id="chharith",
        gil_amount=20000, posted_at=2000,
    )
    p.tip(
        patron_id="dan", recipient_id="chharith",
        gil_amount=15000, posted_at=3000,
    )
    out = p.top_patrons(recipient_id="chharith")
    assert out[0] == ("cara", 20000)
    assert out[1] == ("dan", 15000)
    assert out[2] == ("bob", 5000)


def test_top_patrons_combines_multiple_tips():
    p = GearswapPatronage()
    p.tip(
        patron_id="bob", recipient_id="chharith",
        gil_amount=5000, posted_at=1000,
    )
    p.tip(
        patron_id="bob", recipient_id="chharith",
        gil_amount=8000,
        posted_at=1000 + 30 * 3600,   # next day
    )
    out = p.top_patrons(recipient_id="chharith")
    assert out[0] == ("bob", 13000)


def test_top_patrons_zero_limit():
    p = GearswapPatronage()
    assert p.top_patrons(
        recipient_id="chharith", limit=0,
    ) == []


def test_tips_for_publish():
    p = GearswapPatronage()
    p.tip(
        patron_id="bob", recipient_id="chharith",
        gil_amount=5000, publish_id="pub_42",
        posted_at=1000,
    )
    p.tip(
        patron_id="cara", recipient_id="chharith",
        gil_amount=3000, publish_id="pub_42",
        posted_at=2000,
    )
    p.tip(
        patron_id="dan", recipient_id="chharith",
        gil_amount=8000, publish_id="other",
        posted_at=3000,
    )
    out = p.tips_for_publish(publish_id="pub_42")
    assert len(out) == 2


def test_tips_for_unknown_publish_empty():
    p = GearswapPatronage()
    assert p.tips_for_publish(publish_id="ghost") == []


def test_gil_received_in_window():
    p = GearswapPatronage()
    p.tip(
        patron_id="bob", recipient_id="chharith",
        gil_amount=10000, posted_at=100_000,
    )
    p.tip(
        patron_id="cara", recipient_id="chharith",
        gil_amount=5000, posted_at=200_000,
    )
    out = p.gil_received_this_window(
        recipient_id="chharith", now=250_000,
        day_window=7,
    )
    assert out == 15000


def test_gil_received_in_window_zero_window():
    p = GearswapPatronage()
    p.tip(
        patron_id="bob", recipient_id="chharith",
        gil_amount=10000, posted_at=1000,
    )
    out = p.gil_received_this_window(
        recipient_id="chharith", now=1000, day_window=0,
    )
    assert out == 0


def test_total_tips():
    p = GearswapPatronage()
    p.tip(
        patron_id="bob", recipient_id="chharith",
        gil_amount=5000, posted_at=1000,
    )
    p.tip(
        patron_id="cara", recipient_id="rival",
        gil_amount=3000, posted_at=2000,
    )
    assert p.total_tips() == 2
