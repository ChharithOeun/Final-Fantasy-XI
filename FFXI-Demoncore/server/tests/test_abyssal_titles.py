"""Tests for abyssal titles."""
from __future__ import annotations

from server.abyssal_titles import AbyssalTitles, MAX_RANK


def test_register_happy():
    t = AbyssalTitles()
    assert t.register_title(
        title_id="kraken_slayer", name="Kraken-Slayer",
        rank=2, stat_bonus={"str": 3},
    ) is True


def test_register_blank():
    t = AbyssalTitles()
    assert t.register_title(
        title_id="", name="X", rank=1,
    ) is False


def test_register_bad_rank():
    t = AbyssalTitles()
    assert t.register_title(
        title_id="x", name="X", rank=0,
    ) is False
    assert t.register_title(
        title_id="x", name="X", rank=MAX_RANK + 1,
    ) is False


def test_register_double_blocked():
    t = AbyssalTitles()
    t.register_title(title_id="k", name="K", rank=1)
    assert t.register_title(title_id="k", name="K2", rank=2) is False


def test_grant_happy():
    t = AbyssalTitles()
    t.register_title(title_id="k", name="K", rank=2)
    assert t.grant(player_id="p1", title_id="k") is True


def test_grant_unknown_title():
    t = AbyssalTitles()
    assert t.grant(player_id="p1", title_id="ghost") is False


def test_grant_blank_player():
    t = AbyssalTitles()
    t.register_title(title_id="k", name="K", rank=2)
    assert t.grant(player_id="", title_id="k") is False


def test_grant_double_blocked():
    t = AbyssalTitles()
    t.register_title(title_id="k", name="K", rank=2)
    t.grant(player_id="p1", title_id="k")
    assert t.grant(player_id="p1", title_id="k") is False


def test_grant_with_prereq_blocked():
    t = AbyssalTitles()
    t.register_title(title_id="a", name="A", rank=1)
    t.register_title(
        title_id="b", name="B", rank=3, requires=["a"],
    )
    assert t.grant(player_id="p1", title_id="b") is False


def test_grant_with_prereq_passes():
    t = AbyssalTitles()
    t.register_title(title_id="a", name="A", rank=1)
    t.register_title(
        title_id="b", name="B", rank=3, requires=["a"],
    )
    t.grant(player_id="p1", title_id="a")
    assert t.grant(player_id="p1", title_id="b") is True


def test_equip_happy():
    t = AbyssalTitles()
    t.register_title(title_id="k", name="K", rank=2)
    t.grant(player_id="p1", title_id="k")
    assert t.equip(player_id="p1", title_id="k") is True


def test_equip_unheld_blocked():
    t = AbyssalTitles()
    t.register_title(title_id="k", name="K", rank=2)
    assert t.equip(player_id="p1", title_id="k") is False


def test_unequip():
    t = AbyssalTitles()
    t.register_title(title_id="k", name="K", rank=2)
    t.grant(player_id="p1", title_id="k")
    t.equip(player_id="p1", title_id="k")
    assert t.unequip(player_id="p1") is True


def test_unequip_unset():
    t = AbyssalTitles()
    assert t.unequip(player_id="p1") is False


def test_equipped_for_returns_title():
    t = AbyssalTitles()
    t.register_title(title_id="k", name="K", rank=2)
    t.grant(player_id="p1", title_id="k")
    t.equip(player_id="p1", title_id="k")
    eq = t.equipped_for(player_id="p1")
    assert eq is not None
    assert eq.name == "K"


def test_equipped_for_none_default():
    t = AbyssalTitles()
    assert t.equipped_for(player_id="ghost") is None


def test_titles_held_sorted_rank_desc():
    t = AbyssalTitles()
    t.register_title(title_id="low", name="L", rank=1)
    t.register_title(title_id="high", name="H", rank=4)
    t.grant(player_id="p1", title_id="low")
    t.grant(player_id="p1", title_id="high")
    out = t.titles_held(player_id="p1")
    assert out[0].title_id == "high"
    assert out[1].title_id == "low"


def test_stat_bonuses_only_from_equipped():
    t = AbyssalTitles()
    t.register_title(
        title_id="k", name="K", rank=2,
        stat_bonus={"str": 3},
    )
    t.register_title(
        title_id="m", name="M", rank=2,
        stat_bonus={"int": 5},
    )
    t.grant(player_id="p1", title_id="k")
    t.grant(player_id="p1", title_id="m")
    # equipped K
    t.equip(player_id="p1", title_id="k")
    bonuses = t.stat_bonuses_for(player_id="p1")
    assert bonuses == {"str": 3}
    # swap to M
    t.equip(player_id="p1", title_id="m")
    assert t.stat_bonuses_for(player_id="p1") == {"int": 5}


def test_stat_bonuses_empty_when_unequipped():
    t = AbyssalTitles()
    assert t.stat_bonuses_for(player_id="p1") == {}
