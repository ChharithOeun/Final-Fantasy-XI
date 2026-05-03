"""Unity Concord — pick a Unity leader, climb their ranking.

A second progression layer beside Coalitions. Each player picks
one of 11 canonical Unity leaders (each a famous adventurer);
rank up in their chosen Unity by completing Wildcat NM pops and
Records of Eminence objectives. Higher rank = bigger discounts
at the Concord NPC and richer Unity Wildcat NM rewards.

Players can swap Unity leaders, but at a chat-points cost (10k
chat points = 1 swap), preserving rank only on the previous
leader.

Public surface
--------------
    UnityLeader enum (11 canonical)
    UnityRank enum (R1..R10)
    PlayerUnityState
        .pick(leader) / .swap_to(leader, chat_points) -> bool
        .award_points(amount) -> int
        .current_rank() -> UnityRank
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class UnityLeader(str, enum.Enum):
    PIEUJE = "pieuje"          # WHM, Windurst
    AYAME = "ayame"            # SAM, Norg
    INVINCIBLE_SHIELD = "invincible_shield"  # PLD, Sandoria
    TRION = "trion"            # WAR/PLD, Sandoria
    MAAT = "maat"              # MNK, Bastok / Jeuno
    ALDO = "aldo"              # THF, Jeuno
    NAJA = "naja_salaheem"     # COR/RDM, Aht Urhgan
    ZEID = "zeid"              # DRK, Misareaux
    ARK_ANGEL_HM = "ark_angel_hm"  # capstone hero
    LION = "lion"              # NIN, Jeuno
    LEHKO = "lehko_habhoka"    # SCH, Jeuno


SWAP_COST_CHAT_POINTS = 10000
RANK_THRESHOLDS: tuple[int, ...] = (
    0,        # R1 baseline
    1000,     # R2
    3000,     # R3
    7000,     # R4
    14000,    # R5
    25000,    # R6
    40000,    # R7
    60000,    # R8
    85000,    # R9
    120000,   # R10
)


def rank_for_points(points: int) -> int:
    """Return rank index (0-9) for the given Unity points."""
    rank = 0
    for i, threshold in enumerate(RANK_THRESHOLDS):
        if points >= threshold:
            rank = i
    return rank


def points_to_next_rank(points: int) -> t.Optional[int]:
    rank = rank_for_points(points)
    if rank + 1 >= len(RANK_THRESHOLDS):
        return None      # already at cap
    return RANK_THRESHOLDS[rank + 1] - points


@dataclasses.dataclass
class _LeaderProgress:
    points: int = 0
    wildcat_pops_consumed: int = 0


@dataclasses.dataclass(frozen=True)
class SwapResult:
    accepted: bool
    new_leader: t.Optional[UnityLeader] = None
    chat_points_spent: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerUnityState:
    """Per-player Unity progress. Each leader has its own ledger
    so swapping doesn't lose old progress."""
    player_id: str
    current_leader: t.Optional[UnityLeader] = None
    _progress: dict[UnityLeader, _LeaderProgress] = dataclasses.field(
        default_factory=dict,
    )

    def pick(self, *, leader: UnityLeader) -> bool:
        """First-time pick. Cannot be used to swap if already in
        a Unity (use swap_to())."""
        if self.current_leader is not None:
            return False
        self.current_leader = leader
        self._progress.setdefault(leader, _LeaderProgress())
        return True

    def swap_to(
        self, *, leader: UnityLeader, chat_points: int,
    ) -> SwapResult:
        if leader == self.current_leader:
            return SwapResult(False, reason="already in this Unity")
        if chat_points < SWAP_COST_CHAT_POINTS:
            return SwapResult(
                False, reason="insufficient chat points",
            )
        self.current_leader = leader
        self._progress.setdefault(leader, _LeaderProgress())
        return SwapResult(
            True, new_leader=leader,
            chat_points_spent=SWAP_COST_CHAT_POINTS,
        )

    def award_points(self, *, amount: int) -> int:
        if self.current_leader is None or amount <= 0:
            return 0
        prog = self._progress.setdefault(
            self.current_leader, _LeaderProgress(),
        )
        prog.points += amount
        return prog.points

    def current_rank(self) -> int:
        if self.current_leader is None:
            return 0
        return rank_for_points(self.current_leader_points())

    def current_leader_points(self) -> int:
        if self.current_leader is None:
            return 0
        return self._progress.get(
            self.current_leader, _LeaderProgress(),
        ).points

    def leader_points(self, *, leader: UnityLeader) -> int:
        return self._progress.get(leader, _LeaderProgress()).points

    def consume_wildcat_pop(self) -> bool:
        if self.current_leader is None:
            return False
        prog = self._progress.setdefault(
            self.current_leader, _LeaderProgress(),
        )
        prog.wildcat_pops_consumed += 1
        return True

    def total_wildcat_pops(self) -> int:
        if self.current_leader is None:
            return 0
        return self._progress.get(
            self.current_leader, _LeaderProgress(),
        ).wildcat_pops_consumed


__all__ = [
    "SWAP_COST_CHAT_POINTS", "RANK_THRESHOLDS",
    "UnityLeader", "SwapResult",
    "rank_for_points", "points_to_next_rank",
    "PlayerUnityState",
]
