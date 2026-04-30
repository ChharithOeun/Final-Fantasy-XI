"""Tests for the aggro tracker.

Run:  python -m pytest server/tests/test_aggro_system.py -v
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from aggro_system import (
    AggroState,
    AggroTracker,
    PlayerSnapshot,
    SensoryProfile,
    can_perceive_player,
    compute_player_sound_level,
)


# ----------------------------------------------------------------------
# Sound-level computation
# ----------------------------------------------------------------------

def test_sound_level_quiet_baseline():
    p = PlayerSnapshot(player_id="alice", x_cm=0, y_cm=0, z_cm=0,
                        movement_speed_pct=0.0, weight=10)
    # Still + light = barely audible
    assert compute_player_sound_level(p) < 0.3


def test_sound_level_combat_running():
    p = PlayerSnapshot(player_id="alice", x_cm=0, y_cm=0, z_cm=0,
                        in_combat=True, weapon_just_swung=True,
                        movement_speed_pct=1.0, weight=120)
    # Heavy WAR mid-combat: very loud
    assert compute_player_sound_level(p) > 1.0


def test_sound_level_sneak_dampens():
    base = PlayerSnapshot(player_id="alice", x_cm=0, y_cm=0, z_cm=0,
                          movement_speed_pct=0.5, weight=30)
    sneaky = PlayerSnapshot(player_id="alice", x_cm=0, y_cm=0, z_cm=0,
                            movement_speed_pct=0.5, weight=30,
                            has_sneak=True)
    assert compute_player_sound_level(sneaky) < \
           compute_player_sound_level(base) * 0.2


def test_sound_level_heavy_increases():
    light = PlayerSnapshot(player_id="alice", x_cm=0, y_cm=0, z_cm=0,
                            movement_speed_pct=1.0, weight=10)
    heavy = PlayerSnapshot(player_id="alice", x_cm=0, y_cm=0, z_cm=0,
                            movement_speed_pct=1.0, weight=150)
    assert compute_player_sound_level(heavy) > \
           compute_player_sound_level(light)


# ----------------------------------------------------------------------
# Perception logic
# ----------------------------------------------------------------------

def test_perceive_in_sight_cone():
    profile = SensoryProfile(sight_range_cm=2000, sight_cone_deg=180,
                              sight_requires_los=True)
    player = PlayerSnapshot(player_id="alice", x_cm=1000, y_cm=0, z_cm=0,
                             movement_speed_pct=1.0)
    result = can_perceive_player(
        mob_x=0, mob_y=0, mob_z=0, mob_facing_deg=0,
        mob_health_pct=1.0, mob_profile=profile,
        player=player, line_of_sight_clear=True,
    )
    assert result["sight"] is True


def test_perceive_outside_sight_cone():
    profile = SensoryProfile(sight_range_cm=2000, sight_cone_deg=90,
                              sight_requires_los=False)
    # Player is BEHIND the mob (mob faces +x; player at -x)
    player = PlayerSnapshot(player_id="alice", x_cm=-1000, y_cm=0, z_cm=0,
                             movement_speed_pct=1.0)
    result = can_perceive_player(
        mob_x=0, mob_y=0, mob_z=0, mob_facing_deg=0,
        mob_health_pct=1.0, mob_profile=profile,
        player=player,
    )
    assert result["sight"] is False


def test_invisible_player_not_seen():
    profile = SensoryProfile(sight_range_cm=2000)
    player = PlayerSnapshot(player_id="alice", x_cm=500, y_cm=0, z_cm=0,
                             has_invisible=True)
    result = can_perceive_player(
        mob_x=0, mob_y=0, mob_z=0, mob_facing_deg=0,
        mob_health_pct=1.0, mob_profile=profile,
        player=player,
    )
    assert result["sight"] is False


def test_wounded_mob_sight_reduced():
    """A wounded mob's sight range scales with health percentage."""
    profile = SensoryProfile(sight_range_cm=2000)
    player = PlayerSnapshot(player_id="alice", x_cm=1500, y_cm=0, z_cm=0)

    # Pristine: sees the player
    pristine = can_perceive_player(
        mob_x=0, mob_y=0, mob_z=0, mob_facing_deg=0,
        mob_health_pct=1.0, mob_profile=profile, player=player,
    )
    assert pristine["sight"] is True

    # Wounded at 50%: effective sight is 1000cm; 1500 > 1000, can't see
    wounded = can_perceive_player(
        mob_x=0, mob_y=0, mob_z=0, mob_facing_deg=0,
        mob_health_pct=0.5, mob_profile=profile, player=player,
    )
    assert wounded["sight"] is False


