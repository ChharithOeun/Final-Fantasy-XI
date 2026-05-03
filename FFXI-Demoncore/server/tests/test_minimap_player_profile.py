"""Tests for the minimap player profile registry."""
from __future__ import annotations

from server.minimap_player_profile import (
    AudienceLevel,
    MinimapPlayerProfileRegistry,
)


def _seed_alice(reg: MinimapPlayerProfileRegistry):
    reg.upsert_profile(
        player_id="alice", name="Alice", nation="Bastok",
        level=75, main_job="WAR", sub_job="NIN",
        title="Avatar Slayer", linkshell="VanguardLS",
        fame=850, playtime_hours=1200,
    )


def test_upsert_creates_profile():
    reg = MinimapPlayerProfileRegistry()
    _seed_alice(reg)
    assert reg.total_profiles() == 1


def test_snapshot_unknown_player_returns_none():
    reg = MinimapPlayerProfileRegistry()
    assert reg.snapshot_for(
        viewer_id="bob", target_id="ghost",
    ) is None


def test_stranger_sees_minimal_fields():
    reg = MinimapPlayerProfileRegistry()
    _seed_alice(reg)
    snap = reg.snapshot_for(
        viewer_id="bob", target_id="alice",
    )
    assert snap.audience == AudienceLevel.STRANGER
    assert "name" in snap.fields
    assert "nation" in snap.fields
    assert "level" not in snap.fields
    assert "fame" not in snap.fields


def test_party_sees_more():
    reg = MinimapPlayerProfileRegistry()
    _seed_alice(reg)
    reg.declare_relation(
        viewer_id="bob", target_id="alice",
        audience=AudienceLevel.PARTY,
    )
    snap = reg.snapshot_for(
        viewer_id="bob", target_id="alice",
    )
    assert snap.audience == AudienceLevel.PARTY
    assert "level" in snap.fields
    assert "main_job" in snap.fields
    assert "sub_job" in snap.fields
    assert "title" in snap.fields


def test_friend_sees_everything():
    reg = MinimapPlayerProfileRegistry()
    _seed_alice(reg)
    reg.declare_relation(
        viewer_id="bob", target_id="alice",
        audience=AudienceLevel.FRIEND,
    )
    snap = reg.snapshot_for(
        viewer_id="bob", target_id="alice",
    )
    assert "fame" in snap.fields
    assert "playtime_hours" in snap.fields


def test_linkshell_audience():
    reg = MinimapPlayerProfileRegistry()
    _seed_alice(reg)
    reg.declare_relation(
        viewer_id="bob", target_id="alice",
        audience=AudienceLevel.LINKSHELL,
    )
    snap = reg.snapshot_for(
        viewer_id="bob", target_id="alice",
    )
    assert "linkshell" in snap.fields
    assert "main_job" in snap.fields
    assert "playtime_hours" not in snap.fields


def test_set_privacy_overrides_default():
    reg = MinimapPlayerProfileRegistry()
    _seed_alice(reg)
    reg.set_privacy(
        player_id="alice", audience=AudienceLevel.STRANGER,
        shown_fields=("name",),
    )
    snap = reg.snapshot_for(
        viewer_id="bob", target_id="alice",
    )
    assert "name" in snap.fields
    assert "nation" not in snap.fields


def test_set_privacy_filters_invalid_fields():
    reg = MinimapPlayerProfileRegistry()
    _seed_alice(reg)
    reg.set_privacy(
        player_id="alice",
        audience=AudienceLevel.STRANGER,
        shown_fields=("name", "ssn", "credit_card"),
    )
    snap = reg.snapshot_for(
        viewer_id="bob", target_id="alice",
    )
    assert "name" in snap.fields
    assert "ssn" not in snap.fields
    assert "credit_card" not in snap.fields


def test_set_privacy_unknown_player():
    reg = MinimapPlayerProfileRegistry()
    assert not reg.set_privacy(
        player_id="ghost",
        audience=AudienceLevel.STRANGER,
        shown_fields=("name",),
    )


def test_declare_self_relation_rejected():
    reg = MinimapPlayerProfileRegistry()
    _seed_alice(reg)
    assert not reg.declare_relation(
        viewer_id="alice", target_id="alice",
        audience=AudienceLevel.FRIEND,
    )


def test_relation_default_is_stranger():
    reg = MinimapPlayerProfileRegistry()
    _seed_alice(reg)
    assert reg.relation(
        viewer_id="bob", target_id="alice",
    ) == AudienceLevel.STRANGER


def test_outlaw_flag_visible_to_stranger():
    reg = MinimapPlayerProfileRegistry()
    _seed_alice(reg)
    reg.upsert_profile(
        player_id="alice", outlaw_flag=True,
    )
    snap = reg.snapshot_for(
        viewer_id="bob", target_id="alice",
    )
    assert snap.fields.get("outlaw_flag") is True


def test_outlaw_flag_hidden_when_clean():
    reg = MinimapPlayerProfileRegistry()
    _seed_alice(reg)
    snap = reg.snapshot_for(
        viewer_id="bob", target_id="alice",
    )
    assert "outlaw_flag" not in snap.fields


def test_upsert_updates_existing():
    reg = MinimapPlayerProfileRegistry()
    _seed_alice(reg)
    reg.upsert_profile(
        player_id="alice", level=99, title="Sky Lord",
    )
    reg.declare_relation(
        viewer_id="bob", target_id="alice",
        audience=AudienceLevel.PARTY,
    )
    snap = reg.snapshot_for(
        viewer_id="bob", target_id="alice",
    )
    assert snap.fields["level"] == 99
    assert snap.fields["title"] == "Sky Lord"


def test_per_viewer_isolation():
    reg = MinimapPlayerProfileRegistry()
    _seed_alice(reg)
    reg.declare_relation(
        viewer_id="bob", target_id="alice",
        audience=AudienceLevel.FRIEND,
    )
    snap_bob = reg.snapshot_for(
        viewer_id="bob", target_id="alice",
    )
    snap_carol = reg.snapshot_for(
        viewer_id="carol", target_id="alice",
    )
    assert snap_bob.audience == AudienceLevel.FRIEND
    assert snap_carol.audience == AudienceLevel.STRANGER


def test_total_profiles_count():
    reg = MinimapPlayerProfileRegistry()
    reg.upsert_profile(player_id="a", name="A")
    reg.upsert_profile(player_id="b", name="B")
    assert reg.total_profiles() == 2


def test_unknown_field_in_upsert_ignored():
    reg = MinimapPlayerProfileRegistry()
    reg.upsert_profile(
        player_id="alice", name="Alice",
        bogus_field="foo",
    )
    # Doesn't error and doesn't add the field
    snap = reg.snapshot_for(
        viewer_id="bob", target_id="alice",
    )
    assert "bogus_field" not in snap.fields
