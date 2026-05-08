"""Tests for commission_board."""
from __future__ import annotations

from server.commission_board import (
    Commission, CommissionBoard, State,
)


def _comm(cid="c1", buyer="bob", payment=80000,
          deposit=10000, refund_pct=60,
          posted=10, deliver=17,
          template="pellucid_sword", tier="hq3"):
    return Commission(
        commission_id=cid, buyer_id=buyer,
        template_id=template, desired_tier=tier,
        payment_gil=payment, deposit_gil=deposit,
        refundable_pct=refund_pct,
        posted_day=posted, deliver_by_day=deliver,
    )


def test_post_happy():
    b = CommissionBoard()
    assert b.post(_comm()) is True


def test_post_blank_id_blocked():
    b = CommissionBoard()
    bad = _comm(cid="")
    assert b.post(bad) is False


def test_post_zero_payment_blocked():
    b = CommissionBoard()
    bad = _comm(payment=0)
    assert b.post(bad) is False


def test_post_negative_deposit_blocked():
    b = CommissionBoard()
    bad = _comm(deposit=-1)
    assert b.post(bad) is False


def test_post_deposit_above_payment_blocked():
    b = CommissionBoard()
    bad = _comm(payment=50000, deposit=80000)
    assert b.post(bad) is False


def test_post_invalid_refund_pct_blocked():
    b = CommissionBoard()
    bad = _comm(refund_pct=150)
    assert b.post(bad) is False


def test_post_bad_dates_blocked():
    b = CommissionBoard()
    bad = _comm(posted=20, deliver=15)
    assert b.post(bad) is False


def test_post_dup_blocked():
    b = CommissionBoard()
    b.post(_comm())
    assert b.post(_comm()) is False


def test_accept_happy():
    b = CommissionBoard()
    b.post(_comm())
    assert b.accept(
        commission_id="c1", crafter_id="cara",
        now_day=11,
    ) is True
    assert b.state(commission_id="c1") == State.ACCEPTED


def test_accept_self_blocked():
    """Buyer can't be their own crafter."""
    b = CommissionBoard()
    b.post(_comm())
    assert b.accept(
        commission_id="c1", crafter_id="bob",
        now_day=11,
    ) is False


def test_accept_past_deadline_blocked():
    b = CommissionBoard()
    b.post(_comm(deliver=17))
    assert b.accept(
        commission_id="c1", crafter_id="cara",
        now_day=18,
    ) is False


def test_accept_already_accepted_blocked():
    b = CommissionBoard()
    b.post(_comm())
    b.accept(
        commission_id="c1", crafter_id="cara",
        now_day=11,
    )
    assert b.accept(
        commission_id="c1", crafter_id="dave",
        now_day=12,
    ) is False


def test_deliver():
    b = CommissionBoard()
    b.post(_comm())
    b.accept(
        commission_id="c1", crafter_id="cara",
        now_day=11,
    )
    assert b.deliver(
        commission_id="c1", by_crafter_id="cara",
        item_id="i999", now_day=14,
    ) is True
    assert b.state(commission_id="c1") == State.DELIVERED


def test_deliver_wrong_crafter_blocked():
    b = CommissionBoard()
    b.post(_comm())
    b.accept(
        commission_id="c1", crafter_id="cara",
        now_day=11,
    )
    assert b.deliver(
        commission_id="c1", by_crafter_id="dave",
        item_id="i999", now_day=14,
    ) is False


def test_deliver_after_deadline_blocked():
    b = CommissionBoard()
    b.post(_comm(deliver=17))
    b.accept(
        commission_id="c1", crafter_id="cara",
        now_day=11,
    )
    assert b.deliver(
        commission_id="c1", by_crafter_id="cara",
        item_id="i999", now_day=18,
    ) is False


def test_claim_delivery():
    b = CommissionBoard()
    b.post(_comm(payment=80000))
    b.accept(
        commission_id="c1", crafter_id="cara",
        now_day=11,
    )
    b.deliver(
        commission_id="c1", by_crafter_id="cara",
        item_id="i999", now_day=14,
    )
    paid = b.claim_delivery(
        commission_id="c1", by_buyer_id="bob",
    )
    assert paid == 80000
    assert b.state(commission_id="c1") == State.COMPLETED


def test_claim_wrong_buyer_blocked():
    b = CommissionBoard()
    b.post(_comm())
    b.accept(
        commission_id="c1", crafter_id="cara",
        now_day=11,
    )
    b.deliver(
        commission_id="c1", by_crafter_id="cara",
        item_id="i999", now_day=14,
    )
    assert b.claim_delivery(
        commission_id="c1", by_buyer_id="impostor",
    ) is None


def test_cancel_open_full_refund():
    b = CommissionBoard()
    b.post(_comm(payment=80000))
    refunded = b.cancel_open(
        commission_id="c1", by_buyer_id="bob",
    )
    assert refunded == 80000
    assert b.state(commission_id="c1") == State.CANCELED


def test_cancel_open_after_accepted_blocked():
    b = CommissionBoard()
    b.post(_comm())
    b.accept(
        commission_id="c1", crafter_id="cara",
        now_day=11,
    )
    assert b.cancel_open(
        commission_id="c1", by_buyer_id="bob",
    ) is None


def test_tick_expires_open():
    b = CommissionBoard()
    b.post(_comm(deliver=17))
    expired = b.tick(now_day=20)
    assert "c1" in expired
    assert b.state(commission_id="c1") == State.EXPIRED


def test_tick_expires_accepted():
    b = CommissionBoard()
    b.post(_comm(deliver=17))
    b.accept(
        commission_id="c1", crafter_id="cara",
        now_day=11,
    )
    expired = b.tick(now_day=20)
    assert "c1" in expired


def test_tick_doesnt_expire_completed():
    b = CommissionBoard()
    b.post(_comm())
    b.accept(
        commission_id="c1", crafter_id="cara",
        now_day=11,
    )
    b.deliver(
        commission_id="c1", by_crafter_id="cara",
        item_id="i999", now_day=14,
    )
    b.claim_delivery(
        commission_id="c1", by_buyer_id="bob",
    )
    expired = b.tick(now_day=999)
    assert "c1" not in expired


def test_open_listings_excludes_accepted():
    b = CommissionBoard()
    b.post(_comm("a"))
    b.post(_comm("b", buyer="other"))
    b.accept(
        commission_id="b", crafter_id="cara",
        now_day=11,
    )
    out = b.open_listings()
    assert {c.commission_id for c in out} == {"a"}


def test_expired_refund_split():
    b = CommissionBoard()
    b.post(_comm(payment=10000, refund_pct=60))
    b.tick(now_day=999)
    # 10000 * 60/100 = 6000 to buyer; 4000 kept
    refund = b.expired_refund(commission_id="c1")
    assert refund == (6000, 4000)


def test_expired_refund_unknown_blocked():
    b = CommissionBoard()
    assert b.expired_refund(
        commission_id="ghost",
    ) is None


def test_expired_refund_not_expired_blocked():
    b = CommissionBoard()
    b.post(_comm())
    assert b.expired_refund(
        commission_id="c1",
    ) is None


def test_six_states():
    assert len(list(State)) == 6
