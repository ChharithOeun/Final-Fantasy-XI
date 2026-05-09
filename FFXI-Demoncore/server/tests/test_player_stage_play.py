"""Tests for player_stage_play."""
from __future__ import annotations

from server.player_stage_play import (
    PlayerStagePlaySystem, PlayState,
)


def _author(s: PlayerStagePlaySystem) -> str:
    return s.author_play(
        title="The Tarutaru Heist", author_id="naji",
        num_acts=3, script_quality=70,
    )


def _cast_two(
    s: PlayerStagePlaySystem, pid: str,
) -> tuple[str, str]:
    a = s.cast_role(
        play_id=pid, role_name="Hero",
        actor_id="bob", actor_skill=80,
    )
    b = s.cast_role(
        play_id=pid, role_name="Villain",
        actor_id="cara", actor_skill=70,
    )
    return a, b


def test_author_happy():
    s = PlayerStagePlaySystem()
    pid = _author(s)
    assert pid is not None


def test_author_empty_title():
    s = PlayerStagePlaySystem()
    assert s.author_play(
        title="", author_id="naji",
        num_acts=3, script_quality=70,
    ) is None


def test_author_invalid_acts():
    s = PlayerStagePlaySystem()
    assert s.author_play(
        title="X", author_id="naji",
        num_acts=10, script_quality=70,
    ) is None


def test_author_invalid_quality():
    s = PlayerStagePlaySystem()
    assert s.author_play(
        title="X", author_id="naji",
        num_acts=3, script_quality=200,
    ) is None


def test_cast_role_happy():
    s = PlayerStagePlaySystem()
    pid = _author(s)
    rid = s.cast_role(
        play_id=pid, role_name="Hero",
        actor_id="bob", actor_skill=80,
    )
    assert rid is not None


def test_cast_role_invalid_skill():
    s = PlayerStagePlaySystem()
    pid = _author(s)
    assert s.cast_role(
        play_id=pid, role_name="Hero",
        actor_id="bob", actor_skill=0,
    ) is None


def test_cast_dup_actor_blocked():
    s = PlayerStagePlaySystem()
    pid = _author(s)
    s.cast_role(
        play_id=pid, role_name="Hero",
        actor_id="bob", actor_skill=80,
    )
    second = s.cast_role(
        play_id=pid, role_name="Sidekick",
        actor_id="bob", actor_skill=80,
    )
    assert second is None


def test_lock_cast_happy():
    s = PlayerStagePlaySystem()
    pid = _author(s)
    _cast_two(s, pid)
    assert s.lock_cast(play_id=pid) is True


def test_lock_cast_no_actors_blocked():
    s = PlayerStagePlaySystem()
    pid = _author(s)
    assert s.lock_cast(play_id=pid) is False


def test_lock_cast_double_blocked():
    s = PlayerStagePlaySystem()
    pid = _author(s)
    _cast_two(s, pid)
    s.lock_cast(play_id=pid)
    assert s.lock_cast(play_id=pid) is False


def test_cast_after_lock_blocked():
    s = PlayerStagePlaySystem()
    pid = _author(s)
    _cast_two(s, pid)
    s.lock_cast(play_id=pid)
    third = s.cast_role(
        play_id=pid, role_name="Extra",
        actor_id="dave", actor_skill=40,
    )
    assert third is None


def test_begin_rehearsals_happy():
    s = PlayerStagePlaySystem()
    pid = _author(s)
    _cast_two(s, pid)
    s.lock_cast(play_id=pid)
    assert s.begin_rehearsals(play_id=pid) is True


def test_begin_rehearsals_before_cast_blocked():
    s = PlayerStagePlaySystem()
    pid = _author(s)
    assert s.begin_rehearsals(play_id=pid) is False


def test_rehearse_increments_prep():
    s = PlayerStagePlaySystem()
    pid = _author(s)
    _cast_two(s, pid)
    s.lock_cast(play_id=pid)
    s.begin_rehearsals(play_id=pid)
    p1 = s.rehearse(play_id=pid)
    p2 = s.rehearse(play_id=pid)
    assert p1 == 5
    assert p2 == 10


