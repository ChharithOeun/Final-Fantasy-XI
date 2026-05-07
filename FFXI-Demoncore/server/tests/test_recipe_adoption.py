"""Tests for recipe_adoption."""
from __future__ import annotations

from server.recipe_adoption import PinMode, RecipeAdoption
from server.recipe_publisher import (
    CraftDiscipline, CraftProof, RecipePublisher,
)


def _seed():
    p = RecipePublisher()
    p.set_mentor_status(
        author_id="chharith", is_mentor=True,
        display_name="Chharith",
    )
    rid = p.publish(
        author_id="chharith",
        discipline=CraftDiscipline.COOKING,
        title="Marinara",
        crystal="fire crystal",
        materials=["dough", "tomato", "cheese"],
        sub_craft_caps=[],
        body="tips",
        craft_proof=CraftProof(
            synths_count=10, hq_count=2,
        ),
        published_at=1000,
    )
    a = RecipeAdoption(_publisher=p)
    return p, a, rid


def test_adopt_happy():
    _, a, rid = _seed()
    out = a.adopt(
        player_id="bob", recipe_id=rid,
        mode=PinMode.SHOW_IN_LOG, adopted_at=2000,
    )
    assert out is not None


def test_adopt_blank_player_blocked():
    _, a, rid = _seed()
    assert a.adopt(
        player_id="", recipe_id=rid,
        mode=PinMode.SHOW_IN_LOG, adopted_at=2000,
    ) is None


def test_adopt_unknown_recipe_blocked():
    _, a, _ = _seed()
    assert a.adopt(
        player_id="bob", recipe_id="ghost",
        mode=PinMode.SHOW_IN_LOG, adopted_at=2000,
    ) is None


def test_adopt_revoked_blocked():
    p, a, rid = _seed()
    p.revoke(recipe_id=rid, reason="bad")
    assert a.adopt(
        player_id="bob", recipe_id=rid,
        mode=PinMode.SHOW_IN_LOG, adopted_at=2000,
    ) is None


def test_adopt_unlisted_blocked():
    p, a, rid = _seed()
    p.unlist(author_id="chharith", recipe_id=rid)
    assert a.adopt(
        player_id="bob", recipe_id=rid,
        mode=PinMode.SHOW_IN_LOG, adopted_at=2000,
    ) is None


def test_re_adopt_refreshes_mode():
    _, a, rid = _seed()
    a.adopt(
        player_id="bob", recipe_id=rid,
        mode=PinMode.SHOW_IN_LOG, adopted_at=2000,
    )
    a.adopt(
        player_id="bob", recipe_id=rid,
        mode=PinMode.PROJECT_COST_TOO, adopted_at=3000,
    )
    pins = a.pinned_for(player_id="bob")
    assert len(pins) == 1
    assert pins[0].mode == PinMode.PROJECT_COST_TOO


def test_un_adopt_happy():
    _, a, rid = _seed()
    a.adopt(
        player_id="bob", recipe_id=rid,
        mode=PinMode.SHOW_IN_LOG, adopted_at=2000,
    )
    assert a.un_adopt(
        player_id="bob", recipe_id=rid,
    ) is True


def test_un_adopt_unknown():
    _, a, rid = _seed()
    assert a.un_adopt(
        player_id="bob", recipe_id=rid,
    ) is False


def test_has_adopted_true_false():
    _, a, rid = _seed()
    assert a.has_adopted(
        player_id="bob", recipe_id=rid,
    ) is False
    a.adopt(
        player_id="bob", recipe_id=rid,
        mode=PinMode.SHOW_IN_LOG, adopted_at=2000,
    )
    assert a.has_adopted(
        player_id="bob", recipe_id=rid,
    ) is True


def test_pinned_for_player_sorted():
    p, a, rid = _seed()
    rid2 = p.publish(
        author_id="chharith",
        discipline=CraftDiscipline.COOKING,
        title="Pizza", crystal="fire crystal",
        materials=["dough", "tomato"],
        sub_craft_caps=[], body="x",
        craft_proof=CraftProof(
            synths_count=10, hq_count=2,
        ),
        published_at=2000,
    )
    a.adopt(
        player_id="bob", recipe_id=rid2,
        mode=PinMode.SHOW_IN_LOG, adopted_at=4000,
    )
    a.adopt(
        player_id="bob", recipe_id=rid,
        mode=PinMode.SHOW_IN_LOG, adopted_at=3000,
    )
    out = a.pinned_for(player_id="bob")
    assert out[0].adopted_at == 3000


def test_pinned_for_unknown_empty():
    _, a, _ = _seed()
    assert a.pinned_for(player_id="ghost") == []


def test_adopters_count():
    _, a, rid = _seed()
    a.adopt(
        player_id="bob", recipe_id=rid,
        mode=PinMode.SHOW_IN_LOG, adopted_at=2000,
    )
    a.adopt(
        player_id="cara", recipe_id=rid,
        mode=PinMode.SHOW_IN_LOG, adopted_at=2100,
    )
    assert a.adopters_count(recipe_id=rid) == 2


def test_adopters_count_zero():
    _, a, rid = _seed()
    assert a.adopters_count(recipe_id=rid) == 0


def test_total_adoptions():
    _, a, rid = _seed()
    a.adopt(
        player_id="bob", recipe_id=rid,
        mode=PinMode.SHOW_IN_LOG, adopted_at=2000,
    )
    a.adopt(
        player_id="cara", recipe_id=rid,
        mode=PinMode.SHOW_IN_LOG, adopted_at=2100,
    )
    assert a.total_adoptions() == 2


def test_two_pin_modes():
    assert len(list(PinMode)) == 2
