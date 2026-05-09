"""Player food critic review — public restaurant rating board.

A registered food critic publishes reviews of player-run
restaurants. Each review contains a star rating (1..5), the
specific dish critiqued, and prose commentary. A restaurant's
public score is the cross-critic average of all current
reviews about it; retracting a review removes it from the
average. Critics can publish at most one current review per
restaurant — to update their opinion, they must update_review
or retract first.

Lifecycle (review)
    PUBLISHED     active, contributing to averages
    RETRACTED     pulled by critic, no longer counted

Public surface
--------------
    ReviewState enum
    Critic dataclass (frozen)
    Review dataclass (frozen)
    PlayerFoodCriticReviewSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_MIN_STARS = 1
_MAX_STARS = 5


class ReviewState(str, enum.Enum):
    PUBLISHED = "published"
    RETRACTED = "retracted"


@dataclasses.dataclass(frozen=True)
class Critic:
    critic_id: str
    pen_name: str


@dataclasses.dataclass(frozen=True)
class Review:
    review_id: str
    critic_id: str
    restaurant_id: str
    dish_critiqued: str
    stars: int
    commentary: str
    state: ReviewState


@dataclasses.dataclass
class PlayerFoodCriticReviewSystem:
    _critics: dict[str, Critic] = dataclasses.field(
        default_factory=dict,
    )
    _reviews: dict[str, Review] = dataclasses.field(
        default_factory=dict,
    )
    # (critic_id, restaurant_id) -> review_id of
    # the active (PUBLISHED) review
    _active: dict[tuple[str, str], str] = (
        dataclasses.field(default_factory=dict)
    )
    _next_review: int = 1

    def register_critic(
        self, *, critic_id: str, pen_name: str,
    ) -> bool:
        if not critic_id or not pen_name:
            return False
        if critic_id in self._critics:
            return False
        self._critics[critic_id] = Critic(
            critic_id=critic_id, pen_name=pen_name,
        )
        return True

    def publish_review(
        self, *, critic_id: str, restaurant_id: str,
        dish_critiqued: str, stars: int,
        commentary: str,
    ) -> t.Optional[str]:
        if critic_id not in self._critics:
            return None
        if not restaurant_id or not dish_critiqued:
            return None
        if not commentary:
            return None
        if not _MIN_STARS <= stars <= _MAX_STARS:
            return None
        key = (critic_id, restaurant_id)
        if key in self._active:
            return None
        rid = f"review_{self._next_review}"
        self._next_review += 1
        self._reviews[rid] = Review(
            review_id=rid, critic_id=critic_id,
            restaurant_id=restaurant_id,
            dish_critiqued=dish_critiqued,
            stars=stars, commentary=commentary,
            state=ReviewState.PUBLISHED,
        )
        self._active[key] = rid
        return rid

    def update_review(
        self, *, review_id: str, critic_id: str,
        stars: int, commentary: str,
    ) -> bool:
        if review_id not in self._reviews:
            return False
        rev = self._reviews[review_id]
        if rev.critic_id != critic_id:
            return False
        if rev.state != ReviewState.PUBLISHED:
            return False
        if not _MIN_STARS <= stars <= _MAX_STARS:
            return False
        if not commentary:
            return False
        self._reviews[review_id] = dataclasses.replace(
            rev, stars=stars, commentary=commentary,
        )
        return True

    def retract_review(
        self, *, review_id: str, critic_id: str,
    ) -> bool:
        if review_id not in self._reviews:
            return False
        rev = self._reviews[review_id]
        if rev.critic_id != critic_id:
            return False
        if rev.state != ReviewState.PUBLISHED:
            return False
        self._reviews[review_id] = dataclasses.replace(
            rev, state=ReviewState.RETRACTED,
        )
        key = (rev.critic_id, rev.restaurant_id)
        if self._active.get(key) == review_id:
            del self._active[key]
        return True

    def restaurant_score(
        self, *, restaurant_id: str,
    ) -> t.Optional[float]:
        """Returns the average stars across PUBLISHED
        reviews for the restaurant, or None if no
        reviews."""
        active = [
            r for r in self._reviews.values()
            if (
                r.restaurant_id == restaurant_id
                and r.state == ReviewState.PUBLISHED
            )
        ]
        if not active:
            return None
        return sum(r.stars for r in active) / len(active)

    def critics_for_restaurant(
        self, *, restaurant_id: str,
    ) -> list[str]:
        return sorted({
            r.critic_id for r in self._reviews.values()
            if (
                r.restaurant_id == restaurant_id
                and r.state == ReviewState.PUBLISHED
            )
        })

    def reviews_by_critic(
        self, *, critic_id: str,
    ) -> list[Review]:
        return [
            r for r in self._reviews.values()
            if r.critic_id == critic_id
        ]

    def review(
        self, *, review_id: str,
    ) -> t.Optional[Review]:
        return self._reviews.get(review_id)

    def critic(
        self, *, critic_id: str,
    ) -> t.Optional[Critic]:
        return self._critics.get(critic_id)


__all__ = [
    "ReviewState", "Critic", "Review",
    "PlayerFoodCriticReviewSystem",
]
