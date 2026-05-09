"""Player map publication — published cartographic editions.

A cartographer (registered in player_cartographer_guild)
publishes a map of a zone — a snapshot of landmarks they
believe to be there. Other cartographers can review the
map, scoring it 0..100 for accuracy. The map's overall
quality_score is the average of all reviews. Maps below
30 are de-listed; maps with 5+ reviews and >= 70 average
get a CERTIFIED stamp from the guild.

Lifecycle (map)
    DRAFT         being written
    PUBLISHED     released for review
    CERTIFIED     5+ reviews and >= 70 average
    DELISTED      average dropped below 30

Public surface
--------------
    MapState enum
    PublishedMap dataclass (frozen)
    PlayerMapPublicationSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_MIN_REVIEW = 0
_MAX_REVIEW = 100
_DELIST_THRESHOLD = 30
_CERTIFY_THRESHOLD = 70
_CERTIFY_MIN_REVIEWS = 5


class MapState(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CERTIFIED = "certified"
    DELISTED = "delisted"


@dataclasses.dataclass(frozen=True)
class PublishedMap:
    map_id: str
    cartographer_id: str
    zone: str
    title: str
    landmark_count: int
    state: MapState
    review_count: int
    quality_score: float


@dataclasses.dataclass
class _MState:
    spec: PublishedMap
    reviews: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class PlayerMapPublicationSystem:
    _maps: dict[str, _MState] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def begin_draft(
        self, *, cartographer_id: str, zone: str,
        title: str, landmark_count: int,
    ) -> t.Optional[str]:
        if not cartographer_id or not zone:
            return None
        if not title:
            return None
        if landmark_count <= 0:
            return None
        mid = f"map_{self._next}"
        self._next += 1
        self._maps[mid] = _MState(
            spec=PublishedMap(
                map_id=mid,
                cartographer_id=cartographer_id,
                zone=zone, title=title,
                landmark_count=landmark_count,
                state=MapState.DRAFT,
                review_count=0, quality_score=0.0,
            ),
        )
        return mid

    def publish(
        self, *, map_id: str, cartographer_id: str,
    ) -> bool:
        if map_id not in self._maps:
            return False
        st = self._maps[map_id]
        if st.spec.cartographer_id != cartographer_id:
            return False
        if st.spec.state != MapState.DRAFT:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=MapState.PUBLISHED,
        )
        return True

    def submit_review(
        self, *, map_id: str, reviewer_id: str,
        score: int,
    ) -> bool:
        if map_id not in self._maps:
            return False
        st = self._maps[map_id]
        if st.spec.state == MapState.DRAFT:
            return False
        if st.spec.state == MapState.DELISTED:
            return False
        if not reviewer_id:
            return False
        if reviewer_id == st.spec.cartographer_id:
            return False
        if not _MIN_REVIEW <= score <= _MAX_REVIEW:
            return False
        if reviewer_id in st.reviews:
            return False
        st.reviews[reviewer_id] = score
        self._update_state(st)
        return True

    @staticmethod
    def _update_state(st: _MState) -> None:
        n = len(st.reviews)
        avg = (
            sum(st.reviews.values()) / n
            if n else 0.0
        )
        new_state = st.spec.state
        if n > 0 and avg < _DELIST_THRESHOLD:
            new_state = MapState.DELISTED
        elif (
            n >= _CERTIFY_MIN_REVIEWS
            and avg >= _CERTIFY_THRESHOLD
        ):
            new_state = MapState.CERTIFIED
        else:
            new_state = MapState.PUBLISHED
        st.spec = dataclasses.replace(
            st.spec, state=new_state,
            review_count=n, quality_score=avg,
        )

    def map(
        self, *, map_id: str,
    ) -> t.Optional[PublishedMap]:
        st = self._maps.get(map_id)
        return st.spec if st else None

    def maps_for_zone(
        self, *, zone: str,
    ) -> list[PublishedMap]:
        return [
            st.spec for st in self._maps.values()
            if st.spec.zone == zone
        ]

    def certified_maps(
        self,
    ) -> list[PublishedMap]:
        return [
            st.spec for st in self._maps.values()
            if st.spec.state == MapState.CERTIFIED
        ]


__all__ = [
    "MapState", "PublishedMap",
    "PlayerMapPublicationSystem",
]
