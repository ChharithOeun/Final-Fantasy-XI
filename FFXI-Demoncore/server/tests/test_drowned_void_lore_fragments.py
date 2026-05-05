"""Tests for drowned void lore fragments."""
from __future__ import annotations

from server.drowned_void_lore_fragments import (
    Chapter,
    DrownedVoidLore,
    WHISPER_DURATION_SECONDS,
)


def test_register_fragment_happy():
    d = DrownedVoidLore()
    ok = d.register_fragment(
        fragment_id="frag1",
        chapter=Chapter.DAYS_BEFORE,
        order_in_chapter=1,
    )
    assert ok is True


def test_register_blank_id_rejected():
    d = DrownedVoidLore()
    ok = d.register_fragment(
        fragment_id="",
        chapter=Chapter.DAYS_BEFORE,
        order_in_chapter=1,
    )
    assert ok is False


def test_register_zero_order_rejected():
    d = DrownedVoidLore()
    ok = d.register_fragment(
        fragment_id="x",
        chapter=Chapter.DAYS_BEFORE,
        order_in_chapter=0,
    )
    assert ok is False


def test_register_duplicate_rejected():
    d = DrownedVoidLore()
    d.register_fragment(
        fragment_id="x", chapter=Chapter.DAYS_BEFORE,
        order_in_chapter=1,
    )
    ok = d.register_fragment(
        fragment_id="x", chapter=Chapter.DAYS_BEFORE,
        order_in_chapter=2,
    )
    assert ok is False


def test_approach_unknown_fragment():
    d = DrownedVoidLore()
    ok = d.approach(
        player_id="p", fragment_id="ghost", now_seconds=0,
    )
    assert ok is False


def test_collect_happy():
    d = DrownedVoidLore()
    d.register_fragment(
        fragment_id="x", chapter=Chapter.DAYS_BEFORE,
        order_in_chapter=1,
    )
    d.approach(
        player_id="p", fragment_id="x", now_seconds=0,
    )
    r = d.leave(
        player_id="p",
        now_seconds=WHISPER_DURATION_SECONDS,
    )
    assert r.accepted is True
    assert r.chapter == Chapter.DAYS_BEFORE
    # only 1 fragment in chapter -> chapter unlocked
    assert r.chapter_unlocked is True


def test_left_too_soon():
    d = DrownedVoidLore()
    d.register_fragment(
        fragment_id="x", chapter=Chapter.DAYS_BEFORE,
        order_in_chapter=1,
    )
    d.approach(
        player_id="p", fragment_id="x", now_seconds=0,
    )
    r = d.leave(player_id="p", now_seconds=5)
    assert r.accepted is True
    assert r.reason == "left too soon"
    assert d.collected_count(player_id="p") == 0


def test_no_approach_in_progress():
    d = DrownedVoidLore()
    r = d.leave(player_id="p", now_seconds=10)
    assert r.accepted is False


def test_chapter_unlocked_only_when_all_fragments_collected():
    d = DrownedVoidLore()
    d.register_fragment(
        fragment_id="a",
        chapter=Chapter.THE_SONG_BEGINS,
        order_in_chapter=1,
    )
    d.register_fragment(
        fragment_id="b",
        chapter=Chapter.THE_SONG_BEGINS,
        order_in_chapter=2,
    )
    # collect first fragment
    d.approach(
        player_id="p", fragment_id="a", now_seconds=0,
    )
    r1 = d.leave(
        player_id="p",
        now_seconds=WHISPER_DURATION_SECONDS,
    )
    assert r1.chapter_unlocked is False
    # collect second fragment
    d.approach(
        player_id="p", fragment_id="b", now_seconds=100,
    )
    r2 = d.leave(
        player_id="p",
        now_seconds=100 + WHISPER_DURATION_SECONDS,
    )
    assert r2.chapter_unlocked is True


def test_chapters_unlocked_starts_empty():
    d = DrownedVoidLore()
    d.register_fragment(
        fragment_id="a",
        chapter=Chapter.DAYS_BEFORE,
        order_in_chapter=1,
    )
    assert d.chapters_unlocked(player_id="p") == ()


def test_chapters_unlocked_lists_completed():
    d = DrownedVoidLore()
    d.register_fragment(
        fragment_id="a",
        chapter=Chapter.DAYS_BEFORE,
        order_in_chapter=1,
    )
    d.register_fragment(
        fragment_id="b",
        chapter=Chapter.AFTER_SILENCE,
        order_in_chapter=1,
    )
    d.approach(
        player_id="p", fragment_id="a", now_seconds=0,
    )
    d.leave(
        player_id="p",
        now_seconds=WHISPER_DURATION_SECONDS,
    )
    chapters = d.chapters_unlocked(player_id="p")
    assert Chapter.DAYS_BEFORE in chapters
    assert Chapter.AFTER_SILENCE not in chapters


def test_recollect_does_not_double_unlock():
    d = DrownedVoidLore()
    d.register_fragment(
        fragment_id="x",
        chapter=Chapter.DAYS_BEFORE,
        order_in_chapter=1,
    )
    d.approach(
        player_id="p", fragment_id="x", now_seconds=0,
    )
    r1 = d.leave(
        player_id="p",
        now_seconds=WHISPER_DURATION_SECONDS,
    )
    # second collect of same fragment doesn't trigger another
    # chapter_unlocked spike
    d.approach(
        player_id="p", fragment_id="x", now_seconds=100,
    )
    r2 = d.leave(
        player_id="p",
        now_seconds=100 + WHISPER_DURATION_SECONDS,
    )
    assert r1.chapter_unlocked is True
    assert r2.chapter_unlocked is False


def test_collected_count_dedupes():
    d = DrownedVoidLore()
    d.register_fragment(
        fragment_id="x",
        chapter=Chapter.DAYS_BEFORE,
        order_in_chapter=1,
    )
    for t_offset in (0, 50, 100):
        d.approach(
            player_id="p", fragment_id="x", now_seconds=t_offset,
        )
        d.leave(
            player_id="p",
            now_seconds=t_offset + WHISPER_DURATION_SECONDS,
        )
    assert d.collected_count(player_id="p") == 1
