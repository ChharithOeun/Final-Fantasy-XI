"""Tests for blue chocobo mount quest."""
from __future__ import annotations

from server.blue_chocobo_mount_quest import (
    BlueChocoboMountQuest,
    QuestStage,
)


def test_start_basic():
    q = BlueChocoboMountQuest()
    res = q.start_quest(
        player_id="kraw",
        chocobo_id="c1",
        color_name="light_blue",
    )
    assert res.accepted
    assert res.stage == QuestStage.GROOM


def test_start_wrong_color():
    q = BlueChocoboMountQuest()
    res = q.start_quest(
        player_id="kraw",
        chocobo_id="c1",
        color_name="yellow",
    )
    assert not res.accepted


def test_start_double_blocked():
    q = BlueChocoboMountQuest()
    q.start_quest(
        player_id="kraw",
        chocobo_id="c1",
        color_name="light_blue",
    )
    res = q.start_quest(
        player_id="kraw",
        chocobo_id="c1",
        color_name="light_blue",
    )
    assert not res.accepted


def test_advance_groom():
    q = BlueChocoboMountQuest()
    q.start_quest(
        player_id="kraw",
        chocobo_id="c1",
        color_name="light_blue",
    )
    res = q.advance(
        player_id="kraw",
        chocobo_id="c1",
        evidence=frozenset({"brine_lozenge_x5", "dive_demo"}),
    )
    assert res.accepted
    assert res.stage == QuestStage.BREATH_BOND


def test_advance_missing_evidence():
    q = BlueChocoboMountQuest()
    q.start_quest(
        player_id="kraw",
        chocobo_id="c1",
        color_name="light_blue",
    )
    res = q.advance(
        player_id="kraw",
        chocobo_id="c1",
        evidence=frozenset({"brine_lozenge_x5"}),
    )
    assert not res.accepted


def test_full_chain_to_completion():
    q = BlueChocoboMountQuest()
    q.start_quest(
        player_id="kraw",
        chocobo_id="c1",
        color_name="light_blue",
    )
    q.advance(
        player_id="kraw",
        chocobo_id="c1",
        evidence=frozenset({"brine_lozenge_x5", "dive_demo"}),
    )
    q.advance(
        player_id="kraw",
        chocobo_id="c1",
        evidence=frozenset({"bonded_seapearl"}),
    )
    res = q.advance(
        player_id="kraw",
        chocobo_id="c1",
        evidence=frozenset({"depth_200_survived"}),
    )
    assert res.accepted
    assert res.stage == QuestStage.COMPLETED


def test_can_mount_underwater_after_completion():
    q = BlueChocoboMountQuest()
    q.start_quest(
        player_id="kraw",
        chocobo_id="c1",
        color_name="light_blue",
    )
    q.advance(
        player_id="kraw", chocobo_id="c1",
        evidence=frozenset({"brine_lozenge_x5", "dive_demo"}),
    )
    q.advance(
        player_id="kraw", chocobo_id="c1",
        evidence=frozenset({"bonded_seapearl"}),
    )
    q.advance(
        player_id="kraw", chocobo_id="c1",
        evidence=frozenset({"depth_200_survived"}),
    )
    assert q.can_mount_underwater(
        player_id="kraw", chocobo_id="c1",
    )


def test_cannot_mount_before_completion():
    q = BlueChocoboMountQuest()
    q.start_quest(
        player_id="kraw",
        chocobo_id="c1",
        color_name="light_blue",
    )
    assert not q.can_mount_underwater(
        player_id="kraw", chocobo_id="c1",
    )


def test_advance_already_completed():
    q = BlueChocoboMountQuest()
    q.start_quest(
        player_id="kraw",
        chocobo_id="c1",
        color_name="light_blue",
    )
    q.advance(
        player_id="kraw", chocobo_id="c1",
        evidence=frozenset({"brine_lozenge_x5", "dive_demo"}),
    )
    q.advance(
        player_id="kraw", chocobo_id="c1",
        evidence=frozenset({"bonded_seapearl"}),
    )
    q.advance(
        player_id="kraw", chocobo_id="c1",
        evidence=frozenset({"depth_200_survived"}),
    )
    res = q.advance(
        player_id="kraw", chocobo_id="c1",
        evidence=frozenset({"depth_200_survived"}),
    )
    assert not res.accepted


def test_advance_no_quest():
    q = BlueChocoboMountQuest()
    res = q.advance(
        player_id="ghost", chocobo_id="c1",
        evidence=frozenset(),
    )
    assert not res.accepted


def test_per_chocobo_isolation():
    q = BlueChocoboMountQuest()
    q.start_quest(
        player_id="kraw", chocobo_id="c1",
        color_name="light_blue",
    )
    assert q.stage_for(
        player_id="kraw", chocobo_id="c2",
    ) == QuestStage.NOT_STARTED


def test_stage_for_unknown():
    q = BlueChocoboMountQuest()
    assert q.stage_for(
        player_id="ghost", chocobo_id="c1",
    ) == QuestStage.NOT_STARTED


def test_total_quests():
    q = BlueChocoboMountQuest()
    q.start_quest(
        player_id="alice", chocobo_id="c1",
        color_name="light_blue",
    )
    q.start_quest(
        player_id="bob", chocobo_id="c2",
        color_name="light_blue",
    )
    assert q.total_quests() == 2
