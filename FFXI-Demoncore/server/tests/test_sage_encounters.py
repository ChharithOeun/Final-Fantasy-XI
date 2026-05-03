"""Tests for sage encounters."""
from __future__ import annotations

from server.sage_encounters import (
    DEFAULT_SAGE_COOLDOWN_SECONDS,
    GiftKind,
    SageArchetype,
    SageEncounters,
)


def test_roll_in_remote_zone_succeeds():
    s = SageEncounters()
    res = s.roll_for_encounter(
        player_id="alice",
        zone_id="uleguerand_range",
        archetype=SageArchetype.ELVAAN_ASCETIC,
    )
    assert res.accepted
    assert res.sage is not None


def test_roll_in_non_remote_zone_rejected():
    s = SageEncounters()
    res = s.roll_for_encounter(
        player_id="alice",
        zone_id="bastok_markets",
        archetype=SageArchetype.ELVAAN_ASCETIC,
    )
    assert not res.accepted
    assert "remote" in res.reason


def test_force_overrides_zone_gate():
    s = SageEncounters()
    res = s.roll_for_encounter(
        player_id="alice",
        zone_id="bastok_markets",
        archetype=SageArchetype.ELVAAN_ASCETIC,
        force=True,
    )
    assert res.accepted


def test_cooldown_blocks_second_encounter():
    s = SageEncounters()
    s.roll_for_encounter(
        player_id="alice",
        zone_id="uleguerand_range",
        archetype=SageArchetype.ELVAAN_ASCETIC,
        now_seconds=0.0,
    )
    res = s.roll_for_encounter(
        player_id="alice",
        zone_id="uleguerand_range",
        archetype=SageArchetype.HUME_RECLUSE,
        now_seconds=100.0,
    )
    assert not res.accepted
    assert "cooldown" in res.reason


def test_after_cooldown_new_archetype_works():
    s = SageEncounters()
    s.roll_for_encounter(
        player_id="alice",
        zone_id="uleguerand_range",
        archetype=SageArchetype.ELVAAN_ASCETIC,
        now_seconds=0.0,
    )
    res = s.roll_for_encounter(
        player_id="alice",
        zone_id="ruaun_gardens",
        archetype=SageArchetype.HUME_RECLUSE,
        now_seconds=DEFAULT_SAGE_COOLDOWN_SECONDS + 1,
    )
    assert res.accepted


def test_already_met_archetype_blocked():
    s = SageEncounters()
    s.roll_for_encounter(
        player_id="alice",
        zone_id="uleguerand_range",
        archetype=SageArchetype.ELVAAN_ASCETIC,
        now_seconds=0.0,
    )
    res = s.roll_for_encounter(
        player_id="alice",
        zone_id="ruaun_gardens",
        archetype=SageArchetype.ELVAAN_ASCETIC,
        now_seconds=DEFAULT_SAGE_COOLDOWN_SECONDS + 1,
    )
    assert not res.accepted
    assert "already met" in res.reason


def test_different_players_independent():
    s = SageEncounters()
    res_a = s.roll_for_encounter(
        player_id="alice",
        zone_id="uleguerand_range",
        archetype=SageArchetype.ELVAAN_ASCETIC,
        now_seconds=0.0,
    )
    res_b = s.roll_for_encounter(
        player_id="bob",
        zone_id="uleguerand_range",
        archetype=SageArchetype.ELVAAN_ASCETIC,
        now_seconds=10.0,
    )
    assert res_a.accepted
    assert res_b.accepted


def test_accept_offer_returns_gift():
    s = SageEncounters()
    res = s.roll_for_encounter(
        player_id="alice",
        zone_id="uleguerand_range",
        archetype=SageArchetype.MITHRA_HERBALIST,
    )
    offer = s.accept_offer(
        player_id="alice", sage_id=res.sage.sage_id,
    )
    assert offer is not None
    assert offer.gift_kind == GiftKind.OLD_RECIPE


def test_accept_offer_wrong_player():
    s = SageEncounters()
    res = s.roll_for_encounter(
        player_id="alice",
        zone_id="uleguerand_range",
        archetype=SageArchetype.MITHRA_HERBALIST,
    )
    offer = s.accept_offer(
        player_id="bob", sage_id=res.sage.sage_id,
    )
    assert offer is None


def test_accept_offer_unknown_sage():
    s = SageEncounters()
    assert s.accept_offer(
        player_id="x", sage_id="ghost",
    ) is None


def test_accept_offer_twice_rejected():
    s = SageEncounters()
    res = s.roll_for_encounter(
        player_id="alice",
        zone_id="uleguerand_range",
        archetype=SageArchetype.MITHRA_HERBALIST,
    )
    s.accept_offer(
        player_id="alice", sage_id=res.sage.sage_id,
    )
    second = s.accept_offer(
        player_id="alice", sage_id=res.sage.sage_id,
    )
    assert second is None


def test_player_has_met_lookup():
    s = SageEncounters()
    s.roll_for_encounter(
        player_id="alice",
        zone_id="uleguerand_range",
        archetype=SageArchetype.GALKA_LOREKEEPER,
    )
    assert s.player_has_met(
        player_id="alice",
        archetype=SageArchetype.GALKA_LOREKEEPER,
    )
    assert not s.player_has_met(
        player_id="alice",
        archetype=SageArchetype.HUME_RECLUSE,
    )


def test_each_archetype_has_unique_offer():
    s = SageEncounters()
    for i, archetype in enumerate(SageArchetype):
        res = s.roll_for_encounter(
            player_id=f"p_{i}",
            zone_id="uleguerand_range",
            archetype=archetype,
        )
        offer = s.accept_offer(
            player_id=f"p_{i}", sage_id=res.sage.sage_id,
        )
        assert offer.gift_kind in {
            GiftKind.CRYPTIC_HINT,
            GiftKind.ONESHOT_BUFF,
            GiftKind.OLD_RECIPE,
            GiftKind.KEY_ITEM,
            GiftKind.NM_DIRECTION,
        }


def test_offer_carries_zone_payload():
    s = SageEncounters()
    res = s.roll_for_encounter(
        player_id="alice",
        zone_id="ruaun_gardens",
        archetype=SageArchetype.HUME_RECLUSE,
    )
    offer = s.accept_offer(
        player_id="alice", sage_id=res.sage.sage_id,
    )
    assert offer.payload["zone_id"] == "ruaun_gardens"


def test_total_sages_spawned():
    s = SageEncounters()
    s.roll_for_encounter(
        player_id="a",
        zone_id="uleguerand_range",
        archetype=SageArchetype.ELVAAN_ASCETIC,
    )
    s.roll_for_encounter(
        player_id="b",
        zone_id="uleguerand_range",
        archetype=SageArchetype.ELVAAN_ASCETIC,
    )
    assert s.total_sages_spawned() == 2


def test_force_bypasses_archetype_gate():
    s = SageEncounters()
    s.roll_for_encounter(
        player_id="alice",
        zone_id="uleguerand_range",
        archetype=SageArchetype.ELVAAN_ASCETIC,
    )
    res = s.roll_for_encounter(
        player_id="alice",
        zone_id="uleguerand_range",
        archetype=SageArchetype.ELVAAN_ASCETIC,
        force=True,
    )
    assert res.accepted
