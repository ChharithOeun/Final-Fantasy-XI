"""Tests for artisan_specialization."""
from __future__ import annotations

from server.artisan_specialization import (
    ArtisanSpecialization, Craft, SpecializationDefinition,
)


def _weaponsmith_def():
    return SpecializationDefinition(
        craft=Craft.SMITHING,
        specialization_id="weaponsmith",
        title="Weaponsmith",
        families=("sword", "axe", "polearm"),
        bonus=5, penalty=-5,
    )


def _armorsmith_def():
    return SpecializationDefinition(
        craft=Craft.SMITHING,
        specialization_id="armorsmith",
        title="Armorsmith",
        families=("breastplate", "helm", "gauntlets"),
        bonus=5, penalty=-5,
    )


def test_register_specialization():
    a = ArtisanSpecialization()
    assert a.register_specialization(
        _weaponsmith_def(),
    ) is True


def test_register_blank_id_blocked():
    a = ArtisanSpecialization()
    bad = SpecializationDefinition(
        craft=Craft.SMITHING, specialization_id="",
        title="x", families=("sword",),
        bonus=5, penalty=-5,
    )
    assert a.register_specialization(bad) is False


def test_register_no_families_blocked():
    a = ArtisanSpecialization()
    bad = SpecializationDefinition(
        craft=Craft.SMITHING, specialization_id="x",
        title="x", families=(),
        bonus=5, penalty=-5,
    )
    assert a.register_specialization(bad) is False


def test_register_negative_bonus_blocked():
    a = ArtisanSpecialization()
    bad = SpecializationDefinition(
        craft=Craft.SMITHING, specialization_id="x",
        title="x", families=("sword",),
        bonus=-5, penalty=-5,
    )
    assert a.register_specialization(bad) is False


def test_register_positive_penalty_blocked():
    a = ArtisanSpecialization()
    bad = SpecializationDefinition(
        craft=Craft.SMITHING, specialization_id="x",
        title="x", families=("sword",),
        bonus=5, penalty=5,
    )
    assert a.register_specialization(bad) is False


def test_register_dup_blocked():
    a = ArtisanSpecialization()
    a.register_specialization(_weaponsmith_def())
    assert a.register_specialization(
        _weaponsmith_def(),
    ) is False


def test_commit_happy():
    a = ArtisanSpecialization()
    a.register_specialization(_weaponsmith_def())
    assert a.commit(
        crafter_id="cid", craft=Craft.SMITHING,
        specialization_id="weaponsmith", now_day=10,
    ) is True


def test_commit_blank_crafter_blocked():
    a = ArtisanSpecialization()
    a.register_specialization(_weaponsmith_def())
    assert a.commit(
        crafter_id="", craft=Craft.SMITHING,
        specialization_id="weaponsmith", now_day=10,
    ) is False


def test_commit_unknown_specialization():
    a = ArtisanSpecialization()
    assert a.commit(
        crafter_id="cid", craft=Craft.SMITHING,
        specialization_id="ghost", now_day=10,
    ) is False


def test_commit_already_committed_blocked():
    a = ArtisanSpecialization()
    a.register_specialization(_weaponsmith_def())
    a.commit(
        crafter_id="cid", craft=Craft.SMITHING,
        specialization_id="weaponsmith", now_day=10,
    )
    assert a.commit(
        crafter_id="cid", craft=Craft.SMITHING,
        specialization_id="weaponsmith", now_day=11,
    ) is False


def test_skill_bonus_in_family():
    a = ArtisanSpecialization()
    a.register_specialization(_weaponsmith_def())
    a.commit(
        crafter_id="cid", craft=Craft.SMITHING,
        specialization_id="weaponsmith", now_day=10,
    )
    assert a.effective_skill_modifier(
        crafter_id="cid", craft=Craft.SMITHING,
        recipe_family="sword",
    ) == 5


