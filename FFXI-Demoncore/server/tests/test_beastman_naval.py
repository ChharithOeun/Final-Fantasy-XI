"""Tests for the beastman naval system."""
from __future__ import annotations

from server.beastman_naval import (
    BeastmanNaval,
    CrossingOutcome,
    NauticalKind,
    PortKind,
)


def _seed(b):
    b.register_port(
        port_id="oztroja_dock",
        kind=PortKind.BEASTMAN_HOME,
        zone_id="oztroja_harbor",
    )
    b.register_port(
        port_id="selbina_dock",
        kind=PortKind.HUME_DOCK,
        zone_id="selbina",
    )
    b.register_ship(
        ship_id="wing_alpha",
        kind=NauticalKind.YAGUDO_WING_CRAFT,
        home_port_id="oztroja_dock",
        passenger_capacity=4,
        cargo_capacity=100,
    )
    b.register_leg(
        leg_id="oz_to_sel",
        ship_id="wing_alpha",
        from_port_id="oztroja_dock",
        to_port_id="selbina_dock",
        base_risk_pct=40,
    )


def test_register_port():
    b = BeastmanNaval()
    p = b.register_port(
        port_id="oztroja_dock",
        kind=PortKind.BEASTMAN_HOME,
        zone_id="oztroja_harbor",
    )
    assert p is not None
    assert b.total_ports() == 1


def test_register_port_duplicate_rejected():
    b = BeastmanNaval()
    _seed(b)
    res = b.register_port(
        port_id="oztroja_dock",
        kind=PortKind.HUME_DOCK,
        zone_id="other",
    )
    assert res is None


def test_register_port_empty_zone_rejected():
    b = BeastmanNaval()
    res = b.register_port(
        port_id="x",
        kind=PortKind.NEUTRAL_TRADING,
        zone_id="",
    )
    assert res is None


def test_register_ship():
    b = BeastmanNaval()
    _seed(b)
    assert b.total_ships() == 1


def test_register_ship_unknown_home_port():
    b = BeastmanNaval()
    res = b.register_ship(
        ship_id="ghost",
        kind=NauticalKind.ORC_REAVER,
        home_port_id="nowhere",
    )
    assert res is None


def test_register_ship_zero_capacity():
    b = BeastmanNaval()
    _seed(b)
    res = b.register_ship(
        ship_id="empty",
        kind=NauticalKind.QUADAV_STONESHIP,
        home_port_id="oztroja_dock",
        passenger_capacity=0,
        cargo_capacity=10,
    )
    assert res is None


def test_register_leg():
    b = BeastmanNaval()
    _seed(b)
    assert b.total_legs() == 1


def test_register_leg_same_endpoints_rejected():
    b = BeastmanNaval()
    _seed(b)
    res = b.register_leg(
        leg_id="self_leg",
        ship_id="wing_alpha",
        from_port_id="oztroja_dock",
        to_port_id="oztroja_dock",
        base_risk_pct=10,
    )
    assert res is None


def test_register_leg_invalid_risk():
    b = BeastmanNaval()
    _seed(b)
    res = b.register_leg(
        leg_id="bad",
        ship_id="wing_alpha",
        from_port_id="oztroja_dock",
        to_port_id="selbina_dock",
        base_risk_pct=200,
    )
    assert res is None


def test_register_leg_unknown_ship():
    b = BeastmanNaval()
    _seed(b)
    res = b.register_leg(
        leg_id="orphan",
        ship_id="nope",
        from_port_id="oztroja_dock",
        to_port_id="selbina_dock",
        base_risk_pct=10,
    )
    assert res is None


def test_board_basic():
    b = BeastmanNaval()
    _seed(b)
    res = b.board(
        player_id="kraw",
        ship_id="wing_alpha",
        leg_id="oz_to_sel",
        cargo_units=20,
    )
    assert res.accepted
    manifest, cargo = b.ship_manifest(ship_id="wing_alpha")
    assert "kraw" in manifest
    assert cargo == 20


def test_board_capacity_full():
    b = BeastmanNaval()
    _seed(b)
    for i in range(4):
        b.board(
            player_id=f"p{i}",
            ship_id="wing_alpha",
            leg_id="oz_to_sel",
        )
    res = b.board(
        player_id="overflow",
        ship_id="wing_alpha",
        leg_id="oz_to_sel",
    )
    assert not res.accepted


def test_board_double_rejected():
    b = BeastmanNaval()
    _seed(b)
    b.board(
        player_id="kraw",
        ship_id="wing_alpha",
        leg_id="oz_to_sel",
    )
    res = b.board(
        player_id="kraw",
        ship_id="wing_alpha",
        leg_id="oz_to_sel",
    )
    assert not res.accepted


def test_board_cargo_overflow():
    b = BeastmanNaval()
    _seed(b)
    res = b.board(
        player_id="kraw",
        ship_id="wing_alpha",
        leg_id="oz_to_sel",
        cargo_units=999,
    )
    assert not res.accepted


