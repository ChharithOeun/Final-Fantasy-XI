"""Tests for the synergy catalog."""
from __future__ import annotations

import pytest

from server.automaton_synergy import (
    AOE_RADIUS_PARTY_YALMS,
    DESIGNATED_FOUNDER_IDS,
    SYNERGY_CATALOG,
    EffectKind,
    Frame,
    Head,
    ManeuverElement,
    all_synergy_ids,
    check_synergy,
    get_synergy,
    synergies_for,
)


# -- catalog integrity -----------------------------------------------

def test_catalog_is_non_empty():
    assert len(SYNERGY_CATALOG) >= 25


def test_all_ability_ids_unique():
    ids = [a.ability_id for a in SYNERGY_CATALOG]
    assert len(set(ids)) == len(ids), \
        f"duplicate ids found: {[i for i in ids if ids.count(i) > 1]}"


def test_every_entry_has_filled_in_metadata():
    for a in SYNERGY_CATALOG:
        assert a.ability_id, f"empty ability_id"
        assert a.name, f"{a.ability_id} missing name"
        assert a.description, f"{a.ability_id} missing description"
        assert a.cooldown_seconds > 0, \
            f"{a.ability_id} cooldown must be positive"


def test_every_entry_has_three_total_maneuvers_required():
    """User spec: 'would require a combination of 3 maneuvers to
    trigger'. This is doctrine — pin it."""
    for a in SYNERGY_CATALOG:
        assert a.total_maneuvers_required == 3, (
            f"{a.ability_id} requires "
            f"{a.total_maneuvers_required} maneuvers, expected 3"
        )


def test_aoe_radius_party_default_is_eighteen_yalms():
    """User spec: 'AOE 18 yalms'. Verify the constant."""
    assert AOE_RADIUS_PARTY_YALMS == 18.0


def test_designated_founders_all_present_in_catalog():
    """Tha five user-pinned founders cannot disappear silently."""
    catalog_ids = {a.ability_id for a in SYNERGY_CATALOG}
    for founder_id in DESIGNATED_FOUNDER_IDS:
        assert founder_id in catalog_ids, (
            f"founder {founder_id} missing from catalog"
        )


def test_each_head_has_at_least_one_synergy():
    """Sanity: the catalog should give players a reason to try
    every head."""
    seen_heads = {a.head for a in SYNERGY_CATALOG}
    expected = set(Head) - {Head.HARLEQUIN}     # base, no-synergy OK
    assert expected.issubset(seen_heads), \
        f"missing heads: {expected - seen_heads}"


def test_each_frame_has_at_least_one_synergy():
    seen_frames = {a.frame for a in SYNERGY_CATALOG}
    expected = set(Frame) - {Frame.HARLEQUIN}
    assert expected.issubset(seen_frames), \
        f"missing frames: {expected - seen_frames}"


# -- 5 user-pinned founders -----------------------------------------

def test_founder_death_spikes():
    a = get_synergy("death_spikes")
    assert a.head == Head.SPIRITREAVER
    assert a.frame == Frame.VALOREDGE
    assert dict(a.maneuver_req) == {ManeuverElement.DARK: 3}
    assert a.duration_seconds == 30
    assert a.cooldown_seconds == 900       # 15 min


def test_founder_aoe_stoneskin():
    a = get_synergy("aoe_stoneskin")
    assert a.head == Head.RDM
    assert a.frame == Frame.VALOREDGE
    assert dict(a.maneuver_req) == {ManeuverElement.EARTH: 3}
    assert a.cooldown_seconds == 180        # 3 min
    assert a.aoe_radius_yalms == 18.0


def test_founder_aoe_reraise_1():
    a = get_synergy("aoe_reraise_1")
    assert a.head == Head.SOULSOOTHER
    assert a.frame == Frame.VALOREDGE
    assert dict(a.maneuver_req) == {ManeuverElement.LIGHT: 3}
    assert a.cooldown_seconds == 900
    assert a.aoe_radius_yalms == 18.0


def test_founder_aoe_corsair_roll_eleven():
    a = get_synergy("aoe_corsair_roll_eleven")
    assert a.head == Head.NIN
    assert a.frame == Frame.SHARPSHOT
    assert dict(a.maneuver_req) == {ManeuverElement.WATER: 3}
    assert a.duration_seconds == 180        # 3 min
    assert a.cooldown_seconds == 900        # 15 min


