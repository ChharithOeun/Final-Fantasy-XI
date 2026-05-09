"""Tests for player_concert_hall."""
from __future__ import annotations

from server.player_concert_hall import (
    PlayerConcertHallSystem, ConcertState,
)


def _hall(s: PlayerConcertHallSystem) -> str:
    s.register_hall(
        hall_id="bastok_hall", name="Bastok Hall",
        capacity=100, prestige=50,
    )
    return "bastok_hall"


def _book(
    s: PlayerConcertHallSystem,
    hall_id: str = "bastok_hall",
) -> str:
    return s.book_concert(
        hall_id=hall_id, performer_id="naji",
        performer_skill=70, setlist_size=10,
        ticket_price_gil=100, scheduled_day=10,
    )


def test_register_hall_happy():
    s = PlayerConcertHallSystem()
    assert s.register_hall(
        hall_id="h1", name="Hall One",
        capacity=200, prestige=70,
    ) is True


def test_register_hall_duplicate_blocked():
    s = PlayerConcertHallSystem()
    s.register_hall(
        hall_id="h1", name="Hall One",
        capacity=200, prestige=70,
    )
    assert s.register_hall(
        hall_id="h1", name="Hall One Again",
        capacity=200, prestige=70,
    ) is False


def test_register_hall_bad_capacity():
    s = PlayerConcertHallSystem()
    assert s.register_hall(
        hall_id="h1", name="Hall", capacity=0,
        prestige=50,
    ) is False


def test_register_hall_bad_prestige():
    s = PlayerConcertHallSystem()
    assert s.register_hall(
        hall_id="h1", name="Hall", capacity=100,
        prestige=200,
    ) is False


def test_book_concert_happy():
    s = PlayerConcertHallSystem()
    _hall(s)
    cid = _book(s)
    assert cid is not None


def test_book_unknown_hall_blocked():
    s = PlayerConcertHallSystem()
    assert s.book_concert(
        hall_id="ghost", performer_id="naji",
        performer_skill=70, setlist_size=10,
        ticket_price_gil=100, scheduled_day=10,
    ) is None


def test_book_invalid_skill():
    s = PlayerConcertHallSystem()
    _hall(s)
    assert s.book_concert(
        hall_id="bastok_hall", performer_id="naji",
        performer_skill=0, setlist_size=10,
        ticket_price_gil=100, scheduled_day=10,
    ) is None


def test_book_double_booking_blocked():
    s = PlayerConcertHallSystem()
    _hall(s)
    _book(s)
    second = s.book_concert(
        hall_id="bastok_hall", performer_id="other",
        performer_skill=70, setlist_size=10,
        ticket_price_gil=100, scheduled_day=10,
    )
    assert second is None


def test_book_different_day_ok():
    s = PlayerConcertHallSystem()
    _hall(s)
    _book(s)
    second = s.book_concert(
        hall_id="bastok_hall", performer_id="other",
        performer_skill=70, setlist_size=10,
        ticket_price_gil=100, scheduled_day=11,
    )
    assert second is not None


def test_open_sales_happy():
    s = PlayerConcertHallSystem()
    _hall(s)
    cid = _book(s)
    assert s.open_sales(concert_id=cid) is True


def test_open_sales_double_blocked():
    s = PlayerConcertHallSystem()
    _hall(s)
    cid = _book(s)
    s.open_sales(concert_id=cid)
    assert s.open_sales(concert_id=cid) is False


def test_buy_ticket_happy():
    s = PlayerConcertHallSystem()
    _hall(s)
    cid = _book(s)
    s.open_sales(concert_id=cid)
    tid = s.buy_ticket(
        concert_id=cid, buyer_id="bob",
    )
    assert tid is not None


def test_buy_ticket_before_sales_blocked():
    s = PlayerConcertHallSystem()
    _hall(s)
    cid = _book(s)
    assert s.buy_ticket(
        concert_id=cid, buyer_id="bob",
    ) is None


def test_buy_ticket_performer_blocked():
    s = PlayerConcertHallSystem()
    _hall(s)
    cid = _book(s)
    s.open_sales(concert_id=cid)
    assert s.buy_ticket(
        concert_id=cid, buyer_id="naji",
    ) is None


