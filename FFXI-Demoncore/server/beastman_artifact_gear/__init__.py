"""Beastman artifact gear — AF/Relic/Empyrean/Mythic/Ultimate ladders.

Each beastman job has its own ladder of TOP-TIER gear,
mirroring canon hume progression:
* AF (artifact)         the job-defining set
* RELIC                 dynamis-style set
* EMPYREAN              trial-of-the-magians set
* MYTHIC weapon
* ULTIMATE weapon       the final-form weapon

Each piece carries the parallel hume item id (canon_equiv) so
balance and itemization stay synchronized. An ULTIMATE weapon
requires the player to have unlocked AF + RELIC + EMPYREAN +
MYTHIC for that job/race first; the ladder enforces this.

Public surface
--------------
    GearLadder enum  AF / RELIC / EMPYREAN / MYTHIC / ULTIMATE
    GearSlotKind enum
    BeastmanGearItem dataclass
    UnlockResult dataclass
    BeastmanArtifactGear
        .register_item(item_id, race, job, ladder, slot,
                       canon_equiv, label)
        .unlock(player_id, race, job, item_id, prior_ladders)
        .ladder_for(race, job)
        .next_ladder_for_player(player_id, race, job)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.beastman_playable_races import BeastmanRace
from server.beastman_job_availability import JobCode


class GearLadder(str, enum.Enum):
    AF = "af"
    RELIC = "relic"
    EMPYREAN = "empyrean"
    MYTHIC = "mythic"
    ULTIMATE = "ultimate"


_LADDER_ORDER: tuple[GearLadder, ...] = tuple(GearLadder)
_LADDER_INDEX: dict[GearLadder, int] = {
    L: i for i, L in enumerate(_LADDER_ORDER)
}


class GearSlotKind(str, enum.Enum):
    HEAD = "head"
    BODY = "body"
    HANDS = "hands"
    LEGS = "legs"
    FEET = "feet"
    WEAPON_MAIN = "weapon_main"
    WEAPON_RANGED = "weapon_ranged"


@dataclasses.dataclass(frozen=True)
class BeastmanGearItem:
    item_id: str
    race: BeastmanRace
    job: JobCode
    ladder: GearLadder
    slot: GearSlotKind
    canon_equivalent_item_id: str
    label: str


@dataclasses.dataclass(frozen=True)
class UnlockResult:
    accepted: bool
    item_id: str
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanArtifactGear:
    _items: dict[str, BeastmanGearItem] = dataclasses.field(
        default_factory=dict,
    )
    # (player_id, race, job) -> set of unlocked item_ids
    _unlocked: dict[
        tuple[str, BeastmanRace, JobCode], set[str],
    ] = dataclasses.field(default_factory=dict)

    def register_item(
        self, *, item_id: str,
        race: BeastmanRace,
        job: JobCode,
        ladder: GearLadder,
        slot: GearSlotKind,
        canon_equivalent_item_id: str,
        label: str,
    ) -> t.Optional[BeastmanGearItem]:
        if item_id in self._items:
            return None
        if not label or not canon_equivalent_item_id:
            return None
        # MYTHIC / ULTIMATE ladders are weapon-only
        if (
            ladder in (
                GearLadder.MYTHIC, GearLadder.ULTIMATE,
            )
            and slot not in (
                GearSlotKind.WEAPON_MAIN,
                GearSlotKind.WEAPON_RANGED,
            )
        ):
            return None
        item = BeastmanGearItem(
            item_id=item_id, race=race, job=job,
            ladder=ladder, slot=slot,
            canon_equivalent_item_id=(
                canon_equivalent_item_id
            ),
            label=label,
        )
        self._items[item_id] = item
        return item

    def get(
        self, item_id: str,
    ) -> t.Optional[BeastmanGearItem]:
        return self._items.get(item_id)

    def ladder_for(
        self, *, race: BeastmanRace, job: JobCode,
    ) -> tuple[BeastmanGearItem, ...]:
        rows = [
            it for it in self._items.values()
            if it.race == race and it.job == job
        ]
        rows.sort(
            key=lambda it: (
                _LADDER_INDEX[it.ladder],
                it.slot.value, it.item_id,
            ),
        )
        return tuple(rows)

    def _unlocked_set(
        self, player_id: str,
        race: BeastmanRace, job: JobCode,
    ) -> set[str]:
        return self._unlocked.setdefault(
            (player_id, race, job), set(),
        )

    def _has_any_in_ladder(
        self, *, player_id: str,
        race: BeastmanRace, job: JobCode,
        ladder: GearLadder,
    ) -> bool:
        for iid in self._unlocked_set(
            player_id, race, job,
        ):
            it = self._items.get(iid)
            if it is None:
                continue
            if (
                it.ladder == ladder
                and it.race == race
                and it.job == job
            ):
                return True
        return False

    def unlock(
        self, *, player_id: str,
        race: BeastmanRace,
        job: JobCode,
        item_id: str,
    ) -> UnlockResult:
        item = self._items.get(item_id)
        if item is None:
            return UnlockResult(
                False, item_id=item_id,
                reason="no such item",
            )
        if item.race != race:
            return UnlockResult(
                False, item_id=item_id,
                reason="race mismatch",
            )
        if item.job != job:
            return UnlockResult(
                False, item_id=item_id,
                reason="job mismatch",
            )
        s = self._unlocked_set(player_id, race, job)
        if item_id in s:
            return UnlockResult(
                False, item_id=item_id,
                reason="already unlocked",
            )
        idx = _LADDER_INDEX[item.ladder]
        if idx > 0:
            prior = _LADDER_ORDER[idx - 1]
            if not self._has_any_in_ladder(
                player_id=player_id,
                race=race, job=job, ladder=prior,
            ):
                return UnlockResult(
                    False, item_id=item_id,
                    reason=(
                        f"prior ladder {prior.value}"
                        " has no items unlocked"
                    ),
                )
        s.add(item_id)
        return UnlockResult(
            accepted=True, item_id=item_id,
        )

    def unlocked_for(
        self, *, player_id: str,
        race: BeastmanRace, job: JobCode,
    ) -> tuple[str, ...]:
        return tuple(sorted(
            self._unlocked_set(player_id, race, job),
        ))

    def next_ladder_for_player(
        self, *, player_id: str,
        race: BeastmanRace, job: JobCode,
    ) -> t.Optional[GearLadder]:
        unlocked = self._unlocked_set(
            player_id, race, job,
        )
        if not unlocked:
            return GearLadder.AF
        owned_ladders = {
            self._items[iid].ladder
            for iid in unlocked
            if iid in self._items
        }
        highest = max(
            _LADDER_INDEX[L] for L in owned_ladders
        )
        if highest + 1 >= len(_LADDER_ORDER):
            return None
        return _LADDER_ORDER[highest + 1]

    def total_items(self) -> int:
        return len(self._items)


__all__ = [
    "GearLadder", "GearSlotKind",
    "BeastmanGearItem", "UnlockResult",
    "BeastmanArtifactGear",
]
