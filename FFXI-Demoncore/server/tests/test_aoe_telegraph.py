"""Tests for the AOE telegraph engine.

Run:  python -m pytest server/tests/test_aoe_telegraph.py -v
"""
import math
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from aoe_telegraph import (
    ELEMENT_COLOR_HEX,
    TelegraphInstance,
    TelegraphRegistry,
    TelegraphShape,
    TelegraphSpec,
    TelegraphState,
    color_for_element,
    moods_to_emit,
    point_inside_telegraph,
    reaction_window_seconds,
)


# ----------------------------------------------------------------------
# Geometry
# ----------------------------------------------------------------------

def test_circle_contains_origin():
    assert point_inside_telegraph(
        shape=TelegraphShape.CIRCLE, origin=(0, 0), point=(0, 0),
        radius_cm=500,
    ) is True


def test_circle_excludes_outside():
    assert point_inside_telegraph(
        shape=TelegraphShape.CIRCLE, origin=(0, 0), point=(600, 0),
        radius_cm=500,
    ) is False


def test_circle_includes_edge():
    assert point_inside_telegraph(
        shape=TelegraphShape.CIRCLE, origin=(0, 0), point=(500, 0),
        radius_cm=500,
    ) is True


def test_donut_excludes_inner_hole():
    """Standing at the center of a donut isn't enough — you need the
    annulus ring (between inner and outer radius)."""
    assert point_inside_telegraph(
        shape=TelegraphShape.DONUT, origin=(0, 0), point=(0, 0),
        radius_cm=500, inner_radius_cm=200,
    ) is False


def test_donut_includes_ring():
    assert point_inside_telegraph(
        shape=TelegraphShape.DONUT, origin=(0, 0), point=(300, 0),
        radius_cm=500, inner_radius_cm=200,
    ) is True


def test_donut_excludes_beyond_outer():
    assert point_inside_telegraph(
        shape=TelegraphShape.DONUT, origin=(0, 0), point=(600, 0),
        radius_cm=500, inner_radius_cm=200,
    ) is False


def test_cone_includes_within_arc():
    """90 deg cone facing east; point straight east at 200 = inside."""
    assert point_inside_telegraph(
        shape=TelegraphShape.CONE, origin=(0, 0), point=(200, 0),
        radius_cm=500, angle_deg=90, facing_deg=0,
    ) is True


def test_cone_excludes_behind_caster():
    """Same cone, point straight west = outside (180 from facing)."""
    assert point_inside_telegraph(
        shape=TelegraphShape.CONE, origin=(0, 0), point=(-200, 0),
        radius_cm=500, angle_deg=90, facing_deg=0,
    ) is False


def test_cone_excludes_beyond_radius():
    assert point_inside_telegraph(
        shape=TelegraphShape.CONE, origin=(0, 0), point=(600, 0),
        radius_cm=500, angle_deg=90, facing_deg=0,
    ) is False


def test_cone_arc_boundary():
    """45 deg cone facing east: a point at +30 deg is in, at +60 is out."""
    pt_in = (math.cos(math.radians(20)) * 200,
              math.sin(math.radians(20)) * 200)
    pt_out = (math.cos(math.radians(60)) * 200,
               math.sin(math.radians(60)) * 200)
    assert point_inside_telegraph(
        shape=TelegraphShape.CONE, origin=(0, 0), point=pt_in,
        radius_cm=500, angle_deg=45, facing_deg=0,
    ) is True
    assert point_inside_telegraph(
        shape=TelegraphShape.CONE, origin=(0, 0), point=pt_out,
        radius_cm=500, angle_deg=45, facing_deg=0,
    ) is False