def test_buy_ticket_capacity_cap():
    s = PlayerConcertHallSystem()
    s.register_hall(
        hall_id="tiny", name="Tiny", capacity=2,
        prestige=10,
    )
    cid = s.book_concert(
        hall_id="tiny", performer_id="x",
        performer_skill=50, setlist_size=5,
        ticket_price_gil=10, scheduled_day=10,
    )
    s.open_sales(concert_id=cid)
    s.buy_ticket(concert_id=cid, buyer_id="a")
    s.buy_ticket(concert_id=cid, buyer_id="b")
    assert s.buy_ticket(
        concert_id=cid, buyer_id="c",
    ) is None


def test_revenue_accumulates():
    s = PlayerConcertHallSystem()
    _hall(s)
    cid = _book(s)
    s.open_sales(concert_id=cid)
    s.buy_ticket(concert_id=cid, buyer_id="a")
    s.buy_ticket(concert_id=cid, buyer_id="b")
    s.buy_ticket(concert_id=cid, buyer_id="c")
    c = s.concert(concert_id=cid)
    assert c.revenue_gil == 300
    assert c.tickets_sold == 3


def test_perform_happy():
    s = PlayerConcertHallSystem()
    _hall(s)
    cid = _book(s)
    s.open_sales(concert_id=cid)
    s.buy_ticket(concert_id=cid, buyer_id="a")
    score = s.perform(concert_id=cid, seed=42)
    assert score is not None
    assert score > 0


def test_perform_before_sales_blocked():
    s = PlayerConcertHallSystem()
    _hall(s)
    cid = _book(s)
    assert s.perform(concert_id=cid, seed=42) is None


def test_perform_settles_state():
    s = PlayerConcertHallSystem()
    _hall(s)
    cid = _book(s)
    s.open_sales(concert_id=cid)
    s.perform(concert_id=cid, seed=42)
    c = s.concert(concert_id=cid)
    assert c.state == ConcertState.PERFORMED
    assert c.performance_score > 0


def test_perform_fame_scales_with_audience():
    s = PlayerConcertHallSystem()
    _hall(s)
    cid_full = _book(s)
    s.open_sales(concert_id=cid_full)
    for i in range(50):
        s.buy_ticket(
            concert_id=cid_full, buyer_id=f"f_{i}",
        )
    s.perform(concert_id=cid_full, seed=42)
    full = s.concert(concert_id=cid_full)

    s.register_hall(
        hall_id="h2", name="H2", capacity=100,
        prestige=50,
    )
    cid_empty = s.book_concert(
        hall_id="h2", performer_id="naji",
        performer_skill=70, setlist_size=10,
        ticket_price_gil=100, scheduled_day=20,
    )
    s.open_sales(concert_id=cid_empty)
    s.perform(concert_id=cid_empty, seed=42)
    empty = s.concert(concert_id=cid_empty)
    assert full.fame_earned > empty.fame_earned


def test_cancel_happy():
    s = PlayerConcertHallSystem()
    _hall(s)
    cid = _book(s)
    s.open_sales(concert_id=cid)
    s.buy_ticket(concert_id=cid, buyer_id="a")
    s.buy_ticket(concert_id=cid, buyer_id="b")
    refund = s.cancel(concert_id=cid)
    # 200 gil revenue, 50% refund = 100
    assert refund == 100


def test_cancel_after_perform_blocked():
    s = PlayerConcertHallSystem()
    _hall(s)
    cid = _book(s)
    s.open_sales(concert_id=cid)
    s.perform(concert_id=cid, seed=42)
    assert s.cancel(concert_id=cid) is None


def test_tickets_listed():
    s = PlayerConcertHallSystem()
    _hall(s)
    cid = _book(s)
    s.open_sales(concert_id=cid)
    s.buy_ticket(concert_id=cid, buyer_id="a")
    s.buy_ticket(concert_id=cid, buyer_id="b")
    assert len(s.tickets(concert_id=cid)) == 2


def test_concert_unknown():
    s = PlayerConcertHallSystem()
    assert s.concert(concert_id="ghost") is None


def test_hall_unknown():
    s = PlayerConcertHallSystem()
    assert s.hall(hall_id="ghost") is None


def test_enum_count():
    assert len(list(ConcertState)) == 4
