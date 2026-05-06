"""Tests for wild_forage."""
from __future__ import annotations

from server.wild_forage import ForageKind, WildForageRegistry


def _setup():
    r = WildForageRegistry()
    r.register_node(
        node_id="berry_001", zone_id="ronfaure",
        position=(10.0, 0.0, 5.0),
        kind=ForageKind.BERRY, max_charges=5,
        regen_seconds=60,
    )
    return r


def test_register_happy():
    r = _setup()
    assert r.total_nodes() == 1


def test_blank_id_blocked():
    r = WildForageRegistry()
    out = r.register_node(
        node_id="", zone_id="z", position=(0, 0, 0),
        kind=ForageKind.BERRY, max_charges=5, regen_seconds=60,
    )
    assert out is False


def test_zero_charges_blocked():
    r = WildForageRegistry()
    out = r.register_node(
        node_id="x", zone_id="z", position=(0, 0, 0),
        kind=ForageKind.BERRY, max_charges=0, regen_seconds=60,
    )
    assert out is False


def test_zero_regen_blocked():
    r = WildForageRegistry()
    out = r.register_node(
        node_id="x", zone_id="z", position=(0, 0, 0),
        kind=ForageKind.BERRY, max_charges=5, regen_seconds=0,
    )
    assert out is False


def test_duplicate_blocked():
    r = _setup()
    again = r.register_node(
        node_id="berry_001", zone_id="z", position=(0, 0, 0),
        kind=ForageKind.BERRY, max_charges=5, regen_seconds=60,
    )
    assert again is False


def test_gather_happy():
    r = _setup()
    out = r.gather(
        node_id="berry_001", gatherer_id="alice",
        now_seconds=10,
    )
    assert out.success is True
    assert out.kind == ForageKind.BERRY
    assert out.quantity == 1


def test_gather_unknown_node():
    r = _setup()
    out = r.gather(
        node_id="ghost", gatherer_id="alice", now_seconds=10,
    )
    assert out.success is False


def test_gather_blank_gatherer():
    r = _setup()
    out = r.gather(
        node_id="berry_001", gatherer_id="", now_seconds=10,
    )
    assert out.success is False


def test_gather_depletes():
    r = _setup()
    for _ in range(5):
        r.gather(
            node_id="berry_001", gatherer_id="alice",
            now_seconds=10,
        )
    out = r.gather(
        node_id="berry_001", gatherer_id="alice",
        now_seconds=10,
    )
    assert out.success is False
    assert out.reason == "depleted"


def test_charges_at_full_initially():
    r = _setup()
    assert r.charges_at(
        node_id="berry_001", now_seconds=0,
    ) == 5


def test_charges_at_after_gather():
    r = _setup()
    r.gather(
        node_id="berry_001", gatherer_id="alice",
        now_seconds=10,
    )
    assert r.charges_at(
        node_id="berry_001", now_seconds=10,
    ) == 4


def test_regenerates_over_time():
    r = _setup()
    # deplete
    for _ in range(5):
        r.gather(
            node_id="berry_001", gatherer_id="alice",
            now_seconds=10,
        )
    # 30 sec elapsed, regen_seconds=60 → halfway
    assert r.charges_at(
        node_id="berry_001", now_seconds=10 + 30,
    ) == 2


def test_regen_caps_at_max():
    r = _setup()
    for _ in range(5):
        r.gather(
            node_id="berry_001", gatherer_id="alice",
            now_seconds=10,
        )
    # 200 sec later, fully regrown
    assert r.charges_at(
        node_id="berry_001", now_seconds=210,
    ) == 5


def test_regen_after_partial_gather():
    r = _setup()
    r.gather(
        node_id="berry_001", gatherer_id="alice",
        now_seconds=10,
    )
    # only 1 gathered; node not "depleted" yet, so
    # charges stay at 4 — last_depleted_at unset
    assert r.charges_at(
        node_id="berry_001", now_seconds=100,
    ) == 4


def test_gather_after_regen():
    r = _setup()
    for _ in range(5):
        r.gather(
            node_id="berry_001", gatherer_id="alice",
            now_seconds=10,
        )
    # full regen
    out = r.gather(
        node_id="berry_001", gatherer_id="alice",
        now_seconds=200,
    )
    assert out.success is True


def test_nodes_in_zone():
    r = _setup()
    r.register_node(
        node_id="spring_001", zone_id="ronfaure",
        position=(0, 0, 0), kind=ForageKind.SPRING,
        max_charges=10, regen_seconds=120,
    )
    r.register_node(
        node_id="herb_001", zone_id="gustav",
        position=(0, 0, 0), kind=ForageKind.HERB,
        max_charges=3, regen_seconds=300,
    )
    out = r.nodes_in_zone(zone_id="ronfaure")
    assert len(out) == 2


def test_five_forage_kinds():
    assert len(list(ForageKind)) == 5


def test_unknown_node_zero_charges():
    r = _setup()
    assert r.charges_at(
        node_id="ghost", now_seconds=10,
    ) == 0
