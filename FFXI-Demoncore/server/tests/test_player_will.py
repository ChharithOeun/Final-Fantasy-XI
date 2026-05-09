"""Tests for player_will."""
from __future__ import annotations

from server.player_will import (
    PlayerWillSystem, WillState,
)


def test_draft_happy():
    s = PlayerWillSystem()
    assert s.draft(
        testator_id="bob", residue_heir="cara",
        drafted_day=10,
    ) is not None


def test_draft_self_residue_blocked():
    s = PlayerWillSystem()
    assert s.draft(
        testator_id="bob", residue_heir="bob",
        drafted_day=10,
    ) is None


def test_draft_blank_residue():
    s = PlayerWillSystem()
    assert s.draft(
        testator_id="bob", residue_heir="",
        drafted_day=10,
    ) is None


def test_draft_dup_active_blocked():
    s = PlayerWillSystem()
    s.draft(
        testator_id="bob", residue_heir="cara",
        drafted_day=10,
    )
    assert s.draft(
        testator_id="bob", residue_heir="dave",
        drafted_day=11,
    ) is None


def test_add_bequest():
    s = PlayerWillSystem()
    wid = s.draft(
        testator_id="bob", residue_heir="cara",
        drafted_day=10,
    )
    assert s.add_bequest(
        will_id=wid, item_id="excalibur",
        heir_id="dave",
    ) is True


def test_add_bequest_to_self_blocked():
    s = PlayerWillSystem()
    wid = s.draft(
        testator_id="bob", residue_heir="cara",
        drafted_day=10,
    )
    assert s.add_bequest(
        will_id=wid, item_id="x", heir_id="bob",
    ) is False


def test_add_bequest_dup_item_blocked():
    s = PlayerWillSystem()
    wid = s.draft(
        testator_id="bob", residue_heir="cara",
        drafted_day=10,
    )
    s.add_bequest(
        will_id=wid, item_id="x", heir_id="dave",
    )
    assert s.add_bequest(
        will_id=wid, item_id="x", heir_id="ed",
    ) is False


def test_add_bequest_after_seal_blocked():
    s = PlayerWillSystem()
    wid = s.draft(
        testator_id="bob", residue_heir="cara",
        drafted_day=10,
    )
    s.seal(will_id=wid, now_day=11)
    assert s.add_bequest(
        will_id=wid, item_id="x", heir_id="dave",
    ) is False


def test_remove_bequest():
    s = PlayerWillSystem()
    wid = s.draft(
        testator_id="bob", residue_heir="cara",
        drafted_day=10,
    )
    s.add_bequest(
        will_id=wid, item_id="x", heir_id="dave",
    )
    assert s.remove_bequest(
        will_id=wid, item_id="x",
    ) is True


def test_remove_unknown_bequest():
    s = PlayerWillSystem()
    wid = s.draft(
        testator_id="bob", residue_heir="cara",
        drafted_day=10,
    )
    assert s.remove_bequest(
        will_id=wid, item_id="ghost",
    ) is False


def test_seal():
    s = PlayerWillSystem()
    wid = s.draft(
        testator_id="bob", residue_heir="cara",
        drafted_day=10,
    )
    assert s.seal(will_id=wid, now_day=11) is True


def test_seal_double_blocked():
    s = PlayerWillSystem()
    wid = s.draft(
        testator_id="bob", residue_heir="cara",
        drafted_day=10,
    )
    s.seal(will_id=wid, now_day=11)
    assert s.seal(will_id=wid, now_day=12) is False


def test_unseal():
    s = PlayerWillSystem()
    wid = s.draft(
        testator_id="bob", residue_heir="cara",
        drafted_day=10,
    )
    s.seal(will_id=wid, now_day=11)
    assert s.unseal(will_id=wid) is True


def test_unseal_draft_blocked():
    s = PlayerWillSystem()
    wid = s.draft(
        testator_id="bob", residue_heir="cara",
        drafted_day=10,
    )
    assert s.unseal(will_id=wid) is False


