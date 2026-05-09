"""Tests for player_herbology."""
from __future__ import annotations

from server.player_herbology import (
    PlayerHerbologySystem, PlantTier, Effect,
)


def _populate(s: PlayerHerbologySystem) -> None:
    s.register_plant(
        plant_id="dandelion", common_name="Dandelion",
        tier=PlantTier.COMMON, id_difficulty=20,
        primary_effect=Effect.HEAL,
    )
    s.register_plant(
        plant_id="moonbloom",
        common_name="Moonbloom",
        tier=PlantTier.UNCOMMON, id_difficulty=50,
        primary_effect=Effect.SLEEP,
    )
    s.register_plant(
        plant_id="silverroot",
        common_name="Silverroot",
        tier=PlantTier.RARE, id_difficulty=75,
        primary_effect=Effect.ANTITOXIN,
    )
    s.register_plant(
        plant_id="phoenix_lily",
        common_name="Phoenix Lily",
        tier=PlantTier.LEGENDARY,
        id_difficulty=95,
        primary_effect=Effect.VIGOR,
    )


def test_register_plant_happy():
    s = PlayerHerbologySystem()
    assert s.register_plant(
        plant_id="x", common_name="X",
        tier=PlantTier.COMMON, id_difficulty=10,
        primary_effect=Effect.HEAL,
    ) is True


def test_register_duplicate_blocked():
    s = PlayerHerbologySystem()
    s.register_plant(
        plant_id="x", common_name="X",
        tier=PlantTier.COMMON, id_difficulty=10,
        primary_effect=Effect.HEAL,
    )
    assert s.register_plant(
        plant_id="x", common_name="Other",
        tier=PlantTier.RARE, id_difficulty=80,
        primary_effect=Effect.SLEEP,
    ) is False


def test_register_invalid_difficulty():
    s = PlayerHerbologySystem()
    assert s.register_plant(
        plant_id="x", common_name="X",
        tier=PlantTier.COMMON, id_difficulty=0,
        primary_effect=Effect.HEAL,
    ) is False


def test_identify_happy():
    s = PlayerHerbologySystem()
    _populate(s)
    # skill 50 + variance up to 19 vs difficulty 20
    assert s.identify(
        botanist_id="naji", plant_id="dandelion",
        observer_skill=50, seed=0,
    ) is True


def test_identify_failure_low_skill():
    s = PlayerHerbologySystem()
    _populate(s)
    # skill 1 + variance(0..19) vs difficulty 95
    # max 1+19=20 < 95 → always fails
    assert s.identify(
        botanist_id="naji",
        plant_id="phoenix_lily",
        observer_skill=1, seed=19,
    ) is False


def test_identify_master_succeeds():
    s = PlayerHerbologySystem()
    _populate(s)
    # skill 100 + variance > 95 always
    assert s.identify(
        botanist_id="naji",
        plant_id="phoenix_lily",
        observer_skill=100, seed=0,
    ) is True


def test_identify_unknown_plant():
    s = PlayerHerbologySystem()
    assert s.identify(
        botanist_id="naji", plant_id="ghost",
        observer_skill=50, seed=0,
    ) is False


def test_identify_invalid_skill():
    s = PlayerHerbologySystem()
    _populate(s)
    assert s.identify(
        botanist_id="naji", plant_id="dandelion",
        observer_skill=200, seed=0,
    ) is False


def test_almanac_grows():
    s = PlayerHerbologySystem()
    _populate(s)
    s.identify(
        botanist_id="naji", plant_id="dandelion",
        observer_skill=100, seed=0,
    )
    s.identify(
        botanist_id="naji", plant_id="moonbloom",
        observer_skill=100, seed=0,
    )
    almanac = s.almanac(botanist_id="naji")
    assert len(almanac) == 2


def test_failed_id_not_in_almanac():
    s = PlayerHerbologySystem()
    _populate(s)
    s.identify(
        botanist_id="naji",
        plant_id="phoenix_lily",
        observer_skill=1, seed=0,
    )
    assert s.almanac(botanist_id="naji") == []


