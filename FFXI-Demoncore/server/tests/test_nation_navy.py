"""Tests for nation_navy."""
from __future__ import annotations

from server.nation_navy import (
    NationNavySystem, ShipClass, ShipState,
)


def _setup(s):
    s.add_port(port_id="bastok_harbor",
               nation_id="bastok")
    s.add_port(port_id="selbina",
               nation_id="bastok")
    s.add_route(
        route_id="bastok_selbina",
        port_a="bastok_harbor", port_b="selbina",
        transit_days=2,
    )


def _commission(s, **overrides):
    args = dict(
        ship_id="iron_eagle", nation_id="bastok",
        name="Iron Eagle",
        ship_class=ShipClass.FRIGATE,
        captain="captain_volker", crew=80,
        hull_max=1000, home_port="bastok_harbor",
    )
    args.update(overrides)
    return s.commission_ship(**args)


def test_add_port():
    s = NationNavySystem()
    assert s.add_port(
        port_id="bastok_harbor", nation_id="bastok",
    ) is True


def test_add_port_blank():
    s = NationNavySystem()
    assert s.add_port(
        port_id="", nation_id="bastok",
    ) is False


def test_add_port_dup():
    s = NationNavySystem()
    s.add_port(port_id="bastok_harbor",
               nation_id="bastok")
    assert s.add_port(
        port_id="bastok_harbor", nation_id="bastok",
    ) is False


def test_commission_happy():
    s = NationNavySystem()
    _setup(s)
    assert _commission(s) is True


def test_commission_unknown_port():
    s = NationNavySystem()
    assert _commission(
        s, home_port="ghost",
    ) is False


def test_commission_port_wrong_nation():
    s = NationNavySystem()
    s.add_port(port_id="windy_port",
               nation_id="windy")
    assert _commission(
        s, home_port="windy_port",
    ) is False


def test_commission_zero_crew():
    s = NationNavySystem()
    _setup(s)
    assert _commission(s, crew=0) is False


def test_commission_dup_id():
    s = NationNavySystem()
    _setup(s)
    _commission(s)
    assert _commission(s) is False


def test_add_route_happy():
    s = NationNavySystem()
    s.add_port(port_id="a", nation_id="bastok")
    s.add_port(port_id="b", nation_id="windy")
    assert s.add_route(
        route_id="a_b", port_a="a", port_b="b",
        transit_days=2,
    ) is True


def test_add_route_self():
    s = NationNavySystem()
    s.add_port(port_id="a", nation_id="bastok")
    assert s.add_route(
        route_id="a_a", port_a="a", port_b="a",
        transit_days=2,
    ) is False


def test_add_route_unknown_port():
    s = NationNavySystem()
    s.add_port(port_id="a", nation_id="bastok")
    assert s.add_route(
        route_id="a_b", port_a="a",
        port_b="ghost", transit_days=2,
    ) is False


def test_deploy_ship_happy():
    s = NationNavySystem()
    _setup(s)
    _commission(s)
    assert s.deploy_ship(
        ship_id="iron_eagle",
        route_id="bastok_selbina", now_day=15,
    ) is True


def test_deploy_unknown_route():
    s = NationNavySystem()
    _setup(s)
    _commission(s)
    assert s.deploy_ship(
        ship_id="iron_eagle", route_id="ghost",
        now_day=15,
    ) is False


def test_deploy_when_in_dock_blocked():
    s = NationNavySystem()
    _setup(s)
    _commission(s)
    s.take_hull_damage(
        ship_id="iron_eagle", dmg=900,
    )
    # 100 hull / 1000 max -> below 33%, but must
    # patrol first to get IN_DOCK auto-set; here
    # ship is just heavy-damaged stationed. Force
    # state by another path:
    s.deploy_ship(
        ship_id="iron_eagle",
        route_id="bastok_selbina", now_day=15,
    )
    s.take_hull_damage(
        ship_id="iron_eagle", dmg=10,
    )
    # Should now be IN_DOCK
    assert s.ship(
        ship_id="iron_eagle",
    ).state == ShipState.IN_DOCK
    assert s.deploy_ship(
        ship_id="iron_eagle",
        route_id="bastok_selbina", now_day=20,
    ) is False


