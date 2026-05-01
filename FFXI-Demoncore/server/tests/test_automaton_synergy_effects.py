"""Tests for the EffectInstance packager."""
from __future__ import annotations

from server.automaton_synergy import (
    build_effect_instance,
    compute_modified_ability,
    get_synergy,
)


def _build(
    ability_id: str,
    *,
    overdrive: bool = False,
    fired: int = 1000,
    next_avail: int = 1900,
):
    a = get_synergy(ability_id)
    mod = compute_modified_ability(a, overdrive_active=overdrive)
    return build_effect_instance(
        modified=mod,
        master_id="alice",
        fired_at_tick=fired,
        next_available_tick=next_avail,
    )


def test_effect_instance_carries_metadata():
    inst = _build("death_spikes")
    assert inst.ability_id == "death_spikes"
    assert inst.master_id == "alice"
    assert inst.fired_at_tick == 1000


def test_effect_instance_expires_at_tick_set_from_duration():
    inst = _build("death_spikes")
    # death_spikes duration 30s base -> expires at 1030
    assert inst.expires_at_tick == 1030


def test_effect_instance_expires_extended_under_overdrive():
    inst = _build("death_spikes", overdrive=True)
    # 30 * 5 = 150
    assert inst.expires_at_tick == 1150
    assert inst.overdrive_active is True
    assert inst.effectiveness_scalar == 5.0


def test_instant_effect_instance_is_marked_instant():
    """aoe_stoneskin has duration 0."""
    inst = _build("aoe_stoneskin")
    assert inst.is_instant is True
    assert inst.expires_at_tick == inst.fired_at_tick


def test_payload_scaled_under_overdrive():
    """Death Spikes spike_damage_pct base is 8 -> 40 under Overdrive."""
    inst_off = _build("death_spikes", overdrive=False)
    inst_on = _build("death_spikes", overdrive=True)
    payload_off = inst_off.payload_dict()
    payload_on = inst_on.payload_dict()
    assert payload_off["spike_damage_pct"] == 8.0
    assert payload_on["spike_damage_pct"] == 40.0


def test_payload_non_numeric_keys_unchanged_under_overdrive():
    """spike_trigger is a string ('on_attack_received') — must not
    get scaled."""
    inst = _build("death_spikes", overdrive=True)
    p = inst.payload_dict()
    assert p["spike_trigger"] == "on_attack_received"


def test_payload_boolean_keys_unchanged_under_overdrive():
    """trigger_on_apply on aoe_stoneskin is True — never gets scaled
    even if it were named like a scalable key."""
    inst = _build("aoe_stoneskin", overdrive=True)
    p = inst.payload_dict()
    assert p["trigger_on_apply"] is True


def test_effect_instance_aoe_radius_unchanged_under_overdrive():
    inst_off = _build("aoe_reraise_1", overdrive=False)
    inst_on = _build("aoe_reraise_1", overdrive=True)
    assert inst_off.aoe_radius_yalms == inst_on.aoe_radius_yalms == 18.0


def test_effect_instance_is_active_at_predicate_during_window():
    inst = _build("death_spikes")    # fired 1000, expires 1030
    check = inst.is_active_at
    assert check(1000) is True
    assert check(1015) is True
    assert check(1029) is True


def test_effect_instance_is_active_at_predicate_outside_window():
    inst = _build("death_spikes")
    check = inst.is_active_at
    assert check(999) is False
    assert check(1030) is False        # exclusive at expiry
    assert check(2000) is False


def test_instant_effect_active_only_at_fired_tick():
    inst = _build("aoe_stoneskin")     # duration 0 -> is_instant
    check = inst.is_active_at
    assert check(inst.fired_at_tick) is True
    assert check(inst.fired_at_tick + 1) is False


def test_effect_instance_carries_next_available_tick():
    inst = _build("death_spikes", next_avail=5000)
    assert inst.next_available_tick == 5000
