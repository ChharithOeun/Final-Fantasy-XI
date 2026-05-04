"""NPC assassin contracts — AI hits-for-hire.

NPCs put out CONTRACTS on other NPCs (rivals, traitors,
witnesses) or on player OUTLAWS. A contract has a target, a
payout in gil, a posting NPC, and an expiry. Independent
assassin NPCs (or willing players) can ACCEPT the contract;
COMPLETION pays out the gil.

Distinct from outlaw_system/wanted_poster (city bounties): this
is the SHADOW market — anyone can post, anyone can accept,
crackdowns can SEIZE active contracts.

Public surface
--------------
    ContractStatus enum
    ContractTargetKind enum
    AssassinContract dataclass
    ContractResult dataclass
    NPCAssassinContracts
        .post_contract(poster_id, target_id, target_kind, payout, expires)
        .accept(contract_id, assassin_id)
        .complete(contract_id, assassin_id) -> payout split
        .cancel(contract_id, by_id)
        .seize(contract_id) — moderator/crackdown
        .open_contracts_against(target_id)
        .tick(now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default poster fee fraction kept by the assassin handler
# (the rest goes to the assassin themselves on completion).
DEFAULT_HANDLER_FEE_PCT = 10
MAX_HANDLER_FEE_PCT = 25
MIN_PAYOUT_GIL = 100


class ContractTargetKind(str, enum.Enum):
    NPC = "npc"
    PLAYER_OUTLAW = "player_outlaw"
    BEASTMAN_LEADER = "beastman_leader"
    NM_INTERLOPER = "nm_interloper"


class ContractStatus(str, enum.Enum):
    OPEN = "open"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    CANCELED = "canceled"
    SEIZED = "seized"
    EXPIRED = "expired"


@dataclasses.dataclass
class AssassinContract:
    contract_id: str
    poster_id: str
    target_id: str
    target_kind: ContractTargetKind
    payout_gil: int
    handler_fee_pct: int
    posted_at_seconds: float
    expires_at_seconds: float
    status: ContractStatus = ContractStatus.OPEN
    assassin_id: t.Optional[str] = None
    accepted_at_seconds: t.Optional[float] = None
    completed_at_seconds: t.Optional[float] = None
    note: str = ""


@dataclasses.dataclass(frozen=True)
class CompletionPayout:
    contract_id: str
    assassin_id: str
    gil_to_assassin: int
    gil_to_handler: int
    total_payout: int


@dataclasses.dataclass
class NPCAssassinContracts:
    default_handler_fee_pct: int = DEFAULT_HANDLER_FEE_PCT
    _contracts: dict[str, AssassinContract] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 0

    def post_contract(
        self, *, poster_id: str, target_id: str,
        target_kind: ContractTargetKind,
        payout_gil: int,
        posted_at_seconds: float = 0.0,
        expires_in_seconds: float = 7 * 24 * 3600.0,
        handler_fee_pct: t.Optional[int] = None,
        note: str = "",
    ) -> t.Optional[AssassinContract]:
        if poster_id == target_id:
            return None
        if payout_gil < MIN_PAYOUT_GIL:
            return None
        if expires_in_seconds <= 0:
            return None
        fee = (
            handler_fee_pct
            if handler_fee_pct is not None
            else self.default_handler_fee_pct
        )
        if not (0 <= fee <= MAX_HANDLER_FEE_PCT):
            return None
        cid = f"contract_{self._next_id}"
        self._next_id += 1
        c = AssassinContract(
            contract_id=cid, poster_id=poster_id,
            target_id=target_id, target_kind=target_kind,
            payout_gil=payout_gil,
            handler_fee_pct=fee,
            posted_at_seconds=posted_at_seconds,
            expires_at_seconds=(
                posted_at_seconds + expires_in_seconds
            ),
            note=note,
        )
        self._contracts[cid] = c
        return c

    def get(self, contract_id: str) -> t.Optional[AssassinContract]:
        return self._contracts.get(contract_id)

    def accept(
        self, *, contract_id: str, assassin_id: str,
        now_seconds: float = 0.0,
    ) -> bool:
        c = self._contracts.get(contract_id)
        if c is None:
            return False
        if c.status != ContractStatus.OPEN:
            return False
        if assassin_id == c.poster_id:
            return False
        if assassin_id == c.target_id:
            return False
        if now_seconds > c.expires_at_seconds:
            return False
        c.status = ContractStatus.ACCEPTED
        c.assassin_id = assassin_id
        c.accepted_at_seconds = now_seconds
        return True

    def complete(
        self, *, contract_id: str, assassin_id: str,
        now_seconds: float = 0.0,
    ) -> t.Optional[CompletionPayout]:
        c = self._contracts.get(contract_id)
        if c is None:
            return None
        if c.status != ContractStatus.ACCEPTED:
            return None
        if c.assassin_id != assassin_id:
            return None
        c.status = ContractStatus.COMPLETED
        c.completed_at_seconds = now_seconds
        handler_cut = (
            c.payout_gil * c.handler_fee_pct // 100
        )
        assassin_cut = c.payout_gil - handler_cut
        return CompletionPayout(
            contract_id=contract_id,
            assassin_id=assassin_id,
            gil_to_assassin=assassin_cut,
            gil_to_handler=handler_cut,
            total_payout=c.payout_gil,
        )

    def cancel(
        self, *, contract_id: str, by_id: str,
    ) -> bool:
        c = self._contracts.get(contract_id)
        if c is None:
            return False
        if c.status not in (
            ContractStatus.OPEN,
            ContractStatus.ACCEPTED,
        ):
            return False
        if by_id != c.poster_id:
            return False
        c.status = ContractStatus.CANCELED
        return True

    def seize(self, *, contract_id: str) -> bool:
        c = self._contracts.get(contract_id)
        if c is None:
            return False
        if c.status in (
            ContractStatus.COMPLETED,
            ContractStatus.SEIZED,
            ContractStatus.CANCELED,
            ContractStatus.EXPIRED,
        ):
            return False
        c.status = ContractStatus.SEIZED
        return True

    def open_contracts_against(
        self, *, target_id: str,
    ) -> tuple[AssassinContract, ...]:
        return tuple(
            c for c in self._contracts.values()
            if c.target_id == target_id
            and c.status == ContractStatus.OPEN
        )

    def tick(
        self, *, now_seconds: float,
    ) -> tuple[str, ...]:
        expired: list[str] = []
        for cid, c in self._contracts.items():
            if c.status != ContractStatus.OPEN:
                continue
            if now_seconds >= c.expires_at_seconds:
                c.status = ContractStatus.EXPIRED
                expired.append(cid)
        return tuple(expired)

    def total_contracts(self) -> int:
        return len(self._contracts)


__all__ = [
    "DEFAULT_HANDLER_FEE_PCT",
    "MAX_HANDLER_FEE_PCT",
    "MIN_PAYOUT_GIL",
    "ContractTargetKind", "ContractStatus",
    "AssassinContract", "CompletionPayout",
    "NPCAssassinContracts",
]