def test_line_includes_along_facing():
    """Line facing east, length 500, half-width 100. Point at (200, 50)
    inside; (200, 200) outside; (-50, 0) outside."""
    assert point_inside_telegraph(
        shape=TelegraphShape.LINE, origin=(0, 0), point=(200, 50),
        radius_cm=100, length_cm=500, facing_deg=0,
    ) is True
    assert point_inside_telegraph(
        shape=TelegraphShape.LINE, origin=(0, 0), point=(200, 200),
        radius_cm=100, length_cm=500, facing_deg=0,
    ) is False
    assert point_inside_telegraph(
        shape=TelegraphShape.LINE, origin=(0, 0), point=(-50, 0),
        radius_cm=100, length_cm=500, facing_deg=0,
    ) is False


def test_line_rotated_facing():
    """Line facing north (90 deg). Point at (50, 200) inside; (200, 50)
    outside (sideways)."""
    assert point_inside_telegraph(
        shape=TelegraphShape.LINE, origin=(0, 0), point=(50, 200),
        radius_cm=100, length_cm=500, facing_deg=90,
    ) is True
    assert point_inside_telegraph(
        shape=TelegraphShape.LINE, origin=(0, 0), point=(200, 50),
        radius_cm=100, length_cm=500, facing_deg=90,
    ) is False


def test_square_axis_aligned():
    assert point_inside_telegraph(
        shape=TelegraphShape.SQUARE, origin=(0, 0), point=(100, -100),
        radius_cm=200,
    ) is True
    assert point_inside_telegraph(
        shape=TelegraphShape.SQUARE, origin=(0, 0), point=(250, 0),
        radius_cm=200,
    ) is False


def test_chevron_tapers():
    """Chevron facing east, length 500, half-angle 30 deg.
    At x=100 the half-width is 100*tan(30) = 57.7. (100, 50) inside;
    (100, 80) outside; (400, 200) inside (since width grows to ~230)."""
    assert point_inside_telegraph(
        shape=TelegraphShape.CHEVRON, origin=(0, 0), point=(100, 50),
        length_cm=500, angle_deg=60, facing_deg=0,
    ) is True
    assert point_inside_telegraph(
        shape=TelegraphShape.CHEVRON, origin=(0, 0), point=(100, 80),
        length_cm=500, angle_deg=60, facing_deg=0,
    ) is False
    assert point_inside_telegraph(
        shape=TelegraphShape.CHEVRON, origin=(0, 0), point=(400, 200),
        length_cm=500, angle_deg=60, facing_deg=0,
    ) is True


def test_irregular_polygon_inside_outside():
    """Diamond polygon centered at (0,0)."""
    diamond = [(100, 0), (0, 100), (-100, 0), (0, -100)]
    assert point_inside_telegraph(
        shape=TelegraphShape.IRREGULAR, origin=(0, 0), point=(0, 0),
        polygon=diamond,
    ) is True
    assert point_inside_telegraph(
        shape=TelegraphShape.IRREGULAR, origin=(0, 0), point=(80, 80),
        polygon=diamond,
    ) is False


def test_irregular_requires_polygon():
    with pytest.raises(ValueError, match="polygon"):
        point_inside_telegraph(
            shape=TelegraphShape.IRREGULAR, origin=(0, 0), point=(0, 0),
        )


def test_circle_requires_radius():
    with pytest.raises(ValueError, match="radius"):
        point_inside_telegraph(
            shape=TelegraphShape.CIRCLE, origin=(0, 0), point=(0, 0),
        )


# ----------------------------------------------------------------------
# Palette
# ----------------------------------------------------------------------

def test_color_for_known_elements():
    assert color_for_element("fire") == "#ff6633"
    assert color_for_element("ice") == "#66ccff"
    assert color_for_element("light") == "#fff5cc"
    assert color_for_element("dark") == "#663366"


def test_color_case_insensitive():
    assert color_for_element("FIRE") == "#ff6633"
    assert color_for_element("Light") == "#fff5cc"


def test_color_unknown_falls_back():
    assert color_for_element("plasma_glitch") == "#cccccc"


def test_palette_completeness():
    """All 8 elements + physical/healing/buff/debuff in the table."""
    for e in ("fire", "ice", "lightning", "earth", "wind",
                "water", "light", "dark",
                "physical", "healing", "buff_zone", "debuff_zone"):
        assert e in ELEMENT_COLOR_HEX


