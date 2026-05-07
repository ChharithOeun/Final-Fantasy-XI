"""Tests for content_index."""
from __future__ import annotations

from server.content_index import ContentIndex, ContentKind
from server.gearswap_publisher import GearswapPublisher
from server.recipe_publisher import (
    CraftDiscipline, CraftProof, RecipePublisher,
)
from server.strategy_publisher import (
    ClearProof, EncounterKind, EncounterRef,
    StrategyPublisher,
)


def _seed():
    gp = GearswapPublisher()
    gp.set_mentor_status(
        author_id="chharith", is_mentor=True,
        display_name="Chharith",
    )
    gp.set_mentor_status(
        author_id="bob", is_mentor=True,
        display_name="Bob",
    )
    gpid = gp.publish(
        author_id="chharith", job="RDM",
        addon_id="rdm_chharith", lua_source="-- a",
        reputation_snapshot=80, hours_played_on_job=500,
        published_at=1000,
    )
    bob_lua = gp.publish(
        author_id="bob", job="BLM",
        addon_id="blm_bob", lua_source="-- b",
        reputation_snapshot=20, hours_played_on_job=300,
        published_at=2000,
    )

    sp = StrategyPublisher()
    sp.set_mentor_status(
        author_id="chharith", is_mentor=True,
        display_name="Chharith",
    )
    sg = sp.publish(
        author_id="chharith",
        encounter=EncounterRef(
            kind=EncounterKind.HTBC,
            encounter_id="maat",
            display_name="Maat",
        ),
        title="Maat as RDM", body="step 1...",
        clear_proof=ClearProof(
            clears_count=5, wins_count=4,
        ),
        published_at=3000,
    )

    rp = RecipePublisher()
    rp.set_mentor_status(
        author_id="chharith", is_mentor=True,
        display_name="Chharith",
    )
    rr = rp.publish(
        author_id="chharith",
        discipline=CraftDiscipline.COOKING,
        title="Marinara",
        crystal="fire crystal",
        materials=["dough", "tomato", "cheese"],
        sub_craft_caps=[],
        body="best margin pizza",
        craft_proof=CraftProof(
            synths_count=10, hq_count=2,
        ),
        published_at=4000,
    )

    idx = ContentIndex(
        _gearswap=gp, _strategy=sp, _recipe=rp,
    )
    return idx, {
        "lua_chharith": gpid, "lua_bob": bob_lua,
        "guide_chharith": sg, "recipe_chharith": rr,
    }


def test_by_author_chharith_three_entries():
    idx, _ = _seed()
    out = idx.by_author(author_id="chharith")
    kinds = {e.kind for e in out}
    assert len(out) == 3
    assert kinds == {
        ContentKind.GEARSWAP, ContentKind.STRATEGY,
        ContentKind.RECIPE,
    }


def test_by_author_sorted_newest_first():
    idx, _ = _seed()
    out = idx.by_author(author_id="chharith")
    # recipe (4000) > guide (3000) > lua (1000)
    assert out[0].kind == ContentKind.RECIPE
    assert out[-1].kind == ContentKind.GEARSWAP


def test_by_author_filters_correctly():
    idx, _ = _seed()
    bob_out = idx.by_author(author_id="bob")
    assert len(bob_out) == 1
    assert bob_out[0].kind == ContentKind.GEARSWAP
    assert bob_out[0].author_id == "bob"


def test_by_author_blank_empty():
    idx, _ = _seed()
    assert idx.by_author(author_id="") == []


def test_by_author_unknown_empty():
    idx, _ = _seed()
    assert idx.by_author(author_id="ghost") == []


def test_search_across_all_kinds():
    idx, _ = _seed()
    out = idx.search(query="chharith")
    # 3 entries authored by Chharith match author display
    assert len(out) == 3


def test_search_by_kind_filter():
    idx, _ = _seed()
    out = idx.search(
        query="chharith", kind=ContentKind.RECIPE,
    )
    assert len(out) == 1
    assert out[0].kind == ContentKind.RECIPE


def test_search_substring_match():
    idx, _ = _seed()
    out = idx.search(query="rdm")
    # Lua has "rdm_chharith" addon_id and "RDM" job;
    # guide title is "Maat as RDM"
    assert len(out) >= 2


def test_search_no_match():
    idx, _ = _seed()
    assert idx.search(query="xyzzy_unmatchable") == []


def test_search_blank_query_empty():
    idx, _ = _seed()
    assert idx.search(query="") == []


def test_search_zero_limit_empty():
    idx, _ = _seed()
    assert idx.search(query="chharith", limit=0) == []


def test_search_limit_caps():
    idx, _ = _seed()
    out = idx.search(query="chharith", limit=2)
    assert len(out) == 2


def test_search_excludes_unlisted():
    """Verify that unpublishing in the source publisher
    pulls from the index transparently."""
    idx, ids = _seed()
    # Direct manipulation of the publisher; index reads
    # live state.
    idx._recipe.unlist(
        author_id="chharith",
        recipe_id=ids["recipe_chharith"],
    )
    out = idx.search(query="chharith")
    kinds = {e.kind for e in out}
    assert ContentKind.RECIPE not in kinds


def test_total_by_kind():
    idx, _ = _seed()
    totals = idx.total_by_kind()
    assert totals[ContentKind.GEARSWAP] == 2
    assert totals[ContentKind.STRATEGY] == 1
    assert totals[ContentKind.RECIPE] == 1


def test_browse_recent_returns_within_window():
    idx, _ = _seed()
    out = idx.browse_recent(now=4100, day_window=7)
    # All published at <= 4000, within 7 days of 4100
    assert len(out) == 4


def test_browse_recent_filters_old():
    idx, _ = _seed()
    # Cutoff at 7d before now=2_000_000 — all entries
    # are way older than that
    out = idx.browse_recent(
        now=2_000_000, day_window=1,
    )
    assert out == []


def test_browse_recent_sorted_newest_first():
    idx, _ = _seed()
    out = idx.browse_recent(now=5000, day_window=7)
    assert out[0].published_at >= out[-1].published_at


def test_browse_recent_zero_window():
    idx, _ = _seed()
    assert idx.browse_recent(
        now=5000, day_window=0,
    ) == []


def test_browse_recent_zero_limit():
    idx, _ = _seed()
    assert idx.browse_recent(
        now=5000, day_window=7, limit=0,
    ) == []


def test_index_with_no_publishers_safe():
    idx = ContentIndex()
    assert idx.by_author(author_id="x") == []
    assert idx.search(query="anything") == []
    totals = idx.total_by_kind()
    assert totals[ContentKind.GEARSWAP] == 0


def test_three_content_kinds():
    assert len(list(ContentKind)) == 3
