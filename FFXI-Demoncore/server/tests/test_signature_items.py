"""Tests for signature_items."""
from __future__ import annotations

from server.signature_items import (
    SignatureItems, Tier,
)


def _forge_hq3(s, item_id="i1", maker="cid",
               template="pellucid_sword", day=10):
    return s.forge(
        item_id=item_id, template_id=template,
        maker_id=maker, tier=Tier.HQ3, forged_day=day,
    )


def test_forge_happy():
    s = SignatureItems()
    assert _forge_hq3(s) is True


def test_forge_blank_item_blocked():
    s = SignatureItems()
    assert s.forge(
        item_id="", template_id="x", maker_id="c",
        tier=Tier.HQ1, forged_day=10,
    ) is False


def test_forge_blank_maker_blocked():
    s = SignatureItems()
    assert s.forge(
        item_id="i1", template_id="x", maker_id="",
        tier=Tier.HQ1, forged_day=10,
    ) is False


def test_forge_nq_not_signed():
    s = SignatureItems()
    assert s.forge(
        item_id="i1", template_id="x", maker_id="c",
        tier=Tier.NQ, forged_day=10,
    ) is False


def test_forge_negative_day_blocked():
    s = SignatureItems()
    assert s.forge(
        item_id="i1", template_id="x", maker_id="c",
        tier=Tier.HQ1, forged_day=-1,
    ) is False


def test_forge_dup_blocked():
    s = SignatureItems()
    _forge_hq3(s)
    assert _forge_hq3(s) is False


def test_record_trade():
    s = SignatureItems()
    _forge_hq3(s)
    assert s.record_trade(item_id="i1") is True
    assert s.item(item_id="i1").times_traded == 1


def test_record_trade_unknown():
    s = SignatureItems()
    assert s.record_trade(item_id="ghost") is False


def test_record_combat_use():
    s = SignatureItems()
    _forge_hq3(s)
    s.record_combat_use(item_id="i1")
    s.record_combat_use(item_id="i1")
    assert s.item(
        item_id="i1",
    ).times_used_in_combat == 2


def test_item_returns_full():
    s = SignatureItems()
    _forge_hq3(s)
    it = s.item(item_id="i1")
    assert it is not None
    assert it.tier == Tier.HQ3
    assert it.maker_id == "cid"


def test_item_unknown():
    s = SignatureItems()
    assert s.item(item_id="ghost") is None


def test_items_by_maker():
    s = SignatureItems()
    _forge_hq3(s, item_id="i1", maker="cid")
    _forge_hq3(s, item_id="i2", maker="cid")
    _forge_hq3(s, item_id="i3", maker="boyahda")
    out = s.items_by_maker(maker_id="cid")
    assert {it.item_id for it in out} == {"i1", "i2"}


def test_maker_fame_base():
    s = SignatureItems()
    _forge_hq3(s, item_id="i1")
    # HQ3 base = 4, no trades, no combat
    assert s.maker_fame(maker_id="cid") == 4


def test_maker_fame_masterwork_higher():
    s = SignatureItems()
    s.forge(
        item_id="mw", template_id="x", maker_id="cid",
        tier=Tier.MASTERWORK, forged_day=10,
    )
    # MASTERWORK base = 10
    assert s.maker_fame(maker_id="cid") == 10


def test_maker_fame_aggregates():
    s = SignatureItems()
    _forge_hq3(s, item_id="i1")
    _forge_hq3(s, item_id="i2")
    # 2 HQ3 items = 4 + 4 = 8
    assert s.maker_fame(maker_id="cid") == 8


def test_maker_fame_trade_multiplier():
    s = SignatureItems()
    _forge_hq3(s, item_id="i1")
    # 5 trades = 1 + (5//5) = multiplier 2
    for _ in range(5):
        s.record_trade(item_id="i1")
    # HQ3 base 4 * 2 = 8
    assert s.maker_fame(maker_id="cid") == 8


def test_maker_fame_combat_bonus():
    s = SignatureItems()
    _forge_hq3(s, item_id="i1")
    for _ in range(50):
        s.record_combat_use(item_id="i1")
    # HQ3 base 4 + (50//50)=1 bonus = 5
    assert s.maker_fame(maker_id="cid") == 5


def test_maker_fame_unknown_maker():
    s = SignatureItems()
    assert s.maker_fame(maker_id="ghost") == 0


def test_five_tiers():
    assert len(list(Tier)) == 5
