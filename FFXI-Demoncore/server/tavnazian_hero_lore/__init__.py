"""Tavnazian hero lore — chain that uncovers the hero's name.

Beastmen praise THE TAVNAZIAN HERO without naming him. His true
name is hidden behind a 7-step lore chain. Each step reveals
one FRAGMENT of his story (early life / first march / siege /
last stand / fall / interment / what came after). A player
must visit specific NPCs and locations across the world (including
a Tavnazian-side voyage that requires crossing through the
canon Tavnazia ruins) to collect every fragment.

Only after the seventh fragment is captured does the system
expose the hero's TRUE NAME — gating any reference to it in
the dialogue / quest engine. Until then quest text falls back
to "the Tavnazian Hero".

Public surface
--------------
    FragmentKind enum   EARLY_LIFE / FIRST_MARCH / SIEGE /
                        LAST_STAND / FALL / INTERMENT / AFTER
    HeroProfile dataclass
    BeastmanLoreFragment dataclass
    TavnazianHeroLore
        .seed_canonical_hero(name, fragments)
        .reveal_fragment(player_id, kind, npc_or_location)
        .has_fragment(player_id, kind)
        .true_name_for(player_id) -> Optional[str]
        .display_name_for(player_id) -> str
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Always-rendered alias until full lore is unlocked.
PUBLIC_ALIAS = "the Tavnazian Hero"


class FragmentKind(str, enum.Enum):
    EARLY_LIFE = "early_life"
    FIRST_MARCH = "first_march"
    SIEGE = "siege"
    LAST_STAND = "last_stand"
    FALL = "fall"
    INTERMENT = "interment"
    AFTER = "after"


_FRAGMENT_ORDER: tuple[FragmentKind, ...] = tuple(
    FragmentKind,
)


@dataclasses.dataclass(frozen=True)
class BeastmanLoreFragment:
    kind: FragmentKind
    title: str
    snippet: str
    revealing_source: str        # NPC id or location id


@dataclasses.dataclass(frozen=True)
class HeroProfile:
    true_name: str
    public_alias: str = PUBLIC_ALIAS
    fragments: tuple[BeastmanLoreFragment, ...] = ()


@dataclasses.dataclass(frozen=True)
class RevealResult:
    accepted: bool
    fragment_kind: FragmentKind
    is_fully_revealed: bool
    reason: t.Optional[str] = None


@dataclasses.dataclass
class TavnazianHeroLore:
    _hero: t.Optional[HeroProfile] = None
    # player_id -> set of revealed fragment kinds
    _revealed: dict[
        str, set[FragmentKind],
    ] = dataclasses.field(default_factory=dict)

    def seed_canonical_hero(
        self, *, true_name: str,
        fragments: tuple[
            BeastmanLoreFragment, ...,
        ],
    ) -> bool:
        if self._hero is not None:
            return False
        if not true_name:
            return False
        # All seven fragments must be present, in canon order.
        if len(fragments) != len(_FRAGMENT_ORDER):
            return False
        for i, frag in enumerate(fragments):
            if frag.kind != _FRAGMENT_ORDER[i]:
                return False
            if not frag.revealing_source:
                return False
        self._hero = HeroProfile(
            true_name=true_name,
            fragments=fragments,
        )
        return True

    def hero(self) -> t.Optional[HeroProfile]:
        return self._hero

    def reveal_fragment(
        self, *, player_id: str,
        kind: FragmentKind,
        revealing_source: str,
    ) -> RevealResult:
        if self._hero is None:
            return RevealResult(
                False, fragment_kind=kind,
                is_fully_revealed=False,
                reason="hero not seeded",
            )
        # Validate that the source matches the canon source for
        # this fragment.
        canon_frag = next(
            (
                f for f in self._hero.fragments
                if f.kind == kind
            ),
            None,
        )
        if canon_frag is None:
            return RevealResult(
                False, fragment_kind=kind,
                is_fully_revealed=False,
                reason="unknown fragment",
            )
        if canon_frag.revealing_source != revealing_source:
            return RevealResult(
                False, fragment_kind=kind,
                is_fully_revealed=False,
                reason="wrong source",
            )
        s = self._revealed.setdefault(player_id, set())
        if kind in s:
            return RevealResult(
                False, fragment_kind=kind,
                is_fully_revealed=(
                    len(s) == len(_FRAGMENT_ORDER)
                ),
                reason="already revealed",
            )
        s.add(kind)
        full = len(s) == len(_FRAGMENT_ORDER)
        return RevealResult(
            accepted=True, fragment_kind=kind,
            is_fully_revealed=full,
        )

    def has_fragment(
        self, *, player_id: str, kind: FragmentKind,
    ) -> bool:
        return kind in self._revealed.get(
            player_id, set(),
        )

    def revealed_count(
        self, *, player_id: str,
    ) -> int:
        return len(self._revealed.get(player_id, set()))

    def true_name_for(
        self, *, player_id: str,
    ) -> t.Optional[str]:
        if self._hero is None:
            return None
        if self.revealed_count(
            player_id=player_id,
        ) == len(_FRAGMENT_ORDER):
            return self._hero.true_name
        return None

    def display_name_for(
        self, *, player_id: str,
    ) -> str:
        true_name = self.true_name_for(
            player_id=player_id,
        )
        return true_name if true_name else PUBLIC_ALIAS


__all__ = [
    "PUBLIC_ALIAS",
    "FragmentKind",
    "BeastmanLoreFragment", "HeroProfile",
    "RevealResult",
    "TavnazianHeroLore",
]
