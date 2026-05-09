"""Tests for player_dance_competition."""
from __future__ import annotations

from server.player_dance_competition import (
    PlayerDanceCompetitionSystem, TournamentState,
)


def _open(s: PlayerDanceCompetitionSystem) -> str:
    return s.open_tournament(
        venue_id="windy_amphitheater",
        field_min=3, field_max=8,
        prize_purse_gil=10000,
    )


def _register_three(
    s: PlayerDanceCompetitionSystem, tid: str,
) -> None:
    s.register_dancer(
        tournament_id=tid, dancer_id="alice",
    )
    s.register_dancer(
        tournament_id=tid, dancer_id="bob",
    )
    s.register_dancer(
        tournament_id=tid, dancer_id="cara",
    )


def test_open_tournament_happy():
    s = PlayerDanceCompetitionSystem()
    tid = _open(s)
    assert tid is not None


def test_open_empty_venue():
    s = PlayerDanceCompetitionSystem()
    assert s.open_tournament(
        venue_id="", field_min=3, field_max=8,
        prize_purse_gil=10000,
    ) is None


def test_open_invalid_field_size():
    s = PlayerDanceCompetitionSystem()
    assert s.open_tournament(
        venue_id="v", field_min=1, field_max=8,
        prize_purse_gil=0,
    ) is None


def test_open_negative_purse():
    s = PlayerDanceCompetitionSystem()
    assert s.open_tournament(
        venue_id="v", field_min=3, field_max=8,
        prize_purse_gil=-100,
    ) is None


def test_register_dancer_happy():
    s = PlayerDanceCompetitionSystem()
    tid = _open(s)
    assert s.register_dancer(
        tournament_id=tid, dancer_id="alice",
    ) is True


def test_register_dup_blocked():
    s = PlayerDanceCompetitionSystem()
    tid = _open(s)
    s.register_dancer(
        tournament_id=tid, dancer_id="alice",
    )
    assert s.register_dancer(
        tournament_id=tid, dancer_id="alice",
    ) is False


def test_register_field_full():
    s = PlayerDanceCompetitionSystem()
    tid = s.open_tournament(
        venue_id="v", field_min=2, field_max=2,
        prize_purse_gil=100,
    )
    s.register_dancer(tournament_id=tid, dancer_id="a")
    s.register_dancer(tournament_id=tid, dancer_id="b")
    assert s.register_dancer(
        tournament_id=tid, dancer_id="c",
    ) is False


def test_register_after_lock_blocked():
    s = PlayerDanceCompetitionSystem()
    tid = _open(s)
    _register_three(s, tid)
    s.lock_field(tournament_id=tid)
    assert s.register_dancer(
        tournament_id=tid, dancer_id="dave",
    ) is False


def test_lock_field_happy():
    s = PlayerDanceCompetitionSystem()
    tid = _open(s)
    _register_three(s, tid)
    assert s.lock_field(tournament_id=tid) is True


def test_lock_field_min_required():
    s = PlayerDanceCompetitionSystem()
    tid = _open(s)
    s.register_dancer(tournament_id=tid, dancer_id="a")
    s.register_dancer(tournament_id=tid, dancer_id="b")
    # Only 2 dancers, min is 3
    assert s.lock_field(tournament_id=tid) is False


def test_submit_performance_happy():
    s = PlayerDanceCompetitionSystem()
    tid = _open(s)
    _register_three(s, tid)
    s.lock_field(tournament_id=tid)
    score = s.submit_performance(
        tournament_id=tid, dancer_id="alice",
        tempo_score=80, precision_score=70,
        style_score=90,
    )
    assert score is not None


def test_submit_invalid_score():
    s = PlayerDanceCompetitionSystem()
    tid = _open(s)
    _register_three(s, tid)
    s.lock_field(tournament_id=tid)
    assert s.submit_performance(
        tournament_id=tid, dancer_id="alice",
        tempo_score=0, precision_score=70,
        style_score=90,
    ) is None


def test_submit_unregistered_dancer():
    s = PlayerDanceCompetitionSystem()
    tid = _open(s)
    _register_three(s, tid)
    s.lock_field(tournament_id=tid)
    assert s.submit_performance(
        tournament_id=tid, dancer_id="ghost",
        tempo_score=80, precision_score=80,
        style_score=80,
    ) is None


def test_submit_before_lock_blocked():
    s = PlayerDanceCompetitionSystem()
    tid = _open(s)
    _register_three(s, tid)
    assert s.submit_performance(
        tournament_id=tid, dancer_id="alice",
        tempo_score=80, precision_score=80,
        style_score=80,
    ) is None


def test_weighted_total_correct():
    s = PlayerDanceCompetitionSystem()
    tid = _open(s)
    _register_three(s, tid)
    s.lock_field(tournament_id=tid)
    score = s.submit_performance(
        tournament_id=tid, dancer_id="alice",
        tempo_score=100, precision_score=100,
        style_score=100,
    )
    # 100*30 + 100*40 + 100*30 = 10000 / 100 = 100
    assert score == 100


