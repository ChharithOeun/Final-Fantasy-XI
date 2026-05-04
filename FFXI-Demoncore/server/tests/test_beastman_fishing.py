"""Tests for the beastman fishing system."""
from __future__ import annotations

from server.beastman_fishing import (
    BaitKind,
    BeastmanFishing,
    Catch,
    RodKind,
)


def _seed(f):
    f.register_spot(
        spot_id="lamia_tide",
        zone_id="lamia_cove",
        rods=(RodKind.CORAL_ROD,),
        baits=(BaitKind.KELP, BaitKind.SHADOW_LURE),
        catches=(
            Catch(item_id="moat_carp", base_chance_pct=80, skill_required=0),
            Catch(item_id="shadow_eel", base_chance_pct=20, skill_required=20),
        ),
    )


def test_register_spot():
    f = BeastmanFishing()
    _seed(f)
    assert f.total_spots() == 1


def test_register_duplicate():
    f = BeastmanFishing()
    _seed(f)
    res = f.register_spot(
        spot_id="lamia_tide",
        zone_id="x",
        rods=(RodKind.STONE_ROD,),
        baits=(BaitKind.GRUB,),
        catches=(Catch(item_id="x", base_chance_pct=50),),
    )
    assert res is None


def test_register_empty_rods():
    f = BeastmanFishing()
    res = f.register_spot(
        spot_id="bad",
        zone_id="z",
        rods=(),
        baits=(BaitKind.KELP,),
        catches=(Catch(item_id="x", base_chance_pct=50),),
    )
    assert res is None


def test_register_empty_baits():
    f = BeastmanFishing()
    res = f.register_spot(
        spot_id="bad",
        zone_id="z",
        rods=(RodKind.CORAL_ROD,),
        baits=(),
        catches=(Catch(item_id="x", base_chance_pct=50),),
    )
    assert res is None


def test_register_empty_catches():
    f = BeastmanFishing()
    res = f.register_spot(
        spot_id="bad",
        zone_id="z",
        rods=(RodKind.CORAL_ROD,),
        baits=(BaitKind.KELP,),
        catches=(),
    )
    assert res is None


def test_register_invalid_chance():
    f = BeastmanFishing()
    res = f.register_spot(
        spot_id="bad",
        zone_id="z",
        rods=(RodKind.CORAL_ROD,),
        baits=(BaitKind.KELP,),
        catches=(Catch(item_id="x", base_chance_pct=200),),
    )
    assert res is None


def test_cast_basic_catch():
    f = BeastmanFishing()
    _seed(f)
    res = f.cast(
        player_id="kraw",
        spot_id="lamia_tide",
        rod=RodKind.CORAL_ROD,
        bait=BaitKind.KELP,
        roll_pct=50,
    )
    assert res.accepted
    assert res.item_id == "moat_carp"
    assert res.new_skill == 1


def test_cast_unknown_spot():
    f = BeastmanFishing()
    res = f.cast(
        player_id="kraw",
        spot_id="ghost",
        rod=RodKind.CORAL_ROD,
        bait=BaitKind.KELP,
        roll_pct=50,
    )
    assert not res.accepted


def test_cast_wrong_rod():
    f = BeastmanFishing()
    _seed(f)
    res = f.cast(
        player_id="kraw",
        spot_id="lamia_tide",
        rod=RodKind.BONE_ROD,
        bait=BaitKind.KELP,
        roll_pct=50,
    )
    assert not res.accepted


def test_cast_wrong_bait():
    f = BeastmanFishing()
    _seed(f)
    res = f.cast(
        player_id="kraw",
        spot_id="lamia_tide",
        rod=RodKind.CORAL_ROD,
        bait=BaitKind.GRUB,
        roll_pct=50,
    )
    assert not res.accepted


def test_cast_invalid_roll():
    f = BeastmanFishing()
    _seed(f)
    res = f.cast(
        player_id="kraw",
        spot_id="lamia_tide",
        rod=RodKind.CORAL_ROD,
        bait=BaitKind.KELP,
        roll_pct=200,
    )
    assert not res.accepted


