"""Lore fragments — discoverable lore page collection.

Lore fragments are scattered through the world: tomb inscriptions,
weathered scrolls, NPC dialog flags, drops from rare mobs. Each
fragment belongs to a SET (a multi-piece document like "The
Twin Princes' Diary, pages 1..7" or "Yagudo Heretical Verses"
or "Pre-Crystal War Letters").

When a player discovers a fragment for the first time, they get
a small honor reward and the fragment is added to their
collection. Collecting the COMPLETE set unlocks:

* A SET TITLE (e.g. "Chronicler of the Twin Princes")
* A SIGNATURE DROP (one-time gift from a Lore-Keeper NPC)
* A faction-specific reputation bump

Sets can be REGIONAL (one nation's history), FACTION (a tribe's
rituals), or GLOBAL (Vana'diel-wide).

Public surface
--------------
    LoreScope enum (REGIONAL / FACTION / GLOBAL)
    Fragment dataclass — single piece
    LoreSet dataclass — full set definition + reward
    DiscoveryResult dataclass
    SetCompleteResult dataclass
    LoreFragmentRegistry
        .register_set(set)
        .register_fragment(fragment)
        .discover(player_id, fragment_id, now)
        .check_set_completion(player_id, set_id)
        .player_collection(player_id) / .completed_sets(player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class LoreScope(str, enum.Enum):
    REGIONAL = "regional"
    FACTION = "faction"
    GLOBAL = "global"


@dataclasses.dataclass(frozen=True)
class Fragment:
    fragment_id: str
    set_id: str
    page_number: int
    title: str
    location_hint: str = ""
    honor_reward: int = 5
    notes: str = ""


@dataclasses.dataclass(frozen=True)
class LoreSetReward:
    title_id: str = ""
    signature_item_id: str = ""
    faction_rep_bonus: int = 50


@dataclasses.dataclass(frozen=True)
class LoreSet:
    set_id: str
    label: str
    scope: LoreScope
    total_pages: int
    faction_id: t.Optional[str] = None
    reward: LoreSetReward = LoreSetReward()
    notes: str = ""


@dataclasses.dataclass(frozen=True)
class DiscoveryResult:
    accepted: bool
    fragment_id: str
    is_first_time: bool = False
    honor_gained: int = 0
    set_completed: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class SetCompleteResult:
    set_id: str
    is_complete: bool
    pages_owned: int
    pages_total: int
    reward: t.Optional[LoreSetReward] = None


@dataclasses.dataclass
class LoreFragmentRegistry:
    _sets: dict[str, LoreSet] = dataclasses.field(
        default_factory=dict,
    )
    _fragments: dict[str, Fragment] = dataclasses.field(
        default_factory=dict,
    )
    # player_id -> set of fragment_ids owned
    _collections: dict[
        str, set[str],
    ] = dataclasses.field(default_factory=dict)
    # player_id -> set of completed set_ids
    _completed: dict[
        str, set[str],
    ] = dataclasses.field(default_factory=dict)

    def register_set(self, lore_set: LoreSet) -> LoreSet:
        self._sets[lore_set.set_id] = lore_set
        return lore_set

    def register_fragment(
        self, fragment: Fragment,
    ) -> Fragment:
        if fragment.set_id not in self._sets:
            raise ValueError(
                f"set {fragment.set_id} not registered",
            )
        self._fragments[fragment.fragment_id] = fragment
        return fragment

    def fragment(
        self, fragment_id: str,
    ) -> t.Optional[Fragment]:
        return self._fragments.get(fragment_id)

    def lore_set(self, set_id: str) -> t.Optional[LoreSet]:
        return self._sets.get(set_id)

    def fragments_in_set(
        self, set_id: str,
    ) -> tuple[Fragment, ...]:
        return tuple(
            f for f in self._fragments.values()
            if f.set_id == set_id
        )

    def discover(
        self, *, player_id: str, fragment_id: str,
        now_seconds: float = 0.0,
    ) -> DiscoveryResult:
        f = self._fragments.get(fragment_id)
        if f is None:
            return DiscoveryResult(
                accepted=False, fragment_id=fragment_id,
                reason="unknown fragment",
            )
        bucket = self._collections.setdefault(player_id, set())
        if fragment_id in bucket:
            return DiscoveryResult(
                accepted=True, fragment_id=fragment_id,
                is_first_time=False,
                reason="already collected",
            )
        bucket.add(fragment_id)
        completion = self.check_set_completion(
            player_id=player_id, set_id=f.set_id,
        )
        if completion.is_complete:
            self._completed.setdefault(
                player_id, set(),
            ).add(f.set_id)
        return DiscoveryResult(
            accepted=True, fragment_id=fragment_id,
            is_first_time=True,
            honor_gained=f.honor_reward,
            set_completed=completion.is_complete,
        )

    def check_set_completion(
        self, *, player_id: str, set_id: str,
    ) -> SetCompleteResult:
        s = self._sets.get(set_id)
        if s is None:
            return SetCompleteResult(
                set_id=set_id, is_complete=False,
                pages_owned=0, pages_total=0,
            )
        bucket = self._collections.get(player_id, set())
        owned = sum(
            1 for fid in bucket
            if fid in self._fragments
            and self._fragments[fid].set_id == set_id
        )
        is_complete = owned >= s.total_pages
        return SetCompleteResult(
            set_id=set_id,
            is_complete=is_complete,
            pages_owned=owned,
            pages_total=s.total_pages,
            reward=(s.reward if is_complete else None),
        )

    def player_collection(
        self, player_id: str,
    ) -> tuple[str, ...]:
        return tuple(self._collections.get(player_id, set()))

    def completed_sets(
        self, player_id: str,
    ) -> tuple[str, ...]:
        return tuple(self._completed.get(player_id, set()))

    def total_sets(self) -> int:
        return len(self._sets)

    def total_fragments(self) -> int:
        return len(self._fragments)


__all__ = [
    "LoreScope",
    "Fragment", "LoreSetReward", "LoreSet",
    "DiscoveryResult", "SetCompleteResult",
    "LoreFragmentRegistry",
]
