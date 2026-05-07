"""Tests for recipe_publisher."""
from __future__ import annotations

from server.recipe_publisher import (
    CraftDiscipline, CraftProof, RecipePublisher,
    RecipeStatus,
)


def _setup():
    p = RecipePublisher()
    p.set_mentor_status(
        author_id="chharith", is_mentor=True,
        display_name="Chharith",
    )
    return p


def _publish(p, **overrides):
    kwargs = dict(
        author_id="chharith",
        discipline=CraftDiscipline.COOKING,
        title="Marinara Pizza",
        crystal="fire crystal",
        materials=[
            "dough", "tomato", "cheese",
            "olive_oil", "basil",
        ],
        sub_craft_caps=[("alchemy", 13)],
        body="Use Bastok flour for +HQ.",
        craft_proof=CraftProof(synths_count=10, hq_count=2),
        published_at=1000,
    )
    kwargs.update(overrides)
    return p.publish(**kwargs)


def test_eligibility_happy():
    p = _setup()
    elig = p.check_eligibility(
        author_id="chharith",
        discipline=CraftDiscipline.COOKING,
        craft_proof=CraftProof(
            synths_count=10, hq_count=2,
        ),
    )
    assert elig.eligible is True


def test_non_mentor_rejected():
    p = RecipePublisher()
    elig = p.check_eligibility(
        author_id="someone",
        discipline=CraftDiscipline.COOKING,
        craft_proof=CraftProof(
            synths_count=10, hq_count=2,
        ),
    )
    assert elig.failure_reason == "not_mentor"


def test_insufficient_synths_rejected():
    p = _setup()
    elig = p.check_eligibility(
        author_id="chharith",
        discipline=CraftDiscipline.COOKING,
        craft_proof=CraftProof(
            synths_count=2, hq_count=1,
        ),
    )
    assert elig.failure_reason == "insufficient_synths"


def test_low_hq_rejected():
    p = _setup()
    elig = p.check_eligibility(
        author_id="chharith",
        discipline=CraftDiscipline.COOKING,
        craft_proof=CraftProof(
            synths_count=20, hq_count=1,
        ),
    )
    assert elig.failure_reason == "hq_rate_too_low"


def test_blank_author_rejected():
    p = _setup()
    elig = p.check_eligibility(
        author_id="",
        discipline=CraftDiscipline.COOKING,
        craft_proof=CraftProof(
            synths_count=10, hq_count=2,
        ),
    )
    assert elig.failure_reason == "author_id_required"


def test_publish_happy():
    p = _setup()
    rid = _publish(p)
    assert rid is not None
    assert rid.startswith("rec_")


def test_publish_blank_title_blocked():
    p = _setup()
    assert _publish(p, title="  ") is None


def test_publish_blank_crystal_blocked():
    p = _setup()
    assert _publish(p, crystal="  ") is None


def test_publish_no_materials_blocked():
    p = _setup()
    assert _publish(p, materials=[]) is None


def test_publish_blank_material_blocked():
    p = _setup()
    assert _publish(
        p, materials=["dough", "  ", "cheese"],
    ) is None


def test_publish_too_many_materials_blocked():
    p = _setup()
    assert _publish(
        p, materials=[f"mat_{i}" for i in range(9)],
    ) is None


def test_publish_8_materials_allowed():
    p = _setup()
    rid = _publish(
        p, materials=[f"mat_{i}" for i in range(8)],
    )
    assert rid is not None


def test_lookup_returns_published():
    p = _setup()
    rid = _publish(p)
    r = p.lookup(recipe_id=rid)
    assert r is not None
    assert r.author_display_name == "Chharith"


def test_lookup_unknown_none():
    p = _setup()
    assert p.lookup(recipe_id="ghost") is None


def test_content_hash_stable():
    p = _setup()
    rid = _publish(p)
    r = p.lookup(recipe_id=rid)
    assert len(r.content_hash) == 64


def test_synths_and_hq_recorded():
    p = _setup()
    rid = _publish(
        p, craft_proof=CraftProof(
            synths_count=20, hq_count=5,
        ),
    )
    r = p.lookup(recipe_id=rid)
    assert r.synths_at_publish == 20
    assert r.hq_rate_at_publish == 0.25


def test_unique_recipe_ids():
    p = _setup()
    rid1 = _publish(p)
    rid2 = _publish(p, title="Margherita")
    assert rid1 != rid2


def test_by_author_lists_all():
    p = _setup()
    _publish(p)
    _publish(p, title="another")
    out = p.by_author(author_id="chharith")
    assert len(out) == 2


def test_by_author_unknown_empty():
    p = _setup()
    assert p.by_author(author_id="nobody") == []


def test_by_discipline_filters():
    p = _setup()
    rid = _publish(p)
    _publish(
        p, discipline=CraftDiscipline.SMITHING,
        title="Iron Sword",
    )
    out = p.by_discipline(
        discipline=CraftDiscipline.COOKING,
    )
    assert len(out) == 1
    assert out[0].recipe_id == rid


def test_by_discipline_excludes_unlisted():
    p = _setup()
    rid = _publish(p)
    p.unlist(author_id="chharith", recipe_id=rid)
    out = p.by_discipline(
        discipline=CraftDiscipline.COOKING,
    )
    assert out == []


def test_unlist_owner():
    p = _setup()
    rid = _publish(p)
    assert p.unlist(
        author_id="chharith", recipe_id=rid,
    ) is True
    assert p.lookup(
        recipe_id=rid,
    ).status == RecipeStatus.UNLISTED


def test_unlist_non_owner_blocked():
    p = _setup()
    rid = _publish(p)
    assert p.unlist(
        author_id="impostor", recipe_id=rid,
    ) is False


def test_relist_after_unlist():
    p = _setup()
    rid = _publish(p)
    p.unlist(author_id="chharith", recipe_id=rid)
    assert p.relist(
        author_id="chharith", recipe_id=rid,
    ) is True


def test_relist_when_not_unlisted_blocked():
    p = _setup()
    rid = _publish(p)
    assert p.relist(
        author_id="chharith", recipe_id=rid,
    ) is False


def test_revoke_terminal():
    p = _setup()
    rid = _publish(p)
    assert p.revoke(
        recipe_id=rid, reason="bad_recipe",
    ) is True
    assert p.lookup(
        recipe_id=rid,
    ).status == RecipeStatus.REVOKED


def test_revoke_blank_reason_blocked():
    p = _setup()
    rid = _publish(p)
    assert p.revoke(recipe_id=rid, reason="") is False


def test_revoked_cannot_be_unlisted():
    p = _setup()
    rid = _publish(p)
    p.revoke(recipe_id=rid, reason="bad")
    assert p.unlist(
        author_id="chharith", recipe_id=rid,
    ) is False


def test_total_published_excludes_unlisted():
    p = _setup()
    rid1 = _publish(p)
    _publish(p, title="b")
    p.unlist(author_id="chharith", recipe_id=rid1)
    assert p.total_published() == 1


def test_total_entries_includes_all():
    p = _setup()
    _publish(p)
    _publish(p, title="b")
    assert p.total_entries() == 2


def test_craft_proof_zero_zero_zero():
    cp = CraftProof(synths_count=0, hq_count=0)
    assert cp.hq_rate == 0.0


def test_eight_disciplines():
    assert len(list(CraftDiscipline)) == 8


def test_four_recipe_statuses():
    assert len(list(RecipeStatus)) == 4