def test_skill_penalty_outside_family():
    a = ArtisanSpecialization()
    a.register_specialization(_weaponsmith_def())
    a.commit(
        crafter_id="cid", craft=Craft.SMITHING,
        specialization_id="weaponsmith", now_day=10,
    )
    assert a.effective_skill_modifier(
        crafter_id="cid", craft=Craft.SMITHING,
        recipe_family="breastplate",
    ) == -5


def test_skill_zero_uncommitted():
    a = ArtisanSpecialization()
    assert a.effective_skill_modifier(
        crafter_id="cid", craft=Craft.SMITHING,
        recipe_family="sword",
    ) == 0


def test_switch_specialization():
    a = ArtisanSpecialization()
    a.register_specialization(_weaponsmith_def())
    a.register_specialization(_armorsmith_def())
    a.commit(
        crafter_id="cid", craft=Craft.SMITHING,
        specialization_id="weaponsmith", now_day=10,
    )
    assert a.switch(
        crafter_id="cid", craft=Craft.SMITHING,
        new_specialization_id="armorsmith", now_day=20,
    ) is True
    assert a.current(
        crafter_id="cid", craft=Craft.SMITHING,
    ) == "armorsmith"


def test_switch_to_same_spec_blocked():
    a = ArtisanSpecialization()
    a.register_specialization(_weaponsmith_def())
    a.commit(
        crafter_id="cid", craft=Craft.SMITHING,
        specialization_id="weaponsmith", now_day=10,
    )
    assert a.switch(
        crafter_id="cid", craft=Craft.SMITHING,
        new_specialization_id="weaponsmith", now_day=20,
    ) is False


def test_switch_uncommitted_blocked():
    a = ArtisanSpecialization()
    a.register_specialization(_weaponsmith_def())
    assert a.switch(
        crafter_id="cid", craft=Craft.SMITHING,
        new_specialization_id="weaponsmith", now_day=20,
    ) is False


def test_switch_during_lockout_blocked():
    a = ArtisanSpecialization()
    a.register_specialization(_weaponsmith_def())
    a.register_specialization(_armorsmith_def())
    a.commit(
        crafter_id="cid", craft=Craft.SMITHING,
        specialization_id="weaponsmith", now_day=10,
    )
    a.switch(
        crafter_id="cid", craft=Craft.SMITHING,
        new_specialization_id="armorsmith", now_day=20,
    )
    # 7-day lockout; now_day=23 is too soon
    assert a.switch(
        crafter_id="cid", craft=Craft.SMITHING,
        new_specialization_id="weaponsmith", now_day=23,
    ) is False


def test_switch_after_lockout():
    a = ArtisanSpecialization()
    a.register_specialization(_weaponsmith_def())
    a.register_specialization(_armorsmith_def())
    a.commit(
        crafter_id="cid", craft=Craft.SMITHING,
        specialization_id="weaponsmith", now_day=10,
    )
    a.switch(
        crafter_id="cid", craft=Craft.SMITHING,
        new_specialization_id="armorsmith", now_day=20,
    )
    # now_day=30 is past 27 lockout
    assert a.switch(
        crafter_id="cid", craft=Craft.SMITHING,
        new_specialization_id="weaponsmith", now_day=30,
    ) is True


def test_lockout_until():
    a = ArtisanSpecialization()
    a.register_specialization(_weaponsmith_def())
    a.register_specialization(_armorsmith_def())
    a.commit(
        crafter_id="cid", craft=Craft.SMITHING,
        specialization_id="weaponsmith", now_day=10,
    )
    a.switch(
        crafter_id="cid", craft=Craft.SMITHING,
        new_specialization_id="armorsmith", now_day=20,
    )
    assert a.lockout_until(
        crafter_id="cid", craft=Craft.SMITHING,
    ) == 27


def test_current_unknown():
    a = ArtisanSpecialization()
    assert a.current(
        crafter_id="cid", craft=Craft.SMITHING,
    ) is None


def test_seven_crafts():
    assert len(list(Craft)) == 7
