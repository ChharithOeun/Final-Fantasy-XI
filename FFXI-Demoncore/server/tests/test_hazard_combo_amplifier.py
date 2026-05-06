"""Tests for hazard_combo_amplifier."""
from __future__ import annotations

from server.hazard_combo_amplifier import (
    Combo, HazardComboAmplifier, HazardTag,
)


def test_default_combos_loaded():
    h = HazardComboAmplifier()
    ids = {c.combo_id for c in h.all_combos()}
    assert "steam_explosion" in ids
    assert "conduction_chain" in ids


def test_register_custom_combo():
    h = HazardComboAmplifier()
    ok = h.register_combo(Combo(
        combo_id="custom1", when_present=(HazardTag.OIL_SLICK,),
        label="Slip!", per_target_damage=100,
    ))
    assert ok is True


def test_register_dup_blocked():
    h = HazardComboAmplifier()
    assert h.register_combo(Combo(
        combo_id="steam_explosion",
        when_present=(HazardTag.BURNING,),
        label="x", per_target_damage=10,
    )) is False


def test_register_empty_tags_blocked():
    h = HazardComboAmplifier()
    assert h.register_combo(Combo(
        combo_id="x", when_present=(),
        label="x", per_target_damage=10,
    )) is False


def test_register_negative_damage_blocked():
    h = HazardComboAmplifier()
    assert h.register_combo(Combo(
        combo_id="x", when_present=(HazardTag.BURNING,),
        label="x", per_target_damage=-1,
    )) is False


def test_set_player_tags():
    h = HazardComboAmplifier()
    h.set_player_tags(
        player_id="alice", tags=[HazardTag.BURNING, HazardTag.SOAKED],
    )
    assert HazardTag.BURNING in h.tags(player_id="alice")


def test_add_tag():
    h = HazardComboAmplifier()
    assert h.add_tag(player_id="alice", tag=HazardTag.BURNING) is True
    assert HazardTag.BURNING in h.tags(player_id="alice")


def test_add_dup_tag_blocked():
    h = HazardComboAmplifier()
    h.add_tag(player_id="alice", tag=HazardTag.BURNING)
    assert h.add_tag(player_id="alice", tag=HazardTag.BURNING) is False


def test_remove_tag():
    h = HazardComboAmplifier()
    h.add_tag(player_id="alice", tag=HazardTag.BURNING)
    assert h.remove_tag(player_id="alice", tag=HazardTag.BURNING) is True
    assert HazardTag.BURNING not in h.tags(player_id="alice")


def test_steam_explosion_fires():
    h = HazardComboAmplifier()
    h.set_player_tags(
        player_id="alice", tags=[HazardTag.BURNING, HazardTag.SOAKED],
    )
    out = h.check(
        player_id="alice", nearby_player_ids=["bob", "carol"],
        now_seconds=10,
    )
    assert len(out) == 1
    assert out[0].combo_id == "steam_explosion"
    assert "alice" in out[0].affected_player_ids
    assert "bob" in out[0].affected_player_ids
    assert out[0].damage_per_target == 600
    assert out[0].status_id == "scalded"


def test_combo_doesnt_fire_with_partial_tags():
    h = HazardComboAmplifier()
    h.set_player_tags(player_id="alice", tags=[HazardTag.BURNING])
    out = h.check(
        player_id="alice", nearby_player_ids=[], now_seconds=10,
    )
    assert out == ()


def test_combo_cooldown_blocks_repeat():
    h = HazardComboAmplifier()
    h.set_player_tags(
        player_id="alice", tags=[HazardTag.BURNING, HazardTag.SOAKED],
    )
    first = h.check(player_id="alice", now_seconds=10)
    assert len(first) == 1
    second = h.check(player_id="alice", now_seconds=12)
    assert second == ()
    later = h.check(player_id="alice", now_seconds=20)
    assert len(later) == 1


def test_conduction_chain_radius():
    h = HazardComboAmplifier()
    h.set_player_tags(
        player_id="alice",
        tags=[HazardTag.CHARGED, HazardTag.METAL_GROUND],
    )
    out = h.check(
        player_id="alice", nearby_player_ids=["bob", "carol", "dave"],
        now_seconds=10,
    )
    assert len(out) == 1
    assert out[0].combo_id == "conduction_chain"
    assert out[0].damage_per_target == 900
    # all 4 affected (alice + 3 nearby)
    assert len(out[0].affected_player_ids) == 4


def test_oil_inferno_combo():
    h = HazardComboAmplifier()
    h.set_player_tags(
        player_id="alice", tags=[HazardTag.OIL_SLICK, HazardTag.BURNING],
    )
    out = h.check(player_id="alice", now_seconds=10)
    assert any(r.combo_id == "oil_inferno" for r in out)


def test_multiple_combos_can_fire_same_check():
    h = HazardComboAmplifier()
    h.set_player_tags(
        player_id="alice",
        tags=[
            HazardTag.BURNING, HazardTag.SOAKED,
            HazardTag.OIL_SLICK,
        ],
    )
    out = h.check(player_id="alice", now_seconds=10)
    combo_ids = {r.combo_id for r in out}
    # both steam_explosion and oil_inferno match
    assert "steam_explosion" in combo_ids
    assert "oil_inferno" in combo_ids


def test_unknown_player_returns_empty():
    h = HazardComboAmplifier()
    assert h.check(player_id="ghost", now_seconds=10) == ()


def test_blank_player_blocked():
    h = HazardComboAmplifier()
    assert h.add_tag(player_id="", tag=HazardTag.BURNING) is False


def test_clear_tags_drops_all():
    h = HazardComboAmplifier()
    h.set_player_tags(
        player_id="alice", tags=[HazardTag.BURNING, HazardTag.SOAKED],
    )
    h.clear_tags(player_id="alice")
    assert h.check(player_id="alice", now_seconds=10) == ()


def test_nearby_self_dedup():
    """If the triggering player appears in nearby_ids, dedup."""
    h = HazardComboAmplifier()
    h.set_player_tags(
        player_id="alice", tags=[HazardTag.BURNING, HazardTag.SOAKED],
    )
    out = h.check(
        player_id="alice", nearby_player_ids=["alice", "bob"],
        now_seconds=10,
    )
    # alice listed once
    assert out[0].affected_player_ids.count("alice") == 1


def test_all_combos_count():
    h = HazardComboAmplifier()
    assert len(h.all_combos()) >= 5