def test_revoke():
    s = PlayerWillSystem()
    wid = s.draft(
        testator_id="bob", residue_heir="cara",
        drafted_day=10,
    )
    assert s.revoke(
        will_id=wid, now_day=20,
    ) is True


def test_revoke_clears_active_slot():
    s = PlayerWillSystem()
    wid = s.draft(
        testator_id="bob", residue_heir="cara",
        drafted_day=10,
    )
    s.revoke(will_id=wid, now_day=20)
    new_wid = s.draft(
        testator_id="bob", residue_heir="dave",
        drafted_day=21,
    )
    assert new_wid is not None


def test_execute_named_bequests():
    s = PlayerWillSystem()
    wid = s.draft(
        testator_id="bob", residue_heir="cara",
        drafted_day=10,
    )
    s.add_bequest(
        will_id=wid, item_id="excalibur",
        heir_id="dave",
    )
    s.add_bequest(
        will_id=wid, item_id="ring_of_x",
        heir_id="dave",
    )
    s.seal(will_id=wid, now_day=11)
    distribution = s.execute(
        testator_id="bob", now_day=100,
        owned_items=["excalibur", "ring_of_x",
                     "potion", "elixir"],
    )
    assert sorted(distribution["dave"]) == [
        "excalibur", "ring_of_x",
    ]
    # Residue goes to cara
    assert sorted(distribution["cara"]) == [
        "elixir", "potion",
    ]


def test_execute_drops_unowned_named():
    s = PlayerWillSystem()
    wid = s.draft(
        testator_id="bob", residue_heir="cara",
        drafted_day=10,
    )
    s.add_bequest(
        will_id=wid, item_id="excalibur",
        heir_id="dave",
    )
    s.seal(will_id=wid, now_day=11)
    distribution = s.execute(
        testator_id="bob", now_day=100,
        owned_items=["potion"],
    )
    # excalibur not owned -> nothing for dave
    assert "dave" not in distribution
    assert distribution["cara"] == ["potion"]


def test_execute_unsealed_blocked():
    s = PlayerWillSystem()
    s.draft(
        testator_id="bob", residue_heir="cara",
        drafted_day=10,
    )
    distribution = s.execute(
        testator_id="bob", now_day=100,
        owned_items=["x"],
    )
    assert distribution is None


def test_execute_no_will():
    s = PlayerWillSystem()
    distribution = s.execute(
        testator_id="bob", now_day=100,
        owned_items=["x"],
    )
    assert distribution is None


def test_execute_state_changes_to_executed():
    s = PlayerWillSystem()
    wid = s.draft(
        testator_id="bob", residue_heir="cara",
        drafted_day=10,
    )
    s.seal(will_id=wid, now_day=11)
    s.execute(
        testator_id="bob", now_day=100,
        owned_items=["x"],
    )
    assert s.will(
        will_id=wid,
    ).state == WillState.EXECUTED


def test_active_will():
    s = PlayerWillSystem()
    wid = s.draft(
        testator_id="bob", residue_heir="cara",
        drafted_day=10,
    )
    assert s.active_will(
        testator_id="bob",
    ).will_id == wid


def test_active_will_after_execute_none():
    s = PlayerWillSystem()
    wid = s.draft(
        testator_id="bob", residue_heir="cara",
        drafted_day=10,
    )
    s.seal(will_id=wid, now_day=11)
    s.execute(
        testator_id="bob", now_day=100,
        owned_items=[],
    )
    assert s.active_will(
        testator_id="bob",
    ) is None


def test_history_for():
    s = PlayerWillSystem()
    wid_a = s.draft(
        testator_id="bob", residue_heir="cara",
        drafted_day=10,
    )
    s.revoke(will_id=wid_a, now_day=20)
    s.draft(
        testator_id="bob", residue_heir="dave",
        drafted_day=21,
    )
    out = s.history_for(testator_id="bob")
    assert len(out) == 2


def test_will_unknown():
    s = PlayerWillSystem()
    assert s.will(will_id="ghost") is None


def test_enum_count():
    assert len(list(WillState)) == 4
