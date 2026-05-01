"""Tests for AFK detection + Fomor spawn + mob convergence.

Run:  python -m pytest server/tests/test_anti_cheese.py -v
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from anti_cheese import (
    AFKDetector,
    AFKState,
    ActivityHotspot,
    FomorParty,
    FomorSpawnPolicy,
    MobConvergenceTracker,
    PlayerActivity,
)
from anti_cheese.fomor_spawner import (
    DEFAULT_FOMOR_PACK_SIZE_MAX,
    SpawnDecision,
)


# ----------------------------------------------------------------------
# AFK detector
# ----------------------------------------------------------------------

def _stuck_macro_activity(player_id: str, count: int,
                           start_time: float = 0.0,
                           interval: float = 4.0) -> list[PlayerActivity]:
    """Generate a perfect macro-loop signature: same position, same
    action, regular intervals."""
    return [
        PlayerActivity(
            player_id=player_id,
            timestamp=start_time + i * interval,
            x_cm=0, y_cm=0, z_cm=0,
            action_id="auto_attack",
        )
        for i in range(count)
    ]


def _legit_player_activity(player_id: str, count: int,
                             start_time: float = 0.0) -> list[PlayerActivity]:
    """Generate diverse activity — moving, varying skills, irregular timing."""
    actions = ["auto_attack", "weapon_skill", "cure_iii", "haste"]
    out = []
    for i in range(count):
        out.append(PlayerActivity(
            player_id=player_id,
            timestamp=start_time + i * 4 + (i % 3) * 1.5,
            x_cm=i * 200,
            y_cm=(i % 5) * 150,
            z_cm=0,
            action_id=actions[i % len(actions)],
        ))
    return out


def test_legit_player_stays_active():
    det = AFKDetector(afk_window_seconds=300, afk_confirm_seconds=300)
    for a in _legit_player_activity("alice", count=80):
        det.observe(a)
    assert det.state_of("alice") == AFKState.ACTIVE


def test_macro_player_becomes_suspected_then_confirmed():
    det = AFKDetector(afk_window_seconds=300, afk_confirm_seconds=300)
    activities = _stuck_macro_activity("bob", count=80, interval=4.0)
    for a in activities:
        det.observe(a)
    # Last activity at t=316; window=300; confirm=300. Should be CONFIRMED
    # because position-stuck + actions-repetitive + timing-macro all True.
    assert det.state_of("bob") in (AFKState.SUSPECTED, AFKState.CONFIRMED)


def test_macro_player_with_extended_history_confirms():
    det = AFKDetector(afk_window_seconds=300, afk_confirm_seconds=300)
    # 600 seconds of macro = enough for SUSPECTED + confirm window
    activities = _stuck_macro_activity("bob", count=160, interval=4.0)
    for a in activities:
        det.observe(a)
    assert det.state_of("bob") == AFKState.CONFIRMED


def test_legit_then_macro_transitions_through_states():
    det = AFKDetector(afk_window_seconds=300, afk_confirm_seconds=300)
    for a in _legit_player_activity("carol", count=40):
        det.observe(a)
    assert det.state_of("carol") == AFKState.ACTIVE

    # Switch to macro behavior
    macro = _stuck_macro_activity("carol", count=200, start_time=200, interval=4.0)
    for a in macro:
        det.observe(a)
    # Should have transitioned suspected → confirmed
    assert det.state_of("carol") in (AFKState.SUSPECTED, AFKState.CONFIRMED)


def test_walking_player_doesnt_get_flagged_just_for_repetitive_skill():
    """A WAR auto-attacking the same skill but actually MOVING should
    not be flagged. Position-diversity check should pass."""
    det = AFKDetector(afk_window_seconds=300, afk_confirm_seconds=300)
    # All same skill, but positions varying
    for i in range(80):
        det.observe(PlayerActivity(
            player_id="d", timestamp=i * 4,
            x_cm=i * 100, y_cm=0, z_cm=0,
            action_id="auto_attack",
        ))
    assert det.state_of("d") == AFKState.ACTIVE


def test_reset_clears_state():
    det = AFKDetector()
    for a in _stuck_macro_activity("e", count=200, interval=4.0):
        det.observe(a)
    det.reset("e")
    assert det.state_of("e") == AFKState.ACTIVE


# ----------------------------------------------------------------------
# Fomor spawn policy
# ----------------------------------------------------------------------

@pytest.fixture
def policy():
    return FomorSpawnPolicy()


def test_not_afk_no_spawn(policy):
    decision = policy.decide(
        player_id="alice", afk_confirmed=False,
        location_type="dungeon", is_night=True,
        player_position=(0, 0, 0), player_level=50,
    )
    assert decision == SpawnDecision.DELAY


def test_sanctuary_never_spawns(policy):
    """Even AFK-confirmed players are safe in sanctuary zones."""
    decision = policy.decide(
        player_id="alice", afk_confirmed=True,
        location_type="sanctuary", is_night=True,
        player_position=(0, 0, 0), player_level=50,
    )
    assert decision == SpawnDecision.SKIP


def test_dungeon_always_spawns_when_afk(policy):
    """Dungeons are aggressive regardless of time."""
    decision = policy.decide(
        player_id="alice", afk_confirmed=True,
        location_type="dungeon", is_night=False,   # daytime!
        player_position=(0, 0, 0), player_level=50,
    )
    assert decision == SpawnDecision.SPAWN_FOMOR_PARTY


def test_instance_entrance_always_spawns(policy):
    """Instance entrance camping = bot-farming target. Always spawn."""
    decision = policy.decide(
        player_id="alice", afk_confirmed=True,
        location_type="instance_entrance", is_night=False,
        player_position=(0, 0, 0), player_level=50,
    )
    assert decision == SpawnDecision.SPAWN_FOMOR_PARTY


def test_open_world_night_spawns(policy):
    decision = policy.decide(
        player_id="alice", afk_confirmed=True,
        location_type="open_world", is_night=True,
        player_position=(0, 0, 0), player_level=50,
    )
    assert decision == SpawnDecision.SPAWN_FOMOR_PARTY


def test_open_world_day_delays(policy):
    """Daytime AFK in safe area: no spawn (yet)."""
    decision = policy.decide(
        player_id="alice", afk_confirmed=True,
        location_type="open_world", is_night=False,
        player_position=(0, 0, 0), player_level=50,
    )
    assert decision == SpawnDecision.DELAY


def test_build_party_max_size_for_dungeon(policy):
    party = policy.build_party(
        player_id="alice",
        player_position=(100, 200, 0),
        player_level=50,
        location_type="dungeon",
        is_night=True,
    )
    assert party.target_player_id == "alice"
    assert party.pack_size == DEFAULT_FOMOR_PACK_SIZE_MAX
    assert party.target_position == (100, 200, 0)
    # Levels match player +2 in dungeons
    assert all(l == 52 for l in party.fomor_levels)


def test_build_party_open_world_min_size(policy):
    party = policy.build_party(
        player_id="alice",
        player_position=(0, 0, 0),
        player_level=50,
        location_type="open_world",
        is_night=False,
    )
    # Daytime open-world: minimum size
    from anti_cheese.fomor_spawner import DEFAULT_FOMOR_PACK_SIZE_MIN
    assert party.pack_size == DEFAULT_FOMOR_PACK_SIZE_MIN


# ----------------------------------------------------------------------
# Mob convergence
# ----------------------------------------------------------------------

@pytest.fixture
def conv():
    return MobConvergenceTracker()


def test_first_activity_creates_hotspot(conv):
    conv.observe_player_activity(
        player_id="alice", zone="south_gustaberg",
        x_cm=1000, y_cm=1000, z_cm=0, now=10,
    )
    hotspots = conv.get_hotspots("south_gustaberg")
    assert len(hotspots) == 1
    assert hotspots[0].x_cm == 1000


def test_nearby_activity_merges_into_existing_hotspot(conv):
    conv.observe_player_activity(
        player_id="alice", zone="z", x_cm=1000, y_cm=1000, z_cm=0, now=10,
    )
    # Within 15m → merges
    conv.observe_player_activity(
        player_id="bob", zone="z", x_cm=1500, y_cm=1500, z_cm=0, now=12,
    )
    assert len(conv.get_hotspots("z")) == 1
    h = conv.get_hotspots("z")[0]
    assert h.last_observed_at == 12
    assert h.strength == pytest.approx(2.0)


def test_far_activity_creates_separate_hotspot(conv):
    conv.observe_player_activity(
        player_id="alice", zone="z", x_cm=1000, y_cm=1000, z_cm=0, now=10,
    )
    # 50m away — distinct hotspot
    conv.observe_player_activity(
        player_id="bob", zone="z", x_cm=6000, y_cm=6000, z_cm=0, now=12,
    )
    assert len(conv.get_hotspots("z")) == 2


def test_tick_emits_movement_hints_for_nearby_mobs(conv):
    conv.observe_player_activity(
        player_id="alice", zone="z", x_cm=0, y_cm=0, z_cm=0, now=10,
    )
    mobs = {"z": [
        {"mob_id": "near_mob", "x_cm": 1500, "y_cm": 0, "z_cm": 0,
         "currently_aggressive": False},
        {"mob_id": "far_mob", "x_cm": 50000, "y_cm": 0, "z_cm": 0,
         "currently_aggressive": False},
    ]}
    hints = conv.tick(now=15, mobs_in_zone=mobs)
    mob_ids = {h.mob_id for h in hints}
    assert "near_mob" in mob_ids
    assert "far_mob" not in mob_ids


def test_tick_skips_already_aggressive_mobs(conv):
    conv.observe_player_activity(
        player_id="alice", zone="z", x_cm=0, y_cm=0, z_cm=0, now=10,
    )
    mobs = {"z": [
        {"mob_id": "fighting_mob", "x_cm": 1500, "y_cm": 0, "z_cm": 0,
         "currently_aggressive": True},
        {"mob_id": "passive_mob", "x_cm": 1500, "y_cm": 100, "z_cm": 0,
         "currently_aggressive": False},
    ]}
    hints = conv.tick(now=15, mobs_in_zone=mobs)
    mob_ids = {h.mob_id for h in hints}
    assert "fighting_mob" not in mob_ids
    assert "passive_mob" in mob_ids


def test_gather_radius_grows_over_time(conv):
    conv.observe_player_activity(
        player_id="alice", zone="z", x_cm=0, y_cm=0, z_cm=0, now=0,
    )
    # Mob far away (50m) — outside initial 30m radius
    far_mob = [{"mob_id": "far", "x_cm": 5000, "y_cm": 0, "z_cm": 0,
                 "currently_aggressive": False}]
    mobs_z = {"z": far_mob}

    early = conv.tick(now=10, mobs_in_zone=mobs_z)
    assert len([h for h in early if h.mob_id == "far"]) == 0

    # Re-observe to keep hotspot alive
    conv.observe_player_activity(
        player_id="alice", zone="z", x_cm=0, y_cm=0, z_cm=0, now=400,
    )
    # 400 seconds later: radius widened to 30m + 400×5cm = 50m+ — should reach
    late = conv.tick(now=500, mobs_in_zone=mobs_z)
    assert len([h for h in late if h.mob_id == "far"]) >= 1


def test_decayed_hotspot_cleared(conv):
    conv.observe_player_activity(
        player_id="alice", zone="z", x_cm=0, y_cm=0, z_cm=0, now=0,
    )
    # No further activity. After 700s (>600 decay), tick should clear.
    conv.tick(now=700, mobs_in_zone={"z": []})
    assert conv.get_hotspots("z") == []