def test_almanac_unknown_botanist():
    s = PlayerHerbologySystem()
    assert s.almanac(botanist_id="ghost") == []


def test_brew_remedy_happy():
    s = PlayerHerbologySystem()
    _populate(s)
    s.identify(
        botanist_id="naji", plant_id="dandelion",
        observer_skill=100, seed=0,
    )
    s.identify(
        botanist_id="naji", plant_id="moonbloom",
        observer_skill=100, seed=0,
    )
    rid = s.brew_remedy(
        brewer_id="naji",
        plant_ids=("dandelion", "moonbloom"),
        brewer_skill=70,
    )
    assert rid is not None


def test_brew_remedy_potency_formula():
    s = PlayerHerbologySystem()
    _populate(s)
    s.identify(
        botanist_id="naji", plant_id="dandelion",
        observer_skill=100, seed=0,
    )
    s.identify(
        botanist_id="naji", plant_id="silverroot",
        observer_skill=100, seed=0,
    )
    rid = s.brew_remedy(
        brewer_id="naji",
        plant_ids=("dandelion", "silverroot"),
        brewer_skill=70,
    )
    r = s.remedy(remedy_id=rid)
    # 70 + (1+3)*5 = 90
    assert r.potency == 90


def test_brew_too_few_plants():
    s = PlayerHerbologySystem()
    _populate(s)
    s.identify(
        botanist_id="naji", plant_id="dandelion",
        observer_skill=100, seed=0,
    )
    assert s.brew_remedy(
        brewer_id="naji", plant_ids=("dandelion",),
        brewer_skill=50,
    ) is None


def test_brew_too_many_plants():
    s = PlayerHerbologySystem()
    _populate(s)
    for pid in (
        "dandelion", "moonbloom", "silverroot",
        "phoenix_lily",
    ):
        s.identify(
            botanist_id="naji", plant_id=pid,
            observer_skill=100, seed=0,
        )
    assert s.brew_remedy(
        brewer_id="naji",
        plant_ids=(
            "dandelion", "moonbloom", "silverroot",
            "phoenix_lily",
        ),
        brewer_skill=50,
    ) is None


def test_brew_unknown_plant_blocked():
    s = PlayerHerbologySystem()
    _populate(s)
    s.identify(
        botanist_id="naji", plant_id="dandelion",
        observer_skill=100, seed=0,
    )
    # Trying to brew with an unidentified plant
    assert s.brew_remedy(
        brewer_id="naji",
        plant_ids=("dandelion", "moonbloom"),
        brewer_skill=50,
    ) is None


def test_brew_duplicate_plants_blocked():
    s = PlayerHerbologySystem()
    _populate(s)
    s.identify(
        botanist_id="naji", plant_id="dandelion",
        observer_skill=100, seed=0,
    )
    assert s.brew_remedy(
        brewer_id="naji",
        plant_ids=("dandelion", "dandelion"),
        brewer_skill=50,
    ) is None


def test_brew_unknown_brewer():
    s = PlayerHerbologySystem()
    assert s.brew_remedy(
        brewer_id="ghost",
        plant_ids=("a", "b"), brewer_skill=50,
    ) is None


def test_remedy_effects_distinct():
    s = PlayerHerbologySystem()
    _populate(s)
    for pid in ("dandelion", "moonbloom"):
        s.identify(
            botanist_id="naji", plant_id=pid,
            observer_skill=100, seed=0,
        )
    rid = s.brew_remedy(
        brewer_id="naji",
        plant_ids=("dandelion", "moonbloom"),
        brewer_skill=50,
    )
    r = s.remedy(remedy_id=rid)
    assert set(r.effects) == {Effect.HEAL, Effect.SLEEP}


def test_unknown_remedy():
    s = PlayerHerbologySystem()
    assert s.remedy(remedy_id="ghost") is None


def test_unknown_plant_lookup():
    s = PlayerHerbologySystem()
    assert s.plant(plant_id="ghost") is None


def test_enum_counts():
    assert len(list(PlantTier)) == 4
    assert len(list(Effect)) == 5
