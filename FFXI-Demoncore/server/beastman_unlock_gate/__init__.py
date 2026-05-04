"""Beastman unlock gate — beastman races require lategame proof.

A player CANNOT roll a fresh beastman character. The choice
unlocks per-account once the player has, on a hume/elvaan/
mithra/taru character:

* COMPLETED every expansion MSQ that exists at the time of
  shipping (registered as REQUIRED_EXPANSIONS — base + all
  expansions through Demoncore).
* COMPLETED the three-stage Shadowlands endgame quest chain
  (handled in shadowlands_endgame_quests).
* Reached at least one main job to LEVEL_99.

Once those gates clear for an ACCOUNT, the unlock applies to
all characters on that account — they can then create a
beastman character on a new slot.

Public surface
--------------
    GateRequirement enum
    UnlockState dataclass
    UnlockCheckResult dataclass
    BeastmanUnlockGate
        .register_required_expansion(expansion_id)
        .register_required_endgame_quest(quest_id)
        .mark_account_canon_msq_complete(account_id, expansion_id)
        .mark_account_endgame_quest_complete(account_id, quest_id)
        .mark_account_level_99(account_id)
        .is_unlocked(account_id) -> UnlockCheckResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class GateRequirement(str, enum.Enum):
    EXPANSION_MSQ = "expansion_msq"
    ENDGAME_QUEST = "endgame_quest"
    LEVEL_99 = "level_99"


@dataclasses.dataclass
class UnlockState:
    account_id: str
    completed_expansion_msqs: set[str] = dataclasses.field(
        default_factory=set,
    )
    completed_endgame_quests: set[str] = dataclasses.field(
        default_factory=set,
    )
    has_level_99: bool = False
    unlocked_at_seconds: t.Optional[float] = None


@dataclasses.dataclass(frozen=True)
class UnlockCheckResult:
    unlocked: bool
    account_id: str
    missing_expansion_msqs: tuple[str, ...]
    missing_endgame_quests: tuple[str, ...]
    needs_level_99: bool


@dataclasses.dataclass
class BeastmanUnlockGate:
    _required_expansions: set[str] = dataclasses.field(
        default_factory=set,
    )
    _required_endgame_quests: set[str] = dataclasses.field(
        default_factory=set,
    )
    _states: dict[str, UnlockState] = dataclasses.field(
        default_factory=dict,
    )

    def register_required_expansion(
        self, *, expansion_id: str,
    ) -> bool:
        if not expansion_id:
            return False
        if expansion_id in self._required_expansions:
            return False
        self._required_expansions.add(expansion_id)
        return True

    def register_required_endgame_quest(
        self, *, quest_id: str,
    ) -> bool:
        if not quest_id:
            return False
        if quest_id in self._required_endgame_quests:
            return False
        self._required_endgame_quests.add(quest_id)
        return True

    def _state(self, account_id: str) -> UnlockState:
        st = self._states.get(account_id)
        if st is None:
            st = UnlockState(account_id=account_id)
            self._states[account_id] = st
        return st

    def mark_account_canon_msq_complete(
        self, *, account_id: str, expansion_id: str,
    ) -> bool:
        if not expansion_id:
            return False
        st = self._state(account_id)
        if expansion_id in st.completed_expansion_msqs:
            return False
        st.completed_expansion_msqs.add(expansion_id)
        return True

    def mark_account_endgame_quest_complete(
        self, *, account_id: str, quest_id: str,
    ) -> bool:
        if not quest_id:
            return False
        st = self._state(account_id)
        if quest_id in st.completed_endgame_quests:
            return False
        st.completed_endgame_quests.add(quest_id)
        return True

    def mark_account_level_99(
        self, *, account_id: str,
    ) -> bool:
        st = self._state(account_id)
        if st.has_level_99:
            return False
        st.has_level_99 = True
        return True

    def is_unlocked(
        self, *, account_id: str,
        now_seconds: float = 0.0,
    ) -> UnlockCheckResult:
        st = self._state(account_id)
        missing_msqs = tuple(sorted(
            self._required_expansions
            - st.completed_expansion_msqs,
        ))
        missing_quests = tuple(sorted(
            self._required_endgame_quests
            - st.completed_endgame_quests,
        ))
        needs_lvl99 = not st.has_level_99
        unlocked = (
            not missing_msqs
            and not missing_quests
            and not needs_lvl99
        )
        if (
            unlocked
            and st.unlocked_at_seconds is None
        ):
            st.unlocked_at_seconds = now_seconds
        return UnlockCheckResult(
            unlocked=unlocked,
            account_id=account_id,
            missing_expansion_msqs=missing_msqs,
            missing_endgame_quests=missing_quests,
            needs_level_99=needs_lvl99,
        )

    def can_create_beastman_character(
        self, *, account_id: str,
    ) -> bool:
        return self.is_unlocked(
            account_id=account_id,
        ).unlocked

    def total_required_expansions(self) -> int:
        return len(self._required_expansions)

    def total_required_endgame_quests(self) -> int:
        return len(self._required_endgame_quests)

    def total_accounts_tracked(self) -> int:
        return len(self._states)


__all__ = [
    "GateRequirement",
    "UnlockState", "UnlockCheckResult",
    "BeastmanUnlockGate",
]
