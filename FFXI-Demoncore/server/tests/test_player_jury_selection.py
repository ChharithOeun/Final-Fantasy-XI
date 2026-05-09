"""Tests for player_jury_selection."""
from __future__ import annotations

from server.player_jury_selection import (
    PlayerJurySelectionSystem, CaseState, JuryVerdict,
)


def _enroll_pool(
    s: PlayerJurySelectionSystem, n: int = 5,
) -> None:
    for i in range(n):
        s.enroll_juror(juror_id=f"j_{i}")


def _empaneled(
    s: PlayerJurySelectionSystem, size: int = 3,
) -> str:
    _enroll_pool(s)
    return s.empanel_jury(
        lawsuit_id="suit_1", requested_size=size,
    )


def test_enroll_juror_happy():
    s = PlayerJurySelectionSystem()
    assert s.enroll_juror(juror_id="alice") is True


def test_enroll_juror_dup_blocked():
    s = PlayerJurySelectionSystem()
    s.enroll_juror(juror_id="alice")
    assert s.enroll_juror(juror_id="alice") is False


def test_enroll_juror_empty_blocked():
    s = PlayerJurySelectionSystem()
    assert s.enroll_juror(juror_id="") is False


def test_pool_size():
    s = PlayerJurySelectionSystem()
    _enroll_pool(s, n=4)
    assert s.pool_size() == 4


def test_empanel_jury_happy():
    s = PlayerJurySelectionSystem()
    cid = _empaneled(s, size=3)
    assert cid is not None
    assert s.case(
        case_id=cid,
    ).state == CaseState.EMPANELED


def test_empanel_jury_too_small_blocked():
    s = PlayerJurySelectionSystem()
    _enroll_pool(s, n=10)
    assert s.empanel_jury(
        lawsuit_id="x", requested_size=2,
    ) is None


def test_empanel_jury_too_large_blocked():
    s = PlayerJurySelectionSystem()
    _enroll_pool(s, n=20)
    assert s.empanel_jury(
        lawsuit_id="x", requested_size=15,
    ) is None


def test_empanel_jury_pool_too_small_blocked():
    s = PlayerJurySelectionSystem()
    _enroll_pool(s, n=2)
    assert s.empanel_jury(
        lawsuit_id="x", requested_size=3,
    ) is None


def test_empaneled_jurors_become_busy():
    s = PlayerJurySelectionSystem()
    _enroll_pool(s, n=5)
    s.empanel_jury(
        lawsuit_id="suit_1", requested_size=3,
    )
    assert s.available_count() == 2


def test_empanel_second_jury_uses_remaining_pool():
    s = PlayerJurySelectionSystem()
    _enroll_pool(s, n=6)
    cid1 = s.empanel_jury(
        lawsuit_id="suit_1", requested_size=3,
    )
    cid2 = s.empanel_jury(
        lawsuit_id="suit_2", requested_size=3,
    )
    # Second jury should use j_3, j_4, j_5
    assert cid2 is not None
    assert "j_0" not in s.jurors(case_id=cid2)


def test_submit_verdict_happy():
    s = PlayerJurySelectionSystem()
    cid = _empaneled(s, size=3)
    assert s.submit_verdict(
        case_id=cid, juror_id="j_0", guilty=True,
    ) is True


def test_submit_verdict_non_juror_blocked():
    s = PlayerJurySelectionSystem()
    cid = _empaneled(s, size=3)
    assert s.submit_verdict(
        case_id=cid, juror_id="stranger",
        guilty=True,
    ) is False


def test_submit_verdict_dup_blocked():
    s = PlayerJurySelectionSystem()
    cid = _empaneled(s, size=3)
    s.submit_verdict(
        case_id=cid, juror_id="j_0", guilty=True,
    )
    assert s.submit_verdict(
        case_id=cid, juror_id="j_0", guilty=False,
    ) is False