def test_perceive_via_sound():
    profile = SensoryProfile(sight_range_cm=0, sound_range_cm=2000,
                              sound_passive_threshold=0.3)
    player = PlayerSnapshot(player_id="alice", x_cm=1500, y_cm=0, z_cm=0,
                             in_combat=True, weapon_just_swung=True)
    result = can_perceive_player(
        mob_x=0, mob_y=0, mob_z=0, mob_facing_deg=0,
        mob_health_pct=1.0, mob_profile=profile, player=player,
    )
    # Combat-loud player within 15m sound range — heard
    assert result["sound"] is True


def test_perceive_via_smell_predator():
    """Predator mobs use smell — wide range, no LoS required."""
    profile = SensoryProfile(sight_range_cm=0, sound_range_cm=0,
                              smell_range_cm=4000)
    player = PlayerSnapshot(player_id="alice", x_cm=3500, y_cm=0, z_cm=0)
    result = can_perceive_player(
        mob_x=0, mob_y=0, mob_z=0, mob_facing_deg=0,
        mob_health_pct=1.0, mob_profile=profile, player=player,
    )
    assert result["smell"] is True


def test_deodorize_blocks_smell():
    profile = SensoryProfile(sight_range_cm=0, sound_range_cm=0,
                              smell_range_cm=4000)
    player = PlayerSnapshot(player_id="alice", x_cm=3500, y_cm=0, z_cm=0,
                             has_deodorize=True)
    result = can_perceive_player(
        mob_x=0, mob_y=0, mob_z=0, mob_facing_deg=0,
        mob_health_pct=1.0, mob_profile=profile, player=player,
    )
    assert result["smell"] is False


# ----------------------------------------------------------------------
# AggroTracker state machine
# ----------------------------------------------------------------------

@pytest.fixture
def tracker():
    profile = SensoryProfile(sight_range_cm=2000, sound_range_cm=1000)
    return AggroTracker(mob_id="quadav_helmsman_001",
                         mob_profile=profile)


def test_neutral_initial_state(tracker):
    assert tracker.state_toward("alice") == AggroState.NEUTRAL
    assert tracker.is_pursuing("alice") is False


def test_perception_promotes_to_suspicious(tracker):
    perception = {"sight": True, "sound": False, "smell": False, "any": True}
    state = tracker.notify_perception(player_id="alice", perception=perception,
                                        now_seconds=10.0)
    assert state == AggroState.SUSPICIOUS


def test_damage_promotes_to_aggressive(tracker):
    state = tracker.notify_damage(player_id="alice", damage_pct=0.10,
                                    now_seconds=10.0)
    assert state == AggroState.AGGRESSIVE
    assert tracker.is_pursuing("alice") is True


def test_heavy_damage_triggers_enraged(tracker):
    state = tracker.notify_damage(player_id="alice", damage_pct=0.60,
                                    now_seconds=10.0)
    assert state == AggroState.ENRAGED


def test_provoke_triggers_enraged_immediately(tracker):
    state = tracker.notify_damage(player_id="alice", damage_pct=0.05,
                                    now_seconds=10.0, was_provoked=True)
    assert state == AggroState.ENRAGED


def test_l3_skillchain_triggers_enraged(tracker):
    tracker.notify_damage(player_id="alice", damage_pct=0.10,
                            now_seconds=10.0)
    state = tracker.notify_skillchain_landed(
        player_id="alice", chain_level=3, now_seconds=11.0,
    )
    assert state == AggroState.ENRAGED


