"""Tests for cutscene_recast."""
from __future__ import annotations

from server.cutscene_recast import (
    CutsceneRecastSystem, Resolution, StaleReason,
)


def test_register_happy():
    s = CutsceneRecastSystem()
    assert s.register(
        cutscene_id="cs_volker_oath",
        title="Volker's Oath",
        resolution=Resolution.LIVE_RECAST,
    ) is True


def test_register_blank():
    s = CutsceneRecastSystem()
    assert s.register(
        cutscene_id="", title="x",
        resolution=Resolution.LIVE_RECAST,
    ) is False


def test_register_dup_blocked():
    s = CutsceneRecastSystem()
    s.register(
        cutscene_id="cs1", title="x",
        resolution=Resolution.LIVE_RECAST,
    )
    assert s.register(
        cutscene_id="cs1", title="y",
        resolution=Resolution.LIVE_RECAST,
    ) is False


def test_add_role_happy():
    s = CutsceneRecastSystem()
    s.register(
        cutscene_id="cs1", title="x",
        resolution=Resolution.LIVE_RECAST,
    )
    assert s.add_role(
        cutscene_id="cs1", role="hero",
        npc_id="off_volker",
        expected_faction="bastok",
    ) is True


def test_add_role_unknown_cutscene():
    s = CutsceneRecastSystem()
    assert s.add_role(
        cutscene_id="ghost", role="hero",
        npc_id="o", expected_faction="bastok",
    ) is False


def test_add_role_replaces_same_role():
    s = CutsceneRecastSystem()
    s.register(
        cutscene_id="cs1", title="x",
        resolution=Resolution.LIVE_RECAST,
    )
    s.add_role(
        cutscene_id="cs1", role="hero", npc_id="a",
        expected_faction="bastok",
    )
    s.add_role(
        cutscene_id="cs1", role="hero", npc_id="b",
        expected_faction="bastok",
    )
    c = s.cutscene(cutscene_id="cs1")
    assert len(c.roles) == 1
    assert c.roles[0].npc_id == "b"


def test_set_resolution():
    s = CutsceneRecastSystem()
    s.register(
        cutscene_id="cs1", title="x",
        resolution=Resolution.LIVE_RECAST,
    )
    assert s.set_resolution(
        cutscene_id="cs1",
        resolution=Resolution.HISTORICAL_LOCK,
    ) is True


def test_stale_roles_clean():
    s = CutsceneRecastSystem()
    s.register(
        cutscene_id="cs1", title="x",
        resolution=Resolution.LIVE_RECAST,
    )
    s.add_role(
        cutscene_id="cs1", role="hero",
        npc_id="off_volker",
        expected_faction="bastok",
    )
    out = s.stale_roles(
        cutscene_id="cs1",
        npc_factions={"off_volker": "bastok"},
    )
    assert out == []


def test_stale_roles_detects_defection():
    """The killer test: NPC defected -> stale role
    flagged as NPC_DEFECTED."""
    s = CutsceneRecastSystem()
    s.register(
        cutscene_id="cs_volker_oath",
        title="Volker's Oath",
        resolution=Resolution.LIVE_RECAST,
    )
    s.add_role(
        cutscene_id="cs_volker_oath",
        role="hero", npc_id="off_volker",
        expected_faction="bastok",
    )
    out = s.stale_roles(
        cutscene_id="cs_volker_oath",
        npc_factions={"off_volker": "windy"},
    )
    assert len(out) == 1
    assert out[0].reason == StaleReason.NPC_DEFECTED
    assert out[0].current_faction == "windy"


def test_stale_detects_deceased():
    s = CutsceneRecastSystem()
    s.register(
        cutscene_id="cs1", title="x",
        resolution=Resolution.LIVE_RECAST,
    )
    s.add_role(
        cutscene_id="cs1", role="hero",
        npc_id="o", expected_faction="bastok",
    )
    out = s.stale_roles(
        cutscene_id="cs1",
        npc_factions={"o": "bastok"},
        npc_statuses={"o": "deceased"},
    )
    assert len(out) == 1
    assert out[0].reason == StaleReason.NPC_DECEASED


