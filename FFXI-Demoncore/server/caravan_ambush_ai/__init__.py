"""Caravan ambush AI — bandits intercept trade caravans.

Caravans (trade_routes) move goods between settlements. The
roads are not safe: bandit bands and beastmen ambushes spawn
at intervals along high-risk routes. Players who happen to
travel near the ambush can INTERVENE — drive off the attackers
to save the caravan, or stand by and let it fall.

When a caravan is lost, the merchant guild files an INSURANCE
CLAIM the player can pick up from the relevant NPC; the route
risk goes UP for the next few weeks (game-time).

Public surface
--------------
    AmbushKind enum
    OutcomeKind enum
    CaravanAmbush dataclass
    InterventionResult dataclass
    CaravanAmbushAI
        .schedule_ambush(route_id, kind, severity, ambushers,
                         caravan_strength, fires_at_seconds)
        .intervene(ambush_id, intervener_id, intervener_strength)
        .resolve_unattended(ambush_id) — if no one shows
        .active_ambushes_on_route(route_id)
        .tick(now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Defaults.
DEFAULT_INTERVENTION_WINDOW = 60.0    # seconds to intervene


class AmbushKind(str, enum.Enum):
    BANDITS = "bandits"
    BEASTMEN = "beastmen"
    DEMON_RAIDERS = "demon_raiders"
    DRAGON_HARASSMENT = "dragon_harassment"
    PIRATES = "pirates"


class AmbushSeverity(str, enum.Enum):
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"
    CATASTROPHIC = "catastrophic"


class OutcomeKind(str, enum.Enum):
    PENDING = "pending"
    DRIVEN_OFF = "driven_off"          # player won
    CARAVAN_LOST = "caravan_lost"       # bandits won
    PLAYER_DEFEATED = "player_defeated"


_SEVERITY_BANDIT_STRENGTH: dict[AmbushSeverity, int] = {
    AmbushSeverity.LIGHT: 200,
    AmbushSeverity.MODERATE: 500,
    AmbushSeverity.HEAVY: 1200,
    AmbushSeverity.CATASTROPHIC: 3000,
}


@dataclasses.dataclass
class CaravanAmbush:
    ambush_id: str
    route_id: str
    kind: AmbushKind
    severity: AmbushSeverity
    ambusher_strength: int
    caravan_strength: int
    scheduled_at_seconds: float
    fires_at_seconds: float
    expires_at_seconds: float
    outcome: OutcomeKind = OutcomeKind.PENDING
    intervener_id: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class InterventionResult:
    accepted: bool
    outcome: OutcomeKind
    ambush_id: str
    reward_payout_gil: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class InsuranceClaim:
    claim_id: str
    route_id: str
    ambush_id: str
    payout_gil: int
    issued_at_seconds: float


@dataclasses.dataclass
class CaravanAmbushAI:
    intervention_window_seconds: float = (
        DEFAULT_INTERVENTION_WINDOW
    )
    _ambushes: dict[str, CaravanAmbush] = dataclasses.field(
        default_factory=dict,
    )
    _claims: dict[str, InsuranceClaim] = dataclasses.field(
        default_factory=dict,
    )
    _route_risk_pct: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 0

    def schedule_ambush(
        self, *, route_id: str,
        kind: AmbushKind,
        severity: AmbushSeverity,
        caravan_strength: int,
        scheduled_at_seconds: float = 0.0,
        fires_in_seconds: float = 30.0,
        ambusher_strength: t.Optional[int] = None,
    ) -> t.Optional[CaravanAmbush]:
        if not route_id:
            return None
        if caravan_strength <= 0:
            return None
        if ambusher_strength is None:
            ambusher_strength = _SEVERITY_BANDIT_STRENGTH[
                severity
            ]
        aid = f"ambush_{self._next_id}"
        self._next_id += 1
        ambush = CaravanAmbush(
            ambush_id=aid, route_id=route_id,
            kind=kind, severity=severity,
            ambusher_strength=ambusher_strength,
            caravan_strength=caravan_strength,
            scheduled_at_seconds=scheduled_at_seconds,
            fires_at_seconds=(
                scheduled_at_seconds + fires_in_seconds
            ),
            expires_at_seconds=(
                scheduled_at_seconds
                + fires_in_seconds
                + self.intervention_window_seconds
            ),
        )
        self._ambushes[aid] = ambush
        return ambush

    def intervene(
        self, *, ambush_id: str,
        intervener_id: str,
        intervener_strength: int,
        now_seconds: float = 0.0,
    ) -> InterventionResult:
        ambush = self._ambushes.get(ambush_id)
        if ambush is None:
            return InterventionResult(
                accepted=False,
                outcome=OutcomeKind.PENDING,
                ambush_id=ambush_id,
                reason="no such ambush",
            )
        if ambush.outcome != OutcomeKind.PENDING:
            return InterventionResult(
                accepted=False,
                outcome=ambush.outcome,
                ambush_id=ambush_id,
                reason="already resolved",
            )
        if now_seconds < ambush.fires_at_seconds:
            return InterventionResult(
                accepted=False,
                outcome=OutcomeKind.PENDING,
                ambush_id=ambush_id,
                reason="ambush not fired yet",
            )
        if now_seconds > ambush.expires_at_seconds:
            return InterventionResult(
                accepted=False,
                outcome=OutcomeKind.PENDING,
                ambush_id=ambush_id,
                reason="window expired",
            )
        # Player + caravan vs ambushers
        defender = intervener_strength + ambush.caravan_strength
        if defender >= ambush.ambusher_strength:
            outcome = OutcomeKind.DRIVEN_OFF
            payout = max(
                100,
                ambush.ambusher_strength // 5,
            )
        else:
            outcome = OutcomeKind.PLAYER_DEFEATED
            payout = 0
        ambush.outcome = outcome
        ambush.intervener_id = intervener_id
        if outcome == OutcomeKind.DRIVEN_OFF:
            # Risk decreases on a successful save
            self._adjust_route_risk(
                route_id=ambush.route_id, delta_pct=-3,
            )
        else:
            self._adjust_route_risk(
                route_id=ambush.route_id, delta_pct=+5,
            )
        return InterventionResult(
            accepted=True,
            outcome=outcome,
            ambush_id=ambush_id,
            reward_payout_gil=payout,
        )

    def resolve_unattended(
        self, *, ambush_id: str,
        now_seconds: float = 0.0,
    ) -> t.Optional[OutcomeKind]:
        ambush = self._ambushes.get(ambush_id)
        if ambush is None:
            return None
        if ambush.outcome != OutcomeKind.PENDING:
            return None
        # Caravan vs ambusher alone
        if ambush.caravan_strength >= ambush.ambusher_strength:
            ambush.outcome = OutcomeKind.DRIVEN_OFF
        else:
            ambush.outcome = OutcomeKind.CARAVAN_LOST
            self._issue_claim(ambush, now_seconds)
            self._adjust_route_risk(
                route_id=ambush.route_id, delta_pct=+10,
            )
        return ambush.outcome

    def _issue_claim(
        self, ambush: CaravanAmbush,
        now_seconds: float,
    ) -> None:
        cid = f"claim_{len(self._claims)}"
        payout = ambush.caravan_strength * 2
        self._claims[cid] = InsuranceClaim(
            claim_id=cid, route_id=ambush.route_id,
            ambush_id=ambush.ambush_id,
            payout_gil=payout,
            issued_at_seconds=now_seconds,
        )

    def _adjust_route_risk(
        self, *, route_id: str, delta_pct: int,
    ) -> None:
        cur = self._route_risk_pct.get(route_id, 0)
        self._route_risk_pct[route_id] = max(
            0, min(100, cur + delta_pct),
        )

    def route_risk_pct(self, route_id: str) -> int:
        return self._route_risk_pct.get(route_id, 0)

    def active_ambushes_on_route(
        self, route_id: str,
    ) -> tuple[CaravanAmbush, ...]:
        return tuple(
            a for a in self._ambushes.values()
            if a.route_id == route_id
            and a.outcome == OutcomeKind.PENDING
        )

    def claims_for_route(
        self, route_id: str,
    ) -> tuple[InsuranceClaim, ...]:
        return tuple(
            c for c in self._claims.values()
            if c.route_id == route_id
        )

    def tick(
        self, *, now_seconds: float,
    ) -> tuple[OutcomeKind, ...]:
        out: list[OutcomeKind] = []
        for ambush in list(self._ambushes.values()):
            if ambush.outcome != OutcomeKind.PENDING:
                continue
            if now_seconds < ambush.expires_at_seconds:
                continue
            outcome = self.resolve_unattended(
                ambush_id=ambush.ambush_id,
                now_seconds=now_seconds,
            )
            if outcome is not None:
                out.append(outcome)
        return tuple(out)

    def total_ambushes(self) -> int:
        return len(self._ambushes)

    def total_claims(self) -> int:
        return len(self._claims)


__all__ = [
    "DEFAULT_INTERVENTION_WINDOW",
    "AmbushKind", "AmbushSeverity", "OutcomeKind",
    "CaravanAmbush", "InterventionResult",
    "InsuranceClaim",
    "CaravanAmbushAI",
]
