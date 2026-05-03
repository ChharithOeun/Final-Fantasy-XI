"""Tests for the minimap engine."""
from __future__ import annotations

from server.minimap_engine import (
    DotColor,
    DotKind,
    MinimapEngine,
)


def _seed_viewer(eng: MinimapEngine, vid="alice"):
    eng.register_entity(
        entity_id=vid, kind=DotKind.OTHER_PLAYER,
        zone_id="ronfaure", x=0, y=0, z=0,
        display_name="Alice",
    )
    return vid


def test_register_and_total():
    eng = MinimapEngine()
    eng.register_entity(
        entity_id="x", kind=DotKind.MOB_HOSTILE,
        zone_id="z", x=0, y=0,
    )
    assert eng.total_entities() == 1


def test_double_register_rejected():
    eng = MinimapEngine()
    eng.register_entity(
        entity_id="x", kind=DotKind.NPC,
        zone_id="z", x=0, y=0,
    )
    second = eng.register_entity(
        entity_id="x", kind=DotKind.NPC,
        zone_id="z", x=10, y=10,
    )
    assert second is None


def test_self_dot_uses_blue():
    eng = MinimapEngine()
    _seed_viewer(eng)
    snap = eng.snapshot_for(viewer_id="alice")
    self_dot = next(
        d for d in snap.dots if d.entity_id == "alice"
    )
    assert self_dot.kind == DotKind.SELF
    assert self_dot.color == DotColor.BLUE


def test_other_player_yellow():
    eng = MinimapEngine()
    _seed_viewer(eng)
    eng.register_entity(
        entity_id="bob", kind=DotKind.OTHER_PLAYER,
        zone_id="ronfaure", x=10, y=0,
    )
    snap = eng.snapshot_for(viewer_id="alice")
    bob = next(d for d in snap.dots if d.entity_id == "bob")
    assert bob.kind == DotKind.OTHER_PLAYER
    assert bob.color == DotColor.YELLOW


def test_party_member_promoted_to_cyan():
    eng = MinimapEngine()
    _seed_viewer(eng)
    eng.register_entity(
        entity_id="bob", kind=DotKind.OTHER_PLAYER,
        zone_id="ronfaure", x=20, y=0,
    )
    eng.declare_party(
        leader_id="alice", member_ids=["bob"],
    )
    snap = eng.snapshot_for(viewer_id="alice")
    bob = next(d for d in snap.dots if d.entity_id == "bob")
    assert bob.kind == DotKind.PARTY_MEMBER
    assert bob.color == DotColor.CYAN


def test_hostile_mob_red():
    eng = MinimapEngine()
    _seed_viewer(eng)
    eng.register_entity(
        entity_id="orc_a", kind=DotKind.MOB_HOSTILE,
        zone_id="ronfaure", x=15, y=0,
    )
    snap = eng.snapshot_for(viewer_id="alice")
    orc = next(
        d for d in snap.dots if d.entity_id == "orc_a"
    )
    assert orc.color == DotColor.RED


def test_fomor_excluded():
    eng = MinimapEngine()
    _seed_viewer(eng)
    eng.register_entity(
        entity_id="fomor_a", kind=DotKind.MOB_HOSTILE,
        zone_id="ronfaure", x=5, y=0,
    )
    eng.mark_fomor(entity_id="fomor_a")
    snap = eng.snapshot_for(viewer_id="alice")
    ids = {d.entity_id for d in snap.dots}
    assert "fomor_a" not in ids
    assert snap.excluded_fomors == 1


def test_out_of_radius_excluded():
    eng = MinimapEngine()
    _seed_viewer(eng)
    eng.register_entity(
        entity_id="far", kind=DotKind.MOB_HOSTILE,
        zone_id="ronfaure", x=10000, y=0,
    )
    snap = eng.snapshot_for(viewer_id="alice", radius=50.0)
    ids = {d.entity_id for d in snap.dots}
    assert "far" not in ids


def test_different_zone_excluded():
    eng = MinimapEngine()
    _seed_viewer(eng)
    eng.register_entity(
        entity_id="bob", kind=DotKind.OTHER_PLAYER,
        zone_id="other_zone", x=1, y=0,
    )
    snap = eng.snapshot_for(viewer_id="alice")
    ids = {d.entity_id for d in snap.dots}
    assert "bob" not in ids


