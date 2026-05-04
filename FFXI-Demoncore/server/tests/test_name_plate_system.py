"""Tests for the name plate system."""
from __future__ import annotations

from server.name_plate_system import (
    HPBand,
    NamePlateSystem,
    PlateBadge,
    PlateKind,
)


def test_upsert_player_creates_plate():
    np = NamePlateSystem()
    plate = np.upsert_player(
        entity_id="alice", display_name="Alice",
        level=75, nation="bastok",
        zone_id="bastok",
        job_code="WAR",
    )
    assert plate.kind == PlateKind.PLAYER
    assert plate.nation_color == "yellow"


def test_upsert_player_updates_existing():
    np = NamePlateSystem()
    np.upsert_player(
        entity_id="alice", display_name="Alice",
        level=10, nation="bastok",
        zone_id="bastok",
    )
    np.upsert_player(
        entity_id="alice", display_name="Alice",
        level=99, nation="windurst",
        zone_id="windurst",
    )
    p = np.plate("alice")
    assert p.level == 99
    assert p.nation_color == "magenta"


def test_upsert_mob_with_nm_flag_adds_star():
    np = NamePlateSystem()
    plate = np.upsert_mob(
        entity_id="fafnir", display_name="Fafnir",
        level=85, faction="dragon",
        zone_id="dragons_aery",
        is_nm=True,
    )
    assert plate.kind == PlateKind.NM
    assert PlateBadge.NM_STAR in plate.badges


def test_upsert_mob_default_not_nm():
    np = NamePlateSystem()
    plate = np.upsert_mob(
        entity_id="orc_a", display_name="Orcish Footsoldier",
        level=12, faction="orc",
        zone_id="ranguemont",
    )
    assert plate.kind == PlateKind.MOB
    assert PlateBadge.NM_STAR not in plate.badges


def test_update_hp_band_sets_color():
    np = NamePlateSystem()
    np.upsert_mob(
        entity_id="m", display_name="m",
        level=1, zone_id="z",
    )
    np.update_hp_band(
        entity_id="m", band=HPBand.NEAR_DEATH,
    )
    p = np.plate("m")
    assert p.hp_band == HPBand.NEAR_DEATH
    assert p.hp_color == "red"


def test_update_hp_unknown_returns_false():
    np = NamePlateSystem()
    assert not np.update_hp_band(
        entity_id="ghost", band=HPBand.WOUNDED,
    )


def test_add_badge():
    np = NamePlateSystem()
    np.upsert_player(
        entity_id="alice", display_name="Alice",
        level=10, zone_id="z",
    )
    assert np.add_badge(
        entity_id="alice", badge=PlateBadge.MENTOR,
    )
    p = np.plate("alice")
    assert PlateBadge.MENTOR in p.badges


def test_add_badge_no_duplicate():
    np = NamePlateSystem()
    np.upsert_player(
        entity_id="alice", display_name="Alice",
        level=10, zone_id="z",
    )
    np.add_badge(
        entity_id="alice", badge=PlateBadge.MENTOR,
    )
    np.add_badge(
        entity_id="alice", badge=PlateBadge.MENTOR,
    )
    p = np.plate("alice")
    assert (
        sum(1 for b in p.badges if b == PlateBadge.MENTOR)
        == 1
    )


def test_add_badge_unknown():
    np = NamePlateSystem()
    assert not np.add_badge(
        entity_id="ghost", badge=PlateBadge.GM,
    )


def test_remove_badge():
    np = NamePlateSystem()
    np.upsert_player(
        entity_id="alice", display_name="Alice",
        level=10, zone_id="z",
        badges=(PlateBadge.OUTLAW,),
    )
    assert np.remove_badge(
        entity_id="alice", badge=PlateBadge.OUTLAW,
    )
    p = np.plate("alice")
    assert PlateBadge.OUTLAW not in p.badges


def test_remove_badge_not_present_returns_false():
    np = NamePlateSystem()
    np.upsert_player(
        entity_id="alice", display_name="Alice",
        level=10, zone_id="z",
    )
    assert not np.remove_badge(
        entity_id="alice", badge=PlateBadge.GM,
    )


def test_party_promotion():
    np = NamePlateSystem()
    np.upsert_player(
        entity_id="alice", display_name="Alice",
        level=10, zone_id="z",
    )
    np.upsert_player(
        entity_id="bob", display_name="Bob",
        level=10, zone_id="z",
    )
    np.declare_party(
        viewer_id="alice", member_ids=("bob",),
    )
    plates = np.plates_in_zone(
        zone_id="z", viewer_id="alice",
    )
    bob = next(
        p for p in plates if p.entity_id == "bob"
    )
    assert bob.kind == PlateKind.PARTY_MEMBER
    assert PlateBadge.PARTY in bob.badges


def test_self_not_promoted_to_party_member():
    np = NamePlateSystem()
    np.upsert_player(
        entity_id="alice", display_name="Alice",
        level=10, zone_id="z",
    )
    np.declare_party(
        viewer_id="alice", member_ids=("alice",),
    )
    plates = np.plates_in_zone(
        zone_id="z", viewer_id="alice",
    )
    alice = next(
        p for p in plates if p.entity_id == "alice"
    )
    assert alice.kind == PlateKind.PLAYER


def test_plates_in_zone_filters_zone():
    np = NamePlateSystem()
    np.upsert_player(
        entity_id="alice", display_name="Alice",
        level=10, zone_id="z1",
    )
    np.upsert_player(
        entity_id="bob", display_name="Bob",
        level=10, zone_id="z2",
    )
    plates = np.plates_in_zone(
        zone_id="z1", viewer_id="alice",
    )
    ids = {p.entity_id for p in plates}
    assert ids == {"alice"}


def test_unknown_nation_falls_back_to_white():
    np = NamePlateSystem()
    plate = np.upsert_player(
        entity_id="alice", display_name="Alice",
        level=1, nation="atlantis",
        zone_id="z",
    )
    assert plate.nation_color == "white"


def test_total_plates():
    np = NamePlateSystem()
    np.upsert_player(
        entity_id="a", display_name="A",
        level=1, zone_id="z",
    )
    np.upsert_mob(
        entity_id="m", display_name="M",
        level=1, zone_id="z",
    )
    assert np.total_plates() == 2


def test_hp_band_color_mapping():
    np = NamePlateSystem()
    np.upsert_mob(
        entity_id="m", display_name="m",
        level=1, zone_id="z",
    )
    pairs = (
        (HPBand.FULL, "green"),
        (HPBand.WOUNDED, "yellow"),
        (HPBand.BLOODIED, "orange"),
    )
    for band, color in pairs:
        np.update_hp_band(entity_id="m", band=band)
        assert np.plate("m").hp_color == color
