"""Squadron system — player-led mercenary bands.

A player can RECRUIT AI NPCs into a Squadron they lead. The
squadron has 5 combat slots (TANK / HEALER / DPS_MELEE / DPS_RANGED
/ SUPPORT), each filled by one NPC. Daily wages are paid out of
the captain's treasury; squadron NPCs gain XP + fame alongside
the captain.

Squadrons take CONTRACTS — escort runs, raid commitments, hunts.
A contract has a payout that splits between the captain and
their members (configurable share).

Public surface
--------------
    SquadronSlot enum
    SquadronMember dataclass
    Squadron dataclass
    Contract dataclass
    ContractKind enum
    ContractStatus enum
    SquadronRegistry
        .form_squadron(captain_id, name)
        .recruit(squadron_id, npc_id, slot, daily_wage)
        .dismiss(squadron_id, npc_id)
        .pay_wages(squadron_id, treasury, now)
        .accept_contract(squadron_id, contract)
        .complete_contract(squadron_id, contract_id)
        .squadron_for_player(captain_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


MAX_SQUADRON_SIZE = 5


class SquadronSlot(str, enum.Enum):
    TANK = "tank"
    HEALER = "healer"
    DPS_MELEE = "dps_melee"
    DPS_RANGED = "dps_ranged"
    SUPPORT = "support"


class ContractKind(str, enum.Enum):
    ESCORT = "escort"
    HUNT = "hunt"
    RAID = "raid"
    PATROL = "patrol"
    DEFEND = "defend"


class ContractStatus(str, enum.Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


@dataclasses.dataclass
class SquadronMember:
    npc_id: str
    slot: SquadronSlot
    daily_wage_gil: int = 100
    level: int = 1
    fame: int = 0
    last_paid_at_seconds: float = 0.0


@dataclasses.dataclass
class Squadron:
    squadron_id: str
    captain_id: str
    name: str
    members: list[SquadronMember] = dataclasses.field(
        default_factory=list,
    )
    treasury_gil: int = 0
    formed_at_seconds: float = 0.0
    captain_share_pct: int = 50    # captain's slice of contract pay
    notes: str = ""

    def has_slot_open(self, slot: SquadronSlot) -> bool:
        return all(m.slot != slot for m in self.members)

    def is_full(self) -> bool:
        return len(self.members) >= MAX_SQUADRON_SIZE


@dataclasses.dataclass
class Contract:
    contract_id: str
    kind: ContractKind
    payout_gil: int
    status: ContractStatus = ContractStatus.PROPOSED
    accepted_at_seconds: float = 0.0
    completed_at_seconds: t.Optional[float] = None
    notes: str = ""


@dataclasses.dataclass(frozen=True)
class RecruitResult:
    accepted: bool
    member: t.Optional[SquadronMember] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class WagesResult:
    accepted: bool
    paid_gil: int = 0
    captain_balance_after: int = 0
    underfunded: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ContractResult:
    accepted: bool
    contract: t.Optional[Contract] = None
    captain_payout: int = 0
    member_share_each: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class SquadronRegistry:
    _squadrons: dict[str, Squadron] = dataclasses.field(
        default_factory=dict,
    )
    _captain_to_squadron: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )
    _contracts: dict[str, Contract] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 0

    def form_squadron(
        self, *, captain_id: str, name: str,
        captain_share_pct: int = 50,
        now_seconds: float = 0.0,
    ) -> t.Optional[Squadron]:
        if captain_id in self._captain_to_squadron:
            return None
        if not (0 <= captain_share_pct <= 100):
            return None
        sid = f"sq_{self._next_id}"
        self._next_id += 1
        sq = Squadron(
            squadron_id=sid, captain_id=captain_id,
            name=name,
            captain_share_pct=captain_share_pct,
            formed_at_seconds=now_seconds,
        )
        self._squadrons[sid] = sq
        self._captain_to_squadron[captain_id] = sid
        return sq

    def squadron(
        self, squadron_id: str,
    ) -> t.Optional[Squadron]:
        return self._squadrons.get(squadron_id)

    def squadron_for_player(
        self, captain_id: str,
    ) -> t.Optional[Squadron]:
        sid = self._captain_to_squadron.get(captain_id)
        if sid is None:
            return None
        return self._squadrons.get(sid)

    def recruit(
        self, *, squadron_id: str, npc_id: str,
        slot: SquadronSlot, daily_wage_gil: int = 100,
        level: int = 1,
    ) -> RecruitResult:
        sq = self._squadrons.get(squadron_id)
        if sq is None:
            return RecruitResult(
                False, reason="no such squadron",
            )
        if sq.is_full():
            return RecruitResult(False, reason="squadron full")
        if not sq.has_slot_open(slot):
            return RecruitResult(False, reason="slot taken")
        if any(m.npc_id == npc_id for m in sq.members):
            return RecruitResult(
                False, reason="already in squadron",
            )
        if daily_wage_gil < 0:
            return RecruitResult(
                False, reason="wage cannot be negative",
            )
        member = SquadronMember(
            npc_id=npc_id, slot=slot,
            daily_wage_gil=daily_wage_gil, level=level,
        )
        sq.members.append(member)
        return RecruitResult(True, member=member)

    def dismiss(
        self, *, squadron_id: str, npc_id: str,
    ) -> bool:
        sq = self._squadrons.get(squadron_id)
        if sq is None:
            return False
        before = len(sq.members)
        sq.members = [
            m for m in sq.members if m.npc_id != npc_id
        ]
        return len(sq.members) < before

    def pay_wages(
        self, *, squadron_id: str, now_seconds: float,
    ) -> WagesResult:
        sq = self._squadrons.get(squadron_id)
        if sq is None:
            return WagesResult(
                False, reason="no such squadron",
            )
        total_due = sum(m.daily_wage_gil for m in sq.members)
        if sq.treasury_gil < total_due:
            return WagesResult(
                False, paid_gil=0,
                captain_balance_after=sq.treasury_gil,
                underfunded=True,
                reason="treasury underfunded",
            )
        sq.treasury_gil -= total_due
        for m in sq.members:
            m.last_paid_at_seconds = now_seconds
        return WagesResult(
            accepted=True, paid_gil=total_due,
            captain_balance_after=sq.treasury_gil,
        )

    def deposit(
        self, *, squadron_id: str, gil: int,
    ) -> bool:
        sq = self._squadrons.get(squadron_id)
        if sq is None or gil <= 0:
            return False
        sq.treasury_gil += gil
        return True

    def accept_contract(
        self, *, squadron_id: str,
        contract: Contract,
        now_seconds: float = 0.0,
    ) -> ContractResult:
        sq = self._squadrons.get(squadron_id)
        if sq is None:
            return ContractResult(
                False, reason="no such squadron",
            )
        if not sq.members:
            return ContractResult(
                False,
                reason="squadron has no members",
            )
        contract.status = ContractStatus.ACCEPTED
        contract.accepted_at_seconds = now_seconds
        self._contracts[contract.contract_id] = contract
        return ContractResult(
            accepted=True, contract=contract,
        )

    def complete_contract(
        self, *, squadron_id: str, contract_id: str,
        now_seconds: float = 0.0,
    ) -> ContractResult:
        sq = self._squadrons.get(squadron_id)
        c = self._contracts.get(contract_id)
        if sq is None or c is None:
            return ContractResult(
                False, reason="unknown squadron or contract",
            )
        if c.status != ContractStatus.ACCEPTED:
            return ContractResult(
                False, reason="contract not accepted",
            )
        c.status = ContractStatus.COMPLETED
        c.completed_at_seconds = now_seconds
        captain_cut = c.payout_gil * sq.captain_share_pct // 100
        members_cut = c.payout_gil - captain_cut
        per_member = (
            members_cut // max(1, len(sq.members))
        )
        sq.treasury_gil += captain_cut
        # Members earn fame from completion
        for m in sq.members:
            m.fame += 1
        return ContractResult(
            accepted=True, contract=c,
            captain_payout=captain_cut,
            member_share_each=per_member,
        )

    def fail_contract(
        self, *, contract_id: str,
    ) -> bool:
        c = self._contracts.get(contract_id)
        if c is None or c.status != ContractStatus.ACCEPTED:
            return False
        c.status = ContractStatus.FAILED
        return True

    def total_squadrons(self) -> int:
        return len(self._squadrons)


__all__ = [
    "MAX_SQUADRON_SIZE",
    "SquadronSlot", "ContractKind", "ContractStatus",
    "SquadronMember", "Squadron", "Contract",
    "RecruitResult", "WagesResult", "ContractResult",
    "SquadronRegistry",
]
