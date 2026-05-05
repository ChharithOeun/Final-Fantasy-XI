"""Tests for heretic branded."""
from __future__ import annotations

from server.heretic_branded import (
    HereticBranded,
    NPCClass,
    NPCReaction,
)


def test_default_not_branded():
    h = HereticBranded()
    assert h.is_branded(player_id="p") is False


def test_brand_via_high_taint():
    h = HereticBranded()
    h.recompute(
        player_id="p", taint_level=60, performed_pact=False,
    )
    assert h.is_branded(player_id="p") is True


def test_brand_via_pact():
    h = HereticBranded()
    h.recompute(
        player_id="p", taint_level=0, performed_pact=True,
    )
    assert h.is_branded(player_id="p") is True


def test_brand_clears_below_threshold_for_taint():
    h = HereticBranded()
    h.recompute(
        player_id="p", taint_level=70, performed_pact=False,
    )
    assert h.is_branded(player_id="p") is True
    # drop taint to below clear threshold
    h.recompute(
        player_id="p", taint_level=20, performed_pact=False,
    )
    assert h.is_branded(player_id="p") is False


def test_brand_persists_in_sticky_band():
    h = HereticBranded()
    h.recompute(
        player_id="p", taint_level=70, performed_pact=False,
    )
    # 30..59 is the sticky band — still branded
    h.recompute(
        player_id="p", taint_level=40, performed_pact=False,
    )
    assert h.is_branded(player_id="p") is True


def test_pact_brand_does_not_clear_with_taint_drop():
    h = HereticBranded()
    h.recompute(
        player_id="p", taint_level=80, performed_pact=True,
    )
    # taint cleansed all the way
    h.recompute(
        player_id="p", taint_level=0, performed_pact=True,
    )
    assert h.is_branded(player_id="p") is True


def test_npc_healer_refuses():
    h = HereticBranded()
    h.recompute(
        player_id="p", taint_level=80, performed_pact=False,
    )
    assert h.npc_reaction(
        player_id="p", npc_class=NPCClass.HEALER,
    ) == NPCReaction.REFUSE_HEAL


def test_npc_merchant_refuses():
    h = HereticBranded()
    h.recompute(
        player_id="p", taint_level=80, performed_pact=False,
    )
    assert h.npc_reaction(
        player_id="p", npc_class=NPCClass.MERCHANT,
    ) == NPCReaction.REFUSE_SALE


def test_npc_guard_aggros():
    h = HereticBranded()
    h.recompute(
        player_id="p", taint_level=80, performed_pact=False,
    )
    assert h.npc_reaction(
        player_id="p", npc_class=NPCClass.GUARD,
    ) == NPCReaction.AGGRO


def test_unbranded_normal_reaction():
    h = HereticBranded()
    assert h.npc_reaction(
        player_id="p", npc_class=NPCClass.HEALER,
    ) == NPCReaction.NORMAL


def test_safe_zone_suspends_reaction():
    h = HereticBranded()
    h.recompute(
        player_id="p", taint_level=80, performed_pact=False,
    )
    assert h.npc_reaction(
        player_id="p",
        npc_class=NPCClass.GUARD,
        zone_id="norg_port",
    ) == NPCReaction.NORMAL


def test_unsafe_zone_keeps_reaction():
    h = HereticBranded()
    h.recompute(
        player_id="p", taint_level=80, performed_pact=False,
    )
    assert h.npc_reaction(
        player_id="p",
        npc_class=NPCClass.GUARD,
        zone_id="bastok_markets",
    ) == NPCReaction.AGGRO


def test_council_neutral_always_normal():
    h = HereticBranded()
    h.recompute(
        player_id="p", taint_level=80, performed_pact=False,
    )
    assert h.npc_reaction(
        player_id="p", npc_class=NPCClass.COUNCIL_NEUTRAL,
    ) == NPCReaction.NORMAL


def test_is_safe_zone_lookup():
    assert HereticBranded.is_safe_zone(zone_id="norg_port") is True
    assert HereticBranded.is_safe_zone(zone_id="bastok_port") is False
    assert HereticBranded.is_safe_zone(zone_id="drowned_void") is True


def test_commoner_flees():
    h = HereticBranded()
    h.recompute(
        player_id="p", taint_level=80, performed_pact=False,
    )
    assert h.npc_reaction(
        player_id="p", npc_class=NPCClass.COMMONER,
    ) == NPCReaction.FLEE
