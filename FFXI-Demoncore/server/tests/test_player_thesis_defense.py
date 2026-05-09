"""Tests for player_thesis_defense."""
from __future__ import annotations

from server.player_thesis_defense import (
    PlayerThesisDefenseSystem, ThesisState, Verdict,
)


def _begin(s: PlayerThesisDefenseSystem) -> str:
    return s.begin_thesis(
        candidate_id="naji",
        title="On Mythril Allotropy",
        field="metallurgy",
    )


def _through_submit(
    s: PlayerThesisDefenseSystem,
    examiner_count: int = 3,
) -> str:
    tid = _begin(s)
    for i in range(examiner_count):
        s.add_examiner(
            thesis_id=tid, examiner_id=f"ex_{i}",
        )
    s.submit(thesis_id=tid, candidate_id="naji")
    return tid


def test_begin_happy():
    s = PlayerThesisDefenseSystem()
    tid = _begin(s)
    assert tid is not None


def test_begin_empty_field_blocked():
    s = PlayerThesisDefenseSystem()
    assert s.begin_thesis(
        candidate_id="x", title="t", field="",
    ) is None


def test_add_examiner_happy():
    s = PlayerThesisDefenseSystem()
    tid = _begin(s)
    assert s.add_examiner(
        thesis_id=tid, examiner_id="prof_1",
    ) is True


def test_examiner_self_blocked():
    s = PlayerThesisDefenseSystem()
    tid = _begin(s)
    # Candidate can't be their own examiner
    assert s.add_examiner(
        thesis_id=tid, examiner_id="naji",
    ) is False


def test_examiner_dup_blocked():
    s = PlayerThesisDefenseSystem()
    tid = _begin(s)
    s.add_examiner(
        thesis_id=tid, examiner_id="prof_1",
    )
    assert s.add_examiner(
        thesis_id=tid, examiner_id="prof_1",
    ) is False


def test_examiner_cap():
    s = PlayerThesisDefenseSystem()
    tid = _begin(s)
    for i in range(7):
        s.add_examiner(
            thesis_id=tid, examiner_id=f"ex_{i}",
        )
    assert s.add_examiner(
        thesis_id=tid, examiner_id="overflow",
    ) is False


def test_submit_below_min_blocked():
    s = PlayerThesisDefenseSystem()
    tid = _begin(s)
    s.add_examiner(
        thesis_id=tid, examiner_id="ex_1",
    )
    s.add_examiner(
        thesis_id=tid, examiner_id="ex_2",
    )
    # Only 2 examiners, min is 3
    assert s.submit(
        thesis_id=tid, candidate_id="naji",
    ) is False


def test_submit_wrong_candidate_blocked():
    s = PlayerThesisDefenseSystem()
    tid = _begin(s)
    for i in range(3):
        s.add_examiner(
            thesis_id=tid, examiner_id=f"ex_{i}",
        )
    assert s.submit(
        thesis_id=tid, candidate_id="bob",
    ) is False


def test_submit_happy():
    s = PlayerThesisDefenseSystem()
    tid = _through_submit(s)
    assert s.thesis(
        thesis_id=tid,
    ).state == ThesisState.SUBMITTED


def test_add_examiner_after_submit_blocked():
    s = PlayerThesisDefenseSystem()
    tid = _through_submit(s)
    assert s.add_examiner(
        thesis_id=tid, examiner_id="extra",
    ) is False


def test_submit_score_happy():
    s = PlayerThesisDefenseSystem()
    tid = _through_submit(s)
    assert s.submit_score(
        thesis_id=tid, examiner_id="ex_0",
        score=80,
    ) is True


def test_submit_score_non_examiner_blocked():
    s = PlayerThesisDefenseSystem()
    tid = _through_submit(s)
    assert s.submit_score(
        thesis_id=tid, examiner_id="not_examiner",
        score=80,
    ) is False


def test_submit_score_invalid_blocked():
    s = PlayerThesisDefenseSystem()
    tid = _through_submit(s)
    assert s.submit_score(
        thesis_id=tid, examiner_id="ex_0",
        score=200,
    ) is False


def test_submit_score_double_blocked():
    s = PlayerThesisDefenseSystem()
    tid = _through_submit(s)
    s.submit_score(
        thesis_id=tid, examiner_id="ex_0",
        score=80,
    )
    assert s.submit_score(
        thesis_id=tid, examiner_id="ex_0",
        score=70,
    ) is False


