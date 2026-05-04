"""Beastman garden — lair-attached gardening pots.

The beastman analog to FFXI Mog Garden. Each lair (per
beastman_lair_house tier) carries some PLOT slots that the
player fills with SEEDS. Seeds grow in PHASES (SEEDED → SPROUT
→ MATURE → HARVEST_READY) on a real-time clock, with optional
TENDING actions (water, fertilize) that cut grow time. Skipping
tending past a threshold WILTS the plot — wilted seeds drop only
fertilizer compost.

Public surface
--------------
    SeedKind enum
    GrowthPhase enum
    PlotState dataclass
    BeastmanGarden
        .open_plot(player_id, plot_index)
        .plant(player_id, plot_index, seed, now_seconds)
        .tend(player_id, plot_index, action, now_seconds)
        .check(player_id, plot_index, now_seconds)
        .harvest(player_id, plot_index, now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SeedKind(str, enum.Enum):
    HERB = "herb"
    GRAIN = "grain"
    GOURD = "gourd"
    THORN = "thorn"
    LUMINOUS = "luminous"


class GrowthPhase(str, enum.Enum):
    SEEDED = "seeded"
    SPROUT = "sprout"
    MATURE = "mature"
    HARVEST_READY = "harvest_ready"
    WILTED = "wilted"


class TendAction(str, enum.Enum):
    WATER = "water"
    FERTILIZE = "fertilize"


# Base grow time per seed (seconds to HARVEST_READY without tending)
_SEED_GROW_SECONDS: dict[SeedKind, int] = {
    SeedKind.HERB: 1_800,
    SeedKind.GRAIN: 3_600,
    SeedKind.GOURD: 7_200,
    SeedKind.THORN: 5_400,
    SeedKind.LUMINOUS: 14_400,
}


_SEED_HARVEST: dict[SeedKind, str] = {
    SeedKind.HERB: "shadow_herb_bundle",
    SeedKind.GRAIN: "ashen_grain",
    SeedKind.GOURD: "raider_gourd",
    SeedKind.THORN: "thorn_cluster",
    SeedKind.LUMINOUS: "luminous_petal",
}


_TEND_SHAVE_SECONDS: dict[TendAction, int] = {
    TendAction.WATER: 300,
    TendAction.FERTILIZE: 600,
}


_WILT_GRACE_SECONDS = 14_400  # 4 hours past harvest_ready before wilt


@dataclasses.dataclass
class PlotState:
    plot_index: int
    seed: t.Optional[SeedKind] = None
    planted_at: t.Optional[int] = None
    harvest_at: t.Optional[int] = None
    tend_count: int = 0
    last_tended_at: t.Optional[int] = None
    phase: GrowthPhase = GrowthPhase.SEEDED


@dataclasses.dataclass(frozen=True)
class PhaseResult:
    accepted: bool
    plot_index: int
    phase: GrowthPhase
    seconds_until_harvest: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class HarvestResult:
    accepted: bool
    plot_index: int
    item_id: str = ""
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanGarden:
    _plots: dict[
        tuple[str, int], PlotState,
    ] = dataclasses.field(default_factory=dict)

    def open_plot(
        self, *, player_id: str, plot_index: int,
    ) -> bool:
        if plot_index < 0:
            return False
        key = (player_id, plot_index)
        if key in self._plots:
            return False
        self._plots[key] = PlotState(plot_index=plot_index)
        return True

    def plant(
        self, *, player_id: str,
        plot_index: int,
        seed: SeedKind,
        now_seconds: int,
    ) -> PhaseResult:
        p = self._plots.get((player_id, plot_index))
        if p is None:
            return PhaseResult(
                False, plot_index, GrowthPhase.SEEDED,
                reason="plot not open",
            )
        if p.seed is not None and p.phase != GrowthPhase.WILTED:
            return PhaseResult(
                False, plot_index, p.phase,
                reason="plot already planted",
            )
        p.seed = seed
        p.planted_at = now_seconds
        p.harvest_at = now_seconds + _SEED_GROW_SECONDS[seed]
        p.tend_count = 0
        p.last_tended_at = None
        p.phase = GrowthPhase.SEEDED
        return PhaseResult(
            accepted=True,
            plot_index=plot_index,
            phase=p.phase,
            seconds_until_harvest=p.harvest_at - now_seconds,
        )

    def tend(
        self, *, player_id: str,
        plot_index: int,
        action: TendAction,
        now_seconds: int,
    ) -> PhaseResult:
        p = self._plots.get((player_id, plot_index))
        if p is None or p.seed is None:
            return PhaseResult(
                False, plot_index, GrowthPhase.SEEDED,
                reason="empty or unopened plot",
            )
        if p.phase in (
            GrowthPhase.HARVEST_READY, GrowthPhase.WILTED,
        ):
            return PhaseResult(
                False, plot_index, p.phase,
                reason="cannot tend past maturity",
            )
        # Cap tend benefits at 3 actions to prevent infinite shrink
        if p.tend_count >= 3:
            return PhaseResult(
                False, plot_index, p.phase,
                reason="tend cap reached",
            )
        shave = _TEND_SHAVE_SECONDS[action]
        if p.harvest_at is not None:
            p.harvest_at = max(now_seconds + 1, p.harvest_at - shave)
        p.tend_count += 1
        p.last_tended_at = now_seconds
        return PhaseResult(
            accepted=True,
            plot_index=plot_index,
            phase=p.phase,
            seconds_until_harvest=max(0, (p.harvest_at or 0) - now_seconds),
        )

    def _resolve_phase(
        self, p: PlotState, now_seconds: int,
    ) -> GrowthPhase:
        if p.seed is None or p.harvest_at is None:
            return GrowthPhase.SEEDED
        if p.phase == GrowthPhase.WILTED:
            return GrowthPhase.WILTED
        delta = p.harvest_at - now_seconds
        total = _SEED_GROW_SECONDS[p.seed]
        if now_seconds >= p.harvest_at + _WILT_GRACE_SECONDS:
            p.phase = GrowthPhase.WILTED
        elif now_seconds >= p.harvest_at:
            p.phase = GrowthPhase.HARVEST_READY
        elif delta <= total // 3:
            p.phase = GrowthPhase.MATURE
        elif delta <= (2 * total) // 3:
            p.phase = GrowthPhase.SPROUT
        else:
            p.phase = GrowthPhase.SEEDED
        return p.phase

    def check(
        self, *, player_id: str,
        plot_index: int,
        now_seconds: int,
    ) -> PhaseResult:
        p = self._plots.get((player_id, plot_index))
        if p is None:
            return PhaseResult(
                False, plot_index, GrowthPhase.SEEDED,
                reason="plot not open",
            )
        phase = self._resolve_phase(p, now_seconds)
        seconds_until = (
            max(0, (p.harvest_at or 0) - now_seconds)
            if p.harvest_at is not None else 0
        )
        return PhaseResult(
            accepted=True,
            plot_index=plot_index,
            phase=phase,
            seconds_until_harvest=seconds_until,
        )

    def harvest(
        self, *, player_id: str,
        plot_index: int,
        now_seconds: int,
    ) -> HarvestResult:
        p = self._plots.get((player_id, plot_index))
        if p is None or p.seed is None:
            return HarvestResult(
                False, plot_index, reason="nothing planted",
            )
        phase = self._resolve_phase(p, now_seconds)
        if phase == GrowthPhase.WILTED:
            seed_at_wilt = p.seed
            p.seed = None
            p.harvest_at = None
            p.planted_at = None
            p.last_tended_at = None
            p.tend_count = 0
            p.phase = GrowthPhase.SEEDED
            # Wilted plots drop compost only
            return HarvestResult(
                accepted=True, plot_index=plot_index,
                item_id="fertilizer_compost",
                reason=f"wilted_{seed_at_wilt.value}",
            )
        if phase != GrowthPhase.HARVEST_READY:
            return HarvestResult(
                False, plot_index, reason="not ready",
            )
        item = _SEED_HARVEST[p.seed]
        p.seed = None
        p.harvest_at = None
        p.planted_at = None
        p.last_tended_at = None
        p.tend_count = 0
        p.phase = GrowthPhase.SEEDED
        return HarvestResult(
            accepted=True,
            plot_index=plot_index,
            item_id=item,
        )

    def total_plots(self) -> int:
        return len(self._plots)


__all__ = [
    "SeedKind", "GrowthPhase", "TendAction",
    "PlotState", "PhaseResult", "HarvestResult",
    "BeastmanGarden",
]
