"""Shark humanoid arena — REEF_SPIRE gladiator pit.

The shark-humanoid sea-warriors of REEF_SPIRE host a
gladiator pit at the heart of their citadel. Surface
visitors may CHALLENGE for honor, gear drops, and Reef
Spire faction reputation. The pit is staffed by named
shark CHAMPIONS who scale up over 5 ranks.

Arena ranks:
  ROUKAN (R5)  - Bull Shark; weakest champion
  KASEN (R4)   - Tiger Shark
  IGUMI (R3)   - Hammerhead chieftain
  KAEDE (R2)   - Mako blademaster
  ZAKARA (R1)  - Megalodon Matriarch (final boss)

You must defeat each rank IN ORDER; the next rank only
unlocks after a clean win at the current rank. A clean win
means defeated within the time limit (5 min) and without
dying. Defeats reset progress to the LAST cleared rank
(not all the way to ROUKAN).

Per-clean-win reward:
  + reef_spire reputation
  + a SHARK_TOOTH currency item used to buy underwater gear

Defeating ZAKARA awards a unique title and unlocks the
SHARK_PACT (a one-time SUMMON_SHARK trust ally — wired in
later).

Public surface
--------------
    Champion enum
    BoutResult dataclass
    SharkArena
        .current_unlock(player_id) -> Champion
        .start_bout(player_id, champion, now_seconds)
        .resolve_bout(player_id, won, time_seconds, no_deaths)
        .has_shark_pact(player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Champion(str, enum.Enum):
    ROUKAN = "roukan"     # R5 (start)
    KASEN = "kasen"       # R4
    IGUMI = "igumi"       # R3
    KAEDE = "kaede"       # R2
    ZAKARA = "zakara"     # R1 (boss)


# ascending difficulty order
_RANK_ORDER: tuple[Champion, ...] = (
    Champion.ROUKAN, Champion.KASEN, Champion.IGUMI,
    Champion.KAEDE, Champion.ZAKARA,
)
_TIME_LIMIT_SECONDS = 5 * 60   # clean win window


def _rank_index(c: Champion) -> int:
    return _RANK_ORDER.index(c)


@dataclasses.dataclass
class _Bout:
    player_id: str
    champion: Champion
    started_at: int


@dataclasses.dataclass(frozen=True)
class BoutResult:
    accepted: bool
    champion: Champion
    clean_win: bool = False
    next_unlock: t.Optional[Champion] = None
    shark_teeth_awarded: int = 0
    reputation_delta: int = 0
    title_awarded: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class SharkArena:
    # last cleared champion per player (None means must start
    # at ROUKAN)
    _cleared: dict[str, Champion] = dataclasses.field(
        default_factory=dict,
    )
    _bouts: dict[str, _Bout] = dataclasses.field(
        default_factory=dict,
    )
    _shark_pact: set[str] = dataclasses.field(default_factory=set)

    def current_unlock(self, *, player_id: str) -> Champion:
        last = self._cleared.get(player_id)
        if last is None:
            return Champion.ROUKAN
        idx = _rank_index(last)
        if idx + 1 >= len(_RANK_ORDER):
            return last  # already cleared the final boss
        return _RANK_ORDER[idx + 1]

    def start_bout(
        self, *, player_id: str,
        champion: Champion,
        now_seconds: int,
    ) -> bool:
        if not player_id:
            return False
        if champion not in _RANK_ORDER:
            return False
        if self.current_unlock(player_id=player_id) != champion:
            return False
        self._bouts[player_id] = _Bout(
            player_id=player_id,
            champion=champion,
            started_at=now_seconds,
        )
        return True

    def resolve_bout(
        self, *, player_id: str,
        won: bool,
        time_seconds: int,
        no_deaths: bool,
    ) -> BoutResult:
        bout = self._bouts.pop(player_id, None)
        if bout is None:
            return BoutResult(
                False, Champion.ROUKAN, reason="no active bout",
            )
        elapsed = time_seconds - bout.started_at
        if not won:
            return BoutResult(
                accepted=True,
                champion=bout.champion,
                clean_win=False,
                reason="defeated",
            )
        clean = (
            no_deaths
            and 0 <= elapsed <= _TIME_LIMIT_SECONDS
        )
        if not clean:
            return BoutResult(
                accepted=True,
                champion=bout.champion,
                clean_win=False,
                reason="timed out or died" if won else "lost",
            )
        # advance unlock
        self._cleared[player_id] = bout.champion
        # rewards scale with rank (5 - index = ranking up)
        rank = len(_RANK_ORDER) - _rank_index(bout.champion)
        teeth = rank * 2
        rep = rank * 10
        is_final = bout.champion == Champion.ZAKARA
        if is_final:
            self._shark_pact.add(player_id)
        next_unlock = self.current_unlock(player_id=player_id)
        return BoutResult(
            accepted=True,
            champion=bout.champion,
            clean_win=True,
            next_unlock=next_unlock,
            shark_teeth_awarded=teeth,
            reputation_delta=rep,
            title_awarded=is_final,
        )

    def has_shark_pact(self, *, player_id: str) -> bool:
        return player_id in self._shark_pact


__all__ = [
    "Champion", "BoutResult", "SharkArena",
]
