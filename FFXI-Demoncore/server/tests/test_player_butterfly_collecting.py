"""Tests for player_butterfly_collecting."""
from __future__ import annotations

from server.player_butterfly_collecting import (
    PlayerButterflyCollectingSystem, SpecimenStage,
)


def _populate(s: PlayerButterflyCollectingSystem) -> None:
    s.register_species(
        species_id="cabbage_white",
        common_name="Cabbage White",
        rarity_value=10,
        active_zones=("ronfaure", "konschtat"),
        active_seasons=("spring", "summer"),
    )
    s.register_species(
        species_id="phoenix_swallowtail",
        common_name="Phoenix Swallowtail",
        rarity_value=200,
        active_zones=("riverne",),
        active_seasons=("summer",),
    )


def test_register_species_happy():
    s = PlayerButterflyCollectingSystem()
    assert s.register_species(
        species_id="x", common_name="X",
        rarity_value=10, active_zones=("z",),
        active_seasons=("spring",),
    ) is True


def test_register_duplicate_blocked():
    s = PlayerButterflyCollectingSystem()
    s.register_species(
        species_id="x", common_name="X",
        rarity_value=10, active_zones=("z",),
        active_seasons=("spring",),
    )
    assert s.register_species(
        species_id="x", common_name="Other",
        rarity_value=20, active_zones=("z",),
        active_seasons=("summer",),
    ) is False


def test_register_no_zones():
    s = PlayerButterflyCollectingSystem()
    assert s.register_species(
        species_id="x", common_name="X",
        rarity_value=10, active_zones=(),
        active_seasons=("spring",),
    ) is False


def test_net_specimen_happy():
    s = PlayerButterflyCollectingSystem()
    _populate(s)
    sid = s.net_specimen(
        collector_id="naji",
        species_id="cabbage_white",
        zone_id="ronfaure", season="spring",
        captured_day=10,
    )
    assert sid is not None


def test_net_wrong_zone_blocked():
    s = PlayerButterflyCollectingSystem()
    _populate(s)
    # Phoenix only in riverne
    assert s.net_specimen(
        collector_id="naji",
        species_id="phoenix_swallowtail",
        zone_id="ronfaure", season="summer",
        captured_day=10,
    ) is None


def test_net_wrong_season_blocked():
    s = PlayerButterflyCollectingSystem()
    _populate(s)
    # Phoenix only in summer
    assert s.net_specimen(
        collector_id="naji",
        species_id="phoenix_swallowtail",
        zone_id="riverne", season="winter",
        captured_day=10,
    ) is None


def test_net_unknown_species():
    s = PlayerButterflyCollectingSystem()
    assert s.net_specimen(
        collector_id="naji", species_id="ghost",
        zone_id="z", season="spring",
        captured_day=10,
    ) is None


def test_freshness_on_capture_day():
    s = PlayerButterflyCollectingSystem()
    _populate(s)
    sid = s.net_specimen(
        collector_id="naji",
        species_id="cabbage_white",
        zone_id="ronfaure", season="spring",
        captured_day=10,
    )
    assert s.freshness_on_day(
        specimen_id=sid, current_day=10,
    ) == 100


def test_freshness_decays_daily():
    s = PlayerButterflyCollectingSystem()
    _populate(s)
    sid = s.net_specimen(
        collector_id="naji",
        species_id="cabbage_white",
        zone_id="ronfaure", season="spring",
        captured_day=10,
    )
    assert s.freshness_on_day(
        specimen_id=sid, current_day=15,
    ) == 50


def test_freshness_floor_at_zero():
    s = PlayerButterflyCollectingSystem()
    _populate(s)
    sid = s.net_specimen(
        collector_id="naji",
        species_id="cabbage_white",
        zone_id="ronfaure", season="spring",
        captured_day=10,
    )
    assert s.freshness_on_day(
        specimen_id=sid, current_day=100,
    ) == 0


