"""Tests for the pet tactical advisor."""
from __future__ import annotations

from server.pet_tactical_advisor import (
    MasterState,
    PetKind,
    PetMode,
    PetState,
    PetTacticalAdvisor,
)


def _master(**overrides) -> MasterState:
    base = dict(
        master_id="alice",
        hp_pct=80, mp_pct=80,
        engaged_target_id="goblin_1",
        casting_or_ws=False,
        last_command_id=None,
        is_in_combat=True,
    )
    base.update(overrides)
    return MasterState(**base)


def _pet(**overrides) -> PetState:
    base = dict(
        pet_id="auto", kind=PetKind.PUPPET,
        hp_pct=100, mp_pct=100, pup_oil_pct=100,
        has_signature_ready=False,
        engaged_target_id=None,
        distance_to_master_tiles=5,
    )
    base.update(overrides)
    return PetState(**base)


def test_pet_assists_master_default():
    advisor = PetTacticalAdvisor()
    intent = advisor.recommend(pet=_pet(), master=_master())
    assert intent.mode == PetMode.ASSIST
    assert intent.primary_target_id == "goblin_1"


def test_master_low_hp_pet_defends():
    advisor = PetTacticalAdvisor()
    intent = advisor.recommend(
        pet=_pet(),
        master=_master(hp_pct=20),
    )
    assert intent.mode == PetMode.DEFEND_MASTER


def test_pet_low_hp_recovers():
    advisor = PetTacticalAdvisor()
    intent = advisor.recommend(
        pet=_pet(hp_pct=20),
        master=_master(),
    )
    assert intent.mode == PetMode.RECOVER
    assert intent.primary_target_id is None


def test_pup_low_oil_recommends_recall():
    advisor = PetTacticalAdvisor()
    intent = advisor.recommend(
        pet=_pet(kind=PetKind.PUPPET, pup_oil_pct=2),
        master=_master(),
    )
    assert intent.recall_recommended


def test_smn_avatar_low_mp_recommends_recall():
    advisor = PetTacticalAdvisor()
    intent = advisor.recommend(
        pet=_pet(kind=PetKind.AVATAR, mp_pct=3),
        master=_master(),
    )
    assert intent.recall_recommended


def test_beast_pet_critical_hp_recommends_recall():
    advisor = PetTacticalAdvisor()
    intent = advisor.recommend(
        pet=_pet(kind=PetKind.BEAST, hp_pct=2),
        master=_master(),
    )
    assert intent.recall_recommended


def test_pet_far_from_master_in_combat_retreats():
    advisor = PetTacticalAdvisor()
    intent = advisor.recommend(
        pet=_pet(distance_to_master_tiles=50),
        master=_master(),
    )
    assert intent.mode == PetMode.RETREAT_TO_MASTER


def test_pet_far_from_master_out_of_combat_does_not_panic():
    """Out of combat, distance doesn't trigger retreat."""
    advisor = PetTacticalAdvisor()
    intent = advisor.recommend(
        pet=_pet(distance_to_master_tiles=50),
        master=_master(is_in_combat=False, engaged_target_id=None),
    )
    # No engaged target -> EXECUTE_COMMAND if any, else
    # RETREAT_TO_MASTER (the "hold by master" default)
    assert intent.mode in (
        PetMode.RETREAT_TO_MASTER, PetMode.EXECUTE_COMMAND,
    )


def test_signature_fires_during_master_ws_window():
    """Master mid-WS + pet has signature ready -> SPECIAL."""
    advisor = PetTacticalAdvisor()
    intent = advisor.recommend(
        pet=_pet(has_signature_ready=True),
        master=_master(casting_or_ws=True),
    )
    assert intent.mode == PetMode.SPECIAL
    assert intent.should_use_signature


def test_signature_does_not_fire_if_low_resources():
    """Don't burn the signature if MP/oil is too low to recover."""
    advisor = PetTacticalAdvisor()
    intent = advisor.recommend(
        pet=_pet(
            kind=PetKind.AVATAR,
            has_signature_ready=True, mp_pct=15,
        ),
        master=_master(casting_or_ws=True),
    )
    assert not intent.should_use_signature


def test_no_engaged_target_executes_last_command():
    advisor = PetTacticalAdvisor()
    intent = advisor.recommend(
        pet=_pet(),
        master=_master(
            engaged_target_id=None,
            last_command_id="heel",
            is_in_combat=False,
        ),
    )
    assert intent.mode == PetMode.EXECUTE_COMMAND


def test_no_orders_holds_by_master():
    advisor = PetTacticalAdvisor()
    intent = advisor.recommend(
        pet=_pet(),
        master=_master(
            engaged_target_id=None,
            last_command_id=None,
            is_in_combat=False,
        ),
    )
    assert intent.mode == PetMode.RETREAT_TO_MASTER


def test_full_lifecycle_pup_battle():
    """PUP fight: assist -> master takes hits -> defend ->
    pet takes hits -> recover -> oil low -> recall."""
    advisor = PetTacticalAdvisor()
    # Start: assist
    i1 = advisor.recommend(pet=_pet(), master=_master())
    assert i1.mode == PetMode.ASSIST
    # Master HP drops
    i2 = advisor.recommend(
        pet=_pet(), master=_master(hp_pct=20),
    )
    assert i2.mode == PetMode.DEFEND_MASTER
    # Pet HP drops
    i3 = advisor.recommend(
        pet=_pet(hp_pct=20), master=_master(),
    )
    assert i3.mode == PetMode.RECOVER
    # Long fight, oil running out
    i4 = advisor.recommend(
        pet=_pet(pup_oil_pct=3),
        master=_master(),
    )
    assert i4.recall_recommended