# ----------------------------------------------------------------------
# Reaction window
# ----------------------------------------------------------------------

def test_reaction_window_half_of_cast():
    """Doc examples: 1.5s -> 0.75s, 3.0s -> 1.5s."""
    assert reaction_window_seconds(1.5) == pytest.approx(0.75)
    assert reaction_window_seconds(3.0) == pytest.approx(1.5)


def test_reaction_window_zero_for_instant():
    assert reaction_window_seconds(0) == 0.0
    assert reaction_window_seconds(-1) == 0.0


# ----------------------------------------------------------------------
# Lifecycle: TARGETING -> ACTIVE -> LANDING
# ----------------------------------------------------------------------

def _firaga_spec() -> TelegraphSpec:
    return TelegraphSpec(
        spell_id="firaga_iii", shape=TelegraphShape.CIRCLE,
        element="fire", radius_cm=500,
    )


def test_begin_targeting_creates_instance():
    reg = TelegraphRegistry()
    inst = reg.begin_targeting(
        spec=_firaga_spec(), caster_id="alice",
        caster_faction="player_party", target_position=(1000, 1000),
    )
    assert inst.state == TelegraphState.TARGETING
    assert inst.target_position == (1000, 1000)
    assert reg.get(inst.instance_id) is inst


def test_update_target_during_preview():
    reg = TelegraphRegistry()
    inst = reg.begin_targeting(
        spec=_firaga_spec(), caster_id="alice",
        caster_faction="player_party", target_position=(0, 0),
    )
    ok = reg.update_target_position(inst.instance_id,
                                       new_position=(2000, 0))
    assert ok is True
    assert inst.target_position == (2000, 0)


def test_update_target_after_commit_fails():
    """Once committed, the target position is locked."""
    reg = TelegraphRegistry()
    inst = reg.begin_targeting(
        spec=_firaga_spec(), caster_id="alice",
        caster_faction="player_party", target_position=(0, 0),
    )
    reg.commit_cast(inst.instance_id, cast_duration=2.0, now=0)
    ok = reg.update_target_position(inst.instance_id,
                                       new_position=(2000, 0))
    assert ok is False
    assert inst.target_position == (0, 0)


def test_commit_transitions_to_active():
    reg = TelegraphRegistry()
    inst = reg.begin_targeting(
        spec=_firaga_spec(), caster_id="alice",
        caster_faction="player_party", target_position=(0, 0),
    )
    reg.commit_cast(inst.instance_id, cast_duration=2.0, now=100)
    assert inst.state == TelegraphState.ACTIVE
    assert inst.cast_started_at == 100
    assert inst.cast_duration == 2.0


def test_fill_pct_progresses_during_active():
    reg = TelegraphRegistry()
    inst = reg.begin_targeting(
        spec=_firaga_spec(), caster_id="alice",
        caster_faction="player_party", target_position=(0, 0),
    )
    reg.commit_cast(inst.instance_id, cast_duration=2.0, now=0)
    assert inst.fill_pct(now=0) == 0.0
    assert inst.fill_pct(now=1.0) == pytest.approx(0.5)
    assert inst.fill_pct(now=2.0) == 1.0
    assert inst.fill_pct(now=10.0) == 1.0   # clamped


def test_fill_pct_zero_before_active():
    reg = TelegraphRegistry()
    inst = reg.begin_targeting(
        spec=_firaga_spec(), caster_id="alice",
        caster_faction="player_party", target_position=(0, 0),
    )
    assert inst.fill_pct(now=10.0) == 0.0


def test_cancel_during_targeting():
    reg = TelegraphRegistry()
    inst = reg.begin_targeting(
        spec=_firaga_spec(), caster_id="alice",
        caster_faction="player_party", target_position=(0, 0),
    )
    assert reg.cancel(inst.instance_id) is True
    assert inst.state == TelegraphState.CANCELED