def test_board_negative_cargo():
    b = BeastmanNaval()
    _seed(b)
    res = b.board(
        player_id="kraw",
        ship_id="wing_alpha",
        leg_id="oz_to_sel",
        cargo_units=-5,
    )
    assert not res.accepted


def test_board_unknown_ship_or_leg():
    b = BeastmanNaval()
    _seed(b)
    res = b.board(
        player_id="kraw",
        ship_id="ghost",
        leg_id="oz_to_sel",
    )
    assert not res.accepted


def test_depart_safe_arrival():
    b = BeastmanNaval()
    _seed(b)
    b.board(
        player_id="kraw",
        ship_id="wing_alpha",
        leg_id="oz_to_sel",
        cargo_units=20,
    )
    res = b.depart(leg_id="oz_to_sel", risk_roll_pct=80)
    assert res.accepted
    assert res.outcome == CrossingOutcome.SAFE_ARRIVAL
    assert res.survivors_returned == 1


def test_depart_pirate_attack_yagudo():
    b = BeastmanNaval()
    _seed(b)
    b.board(
        player_id="kraw",
        ship_id="wing_alpha",
        leg_id="oz_to_sel",
        cargo_units=20,
    )
    # Yagudo wing-craft → pirate attack on hostile (not lamia/orc)
    res = b.depart(leg_id="oz_to_sel", risk_roll_pct=10)
    assert res.outcome == CrossingOutcome.PIRATE_ATTACK
    assert res.cargo_lost == 20


def test_depart_hume_navy_intercept_for_lamia():
    b = BeastmanNaval()
    b.register_port(
        port_id="lamia_cove",
        kind=PortKind.BEASTMAN_HOME,
        zone_id="lamia_cove_zone",
    )
    b.register_port(
        port_id="mhaura",
        kind=PortKind.HUME_DOCK,
        zone_id="mhaura",
    )
    b.register_ship(
        ship_id="lamia_alpha",
        kind=NauticalKind.LAMIA_TIDE_RUNNER,
        home_port_id="lamia_cove",
        passenger_capacity=10,
        cargo_capacity=200,
    )
    b.register_leg(
        leg_id="cove_to_mhaura",
        ship_id="lamia_alpha",
        from_port_id="lamia_cove",
        to_port_id="mhaura",
        base_risk_pct=50,
    )
    for i in range(5):
        b.board(
            player_id=f"p{i}",
            ship_id="lamia_alpha",
            leg_id="cove_to_mhaura",
            cargo_units=10,
        )
    res = b.depart(leg_id="cove_to_mhaura", risk_roll_pct=20)
    assert res.outcome == CrossingOutcome.HUME_NAVY_INTERCEPT
    assert res.survivors_returned == 3
    assert res.cargo_lost == 25


def test_depart_wrecked_extreme_gap():
    b = BeastmanNaval()
    _seed(b)
    b.board(
        player_id="kraw",
        ship_id="wing_alpha",
        leg_id="oz_to_sel",
        cargo_units=20,
    )
    # base_risk 40, roll 0 → gap of 40, but to wreck need >=60
    # Re-register higher base risk leg
    b.register_leg(
        leg_id="dangerous",
        ship_id="wing_alpha",
        from_port_id="oztroja_dock",
        to_port_id="selbina_dock",
        base_risk_pct=80,
    )
    b.board(
        player_id="other",
        ship_id="wing_alpha",
        leg_id="dangerous",
        cargo_units=10,
    )
    res = b.depart(leg_id="dangerous", risk_roll_pct=5)
    assert res.outcome == CrossingOutcome.WRECKED
    assert res.survivors_returned == 0


def test_depart_unknown_leg():
    b = BeastmanNaval()
    res = b.depart(leg_id="ghost", risk_roll_pct=50)
    assert not res.accepted


def test_depart_invalid_roll():
    b = BeastmanNaval()
    _seed(b)
    res = b.depart(leg_id="oz_to_sel", risk_roll_pct=-5)
    assert not res.accepted


def test_depart_clears_manifest():
    b = BeastmanNaval()
    _seed(b)
    b.board(
        player_id="kraw",
        ship_id="wing_alpha",
        leg_id="oz_to_sel",
        cargo_units=20,
    )
    b.depart(leg_id="oz_to_sel", risk_roll_pct=90)
    manifest, cargo = b.ship_manifest(ship_id="wing_alpha")
    assert manifest == ()
    assert cargo == 0


def test_ship_manifest_unknown_ship():
    b = BeastmanNaval()
    manifest, cargo = b.ship_manifest(ship_id="ghost")
    assert manifest == ()
    assert cargo == 0


def test_get_ship_lookup():
    b = BeastmanNaval()
    _seed(b)
    s = b.get_ship("wing_alpha")
    assert s is not None
    assert s.kind == NauticalKind.YAGUDO_WING_CRAFT
