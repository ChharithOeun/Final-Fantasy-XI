"""Tests for the beastman cities."""
from __future__ import annotations

from server.beastman_cities import (
    BeastmanCities,
    CityRole,
    CityServiceKind,
)
from server.beastman_playable_races import BeastmanRace


def test_register_city():
    c = BeastmanCities()
    city = c.register_city(
        city_id="oztroja_temple",
        role=CityRole.SAN_DORIA_PARALLEL,
        label="Oztroja Temple of the Bishops",
        anchor_race=BeastmanRace.YAGUDO,
        mission_npc_id="bishop_supreme",
    )
    assert city is not None


def test_register_empty_npc_rejected():
    c = BeastmanCities()
    res = c.register_city(
        city_id="x",
        role=CityRole.SAN_DORIA_PARALLEL,
        label="x",
        anchor_race=BeastmanRace.YAGUDO,
        mission_npc_id="",
    )
    assert res is None


def test_double_register_id_rejected():
    c = BeastmanCities()
    c.register_city(
        city_id="x",
        role=CityRole.SAN_DORIA_PARALLEL,
        label="A",
        anchor_race=BeastmanRace.YAGUDO,
        mission_npc_id="npc",
    )
    res = c.register_city(
        city_id="x",
        role=CityRole.BASTOK_PARALLEL,
        label="B",
        anchor_race=BeastmanRace.QUADAV,
        mission_npc_id="npc2",
    )
    assert res is None


def test_double_role_rejected():
    c = BeastmanCities()
    c.register_city(
        city_id="a",
        role=CityRole.SAN_DORIA_PARALLEL,
        label="A",
        anchor_race=BeastmanRace.YAGUDO,
        mission_npc_id="x",
    )
    res = c.register_city(
        city_id="b",
        role=CityRole.SAN_DORIA_PARALLEL,
        label="B",
        anchor_race=BeastmanRace.ORC,
        mission_npc_id="y",
    )
    assert res is None


def test_default_services_for_role():
    c = BeastmanCities()
    city = c.register_city(
        city_id="x",
        role=CityRole.WINDURST_PARALLEL,
        label="x",
        anchor_race=BeastmanRace.LAMIA,
        mission_npc_id="npc",
    )
    assert CityServiceKind.LIBRARY in city.services
    assert (
        CityServiceKind.AUCTION_HOUSE in city.services
    )


def test_explicit_services_override():
    c = BeastmanCities()
    city = c.register_city(
        city_id="x",
        role=CityRole.WHITEGATE_PARALLEL,
        label="x",
        anchor_race=BeastmanRace.LAMIA,
        mission_npc_id="npc",
        services=frozenset({CityServiceKind.HOMEPOINT}),
    )
    assert city.services == frozenset(
        {CityServiceKind.HOMEPOINT}
    )


def test_get_city():
    c = BeastmanCities()
    c.register_city(
        city_id="x",
        role=CityRole.BASTOK_PARALLEL,
        label="x",
        anchor_race=BeastmanRace.QUADAV,
        mission_npc_id="npc",
    )
    assert c.get("x") is not None
    assert c.get("ghost") is None


def test_by_role():
    c = BeastmanCities()
    c.register_city(
        city_id="x",
        role=CityRole.WINDURST_PARALLEL,
        label="x",
        anchor_race=BeastmanRace.LAMIA,
        mission_npc_id="npc",
    )
    res = c.by_role(CityRole.WINDURST_PARALLEL)
    assert res is not None
    assert res.city_id == "x"


def test_by_role_unknown():
    c = BeastmanCities()
    assert c.by_role(CityRole.JEUNO_PARALLEL) is None


def test_has_service():
    c = BeastmanCities()
    c.register_city(
        city_id="x",
        role=CityRole.BASTOK_PARALLEL,
        label="x",
        anchor_race=BeastmanRace.QUADAV,
        mission_npc_id="npc",
    )
    assert c.has_service(
        city_id="x",
        service=CityServiceKind.CRAFTING_GUILD,
    )
    assert not c.has_service(
        city_id="x",
        service=CityServiceKind.LIBRARY,
    )


def test_has_service_unknown_city():
    c = BeastmanCities()
    assert not c.has_service(
        city_id="ghost",
        service=CityServiceKind.AUCTION_HOUSE,
    )


def test_cities_for_race():
    c = BeastmanCities()
    c.register_city(
        city_id="oztroja",
        role=CityRole.SAN_DORIA_PARALLEL,
        label="Oz",
        anchor_race=BeastmanRace.YAGUDO,
        mission_npc_id="x",
    )
    c.register_city(
        city_id="palborough",
        role=CityRole.BASTOK_PARALLEL,
        label="Pal",
        anchor_race=BeastmanRace.QUADAV,
        mission_npc_id="x",
    )
    yagudo_cities = c.cities_for_race(
        BeastmanRace.YAGUDO,
    )
    assert len(yagudo_cities) == 1


def test_jeuno_parallel_no_anchor_race():
    """Jeuno-parallel can be a mixed council with no
    single anchor race."""
    c = BeastmanCities()
    city = c.register_city(
        city_id="shadow_council",
        role=CityRole.JEUNO_PARALLEL,
        label="Shadow Council",
        anchor_race=None,
        mission_npc_id="council_chair",
    )
    assert city.anchor_race is None


def test_total_cities():
    c = BeastmanCities()
    c.register_city(
        city_id="a",
        role=CityRole.SAN_DORIA_PARALLEL,
        label="A",
        anchor_race=BeastmanRace.YAGUDO,
        mission_npc_id="x",
    )
    c.register_city(
        city_id="b",
        role=CityRole.BASTOK_PARALLEL,
        label="B",
        anchor_race=BeastmanRace.QUADAV,
        mission_npc_id="y",
    )
    assert c.total_cities() == 2


def test_six_role_parallels_all_unique():
    """All six city roles should be claimable in turn."""
    c = BeastmanCities()
    roles = list(CityRole)
    for i, role in enumerate(roles):
        c.register_city(
            city_id=f"city_{i}",
            role=role,
            label=f"City {i}",
            anchor_race=None,
            mission_npc_id=f"npc_{i}",
        )
    assert c.total_cities() == 6


def test_san_doria_parallel_has_barracks():
    c = BeastmanCities()
    c.register_city(
        city_id="x",
        role=CityRole.SAN_DORIA_PARALLEL,
        label="x",
        anchor_race=BeastmanRace.ORC,
        mission_npc_id="npc",
    )
    assert c.has_service(
        city_id="x",
        service=CityServiceKind.BARRACKS,
    )


def test_whitegate_parallel_has_black_market():
    c = BeastmanCities()
    c.register_city(
        city_id="x",
        role=CityRole.WHITEGATE_PARALLEL,
        label="x",
        anchor_race=BeastmanRace.LAMIA,
        mission_npc_id="npc",
    )
    assert c.has_service(
        city_id="x",
        service=CityServiceKind.BLACK_MARKET,
    )


def test_windurst_parallel_has_library():
    c = BeastmanCities()
    c.register_city(
        city_id="x",
        role=CityRole.WINDURST_PARALLEL,
        label="x",
        anchor_race=BeastmanRace.YAGUDO,
        mission_npc_id="npc",
    )
    assert c.has_service(
        city_id="x",
        service=CityServiceKind.LIBRARY,
    )
