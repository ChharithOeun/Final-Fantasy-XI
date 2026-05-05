"""Tests for shark humanoid arena."""
from __future__ import annotations

from server.shark_humanoid_arena import Champion, SharkArena


def test_starting_unlock_is_roukan():
    a = SharkArena()
    assert a.current_unlock(player_id="p") == Champion.ROUKAN


def test_start_bout_at_correct_unlock():
    a = SharkArena()
    ok = a.start_bout(
        player_id="p", champion=Champion.ROUKAN, now_seconds=0,
    )
    assert ok is True


def test_start_bout_skip_rank_rejected():
    a = SharkArena()
    ok = a.start_bout(
        player_id="p", champion=Champion.IGUMI, now_seconds=0,
    )
    assert ok is False


def test_clean_win_advances_unlock():
    a = SharkArena()
    a.start_bout(
        player_id="p", champion=Champion.ROUKAN, now_seconds=0,
    )
    r = a.resolve_bout(
        player_id="p", won=True,
        time_seconds=120, no_deaths=True,
    )
    assert r.clean_win is True
    assert r.next_unlock == Champion.KASEN


def test_clean_win_grants_teeth_and_rep():
    a = SharkArena()
    a.start_bout(
        player_id="p", champion=Champion.ROUKAN, now_seconds=0,
    )
    r = a.resolve_bout(
        player_id="p", won=True,
        time_seconds=60, no_deaths=True,
    )
    # ROUKAN is rank 1 (lowest), but our reward formula gives
    # rank=5-index=5-0=5 -> teeth=10, rep=50 (but rank 1 from
    # bottom): index 0 -> 5 - 0 = 5
    assert r.shark_teeth_awarded > 0
    assert r.reputation_delta > 0


def test_loss_does_not_advance():
    a = SharkArena()
    a.start_bout(
        player_id="p", champion=Champion.ROUKAN, now_seconds=0,
    )
    r = a.resolve_bout(
        player_id="p", won=False,
        time_seconds=60, no_deaths=False,
    )
    assert r.clean_win is False
    assert a.current_unlock(player_id="p") == Champion.ROUKAN


def test_dirty_win_does_not_advance():
    a = SharkArena()
    a.start_bout(
        player_id="p", champion=Champion.ROUKAN, now_seconds=0,
    )
    r = a.resolve_bout(
        player_id="p", won=True,
        time_seconds=60, no_deaths=False,
    )
    assert r.clean_win is False
    assert a.current_unlock(player_id="p") == Champion.ROUKAN


def test_timeout_kills_clean_win():
    a = SharkArena()
    a.start_bout(
        player_id="p", champion=Champion.ROUKAN, now_seconds=0,
    )
    # 5 min limit; 6 min elapsed -> timeout
    r = a.resolve_bout(
        player_id="p", won=True,
        time_seconds=6 * 60, no_deaths=True,
    )
    assert r.clean_win is False


def test_full_climb_to_zakara():
    a = SharkArena()
    for champ in (
        Champion.ROUKAN, Champion.KASEN, Champion.IGUMI,
        Champion.KAEDE, Champion.ZAKARA,
    ):
        a.start_bout(player_id="p", champion=champ, now_seconds=0)
        r = a.resolve_bout(
            player_id="p", won=True,
            time_seconds=120, no_deaths=True,
        )
        assert r.clean_win is True
    # final win awards title and shark pact
    assert a.has_shark_pact(player_id="p") is True


def test_zakara_only_after_kaede():
    a = SharkArena()
    # cleared up to KAEDE only
    a._cleared["p"] = Champion.KAEDE
    assert a.current_unlock(player_id="p") == Champion.ZAKARA


def test_resolve_without_active_bout():
    a = SharkArena()
    r = a.resolve_bout(
        player_id="p", won=True,
        time_seconds=10, no_deaths=True,
    )
    assert r.accepted is False


def test_loss_does_not_demote_past_cleared():
    a = SharkArena()
    # clear ROUKAN
    a.start_bout(
        player_id="p", champion=Champion.ROUKAN, now_seconds=0,
    )
    a.resolve_bout(
        player_id="p", won=True,
        time_seconds=60, no_deaths=True,
    )
    # then lose against KASEN
    a.start_bout(
        player_id="p", champion=Champion.KASEN, now_seconds=200,
    )
    a.resolve_bout(
        player_id="p", won=False,
        time_seconds=300, no_deaths=False,
    )
    # still unlocked at KASEN (not pushed back to ROUKAN)
    assert a.current_unlock(player_id="p") == Champion.KASEN


def test_blank_player_rejected():
    a = SharkArena()
    ok = a.start_bout(
        player_id="", champion=Champion.ROUKAN, now_seconds=0,
    )
    assert ok is False


def test_no_shark_pact_before_zakara():
    a = SharkArena()
    a._cleared["p"] = Champion.KAEDE
    assert a.has_shark_pact(player_id="p") is False
