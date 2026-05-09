"""Tests for player_food_critic_review."""
from __future__ import annotations

from server.player_food_critic_review import (
    PlayerFoodCriticReviewSystem, ReviewState,
)


def _set(s: PlayerFoodCriticReviewSystem) -> None:
    s.register_critic(
        critic_id="naji", pen_name="Naji of Bastok",
    )


def _publish(
    s: PlayerFoodCriticReviewSystem,
    rest: str = "rest_1", stars: int = 4,
    critic: str = "naji",
) -> str:
    return s.publish_review(
        critic_id=critic, restaurant_id=rest,
        dish_critiqued="Mythril Stew", stars=stars,
        commentary="Decent but salty.",
    )


def test_register_critic_happy():
    s = PlayerFoodCriticReviewSystem()
    assert s.register_critic(
        critic_id="naji", pen_name="N",
    ) is True


def test_register_critic_dup_blocked():
    s = PlayerFoodCriticReviewSystem()
    s.register_critic(critic_id="naji", pen_name="N")
    assert s.register_critic(
        critic_id="naji", pen_name="X",
    ) is False


def test_register_critic_empty_blocked():
    s = PlayerFoodCriticReviewSystem()
    assert s.register_critic(
        critic_id="", pen_name="x",
    ) is False


def test_publish_review_happy():
    s = PlayerFoodCriticReviewSystem()
    _set(s)
    assert _publish(s) is not None


def test_publish_review_unknown_critic_blocked():
    s = PlayerFoodCriticReviewSystem()
    assert _publish(s, critic="ghost") is None


def test_publish_review_invalid_stars_blocked():
    s = PlayerFoodCriticReviewSystem()
    _set(s)
    assert _publish(s, stars=10) is None


def test_publish_review_empty_restaurant_blocked():
    s = PlayerFoodCriticReviewSystem()
    _set(s)
    assert s.publish_review(
        critic_id="naji", restaurant_id="",
        dish_critiqued="x", stars=3,
        commentary="y",
    ) is None


def test_publish_review_double_blocked():
    s = PlayerFoodCriticReviewSystem()
    _set(s)
    _publish(s, rest="rest_1")
    # Same critic, same restaurant, no retract — blocked
    assert _publish(s, rest="rest_1") is None


def test_publish_review_different_restaurants_ok():
    s = PlayerFoodCriticReviewSystem()
    _set(s)
    _publish(s, rest="rest_1")
    assert _publish(s, rest="rest_2") is not None


def test_update_review_happy():
    s = PlayerFoodCriticReviewSystem()
    _set(s)
    rid = _publish(s, stars=4)
    assert s.update_review(
        review_id=rid, critic_id="naji",
        stars=5, commentary="Reread: superb.",
    ) is True


def test_update_review_wrong_critic_blocked():
    s = PlayerFoodCriticReviewSystem()
    _set(s)
    s.register_critic(
        critic_id="bob", pen_name="Bob",
    )
    rid = _publish(s)
    assert s.update_review(
        review_id=rid, critic_id="bob",
        stars=2, commentary="x",
    ) is False


def test_retract_review_happy():
    s = PlayerFoodCriticReviewSystem()
    _set(s)
    rid = _publish(s)
    assert s.retract_review(
        review_id=rid, critic_id="naji",
    ) is True
    assert s.review(
        review_id=rid,
    ).state == ReviewState.RETRACTED


def test_retract_review_wrong_critic_blocked():
    s = PlayerFoodCriticReviewSystem()
    _set(s)
    rid = _publish(s)
    assert s.retract_review(
        review_id=rid, critic_id="bob",
    ) is False


def test_publish_after_retract_ok():
    s = PlayerFoodCriticReviewSystem()
    _set(s)
    rid = _publish(s, rest="rest_1")
    s.retract_review(
        review_id=rid, critic_id="naji",
    )
    # Critic can re-publish for same restaurant
    assert _publish(s, rest="rest_1") is not None


def test_restaurant_score_no_reviews_none():
    s = PlayerFoodCriticReviewSystem()
    _set(s)
    assert s.restaurant_score(
        restaurant_id="rest_1",
    ) is None


def test_restaurant_score_single_review():
    s = PlayerFoodCriticReviewSystem()
    _set(s)
    _publish(s, stars=4)
    assert s.restaurant_score(
        restaurant_id="rest_1",
    ) == 4.0


def test_restaurant_score_multi_critic_average():
    s = PlayerFoodCriticReviewSystem()
    _set(s)
    s.register_critic(
        critic_id="bob", pen_name="Bob",
    )
    s.register_critic(
        critic_id="cara", pen_name="Cara",
    )
    _publish(s, critic="naji", stars=5)
    _publish(s, critic="bob", stars=3)
    _publish(s, critic="cara", stars=4)
    assert s.restaurant_score(
        restaurant_id="rest_1",
    ) == 4.0


def test_retract_excludes_from_average():
    s = PlayerFoodCriticReviewSystem()
    _set(s)
    s.register_critic(
        critic_id="bob", pen_name="Bob",
    )
    rid = _publish(s, critic="naji", stars=5)
    _publish(s, critic="bob", stars=3)
    s.retract_review(
        review_id=rid, critic_id="naji",
    )
    assert s.restaurant_score(
        restaurant_id="rest_1",
    ) == 3.0


def test_critics_for_restaurant_listing():
    s = PlayerFoodCriticReviewSystem()
    _set(s)
    s.register_critic(
        critic_id="bob", pen_name="Bob",
    )
    _publish(s, critic="naji")
    _publish(s, critic="bob")
    assert s.critics_for_restaurant(
        restaurant_id="rest_1",
    ) == ["bob", "naji"]


def test_reviews_by_critic_listing():
    s = PlayerFoodCriticReviewSystem()
    _set(s)
    _publish(s, rest="rest_1")
    _publish(s, rest="rest_2")
    assert len(s.reviews_by_critic(
        critic_id="naji",
    )) == 2


def test_unknown_review():
    s = PlayerFoodCriticReviewSystem()
    assert s.review(review_id="ghost") is None


def test_unknown_critic():
    s = PlayerFoodCriticReviewSystem()
    assert s.critic(critic_id="ghost") is None


def test_enum_count():
    assert len(list(ReviewState)) == 2
