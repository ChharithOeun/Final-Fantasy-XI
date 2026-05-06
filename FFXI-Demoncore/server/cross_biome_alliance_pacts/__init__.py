"""Cross-biome alliance pacts — bind crews + LSes + nation military.

Underwater PvP gave us pirate crews. Surface play gave us
linkshells. Surface war gave us nation military forces.
None of those talk to each other. A "pact" lets them
formally ally for a limited window: shared chat, shared
bounty pool, shared loot rights at simultaneous events.

A pact has up to MAX_PARTNERS member organizations of
mixed kinds (crew / linkshell / nation_military). Pacts
are created with an initial AGREEMENT phase requiring
each partner to confirm; once all partners confirm, the
pact ACTIVATES. Either side can DISSOLVE at any time
during ACTIVATED — but a 24-hour cooldown blocks new
pacts between the same partners after dissolution.

Public surface
--------------
    PartnerKind enum
    PactStage enum
    Partner dataclass (frozen)
    AlliancePact dataclass
    CrossBiomeAlliancePacts
        .propose(pact_id, partners, now_seconds)
        .confirm(pact_id, partner_id, now_seconds)
        .dissolve(pact_id, partner_id, now_seconds)
        .stage_of(pact_id) -> PactStage
        .partners_of(pact_id) -> tuple[Partner, ...]
        .is_active(pact_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class PartnerKind(str, enum.Enum):
    CREW = "crew"
    LINKSHELL = "linkshell"
    NATION_MILITARY = "nation_military"


class PactStage(str, enum.Enum):
    PROPOSED = "proposed"
    ACTIVATED = "activated"
    DISSOLVED = "dissolved"


MAX_PARTNERS = 5
DISSOLUTION_COOLDOWN_SECONDS = 24 * 3_600


@dataclasses.dataclass(frozen=True)
class Partner:
    partner_id: str
    kind: PartnerKind


@dataclasses.dataclass
class _PactState:
    pact_id: str
    partners: list[Partner]
    confirmed: set[str] = dataclasses.field(default_factory=set)
    stage: PactStage = PactStage.PROPOSED
    proposed_at: int = 0
    activated_at: t.Optional[int] = None
    dissolved_at: t.Optional[int] = None


@dataclasses.dataclass
class CrossBiomeAlliancePacts:
    _pacts: dict[str, _PactState] = dataclasses.field(default_factory=dict)
    # frozen partner-set -> last dissolution time, for cooldown
    _recent_dissolutions: dict[frozenset[str], int] = dataclasses.field(
        default_factory=dict,
    )

    def propose(
        self, *, pact_id: str,
        partners: t.Iterable[Partner],
        now_seconds: int,
    ) -> bool:
        if not pact_id or pact_id in self._pacts:
            return False
        partner_list = list(partners)
        if len(partner_list) < 2 or len(partner_list) > MAX_PARTNERS:
            return False
        ids = [p.partner_id for p in partner_list]
        if len(set(ids)) != len(ids):
            return False  # duplicates
        if any(not p.partner_id for p in partner_list):
            return False
        # cooldown check
        sig = frozenset(ids)
        last = self._recent_dissolutions.get(sig)
        if (
            last is not None
            and (now_seconds - last) < DISSOLUTION_COOLDOWN_SECONDS
        ):
            return False
        self._pacts[pact_id] = _PactState(
            pact_id=pact_id,
            partners=partner_list,
            proposed_at=now_seconds,
        )
        return True

    def confirm(
        self, *, pact_id: str, partner_id: str,
        now_seconds: int,
    ) -> bool:
        p = self._pacts.get(pact_id)
        if p is None or p.stage != PactStage.PROPOSED:
            return False
        ids = {x.partner_id for x in p.partners}
        if partner_id not in ids:
            return False
        p.confirmed.add(partner_id)
        if p.confirmed == ids:
            p.stage = PactStage.ACTIVATED
            p.activated_at = now_seconds
        return True

    def dissolve(
        self, *, pact_id: str, partner_id: str,
        now_seconds: int,
    ) -> bool:
        p = self._pacts.get(pact_id)
        if p is None or p.stage != PactStage.ACTIVATED:
            return False
        ids = {x.partner_id for x in p.partners}
        if partner_id not in ids:
            return False
        p.stage = PactStage.DISSOLVED
        p.dissolved_at = now_seconds
        sig = frozenset(ids)
        self._recent_dissolutions[sig] = now_seconds
        return True

    def stage_of(self, *, pact_id: str) -> PactStage:
        p = self._pacts.get(pact_id)
        if p is None:
            return PactStage.DISSOLVED
        return p.stage

    def partners_of(
        self, *, pact_id: str,
    ) -> tuple[Partner, ...]:
        p = self._pacts.get(pact_id)
        return tuple(p.partners) if p else ()

    def is_active(self, *, pact_id: str) -> bool:
        p = self._pacts.get(pact_id)
        return bool(p and p.stage == PactStage.ACTIVATED)


__all__ = [
    "PartnerKind", "PactStage", "Partner",
    "CrossBiomeAlliancePacts",
    "MAX_PARTNERS", "DISSOLUTION_COOLDOWN_SECONDS",
]
