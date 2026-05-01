"""Tempo presets — the doc's number table, encoded.

Per COMBAT_TEMPO.md: 'Original FFXI is slow. Modern FFXI is barely
faster. Demoncore is fast.' This module names the seven cadence
metrics + their OG-vs-Demoncore ranges, with helpers for the
build-order's halving passes (steps 2-3 and 5).
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TempoMetric(str, enum.Enum):
    """Each cadence the doc retunes."""
    AUTO_ATTACK_SWING = "auto_attack_swing"
    WS_CAST = "ws_cast"
    SKILLCHAIN_WINDOW = "skillchain_window"
    SPELL_CAST = "spell_cast"
    SPELL_RECAST = "spell_recast"
    PLAYER_RUN_SPEED = "player_run_speed"
    MOUNTED_RUN_SPEED = "mounted_run_speed"


@dataclasses.dataclass(frozen=True)
class TempoBand:
    """An OG-vs-Demoncore cadence band for one metric."""
    metric: TempoMetric
    og_min: float
    og_max: float
    demoncore_min: float
    demoncore_max: float
    unit: str           # "s" or "m/s"
    rationale: str = ""

    @property
    def og_span(self) -> tuple[float, float]:
        return (self.og_min, self.og_max)

    @property
    def demoncore_span(self) -> tuple[float, float]:
        return (self.demoncore_min, self.demoncore_max)

    def contains_demoncore_value(self, value: float) -> bool:
        return self.demoncore_min <= value <= self.demoncore_max

    def midpoint(self) -> float:
        """Default tuning anchor — middle of the Demoncore band."""
        return (self.demoncore_min + self.demoncore_max) / 2.0


# The doc's 7-row tempo table, anchored exactly.
TEMPO_TABLE: dict[TempoMetric, TempoBand] = {
    TempoMetric.AUTO_ATTACK_SWING: TempoBand(
        metric=TempoMetric.AUTO_ATTACK_SWING,
        og_min=4.0, og_max=7.0,
        demoncore_min=1.5, demoncore_max=2.5,
        unit="s",
        rationale=("UE5 animations are fluid; the 2002 cadence was a "
                      "server-tick limitation we no longer have"),
    ),
    TempoMetric.WS_CAST: TempoBand(
        metric=TempoMetric.WS_CAST,
        og_min=1.5, og_max=1.5,
        demoncore_min=0.4, demoncore_max=0.8,
        unit="s",
        rationale="Tight enough to chain into combos",
    ),
    TempoMetric.SKILLCHAIN_WINDOW: TempoBand(
        metric=TempoMetric.SKILLCHAIN_WINDOW,
        og_min=2.0, og_max=7.0,
        demoncore_min=1.5, demoncore_max=3.0,
        unit="s",
        rationale="Chain timing tighter, more skillful",
    ),
    TempoMetric.SPELL_CAST: TempoBand(
        metric=TempoMetric.SPELL_CAST,
        og_min=2.0, og_max=5.0,
        demoncore_min=1.0, demoncore_max=3.0,
        unit="s",
        rationale="Spells feel responsive",
    ),
    TempoMetric.SPELL_RECAST: TempoBand(
        metric=TempoMetric.SPELL_RECAST,
        og_min=4.0, og_max=30.0,
        demoncore_min=2.0, demoncore_max=12.0,
        unit="s",
        rationale=("Halve most recasts; specific keystone spells "
                      "(Raise, etc.) keep their weight"),
    ),
    TempoMetric.PLAYER_RUN_SPEED: TempoBand(
        metric=TempoMetric.PLAYER_RUN_SPEED,
        og_min=5.0, og_max=5.0,
        demoncore_min=6.5, demoncore_max=6.5,
        unit="m/s",
        rationale="Modest baseline lift; mounts amplify",
    ),
    TempoMetric.MOUNTED_RUN_SPEED: TempoBand(
        metric=TempoMetric.MOUNTED_RUN_SPEED,
        og_min=8.0, og_max=8.0,
        demoncore_min=12.0, demoncore_max=15.0,
        unit="m/s",
        rationale="Real difference",
    ),
}


def get_band(metric: TempoMetric) -> TempoBand:
    """Look up a metric's band. Raises KeyError on unknown."""
    return TEMPO_TABLE[metric]


# ----------------------------------------------------------------------
# Tuning helpers
# ----------------------------------------------------------------------

def halve_og_value(metric: TempoMetric, og_value: float) -> float:
    """Build-order step 5: 'halve all spawn timers across the board'.

    For tempo metrics where 'halve and clamp into the new band' is
    the design intent (auto-attack, WS, spell cast, spell recast,
    skillchain window). Clamps into the Demoncore band so a metric
    that was already fast doesn't overshoot the floor.

    Speed metrics (run / mounted) use raise_og_value instead.
    """
    band = get_band(metric)
    if metric in (TempoMetric.PLAYER_RUN_SPEED,
                    TempoMetric.MOUNTED_RUN_SPEED):
        raise ValueError(f"halve_og_value not for speed metric {metric}")
    halved = og_value / 2.0
    return max(band.demoncore_min, min(band.demoncore_max, halved))


def raise_og_value(metric: TempoMetric, og_value: float) -> float:
    """For speed metrics — bump from OG up into the Demoncore band.

    Returns the band's midpoint (the user can tune deeper later).
    """
    if metric not in (TempoMetric.PLAYER_RUN_SPEED,
                          TempoMetric.MOUNTED_RUN_SPEED):
        raise ValueError(f"raise_og_value only for speed metrics; got {metric}")
    band = get_band(metric)
    return max(band.demoncore_min, og_value)


def is_in_band(metric: TempoMetric, value: float) -> bool:
    """Sanity check that a tuning value lands inside the doc's band."""
    return get_band(metric).contains_demoncore_value(value)
