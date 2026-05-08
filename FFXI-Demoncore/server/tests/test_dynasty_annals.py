"""Tests for dynasty_annals."""
from __future__ import annotations

from server.dynasty_annals import (
    AnnalKind, DynastyAnnals,
)


def test_open_dynasty():
    d = DynastyAnnals()
    assert d.open_dynasty(family_name="Stoneforge") is True


def test_open_blank_blocked():
    d = DynastyAnnals()
    assert d.open_dynasty(family_name="") is False


def test_open_dup_blocked():
    d = DynastyAnnals()
    d.open_dynasty(family_name="Stoneforge")
    assert d.open_dynasty(family_name="Stoneforge") is False


def test_record_happy():
    d = DynastyAnnals()
    d.open_dynasty(family_name="Stoneforge")
    eid = d.record(
        family_name="Stoneforge",
        kind=AnnalKind.BIRTH, member_id="bob_jr",
        summary="Heir Bob Jr was born.", day=10,
    )
    assert eid is not None


def test_record_unknown_family():
    d = DynastyAnnals()
    eid = d.record(
        family_name="Ghost", kind=AnnalKind.BIRTH,
        member_id="x", summary="y", day=10,
    )
    assert eid is None


def test_record_blank_member():
    d = DynastyAnnals()
    d.open_dynasty(family_name="Stoneforge")
    eid = d.record(
        family_name="Stoneforge", kind=AnnalKind.BIRTH,
        member_id="", summary="y", day=10,
    )
    assert eid is None


def test_record_blank_summary():
    d = DynastyAnnals()
    d.open_dynasty(family_name="Stoneforge")
    eid = d.record(
        family_name="Stoneforge", kind=AnnalKind.BIRTH,
        member_id="bob_jr", summary="", day=10,
    )
    assert eid is None


def test_record_negative_day():
    d = DynastyAnnals()
    d.open_dynasty(family_name="Stoneforge")
    eid = d.record(
        family_name="Stoneforge", kind=AnnalKind.BIRTH,
        member_id="x", summary="y", day=-1,
    )
    assert eid is None


def test_entries_for_sorted_by_day():
    d = DynastyAnnals()
    d.open_dynasty(family_name="Stoneforge")
    d.record(
        family_name="Stoneforge",
        kind=AnnalKind.ACHIEVEMENT,
        member_id="bob", summary="x", day=20,
    )
    d.record(
        family_name="Stoneforge",
        kind=AnnalKind.BIRTH,
        member_id="bob", summary="y", day=10,
    )
    out = d.entries_for(family_name="Stoneforge")
    assert out[0].day == 10
    assert out[1].day == 20


def test_entries_for_unknown_family():
    d = DynastyAnnals()
    assert d.entries_for(family_name="Ghost") == []


def test_entries_of_kind():
    d = DynastyAnnals()
    d.open_dynasty(family_name="Stoneforge")
    d.record(
        family_name="Stoneforge", kind=AnnalKind.BIRTH,
        member_id="bob", summary="x", day=10,
    )
    d.record(
        family_name="Stoneforge",
        kind=AnnalKind.ACHIEVEMENT,
        member_id="bob", summary="y", day=20,
    )
    out = d.entries_of_kind(
        family_name="Stoneforge",
        kind=AnnalKind.ACHIEVEMENT,
    )
    assert len(out) == 1


def test_annal_score_aggregates():
    d = DynastyAnnals()
    d.open_dynasty(family_name="Stoneforge")
    d.record(
        family_name="Stoneforge", kind=AnnalKind.BIRTH,
        member_id="bob", summary="x", day=10,
    )  # +1
    d.record(
        family_name="Stoneforge",
        kind=AnnalKind.ACHIEVEMENT,
        member_id="bob", summary="y", day=20,
    )  # +5
    d.record(
        family_name="Stoneforge",
        kind=AnnalKind.HONOR_BESTOWED,
        member_id="bob", summary="z", day=30,
    )  # +7
    assert d.annal_score(family_name="Stoneforge") == 13


def test_annal_score_with_infamy():
    d = DynastyAnnals()
    d.open_dynasty(family_name="Stoneforge")
    d.record(
        family_name="Stoneforge",
        kind=AnnalKind.ACHIEVEMENT,
        member_id="bob", summary="x", day=10,
    )  # +5
    d.record(
        family_name="Stoneforge", kind=AnnalKind.INFAMY,
        member_id="bob", summary="y", day=20,
    )  # -8
    assert d.annal_score(family_name="Stoneforge") == -3


def test_annal_score_unknown_zero():
    d = DynastyAnnals()
    assert d.annal_score(family_name="Ghost") == 0


def test_descendant_first_high_score():
    d = DynastyAnnals()
    d.open_dynasty(family_name="Stoneforge")
    d.record(
        family_name="Stoneforge",
        kind=AnnalKind.DESCENDANT_FIRST,
        member_id="bob_iii", summary="First Tiamat kill.",
        day=100,
    )
    assert d.annal_score(family_name="Stoneforge") == 15


def test_members_listed_dedup():
    d = DynastyAnnals()
    d.open_dynasty(family_name="Stoneforge")
    d.record(
        family_name="Stoneforge", kind=AnnalKind.BIRTH,
        member_id="bob", summary="x", day=10,
    )
    d.record(
        family_name="Stoneforge",
        kind=AnnalKind.ACHIEVEMENT,
        member_id="bob", summary="y", day=20,
    )
    d.record(
        family_name="Stoneforge",
        kind=AnnalKind.MARRIAGE,
        member_id="cara", summary="z", day=30,
    )
    out = d.members_listed(family_name="Stoneforge")
    assert out == ["bob", "cara"]


def test_members_listed_unknown_family():
    d = DynastyAnnals()
    assert d.members_listed(family_name="Ghost") == []


def test_seven_annal_kinds():
    assert len(list(AnnalKind)) == 7
