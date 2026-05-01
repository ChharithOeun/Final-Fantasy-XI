"""Speed floors — the doc's 3 hardcaps that prevent EQ-spam-DPS.

Per COMBAT_TEMPO.md (Skill speed thresholds):
    - Min auto-swing:        0.8s (no faster, even with Haste II + Hasso +
                                   Spirit Surge stacking)
    - Min spell cast:        0.5s (most spells respect a hardcap)
    - Min weapon-skill rec:  0.3s (cancel-into-WS chains stay possible)

The buff-stack pipeline calls clamp_* before applying haste/cast-time
multipliers so 'three buffs stacked' can't drive the value below
the floor.

These are speed FLOORS — a value LOWER than the floor is invalid;
the actual time-to-fire is the maximum of the computed value and
the floor. So 'min auto-swing' = 'auto-swing CAN'T go below 0.8s'.
"""
from __future__ import annotations

import enum

# ----------------------------------------------------------------------
# Constants — exact doc values.
# ----------------------------------------------------------------------

MIN_AUTO_SWING_S: float = 0.8
MIN_SPELL_CAST_S: float = 0.5
MIN_WS_RECOVERY_S: float = 0.3


class FloorMetric(str, enum.Enum):
    """Names a hardcap for trace logging / introspection."""
    AUTO_SWING = "auto_swing"
    SPELL_CAST = "spell_cast"
    WS_RECOVERY = "ws_recovery"


FLOOR_VALUES: dict[FloorMetric, float] = {
    FloorMetric.AUTO_SWING: MIN_AUTO_SWING_S,
    FloorMetric.SPELL_CAST: MIN_SPELL_CAST_S,
    FloorMetric.WS_RECOVERY: MIN_WS_RECOVERY_S,
}


def get_floor(metric: FloorMetric) -> float:
    return FLOOR_VALUES[metric]


# ----------------------------------------------------------------------
# Clamp helpers — call AFTER applying buffs / debuffs.
# ----------------------------------------------------------------------

def clamp_auto_swing(value_s: float) -> float:
    """Apply the 0.8s auto-swing floor."""
    if value_s < 0:
        raise ValueError("auto-swing time must be non-negative")
    return max(MIN_AUTO_SWING_S, value_s)


def clamp_spell_cast(value_s: float) -> float:
    """Apply the 0.5s spell-cast floor.

    Instant-cast (0s) is intentionally allowed to bypass — the doc
    floor is for 'most spells'; instant-cast is its own carve-out
    that the caller flags by passing 0.0 (which we return as 0.0).
    """
    if value_s < 0:
        raise ValueError("spell-cast time must be non-negative")
    if value_s == 0.0:
        return 0.0      # explicit instant-cast, leave alone
    return max(MIN_SPELL_CAST_S, value_s)


def clamp_ws_recovery(value_s: float) -> float:
    """Apply the 0.3s WS recovery floor."""
    if value_s < 0:
        raise ValueError("ws recovery time must be non-negative")
    return max(MIN_WS_RECOVERY_S, value_s)


def is_below_floor(metric: FloorMetric, value_s: float) -> bool:
    """Diagnostic: was a buff stack about to push us below the floor?"""
    return value_s < FLOOR_VALUES[metric]