def test_rehearse_caps():
    s = PlayerStagePlaySystem()
    pid = _author(s)
    _cast_two(s, pid)
    s.lock_cast(play_id=pid)
    s.begin_rehearsals(play_id=pid)
    for _ in range(15):
        s.rehearse(play_id=pid)
    p = s.play(play_id=pid)
    assert p.rehearsal_count == 10
    assert p.preparation_score == 50


def test_rehearse_before_begin_blocked():
    s = PlayerStagePlaySystem()
    pid = _author(s)
    _cast_two(s, pid)
    s.lock_cast(play_id=pid)
    assert s.rehearse(play_id=pid) is None


def test_perform_happy():
    s = PlayerStagePlaySystem()
    pid = _author(s)
    _cast_two(s, pid)
    s.lock_cast(play_id=pid)
    s.begin_rehearsals(play_id=pid)
    s.rehearse(play_id=pid)
    s.rehearse(play_id=pid)
    review = s.perform(
        play_id=pid, audience_size=50,
        performed_day=20, seed=42,
    )
    assert review is not None
    assert review > 0


def test_perform_state_transitions():
    s = PlayerStagePlaySystem()
    pid = _author(s)
    _cast_two(s, pid)
    s.lock_cast(play_id=pid)
    s.begin_rehearsals(play_id=pid)
    s.perform(
        play_id=pid, audience_size=10,
        performed_day=20, seed=42,
    )
    p = s.play(play_id=pid)
    assert p.state == PlayState.PERFORMING
    assert p.performance is not None


def test_perform_before_rehearsals_blocked():
    s = PlayerStagePlaySystem()
    pid = _author(s)
    _cast_two(s, pid)
    s.lock_cast(play_id=pid)
    assert s.perform(
        play_id=pid, audience_size=10,
        performed_day=20, seed=42,
    ) is None


def test_perform_invalid_audience():
    s = PlayerStagePlaySystem()
    pid = _author(s)
    _cast_two(s, pid)
    s.lock_cast(play_id=pid)
    s.begin_rehearsals(play_id=pid)
    assert s.perform(
        play_id=pid, audience_size=-1,
        performed_day=20, seed=42,
    ) is None


def test_rehearsals_boost_review():
    """A well-rehearsed play scores higher."""
    def run(rehearsals: int) -> int:
        s = PlayerStagePlaySystem()
        pid = _author(s)
        _cast_two(s, pid)
        s.lock_cast(play_id=pid)
        s.begin_rehearsals(play_id=pid)
        for _ in range(rehearsals):
            s.rehearse(play_id=pid)
        return s.perform(
            play_id=pid, audience_size=50,
            performed_day=20, seed=42,
        )
    poor = run(0)
    rehearsed = run(8)
    assert rehearsed > poor


def test_close_run_happy():
    s = PlayerStagePlaySystem()
    pid = _author(s)
    _cast_two(s, pid)
    s.lock_cast(play_id=pid)
    s.begin_rehearsals(play_id=pid)
    s.perform(
        play_id=pid, audience_size=10,
        performed_day=20, seed=42,
    )
    assert s.close_run(play_id=pid) is True
    assert s.play(play_id=pid).state == PlayState.CLOSED


def test_close_run_before_perform_blocked():
    s = PlayerStagePlaySystem()
    pid = _author(s)
    _cast_two(s, pid)
    s.lock_cast(play_id=pid)
    assert s.close_run(play_id=pid) is False


def test_roles_listed():
    s = PlayerStagePlaySystem()
    pid = _author(s)
    _cast_two(s, pid)
    assert len(s.roles(play_id=pid)) == 2


def test_play_unknown():
    s = PlayerStagePlaySystem()
    assert s.play(play_id="ghost") is None


def test_enum_count():
    assert len(list(PlayState)) == 5
