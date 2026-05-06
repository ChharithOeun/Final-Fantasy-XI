"""Tests for lore hint registry."""
from __future__ import annotations

from server.lore_hint_registry import (
    HintLocation,
    LoreHint,
    LoreHintRegistry,
)


def _poster_hint():
    return LoreHint(
        hint_id="h_poster_01", puzzle_piece_id="p_kill_order_alpha",
        location=HintLocation.POSTER,
        zone_id="mermaid_city_bar",
        text="WANTED: the Marauder. Bring his head before the captain.",
        required_msq_chapter=2, required_side_quests=5,
        subtlety=7,
    )


def _npc_hint():
    return LoreHint(
        hint_id="h_npc_01", puzzle_piece_id="p_double_mb",
        location=HintLocation.NPC_DIALOGUE,
        zone_id="bastok_markets",
        text="Two bursts? My grandfather said the tide-hag fears the second.",
        required_msq_chapter=4, required_side_quests=10,
        npc_id="old_fisherman",
        subtlety=8,
    )


def _cutscene_hint():
    return LoreHint(
        hint_id="h_cs_01", puzzle_piece_id="p_pet_priority",
        location=HintLocation.CUTSCENE_BACKGROUND,
        zone_id="lower_jeuno",
        text="(behind the council) ...kill both pets fast or one will rage...",
        cutscene_id="cs_jeuno_council_03",
        subtlety=9,
    )


def test_register_poster_hint():
    r = LoreHintRegistry()
    assert r.register(_poster_hint()) is True
    assert r.hint_count() == 1


def test_register_blank_hint_id_blocked():
    r = LoreHintRegistry()
    bad = LoreHint(
        hint_id="", puzzle_piece_id="x",
        location=HintLocation.POSTER, zone_id="z", text="t",
    )
    assert r.register(bad) is False


def test_register_dup_blocked():
    r = LoreHintRegistry()
    r.register(_poster_hint())
    assert r.register(_poster_hint()) is False


def test_register_blank_zone_blocked():
    r = LoreHintRegistry()
    bad = LoreHint(
        hint_id="h1", puzzle_piece_id="p", location=HintLocation.POSTER,
        zone_id="", text="t",
    )
    assert r.register(bad) is False


def test_register_blank_text_blocked():
    r = LoreHintRegistry()
    bad = LoreHint(
        hint_id="h1", puzzle_piece_id="p", location=HintLocation.POSTER,
        zone_id="z", text="",
    )
    assert r.register(bad) is False


def test_npc_dialogue_requires_npc_id():
    r = LoreHintRegistry()
    bad = LoreHint(
        hint_id="h1", puzzle_piece_id="p",
        location=HintLocation.NPC_DIALOGUE,
        zone_id="z", text="t",
    )
    assert r.register(bad) is False


def test_register_npc_hint_happy():
    r = LoreHintRegistry()
    assert r.register(_npc_hint()) is True


def test_cutscene_requires_cutscene_id():
    r = LoreHintRegistry()
    bad = LoreHint(
        hint_id="h1", puzzle_piece_id="p",
        location=HintLocation.CUTSCENE_BACKGROUND,
        zone_id="z", text="t",
    )
    assert r.register(bad) is False


def test_register_cutscene_hint_happy():
    r = LoreHintRegistry()
    assert r.register(_cutscene_hint()) is True


def test_subtlety_out_of_range_blocked():
    r = LoreHintRegistry()
    bad = LoreHint(
        hint_id="h1", puzzle_piece_id="p", location=HintLocation.POSTER,
        zone_id="z", text="t", subtlety=11,
    )
    assert r.register(bad) is False


def test_get_returns_hint():
    r = LoreHintRegistry()
    r.register(_poster_hint())
    found = r.get(hint_id="h_poster_01")
    assert found is not None
    assert found.puzzle_piece_id == "p_kill_order_alpha"


def test_get_unknown_returns_none():
    r = LoreHintRegistry()
    assert r.get(hint_id="ghost") is None


def test_for_puzzle_piece_groups_redundant_hints():
    r = LoreHintRegistry()
    r.register(_poster_hint())
    # second hint targeting the same piece
    r.register(LoreHint(
        hint_id="h_poster_02", puzzle_piece_id="p_kill_order_alpha",
        location=HintLocation.AMBIENT_BARK,
        zone_id="docks",
        text="The Marauder. Always the Marauder first, my pa said.",
        npc_id="dock_drunk",
    ))
    out = r.for_puzzle_piece(puzzle_piece_id="p_kill_order_alpha")
    assert len(out) == 2


def test_for_zone():
    r = LoreHintRegistry()
    r.register(_poster_hint())
    r.register(_npc_hint())
    out = r.for_zone(zone_id="mermaid_city_bar")
    assert len(out) == 1
    assert out[0].hint_id == "h_poster_01"


def test_all_hints():
    r = LoreHintRegistry()
    r.register(_poster_hint())
    r.register(_npc_hint())
    r.register(_cutscene_hint())
    assert len(r.all_hints()) == 3


def test_item_description_requires_item_id():
    r = LoreHintRegistry()
    bad = LoreHint(
        hint_id="h_item", puzzle_piece_id="p",
        location=HintLocation.ITEM_DESCRIPTION,
        zone_id="any", text="t",
    )
    assert r.register(bad) is False


def test_item_description_happy():
    r = LoreHintRegistry()
    ok = LoreHint(
        hint_id="h_item", puzzle_piece_id="p_kill_order_bravo",
        location=HintLocation.ITEM_DESCRIPTION,
        zone_id="anywhere",
        text="(carved on the hilt) ...the Captain falls before the Witch...",
        item_id="rusted_sahagin_dagger",
    )
    assert r.register(ok) is True