def test_relative_position_includes_3d_pop():
    """Z delta is preserved so the renderer can pop dots up
    or down to indicate height."""
    eng = MinimapEngine()
    eng.register_entity(
        entity_id="alice", kind=DotKind.OTHER_PLAYER,
        zone_id="z", x=0, y=0, z=0,
    )
    eng.register_entity(
        entity_id="floater", kind=DotKind.MOB_HOSTILE,
        zone_id="z", x=10, y=0, z=20,
    )
    snap = eng.snapshot_for(viewer_id="alice")
    f = next(d for d in snap.dots if d.entity_id == "floater")
    assert f.relative_x == 10
    assert f.relative_z == 20


def test_dots_sorted_by_distance():
    eng = MinimapEngine()
    _seed_viewer(eng)
    eng.register_entity(
        entity_id="far", kind=DotKind.MOB_HOSTILE,
        zone_id="ronfaure", x=50, y=0,
    )
    eng.register_entity(
        entity_id="near", kind=DotKind.MOB_HOSTILE,
        zone_id="ronfaure", x=5, y=0,
    )
    snap = eng.snapshot_for(viewer_id="alice")
    # alice (dist 0) first, then near, then far
    ids = [d.entity_id for d in snap.dots]
    assert ids.index("near") < ids.index("far")


def test_truncation_to_max_dots():
    eng = MinimapEngine(max_dots=3)
    _seed_viewer(eng)
    for i in range(10):
        eng.register_entity(
            entity_id=f"m_{i}", kind=DotKind.MOB_HOSTILE,
            zone_id="ronfaure", x=i + 1, y=0,
        )
    snap = eng.snapshot_for(viewer_id="alice")
    assert len(snap.dots) == 3
    assert snap.truncated == 8


def test_clickable_flag():
    eng = MinimapEngine()
    _seed_viewer(eng)
    eng.register_entity(
        entity_id="bob", kind=DotKind.OTHER_PLAYER,
        zone_id="ronfaure", x=5, y=0,
    )
    snap = eng.snapshot_for(viewer_id="alice")
    bob = next(d for d in snap.dots if d.entity_id == "bob")
    self_dot = next(
        d for d in snap.dots if d.entity_id == "alice"
    )
    assert bob.clickable
    assert not self_dot.clickable


def test_update_position_moves_dot():
    eng = MinimapEngine()
    _seed_viewer(eng)
    eng.register_entity(
        entity_id="bob", kind=DotKind.OTHER_PLAYER,
        zone_id="ronfaure", x=10, y=0,
    )
    eng.update_position(entity_id="bob", x=50, y=0)
    snap = eng.snapshot_for(viewer_id="alice", radius=20.0)
    ids = {d.entity_id for d in snap.dots}
    assert "bob" not in ids


def test_clear_entity():
    eng = MinimapEngine()
    _seed_viewer(eng)
    eng.register_entity(
        entity_id="bob", kind=DotKind.OTHER_PLAYER,
        zone_id="ronfaure", x=10, y=0,
    )
    assert eng.clear_entity(entity_id="bob")
    snap = eng.snapshot_for(viewer_id="alice")
    ids = {d.entity_id for d in snap.dots}
    assert "bob" not in ids


def test_snapshot_unknown_viewer_returns_none():
    eng = MinimapEngine()
    assert eng.snapshot_for(viewer_id="ghost") is None


def test_disband_party_strips_promotion():
    eng = MinimapEngine()
    _seed_viewer(eng)
    eng.register_entity(
        entity_id="bob", kind=DotKind.OTHER_PLAYER,
        zone_id="ronfaure", x=20, y=0,
    )
    eng.declare_party(
        leader_id="alice", member_ids=["bob"],
    )
    eng.disband_party(leader_id="alice")
    snap = eng.snapshot_for(viewer_id="alice")
    bob = next(d for d in snap.dots if d.entity_id == "bob")
    assert bob.kind == DotKind.OTHER_PLAYER


def test_mark_fomor_unknown_returns_false():
    eng = MinimapEngine()
    assert not eng.mark_fomor(entity_id="ghost")


def test_friendly_mob_green():
    eng = MinimapEngine()
    _seed_viewer(eng)
    eng.register_entity(
        entity_id="trust_a", kind=DotKind.MOB_FRIENDLY,
        zone_id="ronfaure", x=2, y=0,
    )
    snap = eng.snapshot_for(viewer_id="alice")
    trust = next(
        d for d in snap.dots if d.entity_id == "trust_a"
    )
    assert trust.color == DotColor.GREEN
