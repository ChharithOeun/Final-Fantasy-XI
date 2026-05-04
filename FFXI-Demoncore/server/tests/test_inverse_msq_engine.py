"""Tests for the inverse MSQ engine."""
from __future__ import annotations

from server.beastman_playable_races import BeastmanRace
from server.inverse_msq_engine import (
    InverseMsqEngine,
    MirrorReactionKind,
    MirrorStatus,
)


def test_register_mirror():
    e = InverseMsqEngine()
    m = e.register_mirror(
        canon_chapter_id="bastok_3_2",
        race=BeastmanRace.QUADAV,
        reaction_kind=MirrorReactionKind.GRIEVE,
        label="The Fallen Earthbreaker",
    )
    assert m is not None
    assert m.status == MirrorStatus.DORMANT


def test_register_empty_fields_rejected():
    e = InverseMsqEngine()
    assert e.register_mirror(
        canon_chapter_id="",
        race=BeastmanRace.YAGUDO,
        reaction_kind=MirrorReactionKind.GRIEVE,
        label="x",
    ) is None
    assert e.register_mirror(
        canon_chapter_id="x",
        race=BeastmanRace.YAGUDO,
        reaction_kind=MirrorReactionKind.GRIEVE,
        label="",
    ) is None


def test_double_mirror_id_rejected():
    e = InverseMsqEngine()
    e.register_mirror(
        canon_chapter_id="x",
        race=BeastmanRace.YAGUDO,
        reaction_kind=MirrorReactionKind.GRIEVE,
        label="Y", mirror_id="m1",
    )
    res = e.register_mirror(
        canon_chapter_id="x",
        race=BeastmanRace.YAGUDO,
        reaction_kind=MirrorReactionKind.AVENGE,
        label="Z", mirror_id="m1",
    )
    assert res is None


def test_canon_completion_opens_mirrors():
    e = InverseMsqEngine()
    e.register_mirror(
        canon_chapter_id="bastok_3_2",
        race=BeastmanRace.QUADAV,
        reaction_kind=MirrorReactionKind.GRIEVE,
        label="x",
    )
    flipped = e.ingest_canon_completion(
        canon_chapter_id="bastok_3_2",
    )
    assert len(flipped) == 1


def test_canon_completion_unknown_no_flip():
    e = InverseMsqEngine()
    flipped = e.ingest_canon_completion(
        canon_chapter_id="ghost",
    )
    assert flipped == ()


def test_canon_completion_idempotent():
    e = InverseMsqEngine()
    e.register_mirror(
        canon_chapter_id="x",
        race=BeastmanRace.YAGUDO,
        reaction_kind=MirrorReactionKind.GRIEVE,
        label="L",
    )
    first = e.ingest_canon_completion(canon_chapter_id="x")
    second = e.ingest_canon_completion(canon_chapter_id="x")
    assert len(first) == 1
    # Second call doesn't re-flip (already OPEN)
    assert second == ()


def test_open_chapters_for_race():
    e = InverseMsqEngine()
    e.register_mirror(
        canon_chapter_id="x", race=BeastmanRace.QUADAV,
        reaction_kind=MirrorReactionKind.GRIEVE,
        label="Q chapter",
    )
    e.register_mirror(
        canon_chapter_id="x", race=BeastmanRace.ORC,
        reaction_kind=MirrorReactionKind.AVENGE,
        label="O chapter",
    )
    e.ingest_canon_completion(canon_chapter_id="x")
    quadav_open = e.open_chapters_for(
        race=BeastmanRace.QUADAV,
    )
    assert len(quadav_open) == 1


def test_start_chapter():
    e = InverseMsqEngine()
    m = e.register_mirror(
        canon_chapter_id="x", race=BeastmanRace.LAMIA,
        reaction_kind=MirrorReactionKind.PROPHESY,
        label="L chapter",
    )
    e.ingest_canon_completion(canon_chapter_id="x")
    prog = e.start_chapter(
        player_id="alice", mirror_id=m.mirror_id,
        race=BeastmanRace.LAMIA,
    )
    assert prog is not None
    assert prog.status == MirrorStatus.IN_PROGRESS


def test_start_dormant_chapter_rejected():
    e = InverseMsqEngine()
    m = e.register_mirror(
        canon_chapter_id="x", race=BeastmanRace.LAMIA,
        reaction_kind=MirrorReactionKind.PROPHESY,
        label="L",
    )
    res = e.start_chapter(
        player_id="alice", mirror_id=m.mirror_id,
        race=BeastmanRace.LAMIA,
    )
    assert res is None


