"""Tests for SP Overdrive 5x multiplier."""
from __future__ import annotations

from server.automaton_synergy import (
    OVERDRIVE_MULTIPLIER,
    compute_modified_ability,
    get_synergy,
    scale_effect_value,
)


def test_overdrive_multiplier_is_five():
    """User spec: '5x the duration and effectiveness'."""
    assert OVERDRIVE_MULTIPLIER == 5


def test_no_overdrive_returns_unscaled_duration():
    death_spikes = get_synergy("death_spikes")
    mod = compute_modified_ability(death_spikes, overdrive_active=False)
    assert mod.duration_seconds == death_spikes.duration_seconds
    assert mod.effectiveness_scalar == 1.0
    assert mod.overdrive_active is False


def test_overdrive_scales_duration_by_five():
    death_spikes = get_synergy("death_spikes")
    mod = compute_modified_ability(death_spikes, overdrive_active=True)
    # Death Spikes is 30s base -> 150s under Overdrive.
    assert mod.duration_seconds == 30 * OVERDRIVE_MULTIPLIER
    assert mod.duration_seconds == 150


def test_overdrive_effectiveness_scalar_is_five():
    death_spikes = get_synergy("death_spikes")
    mod = compute_modified_ability(death_spikes, overdrive_active=True)
    assert mod.effectiveness_scalar == 5.0


def test_overdrive_does_not_scale_cooldown():
    """Overdrive bumps the *effect* but doesn't shorten the lockout.
    Death Spikes cooldown stays at 15 min."""
    death_spikes = get_synergy("death_spikes")
    mod = compute_modified_ability(death_spikes, overdrive_active=True)
    assert mod.cooldown_seconds == death_spikes.cooldown_seconds
    assert mod.cooldown_seconds == 900


def test_overdrive_does_not_scale_aoe_radius():
    """Geometry isn't bigger under overdrive; only damage and
    duration are."""
    a = get_synergy("aoe_reraise_1")
    mod = compute_modified_ability(a, overdrive_active=True)
    assert mod.aoe_radius_yalms == a.aoe_radius_yalms


def test_overdrive_name_decorated():
    """Modified ability under Overdrive labels with suffix for
    UI display."""
    a = get_synergy("death_spikes")
    mod_off = compute_modified_ability(a, overdrive_active=False)
    mod_on = compute_modified_ability(a, overdrive_active=True)
    assert mod_off.name == a.name
    assert "Overdrive" in mod_on.name


def test_instant_ability_under_overdrive_stays_instant():
    """An instant ability has duration_seconds=0; multiplying by 5
    is still 0 — these abilities fire once and don't extend."""
    aoe_stoneskin = get_synergy("aoe_stoneskin")
    assert aoe_stoneskin.duration_seconds == 0
    mod = compute_modified_ability(
        aoe_stoneskin, overdrive_active=True,
    )
    assert mod.duration_seconds == 0


def test_long_duration_ability_scales_correctly():
    """DNC unlock is 5 min base -> 25 min under Overdrive."""
    dnc = get_synergy("dnc_unlock")
    assert dnc.duration_seconds == 300
    mod = compute_modified_ability(dnc, overdrive_active=True)
    assert mod.duration_seconds == 1500    # 25 minutes


def test_scale_effect_value_no_overdrive_is_identity():
    a = get_synergy("death_spikes")
    mod = compute_modified_ability(a, overdrive_active=False)
    assert scale_effect_value(8.0, mod) == 8.0


def test_scale_effect_value_overdrive_multiplies_by_five():
    a = get_synergy("death_spikes")
    mod = compute_modified_ability(a, overdrive_active=True)
    assert scale_effect_value(8.0, mod) == 40.0


def test_scale_effect_value_with_int_input_returns_float():
    a = get_synergy("aoe_stoneskin")
    mod = compute_modified_ability(a, overdrive_active=True)
    result = scale_effect_value(100, mod)
    assert isinstance(result, float)
    assert result == 500.0


def test_modified_ability_id_proxies_base():
    """ModifiedAbility exposes base ability_id for caller convenience."""
    a = get_synergy("death_spikes")
    mod = compute_modified_ability(a, overdrive_active=True)
    assert mod.ability_id == "death_spikes"
