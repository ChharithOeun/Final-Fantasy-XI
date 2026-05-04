"""Tests for the beastman mail runners."""
from __future__ import annotations

from server.beastman_mail_runners import (
    BeastmanMailRunners,
    ParcelState,
)


def test_send_basic():
    m = BeastmanMailRunners()
    res = m.send(
        sender_id="kraw", recipient_id="zlar",
        cargo_item_id="prime_feather",
        gil_amount=500,
        note_text="for the egg feast",
        now_seconds=0,
    )
    assert res.accepted
    assert res.arrives_at == 3600


def test_send_to_self_rejected():
    m = BeastmanMailRunners()
    res = m.send(
        sender_id="kraw", recipient_id="kraw",
        cargo_item_id="x",
        now_seconds=0,
    )
    assert not res.accepted


def test_send_empty_parcel_rejected():
    m = BeastmanMailRunners()
    res = m.send(
        sender_id="kraw", recipient_id="zlar",
        now_seconds=0,
    )
    assert not res.accepted


def test_send_negative_gil_rejected():
    m = BeastmanMailRunners()
    res = m.send(
        sender_id="kraw", recipient_id="zlar",
        gil_amount=-1,
        now_seconds=0,
    )
    assert not res.accepted


def test_send_gil_above_cap_rejected():
    m = BeastmanMailRunners()
    res = m.send(
        sender_id="kraw", recipient_id="zlar",
        gil_amount=10_000_000,
        now_seconds=0,
    )
    assert not res.accepted


def test_send_long_note_rejected():
    m = BeastmanMailRunners()
    res = m.send(
        sender_id="kraw", recipient_id="zlar",
        note_text="x" * 100,
        now_seconds=0,
    )
    assert not res.accepted


def test_send_inbox_full():
    m = BeastmanMailRunners()
    for i in range(8):
        m.send(
            sender_id=f"s{i}", recipient_id="zlar",
            note_text="hi", now_seconds=0,
        )
    res = m.send(
        sender_id="overflow", recipient_id="zlar",
        note_text="hi", now_seconds=0,
    )
    assert not res.accepted


def test_arrive_at_eta():
    m = BeastmanMailRunners()
    res = m.send(
        sender_id="kraw", recipient_id="zlar",
        gil_amount=100, now_seconds=0,
    )
    assert m.arrive(parcel_id=res.parcel_id, now_seconds=3600)


def test_arrive_too_early():
    m = BeastmanMailRunners()
    res = m.send(
        sender_id="kraw", recipient_id="zlar",
        gil_amount=100, now_seconds=0,
    )
    assert not m.arrive(parcel_id=res.parcel_id, now_seconds=10)


def test_arrive_unknown_parcel():
    m = BeastmanMailRunners()
    assert not m.arrive(parcel_id=999, now_seconds=0)


def test_claim_basic():
    m = BeastmanMailRunners()
    res = m.send(
        sender_id="kraw", recipient_id="zlar",
        cargo_item_id="phantom_jay",
        gil_amount=200,
        now_seconds=0,
    )
    cl = m.claim(
        parcel_id=res.parcel_id,
        recipient_id="zlar",
        now_seconds=3600,
    )
    assert cl.accepted
    assert cl.cargo_item_id == "phantom_jay"
    assert cl.gil_amount == 200


def test_claim_not_yet_delivered():
    m = BeastmanMailRunners()
    res = m.send(
        sender_id="kraw", recipient_id="zlar",
        gil_amount=100, now_seconds=0,
    )
    cl = m.claim(
        parcel_id=res.parcel_id,
        recipient_id="zlar",
        now_seconds=10,
    )
    assert not cl.accepted


def test_claim_wrong_recipient():
    m = BeastmanMailRunners()
    res = m.send(
        sender_id="kraw", recipient_id="zlar",
        gil_amount=100, now_seconds=0,
    )
    cl = m.claim(
        parcel_id=res.parcel_id,
        recipient_id="bob",
        now_seconds=3600,
    )
    assert not cl.accepted


def test_claim_unknown():
    m = BeastmanMailRunners()
    cl = m.claim(
        parcel_id=999,
        recipient_id="zlar",
        now_seconds=0,
    )
    assert not cl.accepted


def test_reject_basic():
    m = BeastmanMailRunners()
    res = m.send(
        sender_id="kraw", recipient_id="zlar",
        gil_amount=100, now_seconds=0,
    )
    assert m.reject(
        parcel_id=res.parcel_id, recipient_id="zlar",
    )


def test_reject_then_claim_blocked():
    m = BeastmanMailRunners()
    res = m.send(
        sender_id="kraw", recipient_id="zlar",
        gil_amount=100, now_seconds=0,
    )
    m.reject(
        parcel_id=res.parcel_id, recipient_id="zlar",
    )
    cl = m.claim(
        parcel_id=res.parcel_id,
        recipient_id="zlar",
        now_seconds=9999,
    )
    assert not cl.accepted


def test_reject_wrong_recipient():
    m = BeastmanMailRunners()
    res = m.send(
        sender_id="kraw", recipient_id="zlar",
        gil_amount=100, now_seconds=0,
    )
    assert not m.reject(
        parcel_id=res.parcel_id, recipient_id="bob",
    )


def test_inbox_query():
    m = BeastmanMailRunners()
    m.send(
        sender_id="kraw", recipient_id="zlar",
        gil_amount=100, now_seconds=0,
    )
    m.send(
        sender_id="alice", recipient_id="zlar",
        cargo_item_id="x", now_seconds=0,
    )
    inbox = m.inbox(player_id="zlar")
    assert len(inbox) == 2


def test_set_delivery_lag():
    m = BeastmanMailRunners()
    m.set_delivery_lag(seconds=60)
    res = m.send(
        sender_id="kraw", recipient_id="zlar",
        gil_amount=100, now_seconds=0,
    )
    assert res.arrives_at == 60


def test_set_delivery_lag_negative_rejected():
    m = BeastmanMailRunners()
    assert not m.set_delivery_lag(seconds=-10)


def test_claim_lazy_arrives():
    m = BeastmanMailRunners()
    res = m.send(
        sender_id="kraw", recipient_id="zlar",
        gil_amount=100, now_seconds=0,
    )
    # Skip explicit arrive(); claim should auto-deliver
    cl = m.claim(
        parcel_id=res.parcel_id,
        recipient_id="zlar",
        now_seconds=4000,
    )
    assert cl.accepted
