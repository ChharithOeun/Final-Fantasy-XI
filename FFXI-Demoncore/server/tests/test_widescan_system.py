"""Tests for the widescan system."""
from __future__ import annotations

from server.widescan_system import (
    BASE_SCAN_RADIUS,
    BST_MAIN_BONUS,
    JobKind,
    MobScanRecord,
    THF_MAIN_BONUS,
    WidescanSystem,
    ZONEWIDE,
)


def test_baseline_100_yalms_for_other_jobs():
    w = WidescanSystem()
    r = w.compute_radius(main_job=JobKind.WAR)
    assert r == BASE_SCAN_RADIUS


def test_main_rng_is_zonewide():
    w = WidescanSystem()
    assert w.compute_radius(
        main_job=JobKind.RNG,
    ) == ZONEWIDE


def test_main_bst_500():
    w = WidescanSystem()
    r = w.compute_radius(main_job=JobKind.BST)
    assert r == BASE_SCAN_RADIUS + BST_MAIN_BONUS
    assert r == 500


def test_main_thf_300():
    w = WidescanSystem()
    r = w.compute_radius(main_job=JobKind.THF)
    assert r == BASE_SCAN_RADIUS + THF_MAIN_BONUS
    assert r == 300


def test_sub_rng_adds_200():
    w = WidescanSystem()
    # WHM/RNG = 100 + 200 = 300
    r = w.compute_radius(
        main_job=JobKind.WHM, sub_job=JobKind.RNG,
    )
    assert r == 300


def test_sub_bst_adds_100():
    w = WidescanSystem()
    r = w.compute_radius(
        main_job=JobKind.WHM, sub_job=JobKind.BST,
    )
    assert r == 200


def test_sub_thf_adds_50():
    w = WidescanSystem()
    r = w.compute_radius(
        main_job=JobKind.WHM, sub_job=JobKind.THF,
    )
    assert r == 150


def test_secondary_sub_rng_adds_100():
    w = WidescanSystem()
    # WHM/BST/RNG = 100 + 100 + 100 = 300
    r = w.compute_radius(
        main_job=JobKind.WHM,
        sub_job=JobKind.BST,
        secondary_sub_job=JobKind.RNG,
    )
    assert r == 300


def test_user_example_rdm_rng_thf():
    """Spec: RDM/RNG/THF = 100 + 200 + 25 = 325."""
    w = WidescanSystem()
    r = w.compute_radius(
        main_job=JobKind.RDM,
        sub_job=JobKind.RNG,
        secondary_sub_job=JobKind.THF,
    )
    assert r == 325


def test_main_thf_plus_sub_rng():
    """THF/RNG = 300 + 200 = 500."""
    w = WidescanSystem()
    r = w.compute_radius(
        main_job=JobKind.THF, sub_job=JobKind.RNG,
    )
    assert r == 500


def test_main_bst_plus_thf_sub():
    """BST/THF = 500 + 50 = 550."""
    w = WidescanSystem()
    r = w.compute_radius(
        main_job=JobKind.BST, sub_job=JobKind.THF,
    )
    assert r == 550


def test_main_rng_with_subs_still_zonewide():
    """Sub bonuses do NOT escalate; main RNG is already
    zonewide and stays so."""
    w = WidescanSystem()
    r = w.compute_radius(
        main_job=JobKind.RNG,
        sub_job=JobKind.BST,
        secondary_sub_job=JobKind.THF,
    )
    assert r == ZONEWIDE


def test_sub_matching_main_no_double_count():
    """BST/BST should not stack the sub bonus on top of main."""
    w = WidescanSystem()
    r = w.compute_radius(
        main_job=JobKind.BST, sub_job=JobKind.BST,
    )
    # Main BST = 500. Sub BST should NOT add another 100.
    assert r == 500


def test_secondary_sub_matching_main_no_double_count():
    """BST/THF/BST should not double-count BST."""
    w = WidescanSystem()
    r = w.compute_radius(
        main_job=JobKind.BST, sub_job=JobKind.THF,
        secondary_sub_job=JobKind.BST,
    )
    # 500 + 50 + 0 = 550
    assert r == 550


def test_secondary_sub_matching_first_sub_no_double_count():
    """WHM/RNG/RNG should not stack RNG twice."""
    w = WidescanSystem()
    r = w.compute_radius(
        main_job=JobKind.WHM, sub_job=JobKind.RNG,
        secondary_sub_job=JobKind.RNG,
    )
    # 100 + 200 + 0 = 300
    assert r == 300


def test_scan_filters_by_radius():
    w = WidescanSystem()
    mobs = (
        MobScanRecord(
            mob_id="near", label="Goblin", x=50, y=0,
        ),
        MobScanRecord(
            mob_id="far", label="Orc", x=400, y=0,
        ),
    )
    res = w.scan(
        player_id="alice", zone_id="ronfaure",
        caster_x=0, caster_y=0,
        main_job=JobKind.WHM,
        mobs_in_zone=mobs,
    )
    ids = {m.mob_id for m in res.revealed_mobs}
    assert "near" in ids
    assert "far" not in ids


def test_scan_zonewide_for_main_rng():
    w = WidescanSystem()
    mobs = (
        MobScanRecord(
            mob_id="far", label="Dragon", x=99999, y=0,
        ),
    )
    res = w.scan(
        player_id="alice", zone_id="ronfaure",
        caster_x=0, caster_y=0,
        main_job=JobKind.RNG,
        mobs_in_zone=mobs,
    )
    assert res.is_zonewide
    assert len(res.revealed_mobs) == 1


def test_scan_3d_distance():
    w = WidescanSystem()
    mobs = (
        MobScanRecord(
            mob_id="aerial", label="Wyvern",
            x=0, y=0, z=200,
        ),
    )
    res = w.scan(
        player_id="alice", zone_id="z",
        caster_x=0, caster_y=0, caster_z=0,
        main_job=JobKind.WHM,
        mobs_in_zone=mobs,
    )
    # Wyvern beyond 100-yalm radius (100 horizontal+vertical)
    ids = {m.mob_id for m in res.revealed_mobs}
    assert "aerial" not in ids


def test_scan_at_radius_boundary_included():
    w = WidescanSystem()
    mobs = (
        MobScanRecord(
            mob_id="edge", label="Bat",
            x=100, y=0,
        ),
    )
    res = w.scan(
        player_id="alice", zone_id="z",
        caster_x=0, caster_y=0,
        main_job=JobKind.WHM,
        mobs_in_zone=mobs,
    )
    ids = {m.mob_id for m in res.revealed_mobs}
    assert "edge" in ids


def test_no_subs_baseline_with_random_job():
    w = WidescanSystem()
    assert w.compute_radius(
        main_job=JobKind.SAM,
    ) == 100


def test_secondary_only_no_first_sub():
    """Player with no first sub but a secondary should still
    apply the secondary bonus."""
    w = WidescanSystem()
    r = w.compute_radius(
        main_job=JobKind.WHM,
        sub_job=JobKind.NONE,
        secondary_sub_job=JobKind.RNG,
    )
    # 100 + 100 (RNG secondary) = 200
    assert r == 200
