"""Tests for activate_synergy — full activation pipeline."""
from __future__ import annotations

from server.automaton_synergy import (
    ActivationStatus,
    CooldownTracker,
    Frame,
    Head,
    ManeuverElement,
    activate_synergy,
)


# -- happy path -----------------------------------------------------

def test_activate_death_spikes_first_time_succeeds():
    cd = CooldownTracker()
    res = activate_synergy(
        master_id="alice",
        head=Head.SPIRITREAVER, frame=Frame.VALOREDGE,
        active_maneuvers={ManeuverElement.DARK: 3},
        cooldowns=cd,
        now_tick=1000,
    )
    assert res.accepted is True
    assert res.status == ActivationStatus.SUCCESS
    assert res.matched_ability.ability_id == "death_spikes"
    assert res.instance is not None
    assert res.instance.fired_at_tick == 1000


def test_successful_activation_stamps_cooldown():
    cd = CooldownTracker()
    activate_synergy(
        master_id="alice",
        head=Head.SPIRITREAVER, frame=Frame.VALOREDGE,
        active_maneuvers={ManeuverElement.DARK: 3},
        cooldowns=cd,
        now_tick=1000,
    )
    # 15min cooldown -> next available 1900.
    assert cd.next_available(
        master_id="alice", ability_id="death_spikes",
    ) == 1000 + 900


def test_activation_under_overdrive_extends_duration():
    cd = CooldownTracker()
    res = activate_synergy(
        master_id="alice",
        head=Head.SPIRITREAVER, frame=Frame.VALOREDGE,
        active_maneuvers={ManeuverElement.DARK: 3},
        cooldowns=cd,
        now_tick=1000,
        overdrive_active=True,
    )
    assert res.accepted
    assert res.instance.overdrive_active is True
    # 30s base * 5 = 150s under overdrive
    assert res.instance.expires_at_tick == 1000 + 150


# -- failure: no synergy ------------------------------------------

def test_activate_invalid_combo_no_synergy():
    cd = CooldownTracker()
    res = activate_synergy(
        master_id="alice",
        head=Head.HARLEQUIN, frame=Frame.HARLEQUIN,
        active_maneuvers={ManeuverElement.FIRE: 3},
        cooldowns=cd,
        now_tick=1000,
    )
    assert res.accepted is False
    assert res.status == ActivationStatus.NO_SYNERGY
    assert res.instance is None


def test_activate_insufficient_maneuvers_no_synergy():
    cd = CooldownTracker()
    res = activate_synergy(
        master_id="alice",
        head=Head.SPIRITREAVER, frame=Frame.VALOREDGE,
        active_maneuvers={ManeuverElement.DARK: 2},  # need 3
        cooldowns=cd,
        now_tick=1000,
    )
    assert res.status == ActivationStatus.NO_SYNERGY


# -- failure: cooldown ---------------------------------------------

def test_second_activation_during_cooldown_rejects():
    cd = CooldownTracker()
    activate_synergy(
        master_id="alice",
        head=Head.SPIRITREAVER, frame=Frame.VALOREDGE,
        active_maneuvers={ManeuverElement.DARK: 3},
        cooldowns=cd,
        now_tick=1000,
    )
    # 5 minutes later, still locked (15min cooldown)
    res2 = activate_synergy(
        master_id="alice",
        head=Head.SPIRITREAVER, frame=Frame.VALOREDGE,
        active_maneuvers={ManeuverElement.DARK: 3},
        cooldowns=cd,
        now_tick=1300,
    )
    assert res2.accepted is False
    assert res2.status == ActivationStatus.ON_COOLDOWN
    assert res2.cooldown_remaining_seconds > 0
    assert res2.matched_ability.ability_id == "death_spikes"


def test_activation_after_cooldown_succeeds_again():
    cd = CooldownTracker()
    activate_synergy(
        master_id="alice",
        head=Head.SPIRITREAVER, frame=Frame.VALOREDGE,
        active_maneuvers={ManeuverElement.DARK: 3},
        cooldowns=cd,
        now_tick=1000,
    )
    # 16min later — past the 15min cooldown.
    res2 = activate_synergy(
        master_id="alice",
        head=Head.SPIRITREAVER, frame=Frame.VALOREDGE,
        active_maneuvers={ManeuverElement.DARK: 3},
        cooldowns=cd,
        now_tick=1000 + 960,
    )
    assert res2.accepted is True
    assert res2.status == ActivationStatus.SUCCESS


