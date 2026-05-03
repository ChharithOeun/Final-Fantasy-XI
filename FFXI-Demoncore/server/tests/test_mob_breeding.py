"""Tests for mob breeding."""
from __future__ import annotations

from server.mob_breeding import (
    LifeStage,
    MobBreedingRegistry,
    SECONDS_TO_ADULT,
    SECONDS_TO_ELDER,
    SECONDS_TO_JUVENILE,
)


def test_register_pack_with_founders():
    reg = MobBreedingRegistry()
    pack = reg.register_pack(
        pack_id="orc_clan_a", mob_kind="orc",
        founders=("orc_001", "orc_002"),
        base_traits={"ferocity": 0.8},
    )
    assert pack is not None
    assert len(pack.members) == 2
    assert reg.total_individuals() == 2


def test_double_register_rejected():
    reg = MobBreedingRegistry()
    reg.register_pack(
        pack_id="p1", mob_kind="orc",
        founders=("orc_001",),
    )
    second = reg.register_pack(
        pack_id="p1", mob_kind="orc",
    )
    assert second is None


def test_founders_start_adult():
    reg = MobBreedingRegistry()
    reg.register_pack(
        pack_id="p1", mob_kind="orc",
        founders=("orc_001",),
    )
    ind = reg.individual("orc_001")
    assert ind.stage == LifeStage.ADULT


def test_breed_creates_cub():
    reg = MobBreedingRegistry()
    reg.register_pack(
        pack_id="p1", mob_kind="orc",
        founders=("sire_a", "dam_b"),
        base_traits={"ferocity": 0.8},
    )
    event = reg.breed(
        pack_id="p1", sire_id="sire_a", dam_id="dam_b",
    )
    assert event is not None
    cub = reg.individual(event.cub_uid)
    assert cub.stage == LifeStage.CUB
    assert cub.generation == 1


def test_breed_unknown_pack():
    reg = MobBreedingRegistry()
    assert reg.breed(
        pack_id="ghost", sire_id="x", dam_id="y",
    ) is None


def test_breed_unknown_parent():
    reg = MobBreedingRegistry()
    reg.register_pack(
        pack_id="p1", mob_kind="orc",
        founders=("sire_a",),
    )
    assert reg.breed(
        pack_id="p1", sire_id="sire_a", dam_id="ghost",
    ) is None


def test_breed_cub_cannot_breed():
    reg = MobBreedingRegistry()
    reg.register_pack(
        pack_id="p1", mob_kind="orc",
        founders=("sire_a", "dam_b"),
    )
    event = reg.breed(
        pack_id="p1", sire_id="sire_a", dam_id="dam_b",
    )
    cub_uid = event.cub_uid
    # Try to breed with the cub
    assert reg.breed(
        pack_id="p1", sire_id="sire_a", dam_id=cub_uid,
    ) is None


def test_breed_cross_pack_rejected():
    reg = MobBreedingRegistry()
    reg.register_pack(
        pack_id="p1", mob_kind="orc",
        founders=("a",),
    )
    reg.register_pack(
        pack_id="p2", mob_kind="orc",
        founders=("b",),
    )
    assert reg.breed(
        pack_id="p1", sire_id="a", dam_id="b",
    ) is None


def test_traits_inherited_with_fade():
    reg = MobBreedingRegistry(
        trait_fade_per_generation=0.2,
    )
    reg.register_pack(
        pack_id="p1", mob_kind="orc",
        founders=("sire", "dam"),
        base_traits={"ferocity": 1.0},
    )
    event = reg.breed(
        pack_id="p1", sire_id="sire", dam_id="dam",
    )
    cub = reg.individual(event.cub_uid)
    # avg = 1.0, fade 20% -> 0.8
    assert abs(
        cub.inherited_traits["ferocity"] - 0.8
    ) < 0.001


def test_age_step_promotes_cub_to_juvenile():
    reg = MobBreedingRegistry()
    reg.register_pack(
        pack_id="p1", mob_kind="orc",
        founders=("sire", "dam"),
    )
    ev = reg.breed(
        pack_id="p1", sire_id="sire", dam_id="dam",
    )
    affected = reg.age_step(
        elapsed_seconds=SECONDS_TO_JUVENILE + 1,
    )
    assert affected >= 1
    cub = reg.individual(ev.cub_uid)
    assert cub.stage == LifeStage.JUVENILE


def test_age_step_promotes_to_adult_then_elder():
    reg = MobBreedingRegistry()
    reg.register_pack(
        pack_id="p1", mob_kind="orc",
        founders=("sire", "dam"),
    )
    ev = reg.breed(
        pack_id="p1", sire_id="sire", dam_id="dam",
    )
    reg.age_step(elapsed_seconds=SECONDS_TO_ADULT + 1)
    assert reg.individual(ev.cub_uid).stage == LifeStage.ADULT
    reg.age_step(elapsed_seconds=SECONDS_TO_ELDER)
    assert reg.individual(ev.cub_uid).stage == LifeStage.ELDER


def test_zero_elapsed_no_promotion():
    reg = MobBreedingRegistry()
    reg.register_pack(
        pack_id="p1", mob_kind="orc",
        founders=("sire", "dam"),
    )
    ev = reg.breed(
        pack_id="p1", sire_id="sire", dam_id="dam",
    )
    affected = reg.age_step(elapsed_seconds=0.0)
    assert affected == 0


def test_kill_marks_deceased():
    reg = MobBreedingRegistry()
    reg.register_pack(
        pack_id="p1", mob_kind="orc",
        founders=("orc_a",),
    )
    assert reg.kill("orc_a")
    assert reg.individual("orc_a").stage == LifeStage.DECEASED


def test_kill_twice_returns_false():
    reg = MobBreedingRegistry()
    reg.register_pack(
        pack_id="p1", mob_kind="orc",
        founders=("orc_a",),
    )
    reg.kill("orc_a")
    assert not reg.kill("orc_a")


def test_members_of_filter_by_stage():
    reg = MobBreedingRegistry()
    reg.register_pack(
        pack_id="p1", mob_kind="orc",
        founders=("sire", "dam"),
    )
    reg.breed(pack_id="p1", sire_id="sire", dam_id="dam")
    cubs = reg.members_of(
        "p1", stage_filter=LifeStage.CUB,
    )
    adults = reg.members_of(
        "p1", stage_filter=LifeStage.ADULT,
    )
    assert len(cubs) == 1
    assert len(adults) == 2


def test_generation_increments():
    reg = MobBreedingRegistry()
    reg.register_pack(
        pack_id="p1", mob_kind="orc",
        founders=("g0_a", "g0_b"),
    )
    ev1 = reg.breed(
        pack_id="p1", sire_id="g0_a", dam_id="g0_b",
    )
    # Age cub to adult
    reg.age_step(elapsed_seconds=SECONDS_TO_ADULT + 1)
    # Breed g0_a with the new adult (its child) — gen 2
    ev2 = reg.breed(
        pack_id="p1", sire_id="g0_a", dam_id=ev1.cub_uid,
    )
    cub2 = reg.individual(ev2.cub_uid)
    assert cub2.generation == 2
    pack = reg.pack("p1")
    assert pack.generations_observed == 2
