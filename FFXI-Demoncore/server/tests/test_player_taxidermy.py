"""Tests for player_taxidermy."""
from __future__ import annotations

from server.player_taxidermy import (
    PlayerTaxidermySystem, MountStage, Grade,
)


def test_harvest_happy():
    s = PlayerTaxidermySystem()
    assert s.harvest_part(
        part_id="behemoth_head", owner_id="bob",
        mob_kind="behemoth", mob_was_named=True,
        harvested_day=10,
    ) is True


def test_harvest_blank():
    s = PlayerTaxidermySystem()
    assert s.harvest_part(
        part_id="", owner_id="bob",
        mob_kind="x", mob_was_named=False,
        harvested_day=10,
    ) is False


def test_harvest_dup_blocked():
    s = PlayerTaxidermySystem()
    s.harvest_part(
        part_id="x", owner_id="bob",
        mob_kind="goblin", mob_was_named=False,
        harvested_day=10,
    )
    assert s.harvest_part(
        part_id="x", owner_id="bob",
        mob_kind="goblin", mob_was_named=False,
        harvested_day=11,
    ) is False


def test_freshness_decays_linearly():
    s = PlayerTaxidermySystem()
    s.harvest_part(
        part_id="x", owner_id="bob",
        mob_kind="goblin", mob_was_named=False,
        harvested_day=10, decayed_after_days=10,
    )
    s.tick_part(part_id="x", now_day=15)
    assert s.part(
        part_id="x",
    ).freshness == 50


def test_freshness_zero_after_decay():
    s = PlayerTaxidermySystem()
    s.harvest_part(
        part_id="x", owner_id="bob",
        mob_kind="goblin", mob_was_named=False,
        harvested_day=10, decayed_after_days=10,
    )
    s.tick_part(part_id="x", now_day=25)
    assert s.part(
        part_id="x",
    ).freshness == 0


def test_begin_mount_happy():
    s = PlayerTaxidermySystem()
    s.harvest_part(
        part_id="x", owner_id="bob",
        mob_kind="behemoth", mob_was_named=True,
        harvested_day=10,
    )
    mid = s.begin_mount(
        part_id="x",
        plaque_text="Behemoth, defeated 2026-05",
        started_day=11,
    )
    assert mid is not None


def test_begin_mount_decayed_blocked():
    s = PlayerTaxidermySystem()
    s.harvest_part(
        part_id="x", owner_id="bob",
        mob_kind="goblin", mob_was_named=False,
        harvested_day=10, decayed_after_days=10,
    )
    s.tick_part(part_id="x", now_day=25)
    mid = s.begin_mount(
        part_id="x", plaque_text="Goblin",
        started_day=26,
    )
    assert mid is None


def test_begin_mount_dup_blocked():
    s = PlayerTaxidermySystem()
    s.harvest_part(
        part_id="x", owner_id="bob",
        mob_kind="goblin", mob_was_named=False,
        harvested_day=10,
    )
    s.begin_mount(
        part_id="x", plaque_text="Goblin",
        started_day=11,
    )
    assert s.begin_mount(
        part_id="x", plaque_text="Goblin 2",
        started_day=12,
    ) is None


def test_advance_to_mounting():
    s = PlayerTaxidermySystem()
    s.harvest_part(
        part_id="x", owner_id="bob",
        mob_kind="goblin", mob_was_named=False,
        harvested_day=10,
    )
    mid = s.begin_mount(
        part_id="x", plaque_text="Goblin",
        started_day=11,
    )
    assert s.advance_to_mounting(
        mount_id=mid,
    ) is True


def test_advance_double_blocked():
    s = PlayerTaxidermySystem()
    s.harvest_part(
        part_id="x", owner_id="bob",
        mob_kind="goblin", mob_was_named=False,
        harvested_day=10,
    )
    mid = s.begin_mount(
        part_id="x", plaque_text="Goblin",
        started_day=11,
    )
    s.advance_to_mounting(mount_id=mid)
    assert s.advance_to_mounting(
        mount_id=mid,
    ) is False


def test_complete_named_mob_high_grade():
    s = PlayerTaxidermySystem()
    s.harvest_part(
        part_id="x", owner_id="bob",
        mob_kind="behemoth", mob_was_named=True,
        harvested_day=10,
    )
    mid = s.begin_mount(
        part_id="x", plaque_text="Behemoth",
        started_day=11,
    )
    s.advance_to_mounting(mount_id=mid)
    grade = s.complete_mount(
        mount_id=mid, crafter_skill=90,
        now_day=12,
    )
    # 100 freshness + 90 skill + 30 NM bonus = 220
    # -> MUSEUM
    assert grade == Grade.MUSEUM