# -- isolation -----------------------------------------------------

def test_two_masters_can_fire_same_synergy_independently():
    cd = CooldownTracker()
    res_a = activate_synergy(
        master_id="alice",
        head=Head.SPIRITREAVER, frame=Frame.VALOREDGE,
        active_maneuvers={ManeuverElement.DARK: 3},
        cooldowns=cd, now_tick=1000,
    )
    res_b = activate_synergy(
        master_id="bob",
        head=Head.SPIRITREAVER, frame=Frame.VALOREDGE,
        active_maneuvers={ManeuverElement.DARK: 3},
        cooldowns=cd, now_tick=1010,
    )
    assert res_a.accepted and res_b.accepted


def test_master_can_fire_different_synergies_independently():
    """Alice fires Death Spikes; she's still free to fire Stoneskin
    on a different head/frame combo."""
    cd = CooldownTracker()
    activate_synergy(
        master_id="alice",
        head=Head.SPIRITREAVER, frame=Frame.VALOREDGE,
        active_maneuvers={ManeuverElement.DARK: 3},
        cooldowns=cd, now_tick=1000,
    )
    res = activate_synergy(
        master_id="alice",
        head=Head.RDM, frame=Frame.VALOREDGE,
        active_maneuvers={ManeuverElement.EARTH: 3},
        cooldowns=cd, now_tick=1010,
    )
    assert res.accepted
    assert res.matched_ability.ability_id == "aoe_stoneskin"


# -- mixed-element activation -------------------------------------

def test_dnc_unlock_activates_with_mixed_elements():
    cd = CooldownTracker()
    res = activate_synergy(
        master_id="alice",
        head=Head.VALOREDGE, frame=Frame.NIN,
        active_maneuvers={
            ManeuverElement.ICE: 1,
            ManeuverElement.EARTH: 1,
            ManeuverElement.WATER: 1,
        },
        cooldowns=cd, now_tick=1000,
    )
    assert res.accepted
    assert res.matched_ability.ability_id == "dnc_unlock"
    # Duration is 5min
    assert res.instance.expires_at_tick == 1000 + 300


def test_dnc_unlock_under_overdrive_extends_to_25_min():
    cd = CooldownTracker()
    res = activate_synergy(
        master_id="alice",
        head=Head.VALOREDGE, frame=Frame.NIN,
        active_maneuvers={
            ManeuverElement.ICE: 1,
            ManeuverElement.EARTH: 1,
            ManeuverElement.WATER: 1,
        },
        cooldowns=cd, now_tick=1000,
        overdrive_active=True,
    )
    assert res.accepted
    # 5min * 5 = 25min
    assert res.instance.expires_at_tick == 1000 + 1500


# -- composition: full scene --------------------------------------

def test_full_lifecycle_pup_alliance_synergy_scene():
    """Three PUPs in alliance fire different synergies in sequence;
    cooldowns are per-master so each one fires cleanly."""
    cd = CooldownTracker()

    # Alice fires Death Spikes for tank protection
    r1 = activate_synergy(
        master_id="alice",
        head=Head.SPIRITREAVER, frame=Frame.VALOREDGE,
        active_maneuvers={ManeuverElement.DARK: 3},
        cooldowns=cd, now_tick=1000,
    )
    assert r1.accepted

    # Bob fires Stoneskin for the party
    r2 = activate_synergy(
        master_id="bob",
        head=Head.RDM, frame=Frame.VALOREDGE,
        active_maneuvers={ManeuverElement.EARTH: 3},
        cooldowns=cd, now_tick=1010,
    )
    assert r2.accepted

    # Carol fires Reraise
    r3 = activate_synergy(
        master_id="carol",
        head=Head.SOULSOOTHER, frame=Frame.VALOREDGE,
        active_maneuvers={ManeuverElement.LIGHT: 3},
        cooldowns=cd, now_tick=1020,
    )
    assert r3.accepted

    # All three abilities active concurrently — cooldowns
    # tracked independently.
    assert cd.active_count(now_tick=1100) == 3

    # Alice tries to re-fire — locked out.
    r4 = activate_synergy(
        master_id="alice",
        head=Head.SPIRITREAVER, frame=Frame.VALOREDGE,
        active_maneuvers={ManeuverElement.DARK: 3},
        cooldowns=cd, now_tick=1100,
    )
    assert not r4.accepted
    assert r4.status == ActivationStatus.ON_COOLDOWN
