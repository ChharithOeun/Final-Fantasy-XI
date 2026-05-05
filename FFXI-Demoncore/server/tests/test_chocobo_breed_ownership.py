"""Tests for chocobo breed ownership."""
from __future__ import annotations

from server.chocobo_breed_ownership import (
    BreedQuestStage,
    ChocoboBreedOwnership,
    OwnedKind,
)


def test_grant_mount_when_empty():
    o = ChocoboBreedOwnership()
    r = o.grant_mount(player_id="p1", chocobo_id="c1")
    assert r.accepted is True
    slot = o.slot_for(player_id="p1")
    assert slot.kind == OwnedKind.MOUNT
    assert slot.entity_id == "c1"


def test_cannot_have_two_mounts():
    o = ChocoboBreedOwnership()
    o.grant_mount(player_id="p1", chocobo_id="c1")
    r = o.grant_mount(player_id="p1", chocobo_id="c2")
    assert r.accepted is False
    assert "already owns" in r.reason


def test_cannot_have_mount_and_egg():
    o = ChocoboBreedOwnership()
    o.grant_mount(player_id="p1", chocobo_id="c1")
    r = o.grant_egg(player_id="p1", egg_id="e1")
    assert r.accepted is False


def test_grant_egg_when_empty():
    o = ChocoboBreedOwnership()
    r = o.grant_egg(player_id="p1", egg_id="e1")
    assert r.accepted is True
    assert o.slot_for(player_id="p1").kind == OwnedKind.EGG


def test_release_slot_clears_mount():
    o = ChocoboBreedOwnership()
    o.grant_mount(player_id="p1", chocobo_id="c1")
    r = o.release_slot(player_id="p1")
    assert r.accepted is True
    assert o.slot_for(player_id="p1").kind == OwnedKind.NONE


def test_release_blocks_when_locked():
    o = ChocoboBreedOwnership()
    o.grant_mount(player_id="a", chocobo_id="ca")
    o.grant_mount(player_id="b", chocobo_id="cb")
    o.start_cross_breed(
        quest_id="q1",
        player_a="a", chocobo_a="ca",
        player_b="b", chocobo_b="cb",
        owner_of_egg="a",
    )
    r = o.release_slot(player_id="a")
    assert r.accepted is False
    assert r.reason == "locked by quest"


def test_start_cross_breed_happy():
    o = ChocoboBreedOwnership()
    o.grant_mount(player_id="a", chocobo_id="ca")
    o.grant_mount(player_id="b", chocobo_id="cb")
    r = o.start_cross_breed(
        quest_id="q1",
        player_a="a", chocobo_a="ca",
        player_b="b", chocobo_b="cb",
        owner_of_egg="a",
    )
    assert r.accepted is True
    q = o.quest_status(quest_id="q1")
    assert q.stage == BreedQuestStage.PARENTS_LOCKED


def test_start_cross_breed_rejects_same_player():
    o = ChocoboBreedOwnership()
    o.grant_mount(player_id="a", chocobo_id="ca")
    r = o.start_cross_breed(
        quest_id="q1",
        player_a="a", chocobo_a="ca",
        player_b="a", chocobo_b="ca",
        owner_of_egg="a",
    )
    assert r.accepted is False
    assert r.reason == "needs two players"


def test_start_cross_breed_rejects_same_chocobo():
    o = ChocoboBreedOwnership()
    o.grant_mount(player_id="a", chocobo_id="ca")
    o.grant_mount(player_id="b", chocobo_id="ca")  # contrived
    r = o.start_cross_breed(
        quest_id="q1",
        player_a="a", chocobo_a="ca",
        player_b="b", chocobo_b="ca",
        owner_of_egg="a",
    )
    assert r.accepted is False


def test_start_cross_breed_rejects_owner_outside_pair():
    o = ChocoboBreedOwnership()
    o.grant_mount(player_id="a", chocobo_id="ca")
    o.grant_mount(player_id="b", chocobo_id="cb")
    r = o.start_cross_breed(
        quest_id="q1",
        player_a="a", chocobo_a="ca",
        player_b="b", chocobo_b="cb",
        owner_of_egg="c",
    )
    assert r.accepted is False


def test_start_cross_breed_rejects_missing_mount():
    o = ChocoboBreedOwnership()
    o.grant_mount(player_id="a", chocobo_id="ca")
    # b has nothing
    r = o.start_cross_breed(
        quest_id="q1",
        player_a="a", chocobo_a="ca",
        player_b="b", chocobo_b="cb",
        owner_of_egg="a",
    )
    assert r.accepted is False


def test_complete_ritual_assigns_egg_and_unlocks():
    o = ChocoboBreedOwnership()
    o.grant_mount(player_id="a", chocobo_id="ca")
    o.grant_mount(player_id="b", chocobo_id="cb")
    o.start_cross_breed(
        quest_id="q1",
        player_a="a", chocobo_a="ca",
        player_b="b", chocobo_b="cb",
        owner_of_egg="a",
    )
    r = o.complete_ritual(quest_id="q1", egg_id="e_q1")
    assert r.accepted is True
    q = o.quest_status(quest_id="q1")
    assert q.stage == BreedQuestStage.RITUAL_COMPLETE
    # owner now holds the egg, mount displaced
    a_slot = o.slot_for(player_id="a")
    assert a_slot.kind == OwnedKind.EGG
    assert a_slot.entity_id == "e_q1"
    # parents unlocked
    assert a_slot.locked_quest_id is None
    assert o.slot_for(player_id="b").locked_quest_id is None


def test_complete_ritual_unknown_quest():
    o = ChocoboBreedOwnership()
    r = o.complete_ritual(quest_id="ghost", egg_id="e1")
    assert r.accepted is False


def test_complete_ritual_bad_stage():
    o = ChocoboBreedOwnership()
    o.grant_mount(player_id="a", chocobo_id="ca")
    o.grant_mount(player_id="b", chocobo_id="cb")
    o.start_cross_breed(
        quest_id="q1",
        player_a="a", chocobo_a="ca",
        player_b="b", chocobo_b="cb",
        owner_of_egg="a",
    )
    o.complete_ritual(quest_id="q1", egg_id="e1")
    # second time should fail
    r = o.complete_ritual(quest_id="q1", egg_id="e2")
    assert r.accepted is False


def test_player_cannot_join_two_quests():
    o = ChocoboBreedOwnership()
    o.grant_mount(player_id="a", chocobo_id="ca")
    o.grant_mount(player_id="b", chocobo_id="cb")
    o.grant_mount(player_id="d", chocobo_id="cd")
    o.start_cross_breed(
        quest_id="q1",
        player_a="a", chocobo_a="ca",
        player_b="b", chocobo_b="cb",
        owner_of_egg="a",
    )
    r = o.start_cross_breed(
        quest_id="q2",
        player_a="a", chocobo_a="ca",
        player_b="d", chocobo_b="cd",
        owner_of_egg="a",
    )
    assert r.accepted is False
    assert r.reason == "player already in a quest"


def test_grant_rejects_blank_ids():
    o = ChocoboBreedOwnership()
    assert o.grant_mount(player_id="", chocobo_id="c").accepted is False
    assert o.grant_mount(player_id="p", chocobo_id="").accepted is False
