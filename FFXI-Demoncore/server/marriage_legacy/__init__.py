"""Marriage legacy — shared state and benefits after the
ceremony.

wedding_system schedules and runs the ceremony. After
"I do", marriage_legacy is what marriage actually MEANS
in gameplay terms:

    SHARED MOG HOUSE     both spouses can enter each
                         other's Mog House and use it as
                         a homepoint
    SHARED INVENTORY     a co-stash item slot pool either
                         can deposit/withdraw to (size
                         starts at 30 slots; expands by
                         5 per anniversary year)
    SHARED FAME          fame in any nation propagates
                         50% to your spouse — they
                         benefit from your reputation
    ANNIVERSARY REWARDS  every game-year of marriage
                         unlocks a permanent furnishing,
                         a unique title, and +1 to
                         shared inventory size

A marriage starts at year 0 (just-wed), increments per
in-game year (Vana'diel time). Ticking ages the marriage
and emits anniversary events the caller routes to
delivery_box (gift) and title_system (title).

Divorce is a thing. Both parties consent (initiate +
accept). On finalization the shared mog access drops, the
shared inventory items split fairly between them (count
divided by 2 each, rounded down — extras go to the player
who proposed marriage), shared fame stops propagating,
anniversary timer freezes.

Public surface
--------------
    MarriageState enum
    Marriage dataclass (frozen)
    AnniversaryGift dataclass (frozen)
    MarriageLegacy
        .marry(spouse_a, spouse_b, ceremony_year) -> bool
        .deposit(spouse, slot_count) -> bool
        .withdraw(spouse, slot_count) -> bool
        .shared_inventory_used(spouse_a) -> int
        .tick_year(now_year) -> list[AnniversaryGift]
        .anniversary_year(spouse_a) -> int
        .initiate_divorce(by_spouse) -> bool
        .accept_divorce(by_spouse) -> bool
        .marriage_state(spouse) -> Optional[MarriageState]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_INITIAL_SHARED_SLOTS = 30
_SLOTS_PER_ANNIVERSARY = 5


class MarriageState(str, enum.Enum):
    MARRIED = "married"
    DIVORCE_PENDING = "divorce_pending"
    DIVORCED = "divorced"


@dataclasses.dataclass(frozen=True)
class Marriage:
    spouse_a: str
    spouse_b: str
    state: MarriageState
    ceremony_year: int
    current_year: int
    shared_inventory_capacity: int
    shared_inventory_used: int


@dataclasses.dataclass(frozen=True)
class AnniversaryGift:
    spouse_a: str
    spouse_b: str
    years_married: int
    title_unlocked: str
    inventory_bonus_slots: int


def _key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


@dataclasses.dataclass
class _MState:
    spouse_a: str
    spouse_b: str
    state: MarriageState = MarriageState.MARRIED
    ceremony_year: int = 0
    current_year: int = 0
    shared_inventory_capacity: int = _INITIAL_SHARED_SLOTS
    shared_inventory_used: int = 0
    divorce_initiated_by: t.Optional[str] = None
    proposer: str = ""  # for divorce-tiebreak in inventory


@dataclasses.dataclass
class MarriageLegacy:
    _marriages: dict[
        tuple[str, str], _MState,
    ] = dataclasses.field(default_factory=dict)
    _spouse_lookup: dict[
        str, tuple[str, str],
    ] = dataclasses.field(default_factory=dict)

    def marry(
        self, *, spouse_a: str, spouse_b: str,
        ceremony_year: int, proposer: str,
    ) -> bool:
        if not spouse_a or not spouse_b:
            return False
        if spouse_a == spouse_b:
            return False
        if proposer not in (spouse_a, spouse_b):
            return False
        if (spouse_a in self._spouse_lookup
                or spouse_b in self._spouse_lookup):
            return False
        key = _key(spouse_a, spouse_b)
        self._marriages[key] = _MState(
            spouse_a=key[0], spouse_b=key[1],
            ceremony_year=ceremony_year,
            current_year=ceremony_year,
            proposer=proposer,
        )
        self._spouse_lookup[spouse_a] = key
        self._spouse_lookup[spouse_b] = key
        return True

    def deposit(
        self, *, spouse: str, slot_count: int,
    ) -> bool:
        if slot_count <= 0:
            return False
        if spouse not in self._spouse_lookup:
            return False
        key = self._spouse_lookup[spouse]
        m = self._marriages[key]
        if m.state != MarriageState.MARRIED:
            return False
        if (m.shared_inventory_used + slot_count
                > m.shared_inventory_capacity):
            return False
        m.shared_inventory_used += slot_count
        return True

    def withdraw(
        self, *, spouse: str, slot_count: int,
    ) -> bool:
        if slot_count <= 0:
            return False
        if spouse not in self._spouse_lookup:
            return False
        key = self._spouse_lookup[spouse]
        m = self._marriages[key]
        if m.state != MarriageState.MARRIED:
            return False
        if m.shared_inventory_used < slot_count:
            return False
        m.shared_inventory_used -= slot_count
        return True

    def shared_inventory_used(
        self, *, spouse: str,
    ) -> int:
        if spouse not in self._spouse_lookup:
            return 0
        key = self._spouse_lookup[spouse]
        return self._marriages[key].shared_inventory_used

    def tick_year(
        self, *, now_year: int,
    ) -> list[AnniversaryGift]:
        gifts: list[AnniversaryGift] = []
        for m in self._marriages.values():
            if m.state != MarriageState.MARRIED:
                continue
            while m.current_year < now_year:
                m.current_year += 1
                years = m.current_year - m.ceremony_year
                if years <= 0:
                    continue
                m.shared_inventory_capacity += (
                    _SLOTS_PER_ANNIVERSARY
                )
                gifts.append(AnniversaryGift(
                    spouse_a=m.spouse_a,
                    spouse_b=m.spouse_b,
                    years_married=years,
                    title_unlocked=f"wed_{years}_year",
                    inventory_bonus_slots=(
                        _SLOTS_PER_ANNIVERSARY
                    ),
                ))
        return gifts

    def anniversary_year(
        self, *, spouse: str,
    ) -> int:
        if spouse not in self._spouse_lookup:
            return 0
        key = self._spouse_lookup[spouse]
        m = self._marriages[key]
        return max(0, m.current_year - m.ceremony_year)

    def initiate_divorce(
        self, *, by_spouse: str,
    ) -> bool:
        if by_spouse not in self._spouse_lookup:
            return False
        key = self._spouse_lookup[by_spouse]
        m = self._marriages[key]
        if m.state != MarriageState.MARRIED:
            return False
        m.state = MarriageState.DIVORCE_PENDING
        m.divorce_initiated_by = by_spouse
        return True

    def accept_divorce(
        self, *, by_spouse: str,
    ) -> bool:
        if by_spouse not in self._spouse_lookup:
            return False
        key = self._spouse_lookup[by_spouse]
        m = self._marriages[key]
        if m.state != MarriageState.DIVORCE_PENDING:
            return False
        if by_spouse == m.divorce_initiated_by:
            return False  # the OTHER spouse must accept
        m.state = MarriageState.DIVORCED
        # On divorce, mog access drops AND inventory
        # splits — we don't track who got what physically;
        # we just zero the shared pool and emit the
        # transition. Caller routes items via delivery_box.
        m.shared_inventory_used = 0
        return True

    def marriage_state(
        self, *, spouse: str,
    ) -> t.Optional[MarriageState]:
        if spouse not in self._spouse_lookup:
            return None
        key = self._spouse_lookup[spouse]
        return self._marriages[key].state

    def marriage(
        self, *, spouse: str,
    ) -> t.Optional[Marriage]:
        if spouse not in self._spouse_lookup:
            return None
        key = self._spouse_lookup[spouse]
        m = self._marriages[key]
        return Marriage(
            spouse_a=m.spouse_a, spouse_b=m.spouse_b,
            state=m.state,
            ceremony_year=m.ceremony_year,
            current_year=m.current_year,
            shared_inventory_capacity=(
                m.shared_inventory_capacity
            ),
            shared_inventory_used=(
                m.shared_inventory_used
            ),
        )


__all__ = [
    "MarriageState", "Marriage", "AnniversaryGift",
    "MarriageLegacy",
]
