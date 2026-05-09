"""Tests for nation_diplomacy."""
from __future__ import annotations

from server.nation_diplomacy import (
    NationDiplomacySystem, EmbassyState,
    IncidentSeverity,
)


def _open(s, **overrides):
    args = dict(
        host_nation="windy", sending_nation="bastok",
        ambassador_id="amb_volker",
        opened_day=10,
    )
    args.update(overrides)
    return s.open_embassy(**args)


def test_open_happy():
    s = NationDiplomacySystem()
    assert _open(s) is not None


def test_open_blank_host():
    s = NationDiplomacySystem()
    assert _open(s, host_nation="") is None


def test_open_self_blocked():
    s = NationDiplomacySystem()
    assert _open(
        s, host_nation="bastok",
        sending_nation="bastok",
    ) is None


def test_open_dup_pair_blocked():
    s = NationDiplomacySystem()
    _open(s)
    assert _open(s) is None


def test_replace_ambassador():
    s = NationDiplomacySystem()
    eid = _open(s)
    assert s.replace_ambassador(
        embassy_id=eid,
        new_ambassador="amb_naji",
    ) is True


def test_replace_blank():
    s = NationDiplomacySystem()
    eid = _open(s)
    assert s.replace_ambassador(
        embassy_id=eid, new_ambassador="",
    ) is False


def test_recall_happy():
    s = NationDiplomacySystem()
    eid = _open(s)
    assert s.recall(
        embassy_id=eid, now_day=20,
        reason="protest",
    ) is True


def test_recall_blank_reason():
    s = NationDiplomacySystem()
    eid = _open(s)
    assert s.recall(
        embassy_id=eid, now_day=20, reason="",
    ) is False


def test_recall_when_not_open():
    s = NationDiplomacySystem()
    eid = _open(s)
    s.close_embassy(
        embassy_id=eid, now_day=20,
        reason="severance",
    )
    assert s.recall(
        embassy_id=eid, now_day=21, reason="x",
    ) is False


def test_close_embassy():
    s = NationDiplomacySystem()
    eid = _open(s)
    assert s.close_embassy(
        embassy_id=eid, now_day=20,
        reason="severance",
    ) is True


def test_double_close_blocked():
    s = NationDiplomacySystem()
    eid = _open(s)
    s.close_embassy(
        embassy_id=eid, now_day=20, reason="x",
    )
    assert s.close_embassy(
        embassy_id=eid, now_day=21, reason="y",
    ) is False


def test_reopen_after_recall():
    s = NationDiplomacySystem()
    eid = _open(s)
    s.recall(embassy_id=eid, now_day=20,
             reason="x")
    assert s.reopen(
        embassy_id=eid, ambassador_id="amb_naji",
        now_day=30,
    ) is True
    assert s.embassy(
        embassy_id=eid,
    ).state == EmbassyState.OPEN


def test_reopen_when_open_blocked():
    s = NationDiplomacySystem()
    eid = _open(s)
    assert s.reopen(
        embassy_id=eid, ambassador_id="amb_naji",
        now_day=30,
    ) is False


def test_reopen_after_close():
    s = NationDiplomacySystem()
    eid = _open(s)
    s.close_embassy(
        embassy_id=eid, now_day=20, reason="x",
    )
    assert s.reopen(
        embassy_id=eid, ambassador_id="amb_naji",
        now_day=50,
    ) is True


def test_file_incident_happy():
    s = NationDiplomacySystem()
    iid = s.file_incident(
        complainant="bastok", accused="windy",
        severity=IncidentSeverity.MAJOR,
        summary="Spy caught",
        occurred_day=10,
    )
    assert iid is not None


def test_file_incident_self():
    s = NationDiplomacySystem()
    iid = s.file_incident(
        complainant="bastok", accused="bastok",
        severity=IncidentSeverity.MINOR,
        summary="x", occurred_day=10,
    )
    assert iid is None


def test_file_incident_blank_summary():
    s = NationDiplomacySystem()
    iid = s.file_incident(
        complainant="bastok", accused="windy",
        severity=IncidentSeverity.MINOR,
        summary="", occurred_day=10,
    )
    assert iid is None


def test_resolve_incident_happy():
    s = NationDiplomacySystem()
    iid = s.file_incident(
        complainant="bastok", accused="windy",
        severity=IncidentSeverity.MAJOR,
        summary="x", occurred_day=10,
    )
    assert s.resolve_incident(
        incident_id=iid, resolved_day=20,
        resolution="apology accepted",
    ) is True


def test_double_resolve_blocked():
    s = NationDiplomacySystem()
    iid = s.file_incident(
        complainant="bastok", accused="windy",
        severity=IncidentSeverity.MAJOR,
        summary="x", occurred_day=10,
    )
    s.resolve_incident(
        incident_id=iid, resolved_day=20,
        resolution="x",
    )
    assert s.resolve_incident(
        incident_id=iid, resolved_day=21,
        resolution="y",
    ) is False


def test_resolve_before_occurred_blocked():
    s = NationDiplomacySystem()
    iid = s.file_incident(
        complainant="bastok", accused="windy",
        severity=IncidentSeverity.MAJOR,
        summary="x", occurred_day=10,
    )
    assert s.resolve_incident(
        incident_id=iid, resolved_day=5,
        resolution="x",
    ) is False


def test_embassies_in_host():
    s = NationDiplomacySystem()
    _open(s, host_nation="windy",
          sending_nation="bastok")
    _open(s, host_nation="windy",
          sending_nation="sandy")
    _open(s, host_nation="bastok",
          sending_nation="windy")
    out = s.embassies_in(host_nation="windy")
    assert len(out) == 2


def test_incidents_between_bidirectional():
    s = NationDiplomacySystem()
    s.file_incident(
        complainant="bastok", accused="windy",
        severity=IncidentSeverity.MINOR,
        summary="x", occurred_day=10,
    )
    s.file_incident(
        complainant="windy", accused="bastok",
        severity=IncidentSeverity.MAJOR,
        summary="y", occurred_day=15,
    )
    s.file_incident(
        complainant="bastok", accused="sandy",
        severity=IncidentSeverity.MINOR,
        summary="z", occurred_day=20,
    )
    out = s.incidents_between(
        a="bastok", b="windy",
    )
    assert len(out) == 2


def test_embassy_unknown():
    s = NationDiplomacySystem()
    assert s.embassy(embassy_id="ghost") is None


def test_enum_counts():
    assert len(list(EmbassyState)) == 3
    assert len(list(IncidentSeverity)) == 5