def test_intervention_proc_triggers_enraged(tracker):
    tracker.notify_damage(player_id="alice", damage_pct=0.10,
                            now_seconds=10.0)
    state = tracker.notify_intervention_proc(
        player_id="alice", now_seconds=11.0,
    )
    assert state == AggroState.ENRAGED


def test_sanctuary_drops_aggro(tracker):
    tracker.notify_damage(player_id="alice", damage_pct=0.60,
                            now_seconds=10.0)
    assert tracker.state_toward("alice") == AggroState.ENRAGED
    prev = tracker.notify_player_entered_sanctuary(player_id="alice")
    assert prev == AggroState.ENRAGED
    assert tracker.state_toward("alice") == AggroState.NEUTRAL


# ----------------------------------------------------------------------
# Persistence + deaggro decay
# ----------------------------------------------------------------------

def test_aggressive_decays_after_45s_lost(tracker):
    # Player damages mob → AGGRESSIVE
    tracker.notify_damage(player_id="alice", damage_pct=0.10,
                            now_seconds=0.0)
    # Player escapes — perception fails
    perception = {"sight": False, "sound": False, "smell": False, "any": False}
    tracker.notify_perception(player_id="alice", perception=perception,
                                now_seconds=5.0)

    # Tick at 30s — still in persistence window (45s); state stays
    changes = tracker.tick(now_seconds=35.0)
    assert "alice" not in changes
    assert tracker.state_toward("alice") == AggroState.AGGRESSIVE

    # Tick at 60s — past persistence; mob deaggros
    changes = tracker.tick(now_seconds=60.0)
    assert changes.get("alice") == AggroState.NEUTRAL
    assert tracker.state_toward("alice") == AggroState.NEUTRAL


def test_enraged_persists_5_minutes(tracker):
    """Enraged mobs chase 5 minutes after losing the player."""
    tracker.notify_damage(player_id="alice", damage_pct=0.60,
                            now_seconds=0.0)
    perception = {"sight": False, "sound": False, "smell": False, "any": False}
    tracker.notify_perception(player_id="alice", perception=perception,
                                now_seconds=5.0)

    # Tick at 60s — still well within 5-min enraged persistence
    tracker.tick(now_seconds=65.0)
    assert tracker.state_toward("alice") == AggroState.ENRAGED

    # Tick at 5 minutes + buffer — past persistence
    tracker.tick(now_seconds=320.0)
    assert tracker.state_toward("alice") == AggroState.NEUTRAL


def test_re_perceiving_resets_lost_timer(tracker):
    tracker.notify_damage(player_id="alice", damage_pct=0.10,
                            now_seconds=0.0)
    lost = {"sight": False, "sound": False, "smell": False, "any": False}
    seen = {"sight": True, "sound": False, "smell": False, "any": True}

    tracker.notify_perception(player_id="alice", perception=lost,
                                now_seconds=5.0)
    # Re-acquire at 30s (lost timer was 5s, only 25s elapsed)
    tracker.notify_perception(player_id="alice", perception=seen,
                                now_seconds=30.0)
    # Now lose again at 35s — fresh 45s timer
    tracker.notify_perception(player_id="alice", perception=lost,
                                now_seconds=35.0)

    # Tick at 75s — only 40s since last lost, still in window
    tracker.tick(now_seconds=75.0)
    assert tracker.state_toward("alice") == AggroState.AGGRESSIVE


# ----------------------------------------------------------------------
# Multi-player aggro
# ----------------------------------------------------------------------

def test_independent_aggro_per_player(tracker):
    """Two players: mob is enraged at one, neutral toward the other."""
    tracker.notify_damage(player_id="alice", damage_pct=0.60,
                            now_seconds=0.0)
    assert tracker.state_toward("alice") == AggroState.ENRAGED
    assert tracker.state_toward("bob") == AggroState.NEUTRAL


def test_snapshot_diagnostic(tracker):
    tracker.notify_damage(player_id="alice", damage_pct=0.10,
                            now_seconds=0.0)
    snap = tracker.snapshot()
    assert snap["mob_id"] == "quadav_helmsman_001"
    assert snap["tracked_players"] == 1
    assert "alice" in snap["records"]
    assert snap["records"]["alice"]["state"] == "AGGRESSIVE"
