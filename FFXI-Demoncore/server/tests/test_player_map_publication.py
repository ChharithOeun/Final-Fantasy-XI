"""Tests for player_map_publication."""
from __future__ import annotations

from server.player_map_publication import (
    PlayerMapPublicationSystem, MapState,
)


def _draft(s: PlayerMapPublicationSystem) -> str:
    return s.begin_draft(
        cartographer_id="alice",
        zone="ronfaure_west",
        title="Ronfaure West Survey",
        landmark_count=12,
    )


def _published(s: PlayerMapPublicationSystem) -> str:
    mid = _draft(s)
    s.publish(map_id=mid, cartographer_id="alice")
    return mid


def test_draft_happy():
    s = PlayerMapPublicationSystem()
    assert _draft(s) is not None


def test_draft_zero_landmarks_blocked():
    s = PlayerMapPublicationSystem()
    assert s.begin_draft(
        cartographer_id="alice", zone="z",
        title="t", landmark_count=0,
    ) is None


def test_draft_empty_title_blocked():
    s = PlayerMapPublicationSystem()
    assert s.begin_draft(
        cartographer_id="alice", zone="z",
        title="", landmark_count=5,
    ) is None


def test_publish_happy():
    s = PlayerMapPublicationSystem()
    mid = _draft(s)
    assert s.publish(
        map_id=mid, cartographer_id="alice",
    ) is True


def test_publish_wrong_cartographer_blocked():
    s = PlayerMapPublicationSystem()
    mid = _draft(s)
    assert s.publish(
        map_id=mid, cartographer_id="bob",
    ) is False


def test_publish_twice_blocked():
    s = PlayerMapPublicationSystem()
    mid = _published(s)
    assert s.publish(
        map_id=mid, cartographer_id="alice",
    ) is False


def test_review_happy():
    s = PlayerMapPublicationSystem()
    mid = _published(s)
    assert s.submit_review(
        map_id=mid, reviewer_id="bob", score=80,
    ) is True


def test_review_self_blocked():
    s = PlayerMapPublicationSystem()
    mid = _published(s)
    assert s.submit_review(
        map_id=mid, reviewer_id="alice", score=80,
    ) is False


def test_review_invalid_score_blocked():
    s = PlayerMapPublicationSystem()
    mid = _published(s)
    assert s.submit_review(
        map_id=mid, reviewer_id="bob", score=150,
    ) is False


def test_review_dup_blocked():
    s = PlayerMapPublicationSystem()
    mid = _published(s)
    s.submit_review(
        map_id=mid, reviewer_id="bob", score=80,
    )
    assert s.submit_review(
        map_id=mid, reviewer_id="bob", score=70,
    ) is False


def test_review_draft_blocked():
    s = PlayerMapPublicationSystem()
    mid = _draft(s)
    assert s.submit_review(
        map_id=mid, reviewer_id="bob", score=80,
    ) is False


def test_quality_score_average():
    s = PlayerMapPublicationSystem()
    mid = _published(s)
    s.submit_review(
        map_id=mid, reviewer_id="b", score=80,
    )
    s.submit_review(
        map_id=mid, reviewer_id="c", score=60,
    )
    assert s.map(
        map_id=mid,
    ).quality_score == 70.0


def test_certify_at_5_reviews_70_avg():
    s = PlayerMapPublicationSystem()
    mid = _published(s)
    for i, score in enumerate([75, 80, 70, 75, 80]):
        s.submit_review(
            map_id=mid, reviewer_id=f"r_{i}",
            score=score,
        )
    assert s.map(
        map_id=mid,
    ).state == MapState.CERTIFIED


def test_no_certify_below_5_reviews():
    s = PlayerMapPublicationSystem()
    mid = _published(s)
    for i in range(4):
        s.submit_review(
            map_id=mid, reviewer_id=f"r_{i}",
            score=90,
        )
    assert s.map(
        map_id=mid,
    ).state == MapState.PUBLISHED


def test_delist_below_30_avg():
    s = PlayerMapPublicationSystem()
    mid = _published(s)
    s.submit_review(
        map_id=mid, reviewer_id="b", score=10,
    )
    assert s.map(
        map_id=mid,
    ).state == MapState.DELISTED


def test_review_after_delist_blocked():
    s = PlayerMapPublicationSystem()
    mid = _published(s)
    s.submit_review(
        map_id=mid, reviewer_id="b", score=5,
    )
    assert s.submit_review(
        map_id=mid, reviewer_id="c", score=80,
    ) is False


def test_review_count_tracked():
    s = PlayerMapPublicationSystem()
    mid = _published(s)
    s.submit_review(
        map_id=mid, reviewer_id="b", score=80,
    )
    s.submit_review(
        map_id=mid, reviewer_id="c", score=70,
    )
    assert s.map(
        map_id=mid,
    ).review_count == 2


def test_maps_for_zone_listing():
    s = PlayerMapPublicationSystem()
    s.begin_draft(
        cartographer_id="a", zone="z1",
        title="t1", landmark_count=5,
    )
    s.begin_draft(
        cartographer_id="a", zone="z1",
        title="t2", landmark_count=5,
    )
    s.begin_draft(
        cartographer_id="a", zone="z2",
        title="t3", landmark_count=5,
    )
    assert len(s.maps_for_zone(zone="z1")) == 2


def test_certified_maps_listing():
    s = PlayerMapPublicationSystem()
    mid = _published(s)
    for i in range(5):
        s.submit_review(
            map_id=mid, reviewer_id=f"r_{i}",
            score=80,
        )
    assert len(s.certified_maps()) == 1


def test_unknown_map():
    s = PlayerMapPublicationSystem()
    assert s.map(map_id="ghost") is None


def test_state_count():
    assert len(list(MapState)) == 4
