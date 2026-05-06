"""Tests for gear_autocomplete."""
from __future__ import annotations

from server.gear_autocomplete import (
    GearAutocomplete, MatchMode,
)
from server.gear_slot_filter import (
    GearItem, GearSlotFilter, Slot,
)


def _setup():
    f = GearSlotFilter()
    for iid, name, slots in [
        ("murgleis", "Murgleis", (Slot.MAIN,)),
        ("murasame", "Murasame", (Slot.MAIN,)),
        ("mursaat", "Mursaat Mantle", (Slot.BACK,)),
        ("naegling", "Naegling", (Slot.MAIN,)),
        ("daybreak", "Daybreak", (Slot.SUB,)),
        ("demers_degen", "Demers. Degen +1", (Slot.SUB,)),
        ("crocea_mors", "Crocea Mors", (Slot.MAIN, Slot.SUB)),
    ]:
        f.register_item(item=GearItem(
            item_id=iid, display_name=name,
            slot_compatibility=slots,
        ))
    a = GearAutocomplete(_filter=f)
    return f, a


def test_prefix_match_basic():
    _, a = _setup()
    out = a.suggest(slot=Slot.MAIN, query="Mur",
                    mode=MatchMode.PREFIX)
    names = [s.display_name for s in out]
    # both Murgleis and Murasame match in MAIN slot
    assert "Murgleis" in names
    assert "Murasame" in names
    # Mursaat Mantle is BACK slot, must NOT appear
    assert "Mursaat Mantle" not in names


def test_prefix_no_match():
    _, a = _setup()
    out = a.suggest(slot=Slot.MAIN, query="Zzz",
                    mode=MatchMode.PREFIX)
    assert out == []


def test_contains_match():
    _, a = _setup()
    out = a.suggest(slot=Slot.SUB, query="degen",
                    mode=MatchMode.CONTAINS)
    names = [s.display_name for s in out]
    assert "Demers. Degen +1" in names


def test_fuzzy_match():
    _, a = _setup()
    # 'demers' typo "demos" should still find Demers. Degen
    out = a.suggest(slot=Slot.SUB, query="demos",
                    mode=MatchMode.FUZZY)
    names = [s.display_name for s in out]
    assert "Demers. Degen +1" in names


def test_empty_query_returns_alphabetic():
    _, a = _setup()
    out = a.suggest(slot=Slot.MAIN, query="")
    names = [s.display_name for s in out]
    # alphabetic: Crocea Mors, Murasame, Murgleis, Naegling
    assert names[0] == "Crocea Mors"


def test_empty_query_zero_limit():
    _, a = _setup()
    out = a.suggest(slot=Slot.MAIN, query="", limit=0)
    assert out == []


def test_negative_limit_returns_empty():
    _, a = _setup()
    out = a.suggest(slot=Slot.MAIN, query="Mur", limit=-1)
    assert out == []


def test_limit_caps_results():
    _, a = _setup()
    out = a.suggest(slot=Slot.MAIN, query="", limit=2)
    assert len(out) == 2


def test_record_pick_happy():
    f, a = _setup()
    out = a.record_pick(
        player_id="alice", slot=Slot.MAIN, item_id="murgleis",
    )
    assert out is True
    assert a.recent_for_slot(
        player_id="alice", slot=Slot.MAIN,
    ) == ["murgleis"]


def test_record_pick_invalid_slot():
    _, a = _setup()
    out = a.record_pick(
        player_id="alice", slot=Slot.SUB, item_id="murgleis",
    )
    # Murgleis is MAIN-only; SUB pick refused
    assert out is False


def test_record_pick_blank_player():
    _, a = _setup()
    out = a.record_pick(
        player_id="", slot=Slot.MAIN, item_id="murgleis",
    )
    assert out is False


def test_record_pick_blank_item():
    _, a = _setup()
    out = a.record_pick(
        player_id="alice", slot=Slot.MAIN, item_id="",
    )
    assert out is False


def test_recent_lifo():
    _, a = _setup()
    a.record_pick(
        player_id="alice", slot=Slot.MAIN, item_id="murgleis",
    )
    a.record_pick(
        player_id="alice", slot=Slot.MAIN, item_id="naegling",
    )
    out = a.recent_for_slot(player_id="alice", slot=Slot.MAIN)
    # most recent first
    assert out == ["naegling", "murgleis"]


def test_recent_dedups():
    _, a = _setup()
    a.record_pick(
        player_id="alice", slot=Slot.MAIN, item_id="murgleis",
    )
    a.record_pick(
        player_id="alice", slot=Slot.MAIN, item_id="naegling",
    )
    a.record_pick(
        player_id="alice", slot=Slot.MAIN, item_id="murgleis",
    )
    out = a.recent_for_slot(player_id="alice", slot=Slot.MAIN)
    assert out == ["murgleis", "naegling"]


def test_recent_caps_at_max():
    f, a = _setup()
    # add 6 items (max is 5)
    for iid, name in [
        ("a1", "Aaa1"), ("a2", "Aaa2"), ("a3", "Aaa3"),
        ("a4", "Aaa4"), ("a5", "Aaa5"), ("a6", "Aaa6"),
    ]:
        f.register_item(item=GearItem(
            item_id=iid, display_name=name,
            slot_compatibility=(Slot.MAIN,),
        ))
        a.record_pick(
            player_id="alice", slot=Slot.MAIN, item_id=iid,
        )
    out = a.recent_for_slot(player_id="alice", slot=Slot.MAIN)
    assert len(out) == 5
    # most recent is a6, oldest pruned was a1
    assert out[0] == "a6"
    assert "a1" not in out


def test_empty_query_promotes_recents():
    _, a = _setup()
    a.record_pick(
        player_id="alice", slot=Slot.MAIN, item_id="naegling",
    )
    out = a.suggest(
        slot=Slot.MAIN, query="",
        owned_only=False, owner_id="alice",
    )
    # naegling first (recent), then alphabetic
    assert out[0].item_id == "naegling"


def test_owned_only_filters():
    f, a = _setup()
    f.grant_to_owner(owner_id="alice", item_id="murgleis")
    out = a.suggest(
        slot=Slot.MAIN, query="", owned_only=True,
        owner_id="alice",
    )
    names = [s.display_name for s in out]
    assert names == ["Murgleis"]


def test_clear_recent_for_slot():
    _, a = _setup()
    a.record_pick(
        player_id="alice", slot=Slot.MAIN, item_id="murgleis",
    )
    a.record_pick(
        player_id="alice", slot=Slot.SUB, item_id="daybreak",
    )
    out = a.clear_recent(player_id="alice", slot=Slot.MAIN)
    assert out == 1
    assert a.recent_for_slot(
        player_id="alice", slot=Slot.MAIN,
    ) == []
    # SUB recent still intact
    assert a.recent_for_slot(
        player_id="alice", slot=Slot.SUB,
    ) == ["daybreak"]


def test_clear_recent_all_slots():
    _, a = _setup()
    a.record_pick(
        player_id="alice", slot=Slot.MAIN, item_id="murgleis",
    )
    a.record_pick(
        player_id="alice", slot=Slot.SUB, item_id="daybreak",
    )
    out = a.clear_recent(player_id="alice")
    assert out == 2


def test_clear_recent_unknown_player():
    _, a = _setup()
    out = a.clear_recent(player_id="ghost")
    assert out == 0


def test_three_match_modes():
    assert len(list(MatchMode)) == 3
