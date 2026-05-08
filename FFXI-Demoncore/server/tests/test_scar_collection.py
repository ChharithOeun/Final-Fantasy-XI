"""Tests for scar_collection."""
from __future__ import annotations

from server.scar_collection import (
    BodyPart, Cause, ScarCollection, Severity,
)


def test_acquire_happy():
    s = ScarCollection()
    sid = s.acquire(
        player_id="bob", body_part=BodyPart.FACE,
        severity=Severity.VISIBLE,
        cause=Cause.DEFEAT_BY_NM,
        source_id="behemoth", day=10,
    )
    assert sid is not None
    assert s.scar_count(player_id="bob") == 1


def test_acquire_blank_player_blocked():
    s = ScarCollection()
    sid = s.acquire(
        player_id="", body_part=BodyPart.FACE,
        severity=Severity.VISIBLE,
        cause=Cause.DEFEAT_BY_NM,
        source_id="behemoth", day=10,
    )
    assert sid is None


def test_acquire_blank_source_blocked():
    s = ScarCollection()
    sid = s.acquire(
        player_id="bob", body_part=BodyPart.FACE,
        severity=Severity.VISIBLE,
        cause=Cause.DEFEAT_BY_NM,
        source_id="", day=10,
    )
    assert sid is None


def test_acquire_negative_day_blocked():
    s = ScarCollection()
    sid = s.acquire(
        player_id="bob", body_part=BodyPart.FACE,
        severity=Severity.VISIBLE,
        cause=Cause.DEFEAT_BY_NM,
        source_id="x", day=-1,
    )
    assert sid is None


def test_multiple_scars():
    s = ScarCollection()
    s.acquire(
        player_id="bob", body_part=BodyPart.FACE,
        severity=Severity.FAINT, cause=Cause.DEFEAT_BY_NM,
        source_id="x", day=10,
    )
    s.acquire(
        player_id="bob", body_part=BodyPart.CHEST,
        severity=Severity.DEEP, cause=Cause.BOSS_NEAR_DEATH,
        source_id="tiamat", day=20,
    )
    assert s.scar_count(player_id="bob") == 2


def test_obscure():
    s = ScarCollection()
    sid = s.acquire(
        player_id="bob", body_part=BodyPart.FACE,
        severity=Severity.VISIBLE,
        cause=Cause.DEFEAT_BY_NM,
        source_id="x", day=10,
    )
    assert s.obscure(
        player_id="bob", scar_id=sid, until_day=30,
    ) is True


def test_obscure_unknown_blocked():
    s = ScarCollection()
    assert s.obscure(
        player_id="bob", scar_id="ghost", until_day=30,
    ) is False


def test_obscure_negative_day_blocked():
    s = ScarCollection()
    sid = s.acquire(
        player_id="bob", body_part=BodyPart.FACE,
        severity=Severity.VISIBLE,
        cause=Cause.DEFEAT_BY_NM,
        source_id="x", day=10,
    )
    assert s.obscure(
        player_id="bob", scar_id=sid, until_day=-1,
    ) is False


def test_scars_for_unknown_empty():
    s = ScarCollection()
    assert s.scars_for(player_id="ghost") == []


def test_only_visible_filters():
    s = ScarCollection()
    sid = s.acquire(
        player_id="bob", body_part=BodyPart.FACE,
        severity=Severity.VISIBLE,
        cause=Cause.DEFEAT_BY_NM,
        source_id="x", day=10,
    )
    s.obscure(
        player_id="bob", scar_id=sid, until_day=30,
    )
    visible = s.scars_for(
        player_id="bob", now_day=20, only_visible=True,
    )
    assert visible == []
    all_scars = s.scars_for(
        player_id="bob", only_visible=False,
    )
    assert len(all_scars) == 1


def test_obscure_expires():
    s = ScarCollection()
    sid = s.acquire(
        player_id="bob", body_part=BodyPart.FACE,
        severity=Severity.VISIBLE,
        cause=Cause.DEFEAT_BY_NM,
        source_id="x", day=10,
    )
    s.obscure(
        player_id="bob", scar_id=sid, until_day=30,
    )
    visible = s.scars_for(
        player_id="bob", now_day=50, only_visible=True,
    )
    assert len(visible) == 1


def test_scars_sorted_by_day():
    s = ScarCollection()
    s.acquire(
        player_id="bob", body_part=BodyPart.FACE,
        severity=Severity.VISIBLE,
        cause=Cause.DEFEAT_BY_NM,
        source_id="x", day=20,
    )
    s.acquire(
        player_id="bob", body_part=BodyPart.CHEST,
        severity=Severity.DEEP, cause=Cause.BOSS_NEAR_DEATH,
        source_id="y", day=10,
    )
    out = s.scars_for(player_id="bob")
    assert out[0].acquired_day == 10
    assert out[1].acquired_day == 20


def test_voluntary_oath_scar():
    s = ScarCollection()
    sid = s.acquire(
        player_id="bob", body_part=BodyPart.ARM_RIGHT,
        severity=Severity.DEEP,
        cause=Cause.VOLUNTARY_OATH,
        source_id="nin_initiation", day=50,
    )
    assert sid is not None
    out = s.scars_for(player_id="bob")
    assert out[0].cause == Cause.VOLUNTARY_OATH


def test_inherited_scar_from_permadeath():
    s = ScarCollection()
    sid = s.acquire(
        player_id="bob_jr", body_part=BodyPart.FACE,
        severity=Severity.FAINT,
        cause=Cause.PERMADEATH_PRE,
        source_id="bob_sr_died", day=100,
    )
    out = s.scars_for(player_id="bob_jr")
    assert out[0].cause == Cause.PERMADEATH_PRE


def test_scar_count_unknown_player():
    s = ScarCollection()
    assert s.scar_count(player_id="ghost") == 0


def test_five_causes():
    assert len(list(Cause)) == 5


def test_seven_body_parts():
    assert len(list(BodyPart)) == 7


def test_three_severities():
    assert len(list(Severity)) == 3
