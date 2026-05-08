"""Tests for chronicle_publication."""
from __future__ import annotations

from server.chronicle_publication import (
    ChroniclePublication, Publisher,
)


def _vana_pub():
    return Publisher(
        publisher_id="vana_chronicle",
        name="Vana'diel Chronicle",
        nation="windy",
        cadence_days=30,
    )


def _publish_basic(c, **overrides):
    args = dict(
        publisher_id="vana_chronicle",
        title="Vana'diel Chronicle Vol. 1",
        edition_number=1,
        front_page_headline="Behemoth Felled",
        included_entry_ids=["chron_1", "chron_2"],
        price_gil=200,
        release_day=10,
    )
    args.update(overrides)
    return c.publish_volume(**args)


def test_register_publisher():
    c = ChroniclePublication()
    assert c.register_publisher(_vana_pub()) is True


def test_register_blank_id_blocked():
    c = ChroniclePublication()
    bad = Publisher(
        publisher_id="", name="x", nation="y",
        cadence_days=30,
    )
    assert c.register_publisher(bad) is False


def test_register_zero_cadence_blocked():
    c = ChroniclePublication()
    bad = Publisher(
        publisher_id="x", name="y", nation="z",
        cadence_days=0,
    )
    assert c.register_publisher(bad) is False


def test_register_dup_blocked():
    c = ChroniclePublication()
    c.register_publisher(_vana_pub())
    assert c.register_publisher(_vana_pub()) is False


def test_publish_happy():
    c = ChroniclePublication()
    c.register_publisher(_vana_pub())
    vid = _publish_basic(c)
    assert vid is not None


def test_publish_unknown_publisher():
    c = ChroniclePublication()
    vid = _publish_basic(c)
    assert vid is None


def test_publish_blank_title():
    c = ChroniclePublication()
    c.register_publisher(_vana_pub())
    vid = _publish_basic(c, title="")
    assert vid is None


def test_publish_zero_edition_blocked():
    c = ChroniclePublication()
    c.register_publisher(_vana_pub())
    vid = _publish_basic(c, edition_number=0)
    assert vid is None


def test_publish_no_entries_blocked():
    c = ChroniclePublication()
    c.register_publisher(_vana_pub())
    vid = _publish_basic(c, included_entry_ids=[])
    assert vid is None


def test_publish_dup_edition_blocked():
    c = ChroniclePublication()
    c.register_publisher(_vana_pub())
    _publish_basic(c, edition_number=1)
    vid = _publish_basic(c, edition_number=1)
    assert vid is None


def test_buy_happy():
    c = ChroniclePublication()
    c.register_publisher(_vana_pub())
    vid = _publish_basic(c, release_day=10)
    assert c.buy(
        player_id="bob", volume_id=vid, bought_day=15,
    ) is True


def test_buy_before_release_blocked():
    c = ChroniclePublication()
    c.register_publisher(_vana_pub())
    vid = _publish_basic(c, release_day=10)
    assert c.buy(
        player_id="bob", volume_id=vid, bought_day=5,
    ) is False


def test_buy_blank_player_blocked():
    c = ChroniclePublication()
    c.register_publisher(_vana_pub())
    vid = _publish_basic(c)
    assert c.buy(
        player_id="", volume_id=vid, bought_day=20,
    ) is False


def test_buy_unknown_volume():
    c = ChroniclePublication()
    assert c.buy(
        player_id="bob", volume_id="ghost",
        bought_day=20,
    ) is False


def test_total_sold():
    c = ChroniclePublication()
    c.register_publisher(_vana_pub())
    vid = _publish_basic(c)
    c.buy(player_id="bob", volume_id=vid, bought_day=15)
    c.buy(player_id="cara", volume_id=vid, bought_day=16)
    assert c.total_sold(volume_id=vid) == 2


def test_volume_unknown():
    c = ChroniclePublication()
    assert c.volume(volume_id="ghost") is None


def test_volumes_by_publisher_sorted():
    c = ChroniclePublication()
    c.register_publisher(_vana_pub())
    _publish_basic(c, edition_number=2)
    _publish_basic(c, edition_number=1)
    out = c.volumes_by_publisher(
        publisher_id="vana_chronicle",
    )
    assert [v.edition_number for v in out] == [1, 2]


def test_buyers_of_dedup():
    c = ChroniclePublication()
    c.register_publisher(_vana_pub())
    vid = _publish_basic(c)
    c.buy(player_id="bob", volume_id=vid, bought_day=15)
    c.buy(player_id="bob", volume_id=vid, bought_day=20)
    c.buy(player_id="cara", volume_id=vid, bought_day=21)
    out = c.buyers_of(volume_id=vid)
    assert out == ["bob", "cara"]


def test_buyers_of_unknown():
    c = ChroniclePublication()
    assert c.buyers_of(volume_id="ghost") == []
