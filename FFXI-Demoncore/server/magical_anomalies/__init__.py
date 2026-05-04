"""Magical anomalies — randomly appearing zone phenomena.

The world is not stable. Once in a while, an ANOMALY ruptures
into a zone — a void rift, an aurora storm, a moonshadow well,
a fey curtain, a dimensional fissure. Anomalies are open for a
limited window. Players who arrive before the window closes can
PARTICIPATE — investigate, fight what spills out, harvest the
phenomenon. Tiered rewards.

Anomalies don't repeat: each one is unique by anomaly_id and
auto-closes when its window ends. Most fade on their own;
a few CASCADE into something larger if not addressed.

Public surface
--------------
    AnomalyKind enum
    AnomalyTier enum
    Anomaly dataclass
    ParticipationResult dataclass
    MagicalAnomalies
        .spawn_anomaly(zone_id, kind, tier, ...)
        .participate(anomaly_id, player_id, contribution)
        .resolve(anomaly_id, now_seconds)
        .active_in_zone(zone_id) -> tuple[Anomaly]
        .tick(now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default open windows (seconds).
_TIER_DEFAULT_WINDOW = {
    "lesser": 600.0,
    "moderate": 1200.0,
    "greater": 1800.0,
    "world_shaking": 3600.0,
}


class AnomalyKind(str, enum.Enum):
    VOID_RIFT = "void_rift"
    AURORA_STORM = "aurora_storm"
    MOONSHADOW_WELL = "moonshadow_well"
    FEY_CURTAIN = "fey_curtain"
    DIMENSIONAL_FISSURE = "dimensional_fissure"
    GHOSTLIGHT_BLOOM = "ghostlight_bloom"
    PRIMAL_SURGE = "primal_surge"


class AnomalyTier(str, enum.Enum):
    LESSER = "lesser"
    MODERATE = "moderate"
    GREATER = "greater"
    WORLD_SHAKING = "world_shaking"


class AnomalyStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    EXPIRED = "expired"
    CASCADED = "cascaded"


_TIER_REWARD_BASE: dict[AnomalyTier, int] = {
    AnomalyTier.LESSER: 100,
    AnomalyTier.MODERATE: 500,
    AnomalyTier.GREATER: 2500,
    AnomalyTier.WORLD_SHAKING: 12000,
}


@dataclasses.dataclass
class Anomaly:
    anomaly_id: str
    zone_id: str
    kind: AnomalyKind
    tier: AnomalyTier
    spawned_at_seconds: float
    closes_at_seconds: float
    status: AnomalyStatus = AnomalyStatus.OPEN
    cascades_into: t.Optional[AnomalyTier] = None
    contributors: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )
    total_contribution: int = 0


@dataclasses.dataclass(frozen=True)
class ParticipationResult:
    accepted: bool
    anomaly_id: str
    player_id: str
    contribution_added: int = 0
    cumulative_contribution: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ResolutionPayout:
    anomaly_id: str
    status: AnomalyStatus
    payouts: tuple[tuple[str, int], ...]
    total_pool: int


@dataclasses.dataclass
class MagicalAnomalies:
    _anomalies: dict[str, Anomaly] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 0

    def spawn_anomaly(
        self, *, zone_id: str,
        kind: AnomalyKind,
        tier: AnomalyTier,
        spawned_at_seconds: float = 0.0,
        window_seconds: t.Optional[float] = None,
        cascades_into: t.Optional[AnomalyTier] = None,
    ) -> t.Optional[Anomaly]:
        if not zone_id:
            return None
        win = (
            window_seconds
            if window_seconds is not None
            else _TIER_DEFAULT_WINDOW[tier.value]
        )
        aid = f"anomaly_{self._next_id}"
        self._next_id += 1
        a = Anomaly(
            anomaly_id=aid, zone_id=zone_id,
            kind=kind, tier=tier,
            spawned_at_seconds=spawned_at_seconds,
            closes_at_seconds=(
                spawned_at_seconds + win
            ),
            cascades_into=cascades_into,
        )
        self._anomalies[aid] = a
        return a

    def get(self, anomaly_id: str) -> t.Optional[Anomaly]:
        return self._anomalies.get(anomaly_id)

    def participate(
        self, *, anomaly_id: str, player_id: str,
        contribution: int = 1,
        now_seconds: float = 0.0,
    ) -> ParticipationResult:
        a = self._anomalies.get(anomaly_id)
        if a is None:
            return ParticipationResult(
                False, anomaly_id=anomaly_id,
                player_id=player_id,
                reason="no such anomaly",
            )
        if a.status != AnomalyStatus.OPEN:
            return ParticipationResult(
                False, anomaly_id=anomaly_id,
                player_id=player_id,
                reason="anomaly closed",
            )
        if now_seconds > a.closes_at_seconds:
            return ParticipationResult(
                False, anomaly_id=anomaly_id,
                player_id=player_id,
                reason="window expired",
            )
        if contribution <= 0:
            return ParticipationResult(
                False, anomaly_id=anomaly_id,
                player_id=player_id,
                reason="non-positive contribution",
            )
        a.contributors[player_id] = (
            a.contributors.get(player_id, 0) + contribution
        )
        a.total_contribution += contribution
        return ParticipationResult(
            accepted=True, anomaly_id=anomaly_id,
            player_id=player_id,
            contribution_added=contribution,
            cumulative_contribution=a.contributors[player_id],
        )

    def resolve(
        self, *, anomaly_id: str,
        now_seconds: float = 0.0,
    ) -> t.Optional[ResolutionPayout]:
        a = self._anomalies.get(anomaly_id)
        if a is None or a.status != AnomalyStatus.OPEN:
            return None
        a.status = AnomalyStatus.RESOLVED
        pool = _TIER_REWARD_BASE[a.tier]
        payouts: list[tuple[str, int]] = []
        if a.total_contribution <= 0 or not a.contributors:
            return ResolutionPayout(
                anomaly_id=anomaly_id,
                status=a.status,
                payouts=(),
                total_pool=0,
            )
        for pid, c in a.contributors.items():
            share = pool * c // a.total_contribution
            payouts.append((pid, share))
        # Deterministic order
        payouts.sort(
            key=lambda t: (-t[1], t[0]),
        )
        return ResolutionPayout(
            anomaly_id=anomaly_id,
            status=a.status,
            payouts=tuple(payouts),
            total_pool=pool,
        )

    def tick(
        self, *, now_seconds: float,
    ) -> tuple[str, ...]:
        """Auto-close anomalies whose window has lapsed.
        Returns anomaly_ids that flipped status this tick."""
        flipped: list[str] = []
        for aid, a in list(self._anomalies.items()):
            if a.status != AnomalyStatus.OPEN:
                continue
            if now_seconds < a.closes_at_seconds:
                continue
            # If unresolved AND has a cascade target, cascade
            if (
                not a.contributors
                and a.cascades_into is not None
            ):
                a.status = AnomalyStatus.CASCADED
                # Spawn the cascade child
                self.spawn_anomaly(
                    zone_id=a.zone_id, kind=a.kind,
                    tier=a.cascades_into,
                    spawned_at_seconds=now_seconds,
                )
            else:
                a.status = AnomalyStatus.EXPIRED
            flipped.append(aid)
        return tuple(flipped)

    def active_in_zone(
        self, zone_id: str,
    ) -> tuple[Anomaly, ...]:
        return tuple(
            a for a in self._anomalies.values()
            if a.zone_id == zone_id
            and a.status == AnomalyStatus.OPEN
        )

    def total_anomalies(self) -> int:
        return len(self._anomalies)


__all__ = [
    "AnomalyKind", "AnomalyTier", "AnomalyStatus",
    "Anomaly",
    "ParticipationResult", "ResolutionPayout",
    "MagicalAnomalies",
]
