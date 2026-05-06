"""Hero titles — server-wide prestige earned through history.

A title isn't just flavor text. On Demoncore, titles are the
visible record of what a player has actually done. The
appraisal table runs over the server history log and grants
matching titles automatically — no manual hand-out, no
"GM gave it to a friend." If you earned it, you have it;
if you didn't, no amount of /title spam will fake it.

Tier ladder
-----------
    COMMON       baseline cosmetic (e.g. "of the South Wind")
    RARE         meaningful achievements (5+ NM kills,
                 100k SC closes)
    EPIC         high-bar accomplishments (perfect run vs
                 named boss, world-second kill)
    LEGENDARY    once-per-server-lifetime feats
                 (world-first kills, regional liberation)
    MYTHIC       generational events
                 (server-first expansion clear,
                  longest-held permadeath survivor)

Public surface
--------------
    TitleTier enum
    TitleDef dataclass (frozen) — id, name, tier, predicate hint
    TitleGrant dataclass (frozen) — title_id, player_id,
        granted_at, source_entry_id (history entry that
        triggered the grant)
    HeroTitleRegistry
        .define_title(title_id, name, tier)
        .grant_title(title_id, player_id, granted_at,
                     source_entry_id) -> bool
        .titles_for_player(player_id)
            -> tuple[TitleGrant, ...]
        .holders_of(title_id) -> tuple[str, ...]
        .player_highest_tier(player_id) -> Optional[TitleTier]
        .total_grants() -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TitleTier(str, enum.Enum):
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


_TIER_ORDER = {
    TitleTier.COMMON: 1,
    TitleTier.RARE: 2,
    TitleTier.EPIC: 3,
    TitleTier.LEGENDARY: 4,
    TitleTier.MYTHIC: 5,
}


@dataclasses.dataclass(frozen=True)
class TitleDef:
    title_id: str
    name: str
    tier: TitleTier
    description: str = ""


@dataclasses.dataclass(frozen=True)
class TitleGrant:
    title_id: str
    player_id: str
    granted_at: int
    source_entry_id: t.Optional[str] = None


@dataclasses.dataclass
class HeroTitleRegistry:
    _titles: dict[str, TitleDef] = dataclasses.field(default_factory=dict)
    _grants: list[TitleGrant] = dataclasses.field(default_factory=list)
    # secondary indexes
    _by_player: dict[str, list[int]] = dataclasses.field(default_factory=dict)
    _by_title: dict[str, list[int]] = dataclasses.field(default_factory=dict)
    # uniqueness tracker (player_id, title_id) -> already granted?
    _held: set[tuple[str, str]] = dataclasses.field(default_factory=set)

    def define_title(
        self, *, title_id: str, name: str, tier: TitleTier,
        description: str = "",
    ) -> bool:
        if not title_id or not name:
            return False
        if title_id in self._titles:
            return False
        self._titles[title_id] = TitleDef(
            title_id=title_id, name=name, tier=tier,
            description=description,
        )
        return True

    def get_title(self, *, title_id: str) -> t.Optional[TitleDef]:
        return self._titles.get(title_id)

    def grant_title(
        self, *, title_id: str, player_id: str,
        granted_at: int,
        source_entry_id: t.Optional[str] = None,
    ) -> bool:
        if title_id not in self._titles:
            return False
        if not player_id:
            return False
        key = (player_id, title_id)
        if key in self._held:
            return False  # already holds this title
        idx = len(self._grants)
        self._grants.append(TitleGrant(
            title_id=title_id, player_id=player_id,
            granted_at=granted_at,
            source_entry_id=source_entry_id,
        ))
        self._held.add(key)
        self._by_player.setdefault(player_id, []).append(idx)
        self._by_title.setdefault(title_id, []).append(idx)
        return True

    def titles_for_player(
        self, *, player_id: str,
    ) -> tuple[TitleGrant, ...]:
        idxs = self._by_player.get(player_id, [])
        return tuple(self._grants[i] for i in idxs)

    def holders_of(self, *, title_id: str) -> tuple[str, ...]:
        idxs = self._by_title.get(title_id, [])
        seen: set[str] = set()
        out: list[str] = []
        for i in idxs:
            pid = self._grants[i].player_id
            if pid in seen:
                continue
            seen.add(pid)
            out.append(pid)
        return tuple(out)

    def player_highest_tier(
        self, *, player_id: str,
    ) -> t.Optional[TitleTier]:
        grants = self.titles_for_player(player_id=player_id)
        if not grants:
            return None
        best: t.Optional[TitleTier] = None
        best_rank = 0
        for g in grants:
            td = self._titles.get(g.title_id)
            if td is None:
                continue
            rank = _TIER_ORDER[td.tier]
            if rank > best_rank:
                best_rank = rank
                best = td.tier
        return best

    def total_grants(self) -> int:
        return len(self._grants)

    def total_titles_defined(self) -> int:
        return len(self._titles)


__all__ = [
    "TitleTier", "TitleDef", "TitleGrant",
    "HeroTitleRegistry",
]