def test_render_verdict_pass():
    s = PlayerThesisDefenseSystem()
    tid = _through_submit(s)
    s.submit_score(
        thesis_id=tid, examiner_id="ex_0",
        score=80,
    )
    s.submit_score(
        thesis_id=tid, examiner_id="ex_1",
        score=70,
    )
    s.submit_score(
        thesis_id=tid, examiner_id="ex_2",
        score=50,
    )
    # 2 of 3 passing → majority
    verdict = s.render_verdict(
        thesis_id=tid, defense_day=10,
    )
    assert verdict == Verdict.PASS
    assert s.thesis(
        thesis_id=tid,
    ).state == ThesisState.DEFENDED


def test_render_verdict_fail():
    s = PlayerThesisDefenseSystem()
    tid = _through_submit(s)
    s.submit_score(
        thesis_id=tid, examiner_id="ex_0",
        score=80,
    )
    s.submit_score(
        thesis_id=tid, examiner_id="ex_1",
        score=40,
    )
    s.submit_score(
        thesis_id=tid, examiner_id="ex_2",
        score=30,
    )
    # 1 of 3 passing — fails
    verdict = s.render_verdict(
        thesis_id=tid, defense_day=10,
    )
    assert verdict == Verdict.FAIL
    assert s.thesis(
        thesis_id=tid,
    ).state == ThesisState.FAILED_AWAITING


def test_render_verdict_partial_scores_blocked():
    s = PlayerThesisDefenseSystem()
    tid = _through_submit(s)
    s.submit_score(
        thesis_id=tid, examiner_id="ex_0",
        score=80,
    )
    # Only 1 of 3 examiners scored
    assert s.render_verdict(
        thesis_id=tid, defense_day=10,
    ) is None


def test_average_score_computed():
    s = PlayerThesisDefenseSystem()
    tid = _through_submit(s)
    s.submit_score(
        thesis_id=tid, examiner_id="ex_0",
        score=80,
    )
    s.submit_score(
        thesis_id=tid, examiner_id="ex_1",
        score=70,
    )
    s.submit_score(
        thesis_id=tid, examiner_id="ex_2",
        score=60,
    )
    s.render_verdict(
        thesis_id=tid, defense_day=10,
    )
    assert s.thesis(
        thesis_id=tid,
    ).average_score == 70


def test_retry_after_cooldown():
    s = PlayerThesisDefenseSystem()
    tid = _through_submit(s)
    for i, score in enumerate([20, 30, 40]):
        s.submit_score(
            thesis_id=tid, examiner_id=f"ex_{i}",
            score=score,
        )
    s.render_verdict(thesis_id=tid, defense_day=10)
    assert s.retry(
        thesis_id=tid, candidate_id="naji",
        current_day=45,
    ) is True
    assert s.thesis(
        thesis_id=tid,
    ).state == ThesisState.DRAFT


def test_retry_before_cooldown_blocked():
    s = PlayerThesisDefenseSystem()
    tid = _through_submit(s)
    for i, score in enumerate([20, 30, 40]):
        s.submit_score(
            thesis_id=tid, examiner_id=f"ex_{i}",
            score=score,
        )
    s.render_verdict(thesis_id=tid, defense_day=10)
    assert s.retry(
        thesis_id=tid, candidate_id="naji",
        current_day=20,
    ) is False


def test_retry_passed_thesis_blocked():
    s = PlayerThesisDefenseSystem()
    tid = _through_submit(s)
    for i in range(3):
        s.submit_score(
            thesis_id=tid, examiner_id=f"ex_{i}",
            score=80,
        )
    s.render_verdict(thesis_id=tid, defense_day=10)
    # Passed — can't re-retry
    assert s.retry(
        thesis_id=tid, candidate_id="naji",
        current_day=100,
    ) is False


def test_examiners_listing():
    s = PlayerThesisDefenseSystem()
    tid = _through_submit(s)
    assert len(s.examiners(thesis_id=tid)) == 3


def test_unknown_thesis():
    s = PlayerThesisDefenseSystem()
    assert s.thesis(thesis_id="ghost") is None


def test_enum_counts():
    assert len(list(ThesisState)) == 4
    assert len(list(Verdict)) == 2