def test_full_verdicts_advance_state():
    s = PlayerJurySelectionSystem()
    cid = _empaneled(s, size=3)
    for i in range(3):
        s.submit_verdict(
            case_id=cid, juror_id=f"j_{i}",
            guilty=True,
        )
    assert s.case(
        case_id=cid,
    ).state == CaseState.DELIBERATING


def test_finalize_guilty_majority():
    s = PlayerJurySelectionSystem()
    cid = _empaneled(s, size=3)
    s.submit_verdict(
        case_id=cid, juror_id="j_0", guilty=True,
    )
    s.submit_verdict(
        case_id=cid, juror_id="j_1", guilty=True,
    )
    s.submit_verdict(
        case_id=cid, juror_id="j_2", guilty=False,
    )
    verdict = s.finalize_verdict(case_id=cid)
    assert verdict == JuryVerdict.GUILTY


def test_finalize_not_guilty_majority():
    s = PlayerJurySelectionSystem()
    cid = _empaneled(s, size=3)
    s.submit_verdict(
        case_id=cid, juror_id="j_0", guilty=False,
    )
    s.submit_verdict(
        case_id=cid, juror_id="j_1", guilty=False,
    )
    s.submit_verdict(
        case_id=cid, juror_id="j_2", guilty=True,
    )
    verdict = s.finalize_verdict(case_id=cid)
    assert verdict == JuryVerdict.NOT_GUILTY


def test_finalize_tie_resolves_not_guilty():
    s = PlayerJurySelectionSystem()
    _enroll_pool(s, n=4)
    cid = s.empanel_jury(
        lawsuit_id="suit_1", requested_size=4,
    )
    s.submit_verdict(
        case_id=cid, juror_id="j_0", guilty=True,
    )
    s.submit_verdict(
        case_id=cid, juror_id="j_1", guilty=True,
    )
    s.submit_verdict(
        case_id=cid, juror_id="j_2", guilty=False,
    )
    s.submit_verdict(
        case_id=cid, juror_id="j_3", guilty=False,
    )
    verdict = s.finalize_verdict(case_id=cid)
    assert verdict == JuryVerdict.NOT_GUILTY


def test_finalize_before_full_verdicts_blocked():
    s = PlayerJurySelectionSystem()
    cid = _empaneled(s, size=3)
    s.submit_verdict(
        case_id=cid, juror_id="j_0", guilty=True,
    )
    assert s.finalize_verdict(case_id=cid) is None


def test_finalize_returns_jurors_to_pool():
    s = PlayerJurySelectionSystem()
    cid = _empaneled(s, size=3)
    for i in range(3):
        s.submit_verdict(
            case_id=cid, juror_id=f"j_{i}",
            guilty=True,
        )
    s.finalize_verdict(case_id=cid)
    # All 5 pool members available again
    assert s.available_count() == 5


def test_counts_recorded():
    s = PlayerJurySelectionSystem()
    cid = _empaneled(s, size=3)
    s.submit_verdict(
        case_id=cid, juror_id="j_0", guilty=True,
    )
    s.submit_verdict(
        case_id=cid, juror_id="j_1", guilty=True,
    )
    s.submit_verdict(
        case_id=cid, juror_id="j_2", guilty=False,
    )
    s.finalize_verdict(case_id=cid)
    spec = s.case(case_id=cid)
    assert spec.guilty_count == 2
    assert spec.not_guilty_count == 1


def test_unknown_case():
    s = PlayerJurySelectionSystem()
    assert s.case(case_id="ghost") is None


def test_empanel_empty_lawsuit_blocked():
    s = PlayerJurySelectionSystem()
    _enroll_pool(s, n=5)
    assert s.empanel_jury(
        lawsuit_id="", requested_size=3,
    ) is None


def test_state_count():
    assert len(list(CaseState)) == 3


def test_verdict_count():
    assert len(list(JuryVerdict)) == 2
