"""Tests for the Tavnazian hero lore."""
from __future__ import annotations

from server.tavnazian_hero_lore import (
    BeastmanLoreFragment,
    FragmentKind,
    PUBLIC_ALIAS,
    TavnazianHeroLore,
)


def _seed(t: TavnazianHeroLore):
    fragments = tuple(
        BeastmanLoreFragment(
            kind=k,
            title=f"Fragment of {k.value}",
            snippet="...",
            revealing_source=f"npc_{k.value}",
        )
        for k in FragmentKind
    )
    return t.seed_canonical_hero(
        true_name="Vaurok the Roar-Bound",
        fragments=fragments,
    )


def test_seed_canonical_hero():
    t = TavnazianHeroLore()
    assert _seed(t)
    assert t.hero() is not None


def test_seed_double_rejected():
    t = TavnazianHeroLore()
    _seed(t)
    assert not _seed(t)


def test_seed_empty_name_rejected():
    t = TavnazianHeroLore()
    fragments = tuple(
        BeastmanLoreFragment(
            kind=k, title="x", snippet="x",
            revealing_source="x",
        )
        for k in FragmentKind
    )
    assert not t.seed_canonical_hero(
        true_name="", fragments=fragments,
    )


def test_seed_wrong_count_rejected():
    t = TavnazianHeroLore()
    fragments = (
        BeastmanLoreFragment(
            kind=FragmentKind.EARLY_LIFE,
            title="x", snippet="x",
            revealing_source="x",
        ),
    )
    assert not t.seed_canonical_hero(
        true_name="x", fragments=fragments,
    )


def test_seed_out_of_order_rejected():
    t = TavnazianHeroLore()
    canon_kinds = list(FragmentKind)
    canon_kinds[0], canon_kinds[1] = (
        canon_kinds[1], canon_kinds[0],
    )
    fragments = tuple(
        BeastmanLoreFragment(
            kind=k, title="x", snippet="x",
            revealing_source="x",
        )
        for k in canon_kinds
    )
    assert not t.seed_canonical_hero(
        true_name="x", fragments=fragments,
    )


def test_seed_empty_source_rejected():
    t = TavnazianHeroLore()
    fragments = tuple(
        BeastmanLoreFragment(
            kind=k, title="x", snippet="x",
            revealing_source="",
        )
        for k in FragmentKind
    )
    assert not t.seed_canonical_hero(
        true_name="x", fragments=fragments,
    )


def test_reveal_fragment():
    t = TavnazianHeroLore()
    _seed(t)
    res = t.reveal_fragment(
        player_id="alice",
        kind=FragmentKind.EARLY_LIFE,
        revealing_source="npc_early_life",
    )
    assert res.accepted
    assert not res.is_fully_revealed


def test_reveal_wrong_source_rejected():
    t = TavnazianHeroLore()
    _seed(t)
    res = t.reveal_fragment(
        player_id="alice",
        kind=FragmentKind.EARLY_LIFE,
        revealing_source="random_npc",
    )
    assert not res.accepted
    assert "wrong source" in res.reason


def test_reveal_unseeded_hero_rejected():
    t = TavnazianHeroLore()
    res = t.reveal_fragment(
        player_id="alice",
        kind=FragmentKind.EARLY_LIFE,
        revealing_source="x",
    )
    assert not res.accepted


def test_reveal_double_rejected():
    t = TavnazianHeroLore()
    _seed(t)
    t.reveal_fragment(
        player_id="alice",
        kind=FragmentKind.EARLY_LIFE,
        revealing_source="npc_early_life",
    )
    res = t.reveal_fragment(
        player_id="alice",
        kind=FragmentKind.EARLY_LIFE,
        revealing_source="npc_early_life",
    )
    assert not res.accepted


def test_has_fragment():
    t = TavnazianHeroLore()
    _seed(t)
    assert not t.has_fragment(
        player_id="alice",
        kind=FragmentKind.SIEGE,
    )
    t.reveal_fragment(
        player_id="alice",
        kind=FragmentKind.SIEGE,
        revealing_source="npc_siege",
    )
    assert t.has_fragment(
        player_id="alice",
        kind=FragmentKind.SIEGE,
    )


def test_display_name_default_alias():
    t = TavnazianHeroLore()
    _seed(t)
    assert t.display_name_for(
        player_id="alice",
    ) == PUBLIC_ALIAS


def test_display_name_alias_until_all_revealed():
    t = TavnazianHeroLore()
    _seed(t)
    for k in list(FragmentKind)[:6]:
        t.reveal_fragment(
            player_id="alice",
            kind=k,
            revealing_source=f"npc_{k.value}",
        )
    # 6 of 7 — still alias
    assert t.display_name_for(
        player_id="alice",
    ) == PUBLIC_ALIAS


def test_true_name_after_full_reveal():
    t = TavnazianHeroLore()
    _seed(t)
    for k in FragmentKind:
        t.reveal_fragment(
            player_id="alice",
            kind=k,
            revealing_source=f"npc_{k.value}",
        )
    assert (
        t.true_name_for(player_id="alice")
        == "Vaurok the Roar-Bound"
    )
    assert t.display_name_for(
        player_id="alice",
    ) == "Vaurok the Roar-Bound"


def test_true_name_partial_returns_none():
    t = TavnazianHeroLore()
    _seed(t)
    for k in list(FragmentKind)[:3]:
        t.reveal_fragment(
            player_id="alice",
            kind=k,
            revealing_source=f"npc_{k.value}",
        )
    assert t.true_name_for(
        player_id="alice",
    ) is None


def test_revealed_count():
    t = TavnazianHeroLore()
    _seed(t)
    t.reveal_fragment(
        player_id="alice",
        kind=FragmentKind.EARLY_LIFE,
        revealing_source="npc_early_life",
    )
    t.reveal_fragment(
        player_id="alice",
        kind=FragmentKind.SIEGE,
        revealing_source="npc_siege",
    )
    assert t.revealed_count(
        player_id="alice",
    ) == 2


def test_per_player_isolation():
    t = TavnazianHeroLore()
    _seed(t)
    for k in FragmentKind:
        t.reveal_fragment(
            player_id="alice",
            kind=k,
            revealing_source=f"npc_{k.value}",
        )
    # Bob still sees alias
    assert t.display_name_for(
        player_id="bob",
    ) == PUBLIC_ALIAS


def test_full_reveal_flag_on_final_fragment():
    t = TavnazianHeroLore()
    _seed(t)
    for k in list(FragmentKind)[:6]:
        t.reveal_fragment(
            player_id="alice",
            kind=k,
            revealing_source=f"npc_{k.value}",
        )
    res = t.reveal_fragment(
        player_id="alice",
        kind=FragmentKind.AFTER,
        revealing_source="npc_after",
    )
    assert res.is_fully_revealed