def test_stale_detects_retired():
    s = CutsceneRecastSystem()
    s.register(
        cutscene_id="cs1", title="x",
        resolution=Resolution.LIVE_RECAST,
    )
    s.add_role(
        cutscene_id="cs1", role="hero",
        npc_id="o", expected_faction="bastok",
    )
    out = s.stale_roles(
        cutscene_id="cs1",
        npc_factions={"o": "bastok"},
        npc_statuses={"o": "retired"},
    )
    assert out[0].reason == StaleReason.NPC_RETIRED


def test_stale_detects_missing():
    s = CutsceneRecastSystem()
    s.register(
        cutscene_id="cs1", title="x",
        resolution=Resolution.LIVE_RECAST,
    )
    s.add_role(
        cutscene_id="cs1", role="hero",
        npc_id="o", expected_faction="bastok",
    )
    out = s.stale_roles(
        cutscene_id="cs1", npc_factions={},
    )
    assert out[0].reason == StaleReason.NPC_MISSING


def test_is_playable_clean_cast():
    s = CutsceneRecastSystem()
    s.register(
        cutscene_id="cs1", title="x",
        resolution=Resolution.LIVE_RECAST,
    )
    s.add_role(
        cutscene_id="cs1", role="hero",
        npc_id="o", expected_faction="bastok",
    )
    assert s.is_playable(
        cutscene_id="cs1",
        npc_factions={"o": "bastok"},
    ) is True


def test_is_playable_skip_resolution():
    s = CutsceneRecastSystem()
    s.register(
        cutscene_id="cs1", title="x",
        resolution=Resolution.SKIP,
    )
    assert s.is_playable(
        cutscene_id="cs1", npc_factions={},
    ) is False


def test_is_playable_historical_lock():
    s = CutsceneRecastSystem()
    s.register(
        cutscene_id="cs1", title="x",
        resolution=Resolution.HISTORICAL_LOCK,
    )
    s.add_role(
        cutscene_id="cs1", role="hero",
        npc_id="o", expected_faction="bastok",
    )
    # NPC defected, but HISTORICAL_LOCK plays anyway
    assert s.is_playable(
        cutscene_id="cs1",
        npc_factions={"o": "windy"},
    ) is True


def test_is_playable_live_recast_no_assets():
    s = CutsceneRecastSystem()
    s.register(
        cutscene_id="cs1", title="x",
        resolution=Resolution.LIVE_RECAST,
        has_recast_assets=False,
    )
    s.add_role(
        cutscene_id="cs1", role="hero",
        npc_id="o", expected_faction="bastok",
    )
    # NPC defected and no recast assets — can't play
    assert s.is_playable(
        cutscene_id="cs1",
        npc_factions={"o": "windy"},
    ) is False


def test_is_playable_live_recast_with_assets():
    s = CutsceneRecastSystem()
    s.register(
        cutscene_id="cs1", title="x",
        resolution=Resolution.LIVE_RECAST,
        has_recast_assets=True,
    )
    s.add_role(
        cutscene_id="cs1", role="hero",
        npc_id="o", expected_faction="bastok",
    )
    assert s.is_playable(
        cutscene_id="cs1",
        npc_factions={"o": "windy"},
    ) is True


def test_cutscene_unknown():
    s = CutsceneRecastSystem()
    assert s.cutscene(
        cutscene_id="ghost",
    ) is None


def test_all_cutscenes():
    s = CutsceneRecastSystem()
    s.register(
        cutscene_id="a", title="x",
        resolution=Resolution.LIVE_RECAST,
    )
    s.register(
        cutscene_id="b", title="y",
        resolution=Resolution.HISTORICAL_LOCK,
    )
    assert len(s.all_cutscenes()) == 2


def test_enum_counts():
    assert len(list(Resolution)) == 3
    assert len(list(StaleReason)) == 4
