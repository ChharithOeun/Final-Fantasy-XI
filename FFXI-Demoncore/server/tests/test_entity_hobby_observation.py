"""Tests for entity_hobby_observation."""
from __future__ import annotations

from server.entity_hobby_observation import (
    HobbyObservationSystem,
)
from server.entity_hobbies import HobbyKind


def test_record_happy():
    s = HobbyObservationSystem()
    oid = s.record_observation(
        witness_id="naji", entity_id="volker",
        hobby=HobbyKind.FISHING,
        zone_id="bastok_docks",
        observed_day=10, is_rare=False,
    )
    assert oid is not None


def test_record_self_witness_blocked():
    s = HobbyObservationSystem()
    assert s.record_observation(
        witness_id="naji", entity_id="naji",
        hobby=HobbyKind.FISHING, zone_id="z",
        observed_day=10, is_rare=False,
    ) is None


def test_record_empty_witness():
    s = HobbyObservationSystem()
    assert s.record_observation(
        witness_id="", entity_id="x",
        hobby=HobbyKind.FISHING, zone_id="z",
        observed_day=10, is_rare=False,
    ) is None


def test_record_empty_zone():
    s = HobbyObservationSystem()
    assert s.record_observation(
        witness_id="naji", entity_id="x",
        hobby=HobbyKind.FISHING, zone_id="",
        observed_day=10, is_rare=False,
    ) is None


def test_record_negative_day():
    s = HobbyObservationSystem()
    assert s.record_observation(
        witness_id="naji", entity_id="x",
        hobby=HobbyKind.FISHING, zone_id="z",
        observed_day=-1, is_rare=False,
    ) is None


def test_first_sighting_grants_normal_fame():
    s = HobbyObservationSystem()
    oid = s.record_observation(
        witness_id="naji", entity_id="volker",
        hobby=HobbyKind.FISHING, zone_id="z",
        observed_day=10, is_rare=False,
    )
    assert s.observation(
        observation_id=oid,
    ).fame_earned == 5


def test_first_rare_sighting_grants_higher_fame():
    s = HobbyObservationSystem()
    oid = s.record_observation(
        witness_id="naji", entity_id="taru_war",
        hobby=HobbyKind.WEIGHTLIFTING,
        zone_id="z", observed_day=10, is_rare=True,
    )
    assert s.observation(
        observation_id=oid,
    ).fame_earned == 25


def test_repeat_sighting_no_fame():
    s = HobbyObservationSystem()
    s.record_observation(
        witness_id="naji", entity_id="volker",
        hobby=HobbyKind.FISHING, zone_id="z",
        observed_day=10, is_rare=False,
    )
    oid2 = s.record_observation(
        witness_id="naji", entity_id="volker",
        hobby=HobbyKind.FISHING, zone_id="z",
        observed_day=11, is_rare=False,
    )
    assert s.observation(
        observation_id=oid2,
    ).fame_earned == 0


def test_different_hobby_same_entity_grants_new_fame():
    s = HobbyObservationSystem()
    s.record_observation(
        witness_id="naji", entity_id="volker",
        hobby=HobbyKind.FISHING, zone_id="z",
        observed_day=10, is_rare=False,
    )
    oid2 = s.record_observation(
        witness_id="naji", entity_id="volker",
        hobby=HobbyKind.DRINKING, zone_id="z",
        observed_day=11, is_rare=False,
    )
    assert s.observation(
        observation_id=oid2,
    ).fame_earned == 5


def test_total_fame_aggregates():
    s = HobbyObservationSystem()
    s.record_observation(
        witness_id="naji", entity_id="volker",
        hobby=HobbyKind.FISHING, zone_id="z",
        observed_day=10, is_rare=False,
    )
    s.record_observation(
        witness_id="naji", entity_id="taru_war",
        hobby=HobbyKind.WEIGHTLIFTING,
        zone_id="z", observed_day=11, is_rare=True,
    )
    # 5 + 25 = 30
    assert s.total_fame(witness_id="naji") == 30


def test_total_fame_unknown_witness():
    s = HobbyObservationSystem()
    assert s.total_fame(witness_id="ghost") == 0


def test_discovered_pairs_unique():
    s = HobbyObservationSystem()
    s.record_observation(
        witness_id="naji", entity_id="volker",
        hobby=HobbyKind.FISHING, zone_id="z",
        observed_day=10, is_rare=False,
    )
    s.record_observation(
        witness_id="naji", entity_id="volker",
        hobby=HobbyKind.FISHING, zone_id="z",
        observed_day=12, is_rare=False,
    )
    pairs = s.discovered_pairs(witness_id="naji")
    assert len(pairs) == 1


