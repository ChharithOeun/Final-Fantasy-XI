"""Abyssal titles — visible insignia for underwater milestones.

Players earn TITLES from underwater achievements; titles
display next to the player's name and grant small but
permanent stat bonuses. The point isn't the bonus — it's
the public proof. When a stranger shows up at your wreck
and has TIDE-WALKER on their nameplate, you know they did
the work.

Each title has:
    title_id      - canonical id
    name          - display name ("Kraken-Slayer")
    rank          - 1..5 (rank 5 = mythic)
    stat_bonus    - dict of small permanent bonuses
    requires      - prerequisite achievement ids

Equipped titles are exclusive (one at a time displayed),
but earned titles persist forever and can be swapped.

Public surface
--------------
    Title dataclass (frozen)
    AbyssalTitles
        .register_title(title_id, name, rank, stat_bonus,
                        requires)
        .grant(player_id, title_id, now_seconds)
        .equip(player_id, title_id)
        .unequip(player_id)
        .equipped_for(player_id) -> Optional[Title]
        .titles_held(player_id) -> tuple[Title, ...]
        .stat_bonuses_for(player_id) -> dict[str, int]
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class Title:
    title_id: str
    name: str
    rank: int
    stat_bonus: dict[str, int]
    requires: tuple[str, ...]


MAX_RANK = 5


@dataclasses.dataclass
class AbyssalTitles:
    _catalog: dict[str, Title] = dataclasses.field(default_factory=dict)
    # player_id -> set of held title_ids
    _held: dict[str, set[str]] = dataclasses.field(default_factory=dict)
    # player_id -> currently equipped title_id (or None)
    _equipped: dict[str, str] = dataclasses.field(default_factory=dict)

    def register_title(
        self, *, title_id: str, name: str,
        rank: int,
        stat_bonus: t.Optional[dict[str, int]] = None,
        requires: t.Optional[t.Iterable[str]] = None,
    ) -> bool:
        if not title_id or not name:
            return False
        if rank < 1 or rank > MAX_RANK:
            return False
        if title_id in self._catalog:
            return False
        self._catalog[title_id] = Title(
            title_id=title_id, name=name,
            rank=rank,
            stat_bonus=dict(stat_bonus or {}),
            requires=tuple(requires or ()),
        )
        return True

    def grant(
        self, *, player_id: str, title_id: str,
        now_seconds: int = 0,
    ) -> bool:
        if not player_id:
            return False
        if title_id not in self._catalog:
            return False
        held = self._held.setdefault(player_id, set())
        if title_id in held:
            return False
        # require all prerequisites earned
        title = self._catalog[title_id]
        for req in title.requires:
            if req not in held:
                return False
        held.add(title_id)
        return True

    def equip(
        self, *, player_id: str, title_id: str,
    ) -> bool:
        held = self._held.get(player_id, set())
        if title_id not in held:
            return False
        self._equipped[player_id] = title_id
        return True

    def unequip(self, *, player_id: str) -> bool:
        return self._equipped.pop(player_id, None) is not None

    def equipped_for(
        self, *, player_id: str,
    ) -> t.Optional[Title]:
        tid = self._equipped.get(player_id)
        if tid is None:
            return None
        return self._catalog.get(tid)

    def titles_held(
        self, *, player_id: str,
    ) -> tuple[Title, ...]:
        ids = self._held.get(player_id, set())
        out = [self._catalog[i] for i in ids if i in self._catalog]
        # sort by rank desc then title_id for stable display
        out.sort(key=lambda t: (-t.rank, t.title_id))
        return tuple(out)

    def stat_bonuses_for(
        self, *, player_id: str,
    ) -> dict[str, int]:
        # only the equipped title's bonuses apply
        title = self.equipped_for(player_id=player_id)
        if title is None:
            return {}
        return dict(title.stat_bonus)


__all__ = [
    "Title", "AbyssalTitles", "MAX_RANK",
]