def test_founder_dnc_unlock_uses_mixed_elements():
    """User spec: '1 each ice, earth, water'. Defensively pin."""
    a = get_synergy("dnc_unlock")
    assert a.head == Head.VALOREDGE
    assert a.frame == Frame.NIN
    assert dict(a.maneuver_req) == {
        ManeuverElement.ICE: 1,
        ManeuverElement.EARTH: 1,
        ManeuverElement.WATER: 1,
    }
    assert a.duration_seconds == 300
    assert a.cooldown_seconds == 900
    assert a.effect_kind == EffectKind.UNLOCK_ABILITIES


# -- check_synergy lookup -------------------------------------------

def test_check_synergy_matches_three_dark_for_death_spikes():
    matched = check_synergy(
        head=Head.SPIRITREAVER, frame=Frame.VALOREDGE,
        active_maneuvers={ManeuverElement.DARK: 3},
    )
    assert matched is not None
    assert matched.ability_id == "death_spikes"


def test_check_synergy_returns_none_for_unmatched_combo():
    matched = check_synergy(
        head=Head.HARLEQUIN, frame=Frame.HARLEQUIN,
        active_maneuvers={ManeuverElement.FIRE: 3},
    )
    assert matched is None


def test_check_synergy_rejects_insufficient_maneuvers():
    """3 dark required, only 2 supplied -> no match."""
    matched = check_synergy(
        head=Head.SPIRITREAVER, frame=Frame.VALOREDGE,
        active_maneuvers={ManeuverElement.DARK: 2},
    )
    assert matched is None


def test_check_synergy_extra_maneuvers_still_match():
    """Maneuver requirement is "at least N of element X" — extra
    elements outside the requirement don't disqualify."""
    matched = check_synergy(
        head=Head.SPIRITREAVER, frame=Frame.VALOREDGE,
        active_maneuvers={
            ManeuverElement.DARK: 3,
            ManeuverElement.WIND: 2,    # bonus, doesn't matter
        },
    )
    assert matched is not None
    assert matched.ability_id == "death_spikes"


def test_check_synergy_mixed_element_requirement():
    """DNC unlock needs 1 ice + 1 earth + 1 water; supply exactly
    that and it should match."""
    matched = check_synergy(
        head=Head.VALOREDGE, frame=Frame.NIN,
        active_maneuvers={
            ManeuverElement.ICE: 1,
            ManeuverElement.EARTH: 1,
            ManeuverElement.WATER: 1,
        },
    )
    assert matched is not None
    assert matched.ability_id == "dnc_unlock"


def test_check_synergy_mixed_element_partial_match_rejected():
    """Two of three required mixed elements present -> no match."""
    matched = check_synergy(
        head=Head.VALOREDGE, frame=Frame.NIN,
        active_maneuvers={
            ManeuverElement.ICE: 1,
            ManeuverElement.EARTH: 1,
            # WATER missing
        },
    )
    assert matched is None


def test_check_synergy_wrong_head_no_match():
    """3 dark on the wrong head -> no synergy."""
    matched = check_synergy(
        head=Head.HARLEQUIN, frame=Frame.VALOREDGE,
        active_maneuvers={ManeuverElement.DARK: 3},
    )
    assert matched is None


def test_check_synergy_wrong_frame_no_match():
    matched = check_synergy(
        head=Head.SPIRITREAVER, frame=Frame.HARLEQUIN,
        active_maneuvers={ManeuverElement.DARK: 3},
    )
    assert matched is None


# -- helpers ---------------------------------------------------------

def test_synergies_for_returns_specific_pair_entries():
    pair = synergies_for(
        head=Head.SPIRITREAVER, frame=Frame.VALOREDGE,
    )
    assert "death_spikes" in {a.ability_id for a in pair}


def test_synergies_for_unknown_pair_returns_empty():
    pair = synergies_for(
        head=Head.HARLEQUIN, frame=Frame.HARLEQUIN,
    )
    assert pair == ()


def test_get_synergy_unknown_id_raises():
    with pytest.raises(KeyError):
        get_synergy("not_a_real_id")


def test_all_synergy_ids_matches_catalog_length():
    assert len(all_synergy_ids()) == len(SYNERGY_CATALOG)


def test_total_maneuvers_required_property():
    a = get_synergy("dnc_unlock")
    assert a.total_maneuvers_required == 3      # 1+1+1
    b = get_synergy("death_spikes")
    assert b.total_maneuvers_required == 3      # 3 dark


def test_maneuver_req_map_is_dict():
    a = get_synergy("death_spikes")
    assert a.maneuver_req_map == {ManeuverElement.DARK: 3}