def test_finalize_orders_by_score():
    s = PlayerDanceCompetitionSystem()
    tid = _open(s)
    _register_three(s, tid)
    s.lock_field(tournament_id=tid)
    s.submit_performance(
        tournament_id=tid, dancer_id="alice",
        tempo_score=50, precision_score=50,
        style_score=50,
    )
    s.submit_performance(
        tournament_id=tid, dancer_id="bob",
        tempo_score=90, precision_score=90,
        style_score=90,
    )
    s.submit_performance(
        tournament_id=tid, dancer_id="cara",
        tempo_score=70, precision_score=70,
        style_score=70,
    )
    rankings = s.finalize(tournament_id=tid)
    assert rankings == ("bob", "cara", "alice")


def test_finalize_state_set():
    s = PlayerDanceCompetitionSystem()
    tid = _open(s)
    _register_three(s, tid)
    s.lock_field(tournament_id=tid)
    s.submit_performance(
        tournament_id=tid, dancer_id="alice",
        tempo_score=50, precision_score=50,
        style_score=50,
    )
    s.submit_performance(
        tournament_id=tid, dancer_id="bob",
        tempo_score=90, precision_score=90,
        style_score=90,
    )
    s.submit_performance(
        tournament_id=tid, dancer_id="cara",
        tempo_score=70, precision_score=70,
        style_score=70,
    )
    s.finalize(tournament_id=tid)
    t_obj = s.tournament(tournament_id=tid)
    assert t_obj.state == TournamentState.COMPLETED


def test_finalize_before_lock_blocked():
    s = PlayerDanceCompetitionSystem()
    tid = _open(s)
    _register_three(s, tid)
    assert s.finalize(tournament_id=tid) is None


def test_payout_first_place_50pct():
    s = PlayerDanceCompetitionSystem()
    tid = _open(s)
    _register_three(s, tid)
    s.lock_field(tournament_id=tid)
    s.submit_performance(
        tournament_id=tid, dancer_id="alice",
        tempo_score=50, precision_score=50,
        style_score=50,
    )
    s.submit_performance(
        tournament_id=tid, dancer_id="bob",
        tempo_score=90, precision_score=90,
        style_score=90,
    )
    s.submit_performance(
        tournament_id=tid, dancer_id="cara",
        tempo_score=70, precision_score=70,
        style_score=70,
    )
    s.finalize(tournament_id=tid)
    # purse 10000, bob is 1st (50%) = 5000
    assert s.payout(
        tournament_id=tid, dancer_id="bob",
    ) == 5000


def test_payout_second_third_split():
    s = PlayerDanceCompetitionSystem()
    tid = _open(s)
    _register_three(s, tid)
    s.lock_field(tournament_id=tid)
    s.submit_performance(
        tournament_id=tid, dancer_id="alice",
        tempo_score=50, precision_score=50,
        style_score=50,
    )
    s.submit_performance(
        tournament_id=tid, dancer_id="bob",
        tempo_score=90, precision_score=90,
        style_score=90,
    )
    s.submit_performance(
        tournament_id=tid, dancer_id="cara",
        tempo_score=70, precision_score=70,
        style_score=70,
    )
    s.finalize(tournament_id=tid)
    # cara 2nd: 30% = 3000
    assert s.payout(
        tournament_id=tid, dancer_id="cara",
    ) == 3000
    # alice 3rd: 20% = 2000
    assert s.payout(
        tournament_id=tid, dancer_id="alice",
    ) == 2000


def test_payout_outside_top3_zero():
    s = PlayerDanceCompetitionSystem()
    tid = s.open_tournament(
        venue_id="v", field_min=4, field_max=10,
        prize_purse_gil=10000,
    )
    for d in ("a", "b", "c", "d"):
        s.register_dancer(
            tournament_id=tid, dancer_id=d,
        )
    s.lock_field(tournament_id=tid)
    for d, sc in [
        ("a", 90), ("b", 80), ("c", 70), ("d", 50),
    ]:
        s.submit_performance(
            tournament_id=tid, dancer_id=d,
            tempo_score=sc, precision_score=sc,
            style_score=sc,
        )
    s.finalize(tournament_id=tid)
    assert s.payout(
        tournament_id=tid, dancer_id="d",
    ) == 0


def test_payout_before_finalize_zero():
    s = PlayerDanceCompetitionSystem()
    tid = _open(s)
    _register_three(s, tid)
    s.lock_field(tournament_id=tid)
    assert s.payout(
        tournament_id=tid, dancer_id="alice",
    ) == 0


def test_performances_listed():
    s = PlayerDanceCompetitionSystem()
    tid = _open(s)
    _register_three(s, tid)
    assert len(s.performances(tournament_id=tid)) == 3


def test_unknown_tournament():
    s = PlayerDanceCompetitionSystem()
    assert s.tournament(tournament_id="ghost") is None


def test_enum_count():
    assert len(list(TournamentState)) == 3