def test_start_wrong_race_rejected():
    e = InverseMsqEngine()
    m = e.register_mirror(
        canon_chapter_id="x", race=BeastmanRace.LAMIA,
        reaction_kind=MirrorReactionKind.PROPHESY,
        label="L",
    )
    e.ingest_canon_completion(canon_chapter_id="x")
    res = e.start_chapter(
        player_id="alice", mirror_id=m.mirror_id,
        race=BeastmanRace.ORC,
    )
    assert res is None


def test_start_unknown_mirror():
    e = InverseMsqEngine()
    res = e.start_chapter(
        player_id="alice", mirror_id="ghost",
        race=BeastmanRace.YAGUDO,
    )
    assert res is None


def test_double_start_rejected():
    e = InverseMsqEngine()
    m = e.register_mirror(
        canon_chapter_id="x", race=BeastmanRace.YAGUDO,
        reaction_kind=MirrorReactionKind.SCATTER,
        label="Y",
    )
    e.ingest_canon_completion(canon_chapter_id="x")
    e.start_chapter(
        player_id="alice", mirror_id=m.mirror_id,
        race=BeastmanRace.YAGUDO,
    )
    res = e.start_chapter(
        player_id="alice", mirror_id=m.mirror_id,
        race=BeastmanRace.YAGUDO,
    )
    assert res is None


def test_complete_chapter():
    e = InverseMsqEngine()
    m = e.register_mirror(
        canon_chapter_id="x", race=BeastmanRace.ORC,
        reaction_kind=MirrorReactionKind.RECRUIT,
        label="O",
    )
    e.ingest_canon_completion(canon_chapter_id="x")
    e.start_chapter(
        player_id="alice", mirror_id=m.mirror_id,
        race=BeastmanRace.ORC,
    )
    assert e.complete_chapter(
        player_id="alice", mirror_id=m.mirror_id,
    )
    prog = e.progress_for(
        player_id="alice", mirror_id=m.mirror_id,
    )
    assert prog.status == MirrorStatus.COMPLETE


def test_complete_unknown_returns_false():
    e = InverseMsqEngine()
    assert not e.complete_chapter(
        player_id="alice", mirror_id="ghost",
    )


def test_complete_already_done_returns_false():
    e = InverseMsqEngine()
    m = e.register_mirror(
        canon_chapter_id="x", race=BeastmanRace.YAGUDO,
        reaction_kind=MirrorReactionKind.GRIEVE,
        label="Y",
    )
    e.ingest_canon_completion(canon_chapter_id="x")
    e.start_chapter(
        player_id="alice", mirror_id=m.mirror_id,
        race=BeastmanRace.YAGUDO,
    )
    e.complete_chapter(
        player_id="alice", mirror_id=m.mirror_id,
    )
    assert not e.complete_chapter(
        player_id="alice", mirror_id=m.mirror_id,
    )


def test_progress_for_unknown_returns_none():
    e = InverseMsqEngine()
    assert e.progress_for(
        player_id="alice", mirror_id="ghost",
    ) is None


def test_total_mirrors():
    e = InverseMsqEngine()
    e.register_mirror(
        canon_chapter_id="x", race=BeastmanRace.YAGUDO,
        reaction_kind=MirrorReactionKind.GRIEVE,
        label="A",
    )
    e.register_mirror(
        canon_chapter_id="x", race=BeastmanRace.ORC,
        reaction_kind=MirrorReactionKind.GRIEVE,
        label="B",
    )
    assert e.total_mirrors() == 2


def test_open_chapters_filters_by_race():
    e = InverseMsqEngine()
    e.register_mirror(
        canon_chapter_id="x", race=BeastmanRace.YAGUDO,
        reaction_kind=MirrorReactionKind.GRIEVE,
        label="Y",
    )
    e.register_mirror(
        canon_chapter_id="x", race=BeastmanRace.QUADAV,
        reaction_kind=MirrorReactionKind.GRIEVE,
        label="Q",
    )
    e.ingest_canon_completion(canon_chapter_id="x")
    yagudo = e.open_chapters_for(
        race=BeastmanRace.YAGUDO,
    )
    assert all(
        m.race == BeastmanRace.YAGUDO for m in yagudo
    )


def test_total_progress_records():
    e = InverseMsqEngine()
    m = e.register_mirror(
        canon_chapter_id="x", race=BeastmanRace.YAGUDO,
        reaction_kind=MirrorReactionKind.GRIEVE,
        label="Y",
    )
    e.ingest_canon_completion(canon_chapter_id="x")
    e.start_chapter(
        player_id="alice", mirror_id=m.mirror_id,
        race=BeastmanRace.YAGUDO,
    )
    e.start_chapter(
        player_id="bob", mirror_id=m.mirror_id,
        race=BeastmanRace.YAGUDO,
    )
    assert e.total_progress_records() == 2
