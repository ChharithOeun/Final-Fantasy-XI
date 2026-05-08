"""Courtship system — pre-marriage ritual.

wedding_system covers the ceremony itself. courtship_system
is the journey BEFORE that. Two players who want their
characters to marry must first formally court — exchange
gifts, complete dates, hit mutual fame thresholds, and
finally make a public proposal.

Stages:
    NONE            no courtship
    DATING          mutual interest declared
    ENGAGED         proposal accepted; wedding pending
    BROKEN_OFF      called off (BROKEN_OFF state lasts
                    30 days then auto-clears so they can
                    try again or move on)

Per-courtship state we track:
    requirements_met:
      gifts_exchanged           >= 7 gifts each direction
      dates_completed           >= 5 dates (special quest)
      mutual_friendship_tier    both at CONFIDANT or higher

A "proposal" can only fire when all requirements are met
AND the courtship is in DATING. It transitions to ENGAGED;
the wedding_system then handles ceremony scheduling.

Either player can break_off() at any time. Breaking off
during ENGAGED has reputational cost — the cost layer
emits an event the honor_reputation system reads.

Public surface
--------------
    Stage enum
    Courtship dataclass (frozen)
    CourtshipSystem
        .declare_dating(a, b) -> bool
        .record_gift(from_player, to_player) -> bool
        .record_date(a, b) -> bool
        .set_mutual_confidant(a, b) -> bool
        .propose(proposer, accepter) -> bool
        .break_off(by_player, other) -> bool
        .stage(a, b) -> Optional[Stage]
        .progress(a, b) -> Optional[Courtship]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_GIFTS_REQUIRED_EACH_WAY = 7
_DATES_REQUIRED = 5


class Stage(str, enum.Enum):
    NONE = "none"
    DATING = "dating"
    ENGAGED = "engaged"
    BROKEN_OFF = "broken_off"


@dataclasses.dataclass(frozen=True)
class Courtship:
    player_a: str
    player_b: str
    stage: Stage
    gifts_a_to_b: int
    gifts_b_to_a: int
    dates_completed: int
    mutual_confidant: bool


def _key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


@dataclasses.dataclass
class _State:
    stage: Stage = Stage.DATING
    gifts_a_to_b: int = 0
    gifts_b_to_a: int = 0
    dates_completed: int = 0
    mutual_confidant: bool = False


@dataclasses.dataclass
class CourtshipSystem:
    _states: dict[
        tuple[str, str], _State,
    ] = dataclasses.field(default_factory=dict)

    def declare_dating(
        self, *, player_a: str, player_b: str,
    ) -> bool:
        if not player_a or not player_b:
            return False
        if player_a == player_b:
            return False
        key = _key(player_a, player_b)
        if key in self._states:
            cur = self._states[key].stage
            # Allow re-dating from BROKEN_OFF
            if cur == Stage.BROKEN_OFF:
                self._states[key] = _State()
                return True
            return False
        self._states[key] = _State()
        return True

    def record_gift(
        self, *, from_player: str, to_player: str,
    ) -> bool:
        if not from_player or not to_player:
            return False
        if from_player == to_player:
            return False
        key = _key(from_player, to_player)
        if key not in self._states:
            return False
        st = self._states[key]
        if st.stage not in (Stage.DATING, Stage.ENGAGED):
            return False
        # key sorts alphabetically; from -> to direction
        if from_player == key[0]:
            st.gifts_a_to_b += 1
        else:
            st.gifts_b_to_a += 1
        return True

    def record_date(
        self, *, player_a: str, player_b: str,
    ) -> bool:
        if not player_a or not player_b:
            return False
        if player_a == player_b:
            return False
        key = _key(player_a, player_b)
        if key not in self._states:
            return False
        st = self._states[key]
        if st.stage != Stage.DATING:
            return False
        st.dates_completed += 1
        return True

    def set_mutual_confidant(
        self, *, player_a: str, player_b: str,
    ) -> bool:
        if player_a == player_b:
            return False
        key = _key(player_a, player_b)
        if key not in self._states:
            return False
        st = self._states[key]
        if st.mutual_confidant:
            return False
        st.mutual_confidant = True
        return True

    def propose(
        self, *, proposer: str, accepter: str,
    ) -> bool:
        if proposer == accepter:
            return False
        key = _key(proposer, accepter)
        if key not in self._states:
            return False
        st = self._states[key]
        if st.stage != Stage.DATING:
            return False
        if st.gifts_a_to_b < _GIFTS_REQUIRED_EACH_WAY:
            return False
        if st.gifts_b_to_a < _GIFTS_REQUIRED_EACH_WAY:
            return False
        if st.dates_completed < _DATES_REQUIRED:
            return False
        if not st.mutual_confidant:
            return False
        st.stage = Stage.ENGAGED
        return True

    def break_off(
        self, *, by_player: str, other: str,
    ) -> bool:
        if by_player == other:
            return False
        key = _key(by_player, other)
        if key not in self._states:
            return False
        st = self._states[key]
        if st.stage in (Stage.NONE, Stage.BROKEN_OFF):
            return False
        st.stage = Stage.BROKEN_OFF
        return True

    def stage(
        self, *, player_a: str, player_b: str,
    ) -> t.Optional[Stage]:
        key = _key(player_a, player_b)
        if key not in self._states:
            return None
        return self._states[key].stage

    def progress(
        self, *, player_a: str, player_b: str,
    ) -> t.Optional[Courtship]:
        key = _key(player_a, player_b)
        if key not in self._states:
            return None
        st = self._states[key]
        return Courtship(
            player_a=key[0], player_b=key[1],
            stage=st.stage,
            gifts_a_to_b=st.gifts_a_to_b,
            gifts_b_to_a=st.gifts_b_to_a,
            dates_completed=st.dates_completed,
            mutual_confidant=st.mutual_confidant,
        )


__all__ = ["Stage", "Courtship", "CourtshipSystem"]
