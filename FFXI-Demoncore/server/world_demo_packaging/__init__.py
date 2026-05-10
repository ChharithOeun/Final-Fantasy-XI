"""World demo packaging — multi-zone manifest packager.

The previous batch's ``demo_packaging`` shipped one zone at a
time (Bastok Markets). This batch's packager bundles a *path*
through multiple zones and validates that the streaming and
lighting infrastructure is in place for an end-to-end no-load-
screen demo.

Streaming strategies:
    ALL_RESIDENT  — small demo, all zones in memory
    RING_PRELOAD  — known camera path; prefetch the ring ahead
    ON_DEMAND     — open world; stream as the player moves

Predefined demos:
    bastok_to_konschtat_walkthrough  3 zones, RING_PRELOAD
    three_nations_grand_tour         5 zones, ALL_RESIDENT
    full_world_flythrough            ~all zones, ON_DEMAND

Validation cross-checks (dependency-injected so unit tests can
stub them):
    has_zone(zone_id)         — zone exists in zone_atlas
    has_boundary(boundary_id) — boundary exists in zone_handoff
    has_lighting(zone_id)     — lighting profile registered
    platform_budget_mb(p)     — memory budget per platform

Estimated size formula (GB):
    base 4.0 GB per zone
    + 0.5 GB per boundary (overlap region cost)
    multiplied by streaming-strategy factor:
       ALL_RESIDENT 1.0  RING_PRELOAD 0.6  ON_DEMAND 0.3

Public surface
--------------
    StreamingStrategy enum
    TargetPlatform enum
    ValidationStatus enum
    WorldDemoBuildManifest dataclass (frozen)
    WorldValidationReport dataclass (frozen)
    WorldDemoPackager
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class StreamingStrategy(enum.Enum):
    ALL_RESIDENT = "all_resident"
    RING_PRELOAD = "ring_preload"
    ON_DEMAND = "on_demand"


class TargetPlatform(enum.Enum):
    PC_ULTRA = "pc_ultra"
    PC_HIGH = "pc_high"
    PS5 = "ps5"
    XBOX_SERIES_X = "xbox_series_x"
    XBOX_SERIES_S = "xbox_series_s"


class ValidationStatus(enum.Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


_BASE_PER_ZONE_GB = 4.0
_PER_BOUNDARY_GB = 0.5
_STRATEGY_FACTOR: dict[StreamingStrategy, float] = {
    StreamingStrategy.ALL_RESIDENT: 1.0,
    StreamingStrategy.RING_PRELOAD: 0.6,
    StreamingStrategy.ON_DEMAND: 0.3,
}


# Default platform memory budgets (MB). World streaming uses the
# same numbers; we duplicate the table here so this module has
# no upstream dep at import time.
_DEFAULT_PLATFORM_BUDGET_MB: dict[TargetPlatform, int] = {
    TargetPlatform.PC_ULTRA: 24 * 1024,
    TargetPlatform.PC_HIGH: 16 * 1024,
    TargetPlatform.PS5: 12 * 1024,
    TargetPlatform.XBOX_SERIES_X: 12 * 1024,
    TargetPlatform.XBOX_SERIES_S: 8 * 1024,
}


@dataclasses.dataclass(frozen=True)
class WorldDemoBuildManifest:
    manifest_id: str
    name: str
    target_platform: TargetPlatform
    zone_ids: tuple[str, ...]
    entry_zone_id: str
    exit_zone_ids: tuple[str, ...]  # the camera path, in order
    choreography_per_zone: tuple[tuple[str, str], ...]
    boundary_handoffs_required: tuple[str, ...]
    streaming_strategy: StreamingStrategy
    total_estimated_size_gb: float
    validation_status: ValidationStatus
    missing_assets: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class WorldValidationReport:
    manifest_id: str
    status: ValidationStatus
    missing_zones: tuple[str, ...]
    missing_boundaries: tuple[str, ...]
    missing_lighting: tuple[str, ...]
    over_budget: bool
    budget_mb: int
    estimated_mb: int


def _accept_all(_: str) -> bool:
    return True


def _default_budget(p: TargetPlatform) -> int:
    return _DEFAULT_PLATFORM_BUDGET_MB[p]


def _compute_size_gb(
    n_zones: int,
    n_boundaries: int,
    strategy: StreamingStrategy,
) -> float:
    base = (
        n_zones * _BASE_PER_ZONE_GB
        + n_boundaries * _PER_BOUNDARY_GB
    )
    factor = _STRATEGY_FACTOR.get(strategy, 1.0)
    return round(base * factor, 4)


# Existence-check signatures.
ExistsFn = t.Callable[[str], bool]
BudgetFn = t.Callable[[TargetPlatform], int]


@dataclasses.dataclass
class WorldDemoPackager:
    has_zone: ExistsFn = _accept_all
    has_boundary: ExistsFn = _accept_all
    has_lighting: ExistsFn = _accept_all
    platform_budget_mb: BudgetFn = _default_budget
    _manifests: dict[str, WorldDemoBuildManifest] = dataclasses.field(
        default_factory=dict,
    )
    _next_seq: int = 1

    def _next_id(self) -> str:
        out = f"world_manifest_{self._next_seq:04d}"
        self._next_seq += 1
        return out

    def build_world_manifest(
        self,
        name: str,
        zone_ids: t.Sequence[str],
        entry_zone_id: str,
        exit_zone_ids: t.Sequence[str] = (),
        choreography_per_zone: t.Mapping[str, str] = (),  # type: ignore[arg-type]
        boundary_handoffs_required: t.Sequence[str] = (),
        streaming_strategy: StreamingStrategy
        = StreamingStrategy.RING_PRELOAD,
        target_platform: TargetPlatform = TargetPlatform.PC_ULTRA,
    ) -> WorldDemoBuildManifest:
        if not name:
            raise ValueError("name required")
        if not zone_ids:
            raise ValueError("zone_ids must be non-empty")
        if not entry_zone_id:
            raise ValueError("entry_zone_id required")
        if entry_zone_id not in zone_ids:
            raise ValueError(
                "entry_zone_id must be in zone_ids",
            )
        for ez in exit_zone_ids:
            if ez not in zone_ids:
                raise ValueError(
                    f"exit_zone_id {ez} not in zone_ids",
                )
        if isinstance(choreography_per_zone, dict):
            chor = tuple(
                sorted(choreography_per_zone.items())
            )
        else:
            chor = tuple(choreography_per_zone)
        size = _compute_size_gb(
            n_zones=len(zone_ids),
            n_boundaries=len(boundary_handoffs_required),
            strategy=streaming_strategy,
        )
        m = WorldDemoBuildManifest(
            manifest_id=self._next_id(),
            name=name,
            target_platform=target_platform,
            zone_ids=tuple(zone_ids),
            entry_zone_id=entry_zone_id,
            exit_zone_ids=tuple(exit_zone_ids),
            choreography_per_zone=chor,
            boundary_handoffs_required=tuple(
                boundary_handoffs_required,
            ),
            streaming_strategy=streaming_strategy,
            total_estimated_size_gb=size,
            validation_status=ValidationStatus.PENDING,
        )
        self._manifests[m.manifest_id] = m
        return m

    def lookup(self, manifest_id: str) -> WorldDemoBuildManifest:
        if manifest_id not in self._manifests:
            raise KeyError(
                f"unknown manifest: {manifest_id}",
            )
        return self._manifests[manifest_id]

    def all_manifests(
        self,
    ) -> tuple[WorldDemoBuildManifest, ...]:
        return tuple(self._manifests.values())

    def estimated_size_gb(
        self, manifest_id: str,
    ) -> float:
        return self.lookup(manifest_id).total_estimated_size_gb

    def platform_fits(
        self, manifest_id: str, platform: TargetPlatform,
    ) -> bool:
        m = self.lookup(manifest_id)
        budget_mb = self.platform_budget_mb(platform)
        # 1 GB = 1024 MB.
        est_mb = int(m.total_estimated_size_gb * 1024)
        return est_mb <= budget_mb

    def validate(
        self, manifest_id: str,
    ) -> WorldValidationReport:
        m = self.lookup(manifest_id)
        missing_zones = tuple(
            z for z in m.zone_ids if not self.has_zone(z)
        )
        missing_boundaries = tuple(
            b for b in m.boundary_handoffs_required
            if not self.has_boundary(b)
        )
        missing_lighting = tuple(
            z for z in m.zone_ids if not self.has_lighting(z)
        )
        budget_mb = self.platform_budget_mb(m.target_platform)
        est_mb = int(m.total_estimated_size_gb * 1024)
        over = est_mb > budget_mb
        any_missing = bool(
            missing_zones or missing_boundaries
            or missing_lighting or over
        )
        status = (
            ValidationStatus.FAILED if any_missing
            else ValidationStatus.PASSED
        )
        all_missing: tuple[str, ...] = (
            tuple(f"zone:{z}" for z in missing_zones)
            + tuple(f"boundary:{b}" for b in missing_boundaries)
            + tuple(f"lighting:{z}" for z in missing_lighting)
            + (("budget:over",) if over else ())
        )
        new_m = dataclasses.replace(
            m,
            validation_status=status,
            missing_assets=all_missing,
        )
        self._manifests[manifest_id] = new_m
        return WorldValidationReport(
            manifest_id=manifest_id,
            status=status,
            missing_zones=missing_zones,
            missing_boundaries=missing_boundaries,
            missing_lighting=missing_lighting,
            over_budget=over,
            budget_mb=budget_mb,
            estimated_mb=est_mb,
        )

    # --- Predefined demos ---

    def bastok_to_konschtat_default(
        self,
    ) -> WorldDemoBuildManifest:
        """Three-zone walkthrough demo. Uses zone_atlas zones
        — Konschtat is substituted with north_gustaberg, the
        atlas's canonical Bastok-side golden-hour open field."""
        return self.build_world_manifest(
            name="Bastok-to-Field Walkthrough",
            zone_ids=(
                "bastok_markets",
                "bastok_mines",
                "north_gustaberg",
            ),
            entry_zone_id="bastok_markets",
            exit_zone_ids=(
                "bastok_markets",
                "bastok_mines",
                "north_gustaberg",
            ),
            choreography_per_zone={
                "bastok_markets": "bastok_markets_demo",
                "bastok_mines": "bastok_mines_walk",
                "north_gustaberg":
                    "north_gustaberg_golden_hour",
            },
            boundary_handoffs_required=(
                "bnd_markets_to_mines",
                "bnd_mines_to_north_gustaberg",
            ),
            streaming_strategy=StreamingStrategy.RING_PRELOAD,
            target_platform=TargetPlatform.PC_ULTRA,
        )

    def three_nations_grand_tour_default(
        self,
    ) -> WorldDemoBuildManifest:
        """Five-zone tour: Bastok -> San d'Oria -> Windurst,
        all resident, with airship transit hops."""
        return self.build_world_manifest(
            name="Three Nations Grand Tour",
            zone_ids=(
                "bastok_markets",
                "south_sandoria",
                "windurst_woods",
                "lower_jeuno",
                "port_jeuno",
            ),
            entry_zone_id="bastok_markets",
            exit_zone_ids=(
                "bastok_markets",
                "lower_jeuno",
                "south_sandoria",
                "port_jeuno",
                "windurst_woods",
            ),
            choreography_per_zone={
                "bastok_markets": "bastok_markets_demo",
                "south_sandoria": "sandoria_cathedral_walk",
                "windurst_woods": "windurst_canopy_dance",
                "lower_jeuno": "jeuno_plaza_crossing",
                "port_jeuno": "port_jeuno_airship_arrival",
            },
            boundary_handoffs_required=(
                "bnd_bastok_to_jeuno_airship",
                "bnd_jeuno_to_sandoria_airship",
                "bnd_jeuno_to_windurst_airship",
            ),
            streaming_strategy=StreamingStrategy.ALL_RESIDENT,
            target_platform=TargetPlatform.PC_ULTRA,
        )

    def full_world_flythrough_default(
        self, all_zone_ids: t.Sequence[str],
    ) -> WorldDemoBuildManifest:
        """Drone-camera mode through every zone. Caller passes
        the zone universe (typically zone_atlas.ZONES.keys())
        so this module avoids importing the atlas."""
        if not all_zone_ids:
            raise ValueError("all_zone_ids must be non-empty")
        zones = tuple(all_zone_ids)
        return self.build_world_manifest(
            name="Full World Flythrough",
            zone_ids=zones,
            entry_zone_id=zones[0],
            exit_zone_ids=zones,
            choreography_per_zone={
                z: f"{z}_drone_pass" for z in zones
            },
            boundary_handoffs_required=(),
            streaming_strategy=StreamingStrategy.ON_DEMAND,
            target_platform=TargetPlatform.PC_ULTRA,
        )


__all__ = [
    "StreamingStrategy",
    "TargetPlatform",
    "ValidationStatus",
    "WorldDemoBuildManifest",
    "WorldValidationReport",
    "WorldDemoPackager",
]
