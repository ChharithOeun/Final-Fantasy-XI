"""AI diplomacy — inter-faction peace talks & treaties.

Faction AIs negotiate truces, sign treaties, and break them
under pressure. A treaty is a mutual contract: cease aggression,
honor trade, share intelligence, return prisoners. Each treaty
has a CLAUSE list and an EXPIRY. Breaking a clause raises a
violation — three violations and the treaty collapses, faction
relations crash, and everyone in reputation_cascade feels it.

Distinct from beastmen_factions (that's the per-faction AI
brain) and reputation_cascade (player-vs-faction). Diplomacy is
faction-vs-faction.

Public surface
--------------
    ClauseKind enum
    TreatyStatus enum
    TreatyClause dataclass
    Treaty dataclass
    TreatyProposalResult dataclass
    AIDiplomacy
        .propose_treaty(faction_a, faction_b, clauses, expires_at)
        .accept_treaty(treaty_id, by_faction)
        .reject_treaty(treaty_id, by_faction)
        .report_violation(treaty_id, violator, clause_kind)
        .active_treaties_for(faction_id)
        .expire_check(now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default thresholds.
DEFAULT_VIOLATION_LIMIT = 3
DEFAULT_TREATY_DURATION_SECONDS = 30 * 24 * 3600  # 30 days


class ClauseKind(str, enum.Enum):
    CEASE_HOSTILITY = "cease_hostility"
    OPEN_TRADE = "open_trade"
    RETURN_PRISONERS = "return_prisoners"
    SHARE_INTEL = "share_intel"
    NON_AGGRESSION_PACT = "non_aggression_pact"
    TRIBUTE_PAYMENT = "tribute_payment"
    JOINT_DEFENSE = "joint_defense"


class TreatyStatus(str, enum.Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    BROKEN = "broken"
    EXPIRED = "expired"


@dataclasses.dataclass(frozen=True)
class TreatyClause:
    kind: ClauseKind
    note: str = ""


@dataclasses.dataclass
class Treaty:
    treaty_id: str
    faction_a: str
    faction_b: str
    clauses: tuple[TreatyClause, ...]
    status: TreatyStatus = TreatyStatus.PROPOSED
    proposed_at_seconds: float = 0.0
    accepted_at_seconds: t.Optional[float] = None
    expires_at_seconds: t.Optional[float] = None
    violations: list[tuple[str, ClauseKind]] = dataclasses.field(
        default_factory=list,
    )
    # Both factions must accept before status flips to ACCEPTED
    accepted_by: set[str] = dataclasses.field(
        default_factory=set,
    )

    def involves(self, faction_id: str) -> bool:
        return faction_id in (self.faction_a, self.faction_b)


@dataclasses.dataclass(frozen=True)
class TreatyProposalResult:
    accepted: bool
    treaty: t.Optional[Treaty] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class TreatyOutcome:
    treaty_id: str
    new_status: TreatyStatus
    note: str = ""


@dataclasses.dataclass
class AIDiplomacy:
    violation_limit: int = DEFAULT_VIOLATION_LIMIT
    default_duration_seconds: int = DEFAULT_TREATY_DURATION_SECONDS
    _treaties: dict[str, Treaty] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 0

    def propose_treaty(
        self, *, faction_a: str, faction_b: str,
        clauses: tuple[TreatyClause, ...],
        proposed_at_seconds: float = 0.0,
        expires_at_seconds: t.Optional[float] = None,
    ) -> TreatyProposalResult:
        if faction_a == faction_b:
            return TreatyProposalResult(
                False, reason="cannot treaty with self",
            )
        if not clauses:
            return TreatyProposalResult(
                False, reason="treaty must have clauses",
            )
        # Check for existing active treaty between the pair
        for t_ in self._treaties.values():
            if (
                t_.status
                in (TreatyStatus.PROPOSED, TreatyStatus.ACCEPTED)
                and t_.involves(faction_a)
                and t_.involves(faction_b)
            ):
                return TreatyProposalResult(
                    False,
                    reason="treaty already in progress",
                )
        tid = f"treaty_{self._next_id}"
        self._next_id += 1
        treaty = Treaty(
            treaty_id=tid,
            faction_a=faction_a, faction_b=faction_b,
            clauses=clauses,
            proposed_at_seconds=proposed_at_seconds,
            expires_at_seconds=(
                expires_at_seconds
                if expires_at_seconds is not None
                else proposed_at_seconds
                + self.default_duration_seconds
            ),
        )
        self._treaties[tid] = treaty
        return TreatyProposalResult(
            accepted=True, treaty=treaty,
        )

    def get(self, treaty_id: str) -> t.Optional[Treaty]:
        return self._treaties.get(treaty_id)

    def accept_treaty(
        self, *, treaty_id: str, by_faction: str,
        now_seconds: float = 0.0,
    ) -> t.Optional[TreatyOutcome]:
        treaty = self._treaties.get(treaty_id)
        if treaty is None:
            return None
        if treaty.status != TreatyStatus.PROPOSED:
            return None
        if not treaty.involves(by_faction):
            return None
        treaty.accepted_by.add(by_faction)
        if (
            treaty.faction_a in treaty.accepted_by
            and treaty.faction_b in treaty.accepted_by
        ):
            treaty.status = TreatyStatus.ACCEPTED
            treaty.accepted_at_seconds = now_seconds
            return TreatyOutcome(
                treaty_id=treaty_id,
                new_status=TreatyStatus.ACCEPTED,
            )
        # Still waiting for the other side
        return TreatyOutcome(
            treaty_id=treaty_id,
            new_status=TreatyStatus.PROPOSED,
            note="awaiting other faction",
        )

    def reject_treaty(
        self, *, treaty_id: str, by_faction: str,
    ) -> t.Optional[TreatyOutcome]:
        treaty = self._treaties.get(treaty_id)
        if treaty is None:
            return None
        if treaty.status != TreatyStatus.PROPOSED:
            return None
        if not treaty.involves(by_faction):
            return None
        treaty.status = TreatyStatus.REJECTED
        return TreatyOutcome(
            treaty_id=treaty_id,
            new_status=TreatyStatus.REJECTED,
        )

    def report_violation(
        self, *, treaty_id: str, violator: str,
        clause_kind: ClauseKind,
    ) -> t.Optional[TreatyOutcome]:
        treaty = self._treaties.get(treaty_id)
        if treaty is None:
            return None
        if treaty.status != TreatyStatus.ACCEPTED:
            return None
        if not treaty.involves(violator):
            return None
        # Confirm the clause is part of the treaty
        if not any(c.kind == clause_kind for c in treaty.clauses):
            return None
        treaty.violations.append((violator, clause_kind))
        if len(treaty.violations) >= self.violation_limit:
            treaty.status = TreatyStatus.BROKEN
            return TreatyOutcome(
                treaty_id=treaty_id,
                new_status=TreatyStatus.BROKEN,
                note="violation limit reached",
            )
        return TreatyOutcome(
            treaty_id=treaty_id,
            new_status=TreatyStatus.ACCEPTED,
            note="violation logged",
        )

    def active_treaties_for(
        self, faction_id: str,
    ) -> tuple[Treaty, ...]:
        return tuple(
            t for t in self._treaties.values()
            if t.status == TreatyStatus.ACCEPTED
            and t.involves(faction_id)
        )

    def expire_check(
        self, *, now_seconds: float,
    ) -> tuple[TreatyOutcome, ...]:
        out: list[TreatyOutcome] = []
        for treaty in self._treaties.values():
            if treaty.status != TreatyStatus.ACCEPTED:
                continue
            if treaty.expires_at_seconds is None:
                continue
            if now_seconds >= treaty.expires_at_seconds:
                treaty.status = TreatyStatus.EXPIRED
                out.append(TreatyOutcome(
                    treaty_id=treaty.treaty_id,
                    new_status=TreatyStatus.EXPIRED,
                ))
        return tuple(out)

    def total_treaties(self) -> int:
        return len(self._treaties)


__all__ = [
    "DEFAULT_VIOLATION_LIMIT",
    "DEFAULT_TREATY_DURATION_SECONDS",
    "ClauseKind", "TreatyStatus",
    "TreatyClause", "Treaty",
    "TreatyProposalResult", "TreatyOutcome",
    "AIDiplomacy",
]