def test_complete_no_skill_bad_grade():
    s = PlayerTaxidermySystem()
    s.harvest_part(
        part_id="x", owner_id="bob",
        mob_kind="goblin", mob_was_named=False,
        harvested_day=10, decayed_after_days=10,
    )
    s.tick_part(part_id="x", now_day=18)
    # Freshness ~ 20
    mid = s.begin_mount(
        part_id="x", plaque_text="Goblin",
        started_day=19,
    )
    s.advance_to_mounting(mount_id=mid)
    grade = s.complete_mount(
        mount_id=mid, crafter_skill=20,
        now_day=20,
    )
    # 20 + 20 = 40 -> POOR
    assert grade == Grade.POOR


def test_complete_invalid_skill():
    s = PlayerTaxidermySystem()
    s.harvest_part(
        part_id="x", owner_id="bob",
        mob_kind="goblin", mob_was_named=False,
        harvested_day=10,
    )
    mid = s.begin_mount(
        part_id="x", plaque_text="Goblin",
        started_day=11,
    )
    s.advance_to_mounting(mount_id=mid)
    grade = s.complete_mount(
        mount_id=mid, crafter_skill=120,
        now_day=12,
    )
    assert grade is None


def test_complete_before_mounting_blocked():
    s = PlayerTaxidermySystem()
    s.harvest_part(
        part_id="x", owner_id="bob",
        mob_kind="goblin", mob_was_named=False,
        harvested_day=10,
    )
    mid = s.begin_mount(
        part_id="x", plaque_text="Goblin",
        started_day=11,
    )
    grade = s.complete_mount(
        mount_id=mid, crafter_skill=80,
        now_day=12,
    )
    assert grade is None


def test_ruin_mount():
    s = PlayerTaxidermySystem()
    s.harvest_part(
        part_id="x", owner_id="bob",
        mob_kind="goblin", mob_was_named=False,
        harvested_day=10,
    )
    mid = s.begin_mount(
        part_id="x", plaque_text="Goblin",
        started_day=11,
    )
    assert s.ruin_mount(mount_id=mid) is True


def test_ruin_displayed_blocked():
    s = PlayerTaxidermySystem()
    s.harvest_part(
        part_id="x", owner_id="bob",
        mob_kind="goblin", mob_was_named=False,
        harvested_day=10,
    )
    mid = s.begin_mount(
        part_id="x", plaque_text="Goblin",
        started_day=11,
    )
    s.advance_to_mounting(mount_id=mid)
    s.complete_mount(
        mount_id=mid, crafter_skill=80,
        now_day=12,
    )
    assert s.ruin_mount(mount_id=mid) is False


def test_remount_after_ruin():
    s = PlayerTaxidermySystem()
    s.harvest_part(
        part_id="x", owner_id="bob",
        mob_kind="goblin", mob_was_named=False,
        harvested_day=10,
    )
    mid = s.begin_mount(
        part_id="x", plaque_text="Goblin",
        started_day=11,
    )
    s.ruin_mount(mount_id=mid)
    new_mid = s.begin_mount(
        part_id="x", plaque_text="Try 2",
        started_day=20,
    )
    assert new_mid is not None


def test_mounts_of_owner():
    s = PlayerTaxidermySystem()
    s.harvest_part(
        part_id="a", owner_id="bob",
        mob_kind="goblin", mob_was_named=False,
        harvested_day=10,
    )
    s.harvest_part(
        part_id="b", owner_id="bob",
        mob_kind="orc", mob_was_named=False,
        harvested_day=10,
    )
    s.begin_mount(
        part_id="a", plaque_text="A",
        started_day=11,
    )
    s.begin_mount(
        part_id="b", plaque_text="B",
        started_day=12,
    )
    assert len(
        s.mounts_of(owner_id="bob"),
    ) == 2


def test_parts_of_owner():
    s = PlayerTaxidermySystem()
    s.harvest_part(
        part_id="a", owner_id="bob",
        mob_kind="goblin", mob_was_named=False,
        harvested_day=10,
    )
    s.harvest_part(
        part_id="b", owner_id="other",
        mob_kind="orc", mob_was_named=False,
        harvested_day=10,
    )
    out = s.parts_of(owner_id="bob")
    assert len(out) == 1


def test_part_unknown():
    s = PlayerTaxidermySystem()
    assert s.part(part_id="ghost") is None


def test_mount_unknown():
    s = PlayerTaxidermySystem()
    assert s.mount(mount_id="ghost") is None


def test_enum_counts():
    assert len(list(MountStage)) == 5
    assert len(list(Grade)) == 5
