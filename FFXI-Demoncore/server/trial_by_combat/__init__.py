"""Trial by combat — formal 1v1 honor duels with stakes.

Two players step onto the duel platform, each puts something
on the table — gil, gear, a key item, the right to a name —
and one walks away. This is the formal cousin of /duel: it
records, it broadcasts, and it has consequences.

Result + history flow
---------------------
    issue_challenge -> challenge_id (PENDING)
    accept_challenge -> arena seed, status -> SCHEDULED
    decline_challenge -> CANCELLED + small honor knock for
                         declining without cause
    record_outcome   -> WON / LOST / DRAW; stakes transfer;
                        challenge moves to RESOLVED
    forfeit          -> immediate loss; stakes transfer;
                        large honor penalty

Stakes
------
    GIL          a bag of currency
    GEAR_PIECE   a single item (returned on draw)
    KEY_ITEM     a specific KI (transferred only on win)
    NAME_RIGHT   loser must rename for 30 days (recorded)
    HONOR        only honor and reputation move; no items

Public surface
--------------
    StakeKind enum
    DuelStatus enum
    Stake dataclass (frozen)
    DuelChallenge dataclass (mutable)
    TrialByCombatRegistry
        .issue_challenge(challenger, defender, stake_kind,
                         stake_payload, issued_at,
                         expires_at) -> challenge_id
        .accept(challenge_id, accepted_at) -> bool
        .decline(challenge_id, declined_at) -> bool
        .record_outcome(challenge_id, winner, loser,
                        recorded_at, draw=False) -> bool
        .forfeit(challenge_id, forfeit_by, forfeit_at) -> bool
        .get(challenge_id) -> Optional[DuelChallenge]
        .duels_for_player(player_id) -> tuple[...]
        .pending_for(player_id) -> tuple[...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class StakeKind(str, enum.Enum):
    GIL = "gil"
    GEAR_PIECE = "gear_piece"
    KEY_ITEM = "key_item"
    NAME_RIGHT = "name_right"
    HONOR = "honor"


class DuelStatus(str, enum.Enum):
    PENDING = "pending"        # issued, awaiting response
    SCHEDULED = "scheduled"    # accepted, fight pending
    RESOLVED = "resolved"      # outcome recorded
    CANCELLED = "cancelled"    # declined or expired
    FORFEITED = "forfeited"    # one party forfeited


@dataclasses.dataclass(frozen=True)
class Stake:
    kind: StakeKind
    payload: str   # gil amount, item id, ki id, etc., as string
    description: str = ""


@dataclasses.dataclass
class DuelChallenge:
    challenge_id: str
    challenger_id: str
    defender_id: str
    stake: Stake
    issued_at: int
    expires_at: int
    status: DuelStatus = DuelStatus.PENDING
    accepted_at: t.Optional[int] = None
    resolved_at: t.Optional[int] = None
    winner_id: t.Optional[str] = None
    loser_id: t.Optional[str] = None
    is_draw: bool = False


@dataclasses.dataclass
class TrialByCombatRegistry:
    _duels: dict[str, DuelChallenge] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 0
    _by_player: dict[str, list[str]] = dataclasses.field(
        default_factory=dict,
    )

    def issue_challenge(
        self, *, challenger_id: str, defender_id: str,
        stake_kind: StakeKind, stake_payload: str,
        issued_at: int, expires_at: int,
        description: str = "",
    ) -> str:
        if not challenger_id or not defender_id:
            return ""
        if challenger_id == defender_id:
            return ""
        if expires_at <= issued_at:
            return ""
        if not stake_payload and stake_kind != StakeKind.HONOR:
            return ""
        self._next_id += 1
        cid = f"duel_{self._next_id}"
        stake = Stake(
            kind=stake_kind, payload=stake_payload,
            description=description,
        )
        d = DuelChallenge(
            challenge_id=cid,
            challenger_id=challenger_id,
            defender_id=defender_id,
            stake=stake,
            issued_at=issued_at,
            expires_at=expires_at,
        )
        self._duels[cid] = d
        self._by_player.setdefault(challenger_id, []).append(cid)
        self._by_player.setdefault(defender_id, []).append(cid)
        return cid

    def get(
        self, *, challenge_id: str,
    ) -> t.Optional[DuelChallenge]:
        return self._duels.get(challenge_id)

    def accept(
        self, *, challenge_id: str, accepted_at: int,
    ) -> bool:
        d = self._duels.get(challenge_id)
        if d is None:
            return False
        if d.status != DuelStatus.PENDING:
            return False
        if accepted_at > d.expires_at:
            d.status = DuelStatus.CANCELLED
            return False
        d.status = DuelStatus.SCHEDULED
        d.accepted_at = accepted_at
        return True

    def decline(
        self, *, challenge_id: str, declined_at: int,
    ) -> bool:
        d = self._duels.get(challenge_id)
        if d is None:
            return False
        if d.status != DuelStatus.PENDING:
            return False
        d.status = DuelStatus.CANCELLED
        return True

    def record_outcome(
        self, *, challenge_id: str,
        winner_id: t.Optional[str],
        loser_id: t.Optional[str],
        recorded_at: int,
        draw: bool = False,
    ) -> bool:
        d = self._duels.get(challenge_id)
        if d is None:
            return False
        if d.status != DuelStatus.SCHEDULED:
            return False
        if draw:
            d.is_draw = True
        else:
            if winner_id is None or loser_id is None:
                return False
            valid = {d.challenger_id, d.defender_id}
            if winner_id not in valid or loser_id not in valid:
                return False
            if winner_id == loser_id:
                return False
            d.winner_id = winner_id
            d.loser_id = loser_id
        d.status = DuelStatus.RESOLVED
        d.resolved_at = recorded_at
        return True

    def forfeit(
        self, *, challenge_id: str, forfeit_by: str,
        forfeit_at: int,
    ) -> bool:
        d = self._duels.get(challenge_id)
        if d is None:
            return False
        if d.status not in (DuelStatus.PENDING, DuelStatus.SCHEDULED):
            return False
        if forfeit_by not in (d.challenger_id, d.defender_id):
            return False
        d.status = DuelStatus.FORFEITED
        d.loser_id = forfeit_by
        if forfeit_by == d.challenger_id:
            d.winner_id = d.defender_id
        else:
            d.winner_id = d.challenger_id
        d.resolved_at = forfeit_at
        return True

    def duels_for_player(
        self, *, player_id: str,
    ) -> tuple[DuelChallenge, ...]:
        ids = self._by_player.get(player_id, [])
        return tuple(self._duels[i] for i in ids if i in self._duels)

    def pending_for(
        self, *, player_id: str,
    ) -> tuple[DuelChallenge, ...]:
        return tuple(
            d for d in self.duels_for_player(player_id=player_id)
            if d.status == DuelStatus.PENDING
        )

    def total_duels(self) -> int:
        return len(self._duels)


__all__ = [
    "StakeKind", "DuelStatus", "Stake", "DuelChallenge",
    "TrialByCombatRegistry",
]