def test_recall_ship():
    s = NationNavySystem()
    _setup(s)
    _commission(s)
    s.deploy_ship(
        ship_id="iron_eagle",
        route_id="bastok_selbina", now_day=15,
    )
    assert s.recall_ship(
        ship_id="iron_eagle", now_day=20,
    ) is True


def test_take_hull_damage():
    s = NationNavySystem()
    _setup(s)
    _commission(s, hull_max=1000)
    s.take_hull_damage(
        ship_id="iron_eagle", dmg=200,
    )
    assert s.ship(
        ship_id="iron_eagle",
    ).hull_current == 800


def test_hull_to_zero_sinks():
    s = NationNavySystem()
    _setup(s)
    _commission(s, hull_max=1000)
    s.take_hull_damage(
        ship_id="iron_eagle", dmg=1000,
    )
    assert s.ship(
        ship_id="iron_eagle",
    ).state == ShipState.SUNK


def test_repair_caps_at_max():
    s = NationNavySystem()
    _setup(s)
    _commission(s, hull_max=1000)
    s.take_hull_damage(
        ship_id="iron_eagle", dmg=300,
    )
    s.repair(
        ship_id="iron_eagle", hp=500, now_day=20,
    )
    assert s.ship(
        ship_id="iron_eagle",
    ).hull_current == 1000


def test_repair_full_returns_to_stationed():
    s = NationNavySystem()
    _setup(s)
    _commission(s, hull_max=1000)
    s.deploy_ship(
        ship_id="iron_eagle",
        route_id="bastok_selbina", now_day=15,
    )
    s.take_hull_damage(
        ship_id="iron_eagle", dmg=900,
    )
    assert s.ship(
        ship_id="iron_eagle",
    ).state == ShipState.IN_DOCK
    s.repair(
        ship_id="iron_eagle", hp=900, now_day=20,
    )
    assert s.ship(
        ship_id="iron_eagle",
    ).state == ShipState.STATIONED


def test_repair_sunk_blocked():
    s = NationNavySystem()
    _setup(s)
    _commission(s, hull_max=1000)
    s.take_hull_damage(
        ship_id="iron_eagle", dmg=1000,
    )
    assert s.repair(
        ship_id="iron_eagle", hp=500, now_day=20,
    ) is False


def test_replace_captain():
    s = NationNavySystem()
    _setup(s)
    _commission(s)
    assert s.replace_captain(
        ship_id="iron_eagle", captain="cara",
    ) is True
    assert s.ship(
        ship_id="iron_eagle",
    ).captain == "cara"


def test_scuttle_happy():
    s = NationNavySystem()
    _setup(s)
    _commission(s)
    assert s.scuttle(
        ship_id="iron_eagle", now_day=100,
    ) is True
    assert s.ship(
        ship_id="iron_eagle",
    ).state == ShipState.SUNK


def test_scuttle_double_blocked():
    s = NationNavySystem()
    _setup(s)
    _commission(s)
    s.scuttle(ship_id="iron_eagle", now_day=100)
    assert s.scuttle(
        ship_id="iron_eagle", now_day=101,
    ) is False


def test_ships_for_nation():
    s = NationNavySystem()
    _setup(s)
    _commission(s, ship_id="a")
    _commission(s, ship_id="b",
                captain="naji",
                home_port="bastok_harbor",
                name="Other")
    s.add_port(port_id="windy_port",
               nation_id="windy")
    _commission(s, ship_id="c", nation_id="windy",
                captain="kerutoto",
                home_port="windy_port",
                name="Windy Ship")
    out = s.ships_for(nation_id="bastok")
    assert len(out) == 2


def test_ships_at_port_filters():
    s = NationNavySystem()
    _setup(s)
    _commission(s, ship_id="a")
    _commission(s, ship_id="b", captain="naji",
                home_port="bastok_harbor",
                name="Iron2")
    s.deploy_ship(
        ship_id="a",
        route_id="bastok_selbina", now_day=15,
    )
    out = s.ships_at(port_id="bastok_harbor")
    ids = [sh.ship_id for sh in out]
    assert "a" not in ids
    assert "b" in ids


def test_ship_unknown():
    s = NationNavySystem()
    assert s.ship(ship_id="ghost") is None


def test_enum_counts():
    assert len(list(ShipClass)) == 4
    assert len(list(ShipState)) == 4
