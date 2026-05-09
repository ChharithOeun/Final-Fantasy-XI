"""NPC family consequences — kin face fallout from defection.

When Volker defects, his sister still lives in Bastok.
Her social status, employment prospects, and friendships
are now entangled with her brother's choice. She may
be:
    - shunned by neighbors (mood / relationship hit)
    - fired from her job (employment update)
    - placed under surveillance (intel watchlist)
    - exiled by decree (relocation event)
    - or — if she publicly disowns him — protected.

This module manages the FAMILY GRAPH (kin links) and
applies CONSEQUENCE EVENTS to specific kin when their
related officer defects.

Kin link kinds:
    PARENT, CHILD, SIBLING, SPOUSE, COUSIN, MENTOR,
    APPRENTICE, BUSINESS_PARTNER

Consequence severities:
    SHUNNED       social mood penalty
    EMPLOYMENT    job loss
    SURVEILLANCE  watched by intel
    EXILED        forced relocation
    EXECUTED      rare; only in totalitarian regimes
    PROTECTED     publicly disowned, no consequence

Public surface
--------------
    KinKind enum
    Severity enum
    KinLink dataclass (frozen)
    Consequence dataclass (frozen)
    NPCFamilyConsequencesSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class KinKind(str, enum.Enum):
    PARENT = "parent"
    CHILD = "child"
    SIBLING = "sibling"
    SPOUSE = "spouse"
    COUSIN = "cousin"
    MENTOR = "mentor"
    APPRENTICE = "apprentice"
    BUSINESS_PARTNER = "business_partner"


class Severity(str, enum.Enum):
    SHUNNED = "shunned"
    EMPLOYMENT = "employment"
    SURVEILLANCE = "surveillance"
    EXILED = "exiled"
    EXECUTED = "executed"
    PROTECTED = "protected"


@dataclasses.dataclass(frozen=True)
class KinLink:
    npc_id: str
    relative_id: str
    kind: KinKind


@dataclasses.dataclass(frozen=True)
class Consequence:
    consequence_id: str
    relative_id: str
    defector_id: str
    severity: Severity
    note: str
    occurred_day: int
    revoked_day: t.Optional[int]
    revoked_reason: str


@dataclasses.dataclass
class NPCFamilyConsequencesSystem:
    _links: list[KinLink] = dataclasses.field(
        default_factory=list,
    )
    _consequences: dict[str, Consequence] = (
        dataclasses.field(default_factory=dict)
    )
    _next_id: int = 1

    def add_kin(
        self, *, npc_id: str, relative_id: str,
        kind: KinKind,
    ) -> bool:
        if not npc_id or not relative_id:
            return False
        if npc_id == relative_id:
            return False
        # Block exact-duplicate link
        for k in self._links:
            if (k.npc_id == npc_id
                    and k.relative_id == relative_id
                    and k.kind == kind):
                return False
        self._links.append(KinLink(
            npc_id=npc_id, relative_id=relative_id,
            kind=kind,
        ))
        return True

    def kin_of(
        self, *, npc_id: str,
    ) -> list[KinLink]:
        return [
            k for k in self._links
            if k.npc_id == npc_id
        ]

    def apply_consequence(
        self, *, relative_id: str,
        defector_id: str, severity: Severity,
        note: str, occurred_day: int,
    ) -> t.Optional[str]:
        if not relative_id or not defector_id:
            return None
        if not note or occurred_day < 0:
            return None
        cid = f"cons_{self._next_id}"
        self._next_id += 1
        self._consequences[cid] = Consequence(
            consequence_id=cid,
            relative_id=relative_id,
            defector_id=defector_id,
            severity=severity, note=note,
            occurred_day=occurred_day,
            revoked_day=None, revoked_reason="",
        )
        return cid

    def revoke_consequence(
        self, *, consequence_id: str,
        now_day: int, reason: str,
    ) -> bool:
        if consequence_id not in self._consequences:
            return False
        if not reason:
            return False
        c = self._consequences[consequence_id]
        if c.revoked_day is not None:
            return False
        if now_day < c.occurred_day:
            return False
        self._consequences[consequence_id] = (
            dataclasses.replace(
                c, revoked_day=now_day,
                revoked_reason=reason,
            )
        )
        return True

    def consequences_for_relative(
        self, *, relative_id: str,
    ) -> list[Consequence]:
        return [
            c for c in self._consequences.values()
            if c.relative_id == relative_id
        ]

    def active_consequences(
        self, *, relative_id: str,
    ) -> list[Consequence]:
        return [
            c for c in self._consequences.values()
            if (c.relative_id == relative_id
                and c.revoked_day is None)
        ]

    def auto_apply_on_defection(
        self, *, defector_id: str, now_day: int,
        protected_relatives: t.Sequence[str] = (),
    ) -> list[str]:
        """Apply default-severity consequences to all
        kin of defector_id. Default severities by
        kin kind:
            SPOUSE / CHILD / PARENT -> SHUNNED
            SIBLING / COUSIN -> SURVEILLANCE
            MENTOR / APPRENTICE -> EMPLOYMENT
            BUSINESS_PARTNER -> EMPLOYMENT
        Relatives in protected_relatives get the
        PROTECTED severity instead (publicly disowned).
        """
        defaults = {
            KinKind.SPOUSE: Severity.SHUNNED,
            KinKind.CHILD: Severity.SHUNNED,
            KinKind.PARENT: Severity.SHUNNED,
            KinKind.SIBLING: Severity.SURVEILLANCE,
            KinKind.COUSIN: Severity.SURVEILLANCE,
            KinKind.MENTOR: Severity.EMPLOYMENT,
            KinKind.APPRENTICE: Severity.EMPLOYMENT,
            KinKind.BUSINESS_PARTNER: (
                Severity.EMPLOYMENT
            ),
        }
        protected = set(protected_relatives)
        applied: list[str] = []
        for k in self._links:
            if k.npc_id != defector_id:
                continue
            sev = (
                Severity.PROTECTED
                if k.relative_id in protected
                else defaults[k.kind]
            )
            cid = self.apply_consequence(
                relative_id=k.relative_id,
                defector_id=defector_id,
                severity=sev,
                note=f"auto:{k.kind.value}",
                occurred_day=now_day,
            )
            if cid:
                applied.append(cid)
        return applied

    def consequence(
        self, *, consequence_id: str,
    ) -> t.Optional[Consequence]:
        return self._consequences.get(consequence_id)


__all__ = [
    "KinKind", "Severity", "KinLink",
    "Consequence", "NPCFamilyConsequencesSystem",
]