def test_entity_public_renown_aggregates():
    s = HobbyObservationSystem()
    s.record_observation(
        witness_id="naji", entity_id="volker",
        hobby=HobbyKind.FISHING, zone_id="z",
        observed_day=10, is_rare=False,
    )
    s.record_observation(
        witness_id="bob", entity_id="volker",
        hobby=HobbyKind.FISHING, zone_id="z",
        observed_day=11, is_rare=False,
    )
    s.record_observation(
        witness_id="cara", entity_id="volker",
        hobby=HobbyKind.DRINKING, zone_id="z",
        observed_day=12, is_rare=False,
    )
    assert s.entity_public_renown(
        entity_id="volker",
    ) == 3


def test_entity_public_renown_unknown_zero():
    s = HobbyObservationSystem()
    assert s.entity_public_renown(
        entity_id="ghost",
    ) == 0


def test_witnesses_of_lookup():
    s = HobbyObservationSystem()
    s.record_observation(
        witness_id="naji", entity_id="volker",
        hobby=HobbyKind.FISHING, zone_id="z",
        observed_day=10, is_rare=False,
    )
    s.record_observation(
        witness_id="bob", entity_id="volker",
        hobby=HobbyKind.FISHING, zone_id="z",
        observed_day=11, is_rare=False,
    )
    s.record_observation(
        witness_id="cara", entity_id="volker",
        hobby=HobbyKind.DRINKING, zone_id="z",
        observed_day=12, is_rare=False,
    )
    fishing_witnesses = s.witnesses_of(
        entity_id="volker", hobby=HobbyKind.FISHING,
    )
    drinking_witnesses = s.witnesses_of(
        entity_id="volker", hobby=HobbyKind.DRINKING,
    )
    assert set(fishing_witnesses) == {"naji", "bob"}
    assert set(drinking_witnesses) == {"cara"}


def test_observations_by_witness():
    s = HobbyObservationSystem()
    s.record_observation(
        witness_id="naji", entity_id="volker",
        hobby=HobbyKind.FISHING, zone_id="z",
        observed_day=10, is_rare=False,
    )
    s.record_observation(
        witness_id="naji", entity_id="taru_war",
        hobby=HobbyKind.WEIGHTLIFTING,
        zone_id="z", observed_day=11, is_rare=True,
    )
    s.record_observation(
        witness_id="bob", entity_id="volker",
        hobby=HobbyKind.FISHING, zone_id="z",
        observed_day=12, is_rare=False,
    )
    naji = s.observations_by_witness(
        witness_id="naji",
    )
    bob = s.observations_by_witness(witness_id="bob")
    assert len(naji) == 2
    assert len(bob) == 1


def test_unknown_observation():
    s = HobbyObservationSystem()
    assert s.observation(
        observation_id="ghost",
    ) is None


def test_discovered_pairs_unknown_witness():
    s = HobbyObservationSystem()
    assert s.discovered_pairs(
        witness_id="ghost",
    ) == []


def test_repeat_sightings_count_in_renown():
    """Even non-fame-granting repeats grow public
    renown."""
    s = HobbyObservationSystem()
    for _ in range(5):
        s.record_observation(
            witness_id="naji", entity_id="volker",
            hobby=HobbyKind.FISHING, zone_id="z",
            observed_day=10, is_rare=False,
        )
    # Total fame for naji = 5 (only first one paid),
    # public renown for volker = 5 sightings.
    assert s.total_fame(witness_id="naji") == 5
    assert s.entity_public_renown(
        entity_id="volker",
    ) == 5


def test_zero_observations_default_state():
    s = HobbyObservationSystem()
    assert s.discovered_pairs(witness_id="x") == []
    assert s.total_fame(witness_id="x") == 0
    assert s.entity_public_renown(entity_id="x") == 0


def test_multiple_witnesses_no_cross_contamination():
    s = HobbyObservationSystem()
    s.record_observation(
        witness_id="naji", entity_id="volker",
        hobby=HobbyKind.FISHING, zone_id="z",
        observed_day=10, is_rare=False,
    )
    # Bob hasn't witnessed yet
    assert s.discovered_pairs(witness_id="bob") == []
    s.record_observation(
        witness_id="bob", entity_id="volker",
        hobby=HobbyKind.FISHING, zone_id="z",
        observed_day=11, is_rare=False,
    )
    # Bob now has the discovery, gets fame too
    assert s.total_fame(witness_id="bob") == 5