def test_cancel_during_active_fails():
    """Once cast has started, cancel doesn't apply — interrupt does."""
    reg = TelegraphRegistry()
    inst = reg.begin_targeting(
        spec=_firaga_spec(), caster_id="alice",
        caster_faction="player_party", target_position=(0, 0),
    )
    reg.commit_cast(inst.instance_id, cast_duration=2.0, now=0)
    assert reg.cancel(inst.instance_id) is False
    assert inst.state == TelegraphState.ACTIVE


def test_interrupt_during_active():
    reg = TelegraphRegistry()
    inst = reg.begin_targeting(
        spec=_firaga_spec(), caster_id="alice",
        caster_faction="player_party", target_position=(0, 0),
    )
    reg.commit_cast(inst.instance_id, cast_duration=2.0, now=0)
    assert reg.interrupt(inst.instance_id) is True
    assert inst.state == TelegraphState.INTERRUPTED


def test_complete_hits_only_inside():
    reg = TelegraphRegistry()
    inst = reg.begin_targeting(
        spec=_firaga_spec(), caster_id="alice",
        caster_faction="player_party", target_position=(0, 0),
    )
    reg.commit_cast(inst.instance_id, cast_duration=2.0, now=0)
    hit = reg.complete(
        inst.instance_id, now=2.0,
        candidate_targets=[
            ("bob", (100, 100)),         # inside (radius 500)
            ("carol", (1000, 1000)),     # outside
            ("dave", (300, 0)),           # inside
        ],
    )
    assert "bob" in hit
    assert "dave" in hit
    assert "carol" not in hit
    assert inst.state == TelegraphState.LANDING


def test_complete_inactive_returns_empty():
    reg = TelegraphRegistry()
    inst = reg.begin_targeting(
        spec=_firaga_spec(), caster_id="alice",
        caster_faction="player_party", target_position=(0, 0),
    )
    # Never committed: complete should no-op
    hit = reg.complete(inst.instance_id, now=2.0,
                         candidate_targets=[("bob", (0, 0))])
    assert hit == []


def test_prune_terminal_clears():
    reg = TelegraphRegistry()
    a = reg.begin_targeting(
        spec=_firaga_spec(), caster_id="alice",
        caster_faction="player_party", target_position=(0, 0),
    )
    b = reg.begin_targeting(
        spec=_firaga_spec(), caster_id="bob",
        caster_faction="player_party", target_position=(0, 0),
    )
    reg.cancel(a.instance_id)
    reg.commit_cast(b.instance_id, cast_duration=1.0, now=0)
    pruned = reg.prune_terminal()
    assert pruned == 1
    assert reg.get(a.instance_id) is None
    assert reg.get(b.instance_id) is not None


# ----------------------------------------------------------------------
# Visibility — asymmetric rules
# ----------------------------------------------------------------------

def test_preview_only_visible_to_caster():
    reg = TelegraphRegistry()
    reg.begin_targeting(
        spec=_firaga_spec(), caster_id="alice",
        caster_faction="player_party", target_position=(0, 0),
    )
    # Other players don't see Alice's targeting preview
    visible = reg.visible_to_observer(
        observer_id="bob", observer_faction="player_party",
        observer_kind="player",
    )
    assert visible == []
    # Alice does
    visible = reg.visible_to_observer(
        observer_id="alice", observer_faction="player_party",
        observer_kind="player",
    )
    assert len(visible) == 1


def test_active_player_telegraph_broadcast_to_all():
    reg = TelegraphRegistry()
    inst = reg.begin_targeting(
        spec=_firaga_spec(), caster_id="alice",
        caster_faction="player_party", target_position=(0, 0),
    )
    reg.commit_cast(inst.instance_id, cast_duration=2.0, now=0)
    # Other players see it
    visible = reg.visible_to_observer(
        observer_id="bob", observer_faction="player_party",
        observer_kind="player",
    )
    assert len(visible) == 1
    # NPCs also see it
    visible = reg.visible_to_observer(
        observer_id="npc_guard", observer_faction="ally_npc",
        observer_kind="npc",
    )
    assert len(visible) == 1


