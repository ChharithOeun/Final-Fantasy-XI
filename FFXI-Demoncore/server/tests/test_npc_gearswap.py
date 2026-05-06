"""Tests for npc_gearswap."""
from __future__ import annotations

from server.npc_gearswap import (
    GearSet, GearTrigger, NpcGearswapRegistry,
)


def _setup():
    r = NpcGearswapRegistry()
    r.define_profile(
        npc_id="maat",
        sets={
            GearTrigger.IDLE: GearSet(
                set_name="idle",
                items={"body": "maat_robe", "head": "maat_hat"},
            ),
            GearTrigger.ENGAGED: GearSet(
                set_name="hundred_fists_tp",
                items={"main": "spharai", "body": "destroyers"},
            ),
            GearTrigger.WEAPONSKILL: GearSet(
                set_name="ws_burst",
                items={"main": "spharai", "ring1": "rajas"},
            ),
        },
    )
    return r


def test_define_happy():
    r = _setup()
    assert r.total_profiles() == 1


def test_define_blank_npc_blocked():
    r = NpcGearswapRegistry()
    out = r.define_profile(
        npc_id="",
        sets={
            GearTrigger.IDLE: GearSet(
                set_name="x", items={"main": "y"},
            ),
        },
    )
    assert out is False


def test_define_no_sets_blocked():
    r = NpcGearswapRegistry()
    out = r.define_profile(npc_id="x", sets={})
    assert out is False


def test_define_empty_set_blocked():
    r = NpcGearswapRegistry()
    out = r.define_profile(
        npc_id="x",
        sets={
            GearTrigger.IDLE: GearSet(
                set_name="empty", items={},
            ),
        },
    )
    assert out is False


def test_define_duplicate_blocked():
    r = _setup()
    out = r.define_profile(
        npc_id="maat",
        sets={
            GearTrigger.IDLE: GearSet(
                set_name="x", items={"main": "y"},
            ),
        },
    )
    assert out is False


def test_swap_returns_set():
    r = _setup()
    out = r.swap_for(
        npc_id="maat", trigger=GearTrigger.ENGAGED,
    )
    assert out is not None
    assert out.set_name == "hundred_fists_tp"


def test_swap_unknown_npc():
    r = _setup()
    out = r.swap_for(
        npc_id="ghost", trigger=GearTrigger.IDLE,
    )
    assert out is None


def test_swap_undefined_trigger():
    r = _setup()
    # MIDCAST is not defined for maat
    out = r.swap_for(
        npc_id="maat", trigger=GearTrigger.MIDCAST,
    )
    assert out is None


def test_swap_undefined_does_not_change_current():
    r = _setup()
    r.swap_for(npc_id="maat", trigger=GearTrigger.ENGAGED)
    # try to swap to MIDCAST (not defined) — current stays ENGAGED
    r.swap_for(npc_id="maat", trigger=GearTrigger.MIDCAST)
    cur = r.current_set(npc_id="maat")
    assert cur.set_name == "hundred_fists_tp"


def test_current_set_before_swap_none():
    r = _setup()
    cur = r.current_set(npc_id="maat")
    assert cur is None


def test_current_set_unknown_npc():
    r = _setup()
    cur = r.current_set(npc_id="ghost")
    assert cur is None


def test_swap_then_current_matches():
    r = _setup()
    r.swap_for(npc_id="maat", trigger=GearTrigger.WEAPONSKILL)
    cur = r.current_set(npc_id="maat")
    assert cur.set_name == "ws_burst"


def test_has_set_for_known():
    r = _setup()
    assert r.has_set_for(
        npc_id="maat", trigger=GearTrigger.IDLE,
    ) is True


def test_has_set_for_unknown_trigger():
    r = _setup()
    assert r.has_set_for(
        npc_id="maat", trigger=GearTrigger.MIDCAST,
    ) is False


def test_has_set_for_unknown_npc():
    r = NpcGearswapRegistry()
    assert r.has_set_for(
        npc_id="ghost", trigger=GearTrigger.IDLE,
    ) is False


def test_reset_clears_current():
    r = _setup()
    r.swap_for(npc_id="maat", trigger=GearTrigger.ENGAGED)
    assert r.reset(npc_id="maat") is True
    cur = r.current_set(npc_id="maat")
    assert cur is None


def test_reset_unknown_npc():
    r = NpcGearswapRegistry()
    assert r.reset(npc_id="ghost") is False


def test_six_gear_triggers():
    assert len(list(GearTrigger)) == 6


def test_swap_returns_correct_items():
    r = _setup()
    out = r.swap_for(
        npc_id="maat", trigger=GearTrigger.IDLE,
    )
    assert out.items["body"] == "maat_robe"


def test_total_profiles_grows():
    r = _setup()
    r.define_profile(
        npc_id="prishe",
        sets={
            GearTrigger.IDLE: GearSet(
                set_name="x", items={"main": "y"},
            ),
        },
    )
    assert r.total_profiles() == 2
