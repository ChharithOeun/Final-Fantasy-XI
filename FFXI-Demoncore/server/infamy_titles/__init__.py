"""Infamy titles — the dark counterpart to hero_titles.

Not all "legends" are heroes. Some players earn the
opposite: a permanent record of betrayal, cowardice,
murder, or sacrilege. Infamy titles are sticky — they
stay attached to a player until either the title's
specific cleansing condition is met, or the title
explicitly notes itself as INDELIBLE (cannot be removed).

Infamy tiers (mirrors hero_titles tiers but inverted):
    PETTY        minor disgrace (e.g. "Caught Cheating")
    SHAMEFUL     known cowardice
    NOTORIOUS    server-wide infamy (e.g. "Bandit King")
    INFAMOUS     truly dark deed (e.g. "Defiler of Tombs")
    BLACK        the worst (e.g. "Kingslayer", "Demonbinder")
                 — INDELIBLE, never removable

Effects of holding an infamy title:
    - npc_legend_awareness can fold infamy in for hostile
      reactions (handled by callers; this module just
      records the title)
    - vendor_discount_legends caller may treat as outlaw
    - hero_titles still grants normally; infamy is stacked
      on top, not exclusive

Public surface
--------------
    InfamyTier enum
    InfamyTitleDef dataclass (frozen) — id, name, tier,
        description, indelible, cleanse_quest_id
    InfamyMark dataclass (frozen) — title_id, player_id,
        marked_at, source_entry_id
    InfamyRegistry
        .define_infamy(...) -> bool
        .mark_player(...) -> bool
        .cleanse(player_id, title_id, cleansed_at,
                 quest_id_used) -> bool
        .marks_for_player(player_id) -> tuple[InfamyMark, ...]
        .holders_of(title_id) -> tuple[str, ...]
        .player_worst_tier(player_id) -> Optional[InfamyTier]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class InfamyTier(str, enum.Enum):
    PETTY = "petty"
    SHAMEFUL = "shameful"
    NOTORIOUS = "notorious"
    INFAMOUS = "infamous"
    BLACK = "black"


_TIER_ORDER = {
    InfamyTier.PETTY: 1,
    InfamyTier.SHAMEFUL: 2,
    InfamyTier.NOTORIOUS: 3,
    InfamyTier.INFAMOUS: 4,
    InfamyTier.BLACK: 5,
}


@dataclasses.dataclass(frozen=True)
class InfamyTitleDef:
    title_id: str
    name: str
    tier: InfamyTier
    description: str = ""
    indelible: bool = False
    cleanse_quest_id: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class InfamyMark:
    title_id: str
    player_id: str
    marked_at: int
    source_entry_id: t.Optional[str]


@dataclasses.dataclass
class InfamyRegistry:
    _titles: dict[str, InfamyTitleDef] = dataclasses.field(
        default_factory=dict,
    )
    # (player_id, title_id) -> InfamyMark
    _marks: dict[tuple[str, str], InfamyMark] = dataclasses.field(
        default_factory=dict,
    )
    _by_player: dict[str, list[str]] = dataclasses.field(
        default_factory=dict,
    )
    _by_title: dict[str, list[str]] = dataclasses.field(
        default_factory=dict,
    )

    def define_infamy(
        self, *, title_id: str, name: str,
        tier: InfamyTier, description: str = "",
        indelible: bool = False,
        cleanse_quest_id: t.Optional[str] = None,
    ) -> bool:
        if not title_id or not name:
            return False
        if title_id in self._titles:
            return False
        # BLACK tier is automatically indelible
        if tier == InfamyTier.BLACK:
            indelible = True
            cleanse_quest_id = None
        self._titles[title_id] = InfamyTitleDef(
            title_id=title_id, name=name, tier=tier,
            description=description, indelible=indelible,
            cleanse_quest_id=cleanse_quest_id,
        )
        return True

    def get_title(
        self, *, title_id: str,
    ) -> t.Optional[InfamyTitleDef]:
        return self._titles.get(title_id)

    def mark_player(
        self, *, player_id: str, title_id: str,
        marked_at: int,
        source_entry_id: t.Optional[str] = None,
    ) -> bool:
        if title_id not in self._titles:
            return False
        if not player_id:
            return False
        key = (player_id, title_id)
        if key in self._marks:
            return False  # already holds this infamy
        self._marks[key] = InfamyMark(
            title_id=title_id, player_id=player_id,
            marked_at=marked_at,
            source_entry_id=source_entry_id,
        )
        self._by_player.setdefault(player_id, []).append(title_id)
        self._by_title.setdefault(title_id, []).append(player_id)
        return True

    def cleanse(
        self, *, player_id: str, title_id: str,
        cleansed_at: int,
        quest_id_used: t.Optional[str] = None,
    ) -> bool:
        td = self._titles.get(title_id)
        if td is None:
            return False
        key = (player_id, title_id)
        if key not in self._marks:
            return False
        if td.indelible:
            return False
        # if a cleanse quest is specified, must use it
        if td.cleanse_quest_id is not None:
            if quest_id_used != td.cleanse_quest_id:
                return False
        del self._marks[key]
        if title_id in self._by_player.get(player_id, []):
            self._by_player[player_id].remove(title_id)
        if player_id in self._by_title.get(title_id, []):
            self._by_title[title_id].remove(player_id)
        return True

    def marks_for_player(
        self, *, player_id: str,
    ) -> tuple[InfamyMark, ...]:
        ids = self._by_player.get(player_id, [])
        return tuple(self._marks[(player_id, tid)] for tid in ids)

    def holders_of(self, *, title_id: str) -> tuple[str, ...]:
        return tuple(self._by_title.get(title_id, []))

    def player_worst_tier(
        self, *, player_id: str,
    ) -> t.Optional[InfamyTier]:
        ids = self._by_player.get(player_id, [])
        if not ids:
            return None
        worst: t.Optional[InfamyTier] = None
        worst_rank = 0
        for tid in ids:
            td = self._titles.get(tid)
            if td is None:
                continue
            r = _TIER_ORDER[td.tier]
            if r > worst_rank:
                worst_rank = r
                worst = td.tier
        return worst

    def total_titles(self) -> int:
        return len(self._titles)

    def total_marks(self) -> int:
        return len(self._marks)


__all__ = [
    "InfamyTier", "InfamyTitleDef", "InfamyMark",
    "InfamyRegistry",
]
