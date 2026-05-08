"""World records board — server records leaderboard.

Beyond achievements/personal milestones, demoncore tracks
SERVER RECORDS — categories where ONE record-holder is
the current best on the server. Submitting a better
record evicts the previous holder.

Categories:
    FASTEST_HNM_KILL          {hnm_id}: kill time in sec
    LONGEST_PERMADEATH_SURVIVOR cumulative game-days alive
    HIGHEST_GIL_DONATION       single public_works contribution
    LARGEST_LS                 simultaneous LS member count
    LONGEST_FRIENDSHIP         oldest BLOOD_BOND friendship
    DEEPEST_LINEAGE            highest-generation heir
    MOST_SCARS                 scar_count for a player
    HIGHEST_BOUNTY             single outlaw bounty paid
    QUICKEST_DUNGEON_CLEAR     {dungeon_id}: clear time
    MOST_MASTERWORKS           lifetime masterwork count

Sub-records: some categories take a sub-key (which HNM,
which dungeon, etc.). The leaderboard is indexed by
(category, sub_key).

Each record carries the holder, value, and submitted_day.
A new submission with a BETTER value displaces the
current holder. "Better" depends on category — fastest
times are LOWER, biggest counts are HIGHER. Each category
has a comparator direction.

Public surface
--------------
    Category enum
    Direction enum
    Record dataclass (frozen)
    WorldRecordsBoard
        .submit(category, sub_key, holder, value, day)
            -> bool
        .current(category, sub_key) -> Optional[Record]
        .all_in_category(category) -> list[Record]
        .records_for_holder(holder) -> list[Record]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Direction(str, enum.Enum):
    LOWER_IS_BETTER = "lower"
    HIGHER_IS_BETTER = "higher"


class Category(str, enum.Enum):
    FASTEST_HNM_KILL = "fastest_hnm_kill"
    LONGEST_PERMADEATH_SURVIVOR = "longest_permadeath_survivor"
    HIGHEST_GIL_DONATION = "highest_gil_donation"
    LARGEST_LS = "largest_ls"
    LONGEST_FRIENDSHIP = "longest_friendship"
    DEEPEST_LINEAGE = "deepest_lineage"
    MOST_SCARS = "most_scars"
    HIGHEST_BOUNTY = "highest_bounty"
    QUICKEST_DUNGEON_CLEAR = "quickest_dungeon_clear"
    MOST_MASTERWORKS = "most_masterworks"


_DIRECTION = {
    Category.FASTEST_HNM_KILL: Direction.LOWER_IS_BETTER,
    Category.LONGEST_PERMADEATH_SURVIVOR: Direction.HIGHER_IS_BETTER,
    Category.HIGHEST_GIL_DONATION: Direction.HIGHER_IS_BETTER,
    Category.LARGEST_LS: Direction.HIGHER_IS_BETTER,
    Category.LONGEST_FRIENDSHIP: Direction.HIGHER_IS_BETTER,
    Category.DEEPEST_LINEAGE: Direction.HIGHER_IS_BETTER,
    Category.MOST_SCARS: Direction.HIGHER_IS_BETTER,
    Category.HIGHEST_BOUNTY: Direction.HIGHER_IS_BETTER,
    Category.QUICKEST_DUNGEON_CLEAR: Direction.LOWER_IS_BETTER,
    Category.MOST_MASTERWORKS: Direction.HIGHER_IS_BETTER,
}


@dataclasses.dataclass(frozen=True)
class Record:
    category: Category
    sub_key: str
    holder_id: str
    value: int
    submitted_day: int


@dataclasses.dataclass
class WorldRecordsBoard:
    _records: dict[
        tuple[Category, str], Record,
    ] = dataclasses.field(default_factory=dict)

    def submit(
        self, *, category: Category, sub_key: str,
        holder_id: str, value: int, day: int,
    ) -> bool:
        if not holder_id:
            return False
        if value < 0:
            return False
        if day < 0:
            return False
        # Use empty string for global (no sub-key) records
        key = (category, sub_key or "")
        new_record = Record(
            category=category, sub_key=sub_key or "",
            holder_id=holder_id, value=value,
            submitted_day=day,
        )
        existing = self._records.get(key)
        if existing is None:
            self._records[key] = new_record
            return True
        direction = _DIRECTION[category]
        if direction == Direction.LOWER_IS_BETTER:
            beats = value < existing.value
        else:
            beats = value > existing.value
        if not beats:
            return False
        self._records[key] = new_record
        return True

    def current(
        self, *, category: Category, sub_key: str = "",
    ) -> t.Optional[Record]:
        return self._records.get((category, sub_key))

    def all_in_category(
        self, *, category: Category,
    ) -> list[Record]:
        return sorted(
            (r for (c, _), r in self._records.items()
             if c == category),
            key=lambda r: r.sub_key,
        )

    def records_for_holder(
        self, *, holder_id: str,
    ) -> list[Record]:
        return sorted(
            (r for r in self._records.values()
             if r.holder_id == holder_id),
            key=lambda r: r.category.value,
        )

    def total(self) -> int:
        return len(self._records)


__all__ = [
    "Category", "Direction", "Record",
    "WorldRecordsBoard",
]