def test_cast_no_catch():
    f = BeastmanFishing()
    _seed(f)
    res = f.cast(
        player_id="kraw",
        spot_id="lamia_tide",
        rod=RodKind.CORAL_ROD,
        bait=BaitKind.KELP,
        roll_pct=99,
    )
    assert res.accepted
    assert res.item_id == ""
    assert res.new_skill == 0  # no skill gain on miss


def test_cast_skill_gated_catch():
    f = BeastmanFishing()
    _seed(f)
    # Roll 10 < 20 base for shadow_eel, but skill 0 < required 20
    # so falls back to moat_carp (80% < 50 is false, wait 10 < 80 true)
    # Actually first eligible catch in order is moat_carp at chance 80
    res = f.cast(
        player_id="kraw",
        spot_id="lamia_tide",
        rod=RodKind.CORAL_ROD,
        bait=BaitKind.KELP,
        roll_pct=10,
    )
    assert res.item_id == "moat_carp"


def test_cast_skill_unlocks_eel():
    f = BeastmanFishing()
    f.register_spot(
        spot_id="lamia_tide",
        zone_id="lamia_cove",
        rods=(RodKind.CORAL_ROD,),
        baits=(BaitKind.SHADOW_LURE,),
        catches=(
            # Eel listed first; with sufficient skill and low roll, eel wins
            Catch(item_id="shadow_eel", base_chance_pct=20, skill_required=20),
            Catch(item_id="moat_carp", base_chance_pct=80, skill_required=0),
        ),
    )
    # Manually pump skill to 25
    for _ in range(25):
        f.cast(
            player_id="kraw",
            spot_id="lamia_tide",
            rod=RodKind.CORAL_ROD,
            bait=BaitKind.SHADOW_LURE,
            roll_pct=10,
        )
    assert f.skill_for(player_id="kraw") >= 20
    res = f.cast(
        player_id="kraw",
        spot_id="lamia_tide",
        rod=RodKind.CORAL_ROD,
        bait=BaitKind.SHADOW_LURE,
        roll_pct=5,
    )
    assert res.item_id == "shadow_eel"


def test_skill_caps_at_100():
    f = BeastmanFishing()
    _seed(f)
    for _ in range(500):
        f.cast(
            player_id="kraw",
            spot_id="lamia_tide",
            rod=RodKind.CORAL_ROD,
            bait=BaitKind.KELP,
            roll_pct=10,
        )
    assert f.skill_for(player_id="kraw") == 100


def test_skill_diminish_past_70():
    f = BeastmanFishing()
    _seed(f)
    # Pump exactly to 70 with 70 catches
    for _ in range(70):
        f.cast(
            player_id="kraw",
            spot_id="lamia_tide",
            rod=RodKind.CORAL_ROD,
            bait=BaitKind.KELP,
            roll_pct=10,
        )
    assert f.skill_for(player_id="kraw") == 70
    # Now 2 more casts should not raise skill yet
    f.cast(
        player_id="kraw",
        spot_id="lamia_tide",
        rod=RodKind.CORAL_ROD,
        bait=BaitKind.KELP,
        roll_pct=10,
    )
    f.cast(
        player_id="kraw",
        spot_id="lamia_tide",
        rod=RodKind.CORAL_ROD,
        bait=BaitKind.KELP,
        roll_pct=10,
    )
    assert f.skill_for(player_id="kraw") == 70
    # Third should bump to 71
    f.cast(
        player_id="kraw",
        spot_id="lamia_tide",
        rod=RodKind.CORAL_ROD,
        bait=BaitKind.KELP,
        roll_pct=10,
    )
    assert f.skill_for(player_id="kraw") == 71


def test_skill_for_default_zero():
    f = BeastmanFishing()
    assert f.skill_for(player_id="ghost") == 0


def test_per_player_skill_isolation():
    f = BeastmanFishing()
    _seed(f)
    f.cast(
        player_id="alice",
        spot_id="lamia_tide",
        rod=RodKind.CORAL_ROD,
        bait=BaitKind.KELP,
        roll_pct=10,
    )
    assert f.skill_for(player_id="bob") == 0


def test_register_negative_skill_required():
    f = BeastmanFishing()
    res = f.register_spot(
        spot_id="bad",
        zone_id="z",
        rods=(RodKind.CORAL_ROD,),
        baits=(BaitKind.KELP,),
        catches=(Catch(item_id="x", base_chance_pct=50, skill_required=-1),),
    )
    assert res is None