def test_pin_happy():
    s = PlayerButterflyCollectingSystem()
    _populate(s)
    sid = s.net_specimen(
        collector_id="naji",
        species_id="cabbage_white",
        zone_id="ronfaure", season="spring",
        captured_day=10,
    )
    f = s.pin(specimen_id=sid, current_day=12)
    # 100 - 2*10 = 80
    assert f == 80
    assert s.specimen(
        specimen_id=sid,
    ).stage == SpecimenStage.PINNED


def test_pin_too_late_spoils():
    s = PlayerButterflyCollectingSystem()
    _populate(s)
    sid = s.net_specimen(
        collector_id="naji",
        species_id="cabbage_white",
        zone_id="ronfaure", season="spring",
        captured_day=10,
    )
    # day 25 → freshness 0 → spoiled
    assert s.pin(
        specimen_id=sid, current_day=25,
    ) is None
    assert s.specimen(
        specimen_id=sid,
    ).stage == SpecimenStage.SPOILED


def test_pin_double_blocked():
    s = PlayerButterflyCollectingSystem()
    _populate(s)
    sid = s.net_specimen(
        collector_id="naji",
        species_id="cabbage_white",
        zone_id="ronfaure", season="spring",
        captured_day=10,
    )
    s.pin(specimen_id=sid, current_day=11)
    assert s.pin(
        specimen_id=sid, current_day=12,
    ) is None


def test_pin_before_capture_blocked():
    s = PlayerButterflyCollectingSystem()
    _populate(s)
    sid = s.net_specimen(
        collector_id="naji",
        species_id="cabbage_white",
        zone_id="ronfaure", season="spring",
        captured_day=10,
    )
    assert s.pin(
        specimen_id=sid, current_day=5,
    ) is None


def test_display_value_pinned():
    s = PlayerButterflyCollectingSystem()
    _populate(s)
    sid = s.net_specimen(
        collector_id="naji",
        species_id="phoenix_swallowtail",
        zone_id="riverne", season="summer",
        captured_day=10,
    )
    s.pin(specimen_id=sid, current_day=10)
    # 200 * 100 / 10 = 2000
    assert s.display_value(specimen_id=sid) == 2000


def test_display_value_unpinned_zero():
    s = PlayerButterflyCollectingSystem()
    _populate(s)
    sid = s.net_specimen(
        collector_id="naji",
        species_id="cabbage_white",
        zone_id="ronfaure", season="spring",
        captured_day=10,
    )
    assert s.display_value(specimen_id=sid) == 0


def test_collection_lists_pinned_only():
    s = PlayerButterflyCollectingSystem()
    _populate(s)
    pinned = s.net_specimen(
        collector_id="naji",
        species_id="cabbage_white",
        zone_id="ronfaure", season="spring",
        captured_day=10,
    )
    s.pin(specimen_id=pinned, current_day=10)
    s.net_specimen(
        collector_id="naji",
        species_id="cabbage_white",
        zone_id="ronfaure", season="spring",
        captured_day=20,
    )  # captured but not pinned
    coll = s.collection(collector_id="naji")
    assert len(coll) == 1


def test_collection_isolation():
    s = PlayerButterflyCollectingSystem()
    _populate(s)
    sid_a = s.net_specimen(
        collector_id="naji",
        species_id="cabbage_white",
        zone_id="ronfaure", season="spring",
        captured_day=10,
    )
    s.pin(specimen_id=sid_a, current_day=10)
    sid_b = s.net_specimen(
        collector_id="bob",
        species_id="cabbage_white",
        zone_id="ronfaure", season="spring",
        captured_day=10,
    )
    s.pin(specimen_id=sid_b, current_day=10)
    assert len(s.collection(collector_id="naji")) == 1
    assert len(s.collection(collector_id="bob")) == 1


def test_freshness_unknown_specimen():
    s = PlayerButterflyCollectingSystem()
    assert s.freshness_on_day(
        specimen_id="ghost", current_day=10,
    ) == 0


def test_specimen_unknown():
    s = PlayerButterflyCollectingSystem()
    assert s.specimen(specimen_id="ghost") is None


def test_enum_count():
    assert len(list(SpecimenStage)) == 3
