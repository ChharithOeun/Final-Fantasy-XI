"""Tests for player_birdwatching."""
from __future__ import annotations

from server.player_birdwatching import (
    PlayerBirdwatchingSystem, Rarity, TimeOfDay,
)


def _populate(s: PlayerBirdwatchingSystem) -> None:
    s.register_species(
        species_id="ronfaure_robin",
        common_name="Ronfaure Robin", rarity=Rarity.COMMON,
        preferred_zones=("ronfaure",),
        active_times=(TimeOfDay.DAWN, TimeOfDay.DAY),
    )
    s.register_species(
        species_id="phoenix",
        common_name="Phoenix", rarity=Rarity.LEGENDARY,
        preferred_zones=("riverne",),
        active_times=(TimeOfDay.DUSK,),
    )
    s.register_species(
        species_id="moogle_owl",
        common_name="Moogle Owl", rarity=Rarity.RARE,
        preferred_zones=("ronfaure", "konschtat"),
        active_times=(TimeOfDay.NIGHT,),
    )


def test_register_species_happy():
    s = PlayerBirdwatchingSystem()
    assert s.register_species(
        species_id="x", common_name="X",
        rarity=Rarity.COMMON,
        preferred_zones=("z",),
        active_times=(TimeOfDay.DAY,),
    ) is True


def test_register_duplicate_blocked():
    s = PlayerBirdwatchingSystem()
    s.register_species(
        species_id="x", common_name="X",
        rarity=Rarity.COMMON,
        preferred_zones=("z",),
        active_times=(TimeOfDay.DAY,),
    )
    assert s.register_species(
        species_id="x", common_name="Other",
        rarity=Rarity.RARE,
        preferred_zones=("z",),
        active_times=(TimeOfDay.DAY,),
    ) is False


def test_register_empty_common_name():
    s = PlayerBirdwatchingSystem()
    assert s.register_species(
        species_id="x", common_name="",
        rarity=Rarity.COMMON,
        preferred_zones=("z",),
        active_times=(TimeOfDay.DAY,),
    ) is False


def test_register_no_zones():
    s = PlayerBirdwatchingSystem()
    assert s.register_species(
        species_id="x", common_name="X",
        rarity=Rarity.COMMON, preferred_zones=(),
        active_times=(TimeOfDay.DAY,),
    ) is False


def test_spot_happy():
    s = PlayerBirdwatchingSystem()
    _populate(s)
    sid = s.spot_bird(
        watcher_id="naji",
        species_id="ronfaure_robin",
        zone_id="ronfaure",
        time_of_day=TimeOfDay.DAWN,
        observed_day=10,
    )
    assert sid is not None


def test_spot_unknown_species():
    s = PlayerBirdwatchingSystem()
    assert s.spot_bird(
        watcher_id="naji", species_id="ghost",
        zone_id="z", time_of_day=TimeOfDay.DAY,
        observed_day=10,
    ) is None


def test_spot_wrong_zone_blocked():
    s = PlayerBirdwatchingSystem()
    _populate(s)
    assert s.spot_bird(
        watcher_id="naji", species_id="phoenix",
        zone_id="ronfaure",
        time_of_day=TimeOfDay.DUSK,
        observed_day=10,
    ) is None


def test_spot_wrong_time_blocked():
    s = PlayerBirdwatchingSystem()
    _populate(s)
    # Phoenix only at dusk
    assert s.spot_bird(
        watcher_id="naji", species_id="phoenix",
        zone_id="riverne",
        time_of_day=TimeOfDay.DAY,
        observed_day=10,
    ) is None


def test_life_list_grows():
    s = PlayerBirdwatchingSystem()
    _populate(s)
    s.spot_bird(
        watcher_id="naji",
        species_id="ronfaure_robin",
        zone_id="ronfaure",
        time_of_day=TimeOfDay.DAWN,
        observed_day=10,
    )
    s.spot_bird(
        watcher_id="naji", species_id="phoenix",
        zone_id="riverne",
        time_of_day=TimeOfDay.DUSK,
        observed_day=11,
    )
    ll = s.life_list(watcher_id="naji")
    assert len(ll) == 2