def test_active_enemy_telegraph_invisible_to_players():
    """Skill-ceiling design: enemy AOE never gets a decal for players."""
    reg = TelegraphRegistry()
    inst = reg.begin_targeting(
        spec=_firaga_spec(), caster_id="quadav_boss",
        caster_faction="enemy", target_position=(0, 0),
    )
    reg.commit_cast(inst.instance_id, cast_duration=2.0, now=0)
    # Player observer: nothing
    visible = reg.visible_to_observer(
        observer_id="alice", observer_faction="player_party",
        observer_kind="player",
    )
    assert visible == []


def test_active_enemy_telegraph_visible_to_npcs():
    """NPCs DO see enemy AOE for mood propagation."""
    reg = TelegraphRegistry()
    inst = reg.begin_targeting(
        spec=_firaga_spec(), caster_id="quadav_boss",
        caster_faction="enemy", target_position=(0, 0),
    )
    reg.commit_cast(inst.instance_id, cast_duration=2.0, now=0)
    visible = reg.visible_to_observer(
        observer_id="bystander_npc", observer_faction="ally_npc",
        observer_kind="npc",
    )
    assert len(visible) == 1


def test_caster_always_sees_own_telegraph():
    """Even an enemy caster sees its own telegraph (server-side)."""
    reg = TelegraphRegistry()
    inst = reg.begin_targeting(
        spec=_firaga_spec(), caster_id="quadav_boss",
        caster_faction="enemy", target_position=(0, 0),
    )
    reg.commit_cast(inst.instance_id, cast_duration=2.0, now=0)
    visible = reg.visible_to_observer(
        observer_id="quadav_boss", observer_faction="enemy",
        observer_kind="player",   # kind doesn't matter for self
    )
    assert len(visible) == 1


def test_terminal_states_not_visible():
    reg = TelegraphRegistry()
    inst = reg.begin_targeting(
        spec=_firaga_spec(), caster_id="alice",
        caster_faction="player_party", target_position=(0, 0),
    )
    reg.cancel(inst.instance_id)
    visible = reg.visible_to_observer(
        observer_id="alice", observer_faction="player_party",
        observer_kind="player",
    )
    assert visible == []


# ----------------------------------------------------------------------
# Mood emission
# ----------------------------------------------------------------------

def test_civilian_panics_at_telegraph():
    moods = moods_to_emit("civilian")
    assert ("fearful", 0.4) in moods


def test_soldier_alerts_at_telegraph():
    moods = moods_to_emit("soldier")
    assert ("alert", 0.3) in moods


def test_unknown_archetype_no_moods():
    assert moods_to_emit("unknown_role") == []


def test_other_event_returns_empty():
    """Only 'aoe_telegraph_visible_to_self' is encoded here; the
    orchestrator owns the dodged/hit cases."""
    assert moods_to_emit("hero", event="dodged_aoe") == []


# ----------------------------------------------------------------------
# Integration scenario: enemy boss cone
# ----------------------------------------------------------------------

def test_dragon_breath_cone_hits_party_in_front():
    reg = TelegraphRegistry()
    spec = TelegraphSpec(
        spell_id="dragon_breath",
        shape=TelegraphShape.CONE,
        element="fire",
        radius_cm=2000, angle_deg=120,
    )
    inst = reg.begin_targeting(
        spec=spec, caster_id="dragon_nm", caster_faction="enemy",
        target_position=(0, 0), facing_deg=0,
    )
    reg.commit_cast(inst.instance_id, cast_duration=3.0, now=0)
    # Doc claim: 3.0s cast = 1.5s reaction window
    assert reaction_window_seconds(inst.cast_duration) == 1.5

    hit = reg.complete(
        inst.instance_id, now=3.0,
        candidate_targets=[
            ("tank", (1500, 200)),       # in cone
            ("dps_back", (1500, 1500)),  # outside arc
            ("healer", (-500, 0)),       # behind dragon
        ],
    )
    assert "tank" in hit
    assert "dps_back" not in hit
    assert "healer" not in hit