def test_duplicate_sighting_no_dup_in_life_list():
    s = PlayerBirdwatchingSystem()
    _populate(s)
    s.spot_bird(
        watcher_id="naji",
        species_id="ronfaure_robin",
        zone_id="ronfaure",
        time_of_day=TimeOfDay.DAWN,
        observed_day=10,
    )
    s.spot_bird(
        watcher_id="naji",
        species_id="ronfaure_robin",
        zone_id="ronfaure",
        time_of_day=TimeOfDay.DAY,
        observed_day=11,
    )
    ll = s.life_list(watcher_id="naji")
    assert len(ll) == 1


def test_observation_hours_accumulates():
    s = PlayerBirdwatchingSystem()
    _populate(s)
    s.spot_bird(
        watcher_id="naji",
        species_id="ronfaure_robin",
        zone_id="ronfaure",
        time_of_day=TimeOfDay.DAWN,
        observed_day=10,
    )
    s.spot_bird(
        watcher_id="naji",
        species_id="ronfaure_robin",
        zone_id="ronfaure",
        time_of_day=TimeOfDay.DAY,
        observed_day=11,
    )
    assert s.observation_hours(
        watcher_id="naji",
    ) == 2


def test_fame_score_weights_rarity():
    s = PlayerBirdwatchingSystem()
    _populate(s)
    # Common (1) + legendary (40) = 41
    s.spot_bird(
        watcher_id="naji",
        species_id="ronfaure_robin",
        zone_id="ronfaure",
        time_of_day=TimeOfDay.DAWN,
        observed_day=10,
    )
    s.spot_bird(
        watcher_id="naji", species_id="phoenix",
        zone_id="riverne",
        time_of_day=TimeOfDay.DUSK,
        observed_day=11,
    )
    assert s.fame_score(watcher_id="naji") == 41


def test_fame_score_unknown_watcher():
    s = PlayerBirdwatchingSystem()
    assert s.fame_score(watcher_id="ghost") == 0


def test_life_list_unknown_watcher():
    s = PlayerBirdwatchingSystem()
    assert s.life_list(watcher_id="ghost") == []


def test_observation_hours_unknown():
    s = PlayerBirdwatchingSystem()
    assert s.observation_hours(
        watcher_id="ghost",
    ) == 0


def test_sightings_by_watcher_isolation():
    s = PlayerBirdwatchingSystem()
    _populate(s)
    s.spot_bird(
        watcher_id="naji",
        species_id="ronfaure_robin",
        zone_id="ronfaure",
        time_of_day=TimeOfDay.DAWN,
        observed_day=10,
    )
    s.spot_bird(
        watcher_id="bob",
        species_id="ronfaure_robin",
        zone_id="ronfaure",
        time_of_day=TimeOfDay.DAY,
        observed_day=11,
    )
    naji_sightings = s.sightings_by_watcher(
        watcher_id="naji",
    )
    bob_sightings = s.sightings_by_watcher(
        watcher_id="bob",
    )
    assert len(naji_sightings) == 1
    assert len(bob_sightings) == 1


def test_species_lookup():
    s = PlayerBirdwatchingSystem()
    _populate(s)
    sp = s.species(species_id="phoenix")
    assert sp.rarity == Rarity.LEGENDARY


def test_species_unknown():
    s = PlayerBirdwatchingSystem()
    assert s.species(species_id="ghost") is None


def test_negative_day_blocked():
    s = PlayerBirdwatchingSystem()
    _populate(s)
    assert s.spot_bird(
        watcher_id="naji",
        species_id="ronfaure_robin",
        zone_id="ronfaure",
        time_of_day=TimeOfDay.DAWN,
        observed_day=-1,
    ) is None


def test_enum_counts():
    assert len(list(Rarity)) == 5
    assert len(list(TimeOfDay)) == 4
