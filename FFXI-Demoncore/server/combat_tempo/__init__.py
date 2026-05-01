"""Combat tempo — the cadence retune that makes Demoncore feel modern.

Per COMBAT_TEMPO.md: 'Original FFXI is slow. Modern FFXI is barely
faster. Demoncore is fast.' The principle: action that's about
reflex gets faster; action that's about commitment stays slow.

Module layout:
    tempo_presets.py    - 7-row metric table + halve/raise helpers
    speed_floors.py     - 3 hardcaps (0.8s swing / 0.5s cast / 0.3s rec)
    slow_actions.py     - 6 carve-outs (Raise/Tractor/Reraise/Teleport/
                              boss enrage/crafting)
    animation_cancel.py - 3 cancel rules + ActionPhase / CancelOutcome
    mob_tiers.py        - HERO/ACTIVE/AMBIENT proximity classifier
    zone_density.py     - 4-tier zone spawn-count anchors + NM mult
    respawn_timers.py   - trash 1-15min / NM 30m-12hr / HNM 24hr+PoP
    skillchain_ui.py    - 1.5s MB window + auto-WS toggle + indicator

Public surface:
    TempoMetric, TempoBand, TEMPO_TABLE, get_band,
        halve_og_value, raise_og_value, is_in_band
    FloorMetric, FLOOR_VALUES, MIN_AUTO_SWING_S, MIN_SPELL_CAST_S,
        MIN_WS_RECOVERY_S, get_floor, clamp_auto_swing,
        clamp_spell_cast, clamp_ws_recovery, is_below_floor
    SlowActionId, SlowActionRule, SLOW_ACTION_RULES,
        is_slow_action, get_rule, should_halve_recast
    ActionPhase, CancelIntent, CancelOutcome, CancelResult,
        resolve_cancel, can_cancel
    MobTempoTier, TierProfile, TIER_PROFILES,
        ACTIVE_RADIUS_METERS, ACTIVE_TIER_PARTY_BOUNDS,
        MobTierState, classify_tier, update_state,
        total_compute_cost, count_by_tier
    ZoneTier, ZoneDensityBand, ZONE_DENSITY_BANDS,
        TIER_ANCHOR_ZONES, density_target, nm_target_count,
        tier_for_zone
    RespawnCategory, RespawnBand, RESPAWN_BANDS,
        TRASH_RESPAWN_BY_ZONE_TIER, trash_respawn_seconds,
        respawn_seconds_for, halve_og_respawn
    MB_WINDOW_SECONDS, MB_DAMAGE_BONUS_MULTIPLIER,
        SkillchainIndicator, SkillchainIndicatorPlacement,
        AutoWsToggle, make_indicator, damage_in_mb_window
"""
from .animation_cancel import (
    ActionPhase,
    CancelIntent,
    CancelOutcome,
    CancelResult,
    can_cancel,
    resolve_cancel,
)
from .mob_tiers import (
    ACTIVE_RADIUS_METERS,
    ACTIVE_TIER_PARTY_BOUNDS,
    TIER_PROFILES,
    MobTempoTier,
    MobTierState,
    TierProfile,
    classify_tier,
    count_by_tier,
    total_compute_cost,
    update_state,
)
from .respawn_timers import (
    RESPAWN_BANDS,
    TRASH_RESPAWN_BY_ZONE_TIER,
    RespawnBand,
    RespawnCategory,
    halve_og_respawn,
    respawn_seconds_for,
    trash_respawn_seconds,
)
from .respawn_timers import get_band as get_respawn_band
from .respawn_timers import is_in_band as respawn_is_in_band
from .skillchain_ui import (
    MB_DAMAGE_BONUS_MULTIPLIER,
    MB_WINDOW_SECONDS,
    AutoWsToggle,
    SkillchainIndicator,
    SkillchainIndicatorPlacement,
    damage_in_mb_window,
    make_indicator,
)
from .slow_actions import (
    SLOW_ACTION_RULES,
    SlowActionId,
    SlowActionRule,
    get_rule,
    is_slow_action,
    should_halve_recast,
)
from .speed_floors import (
    FLOOR_VALUES,
    MIN_AUTO_SWING_S,
    MIN_SPELL_CAST_S,
    MIN_WS_RECOVERY_S,
    FloorMetric,
    clamp_auto_swing,
    clamp_spell_cast,
    clamp_ws_recovery,
    get_floor,
    is_below_floor,
)
from .tempo_presets import (
    TEMPO_TABLE,
    TempoBand,
    TempoMetric,
    halve_og_value,
    is_in_band,
    raise_og_value,
)
from .tempo_presets import get_band as get_tempo_band
from .zone_density import (
    TIER_ANCHOR_ZONES,
    ZONE_DENSITY_BANDS,
    ZoneDensityBand,
    ZoneTier,
    density_target,
    nm_target_count,
    tier_for_zone,
)
from .zone_density import get_band as get_density_band
from .zone_density import is_in_band as zone_density_in_band

__all__ = [
    # tempo_presets
    "TempoMetric", "TempoBand", "TEMPO_TABLE",
    "get_tempo_band", "halve_og_value",
    "raise_og_value", "is_in_band",
    # speed_floors
    "FloorMetric", "FLOOR_VALUES",
    "MIN_AUTO_SWING_S", "MIN_SPELL_CAST_S", "MIN_WS_RECOVERY_S",
    "get_floor", "clamp_auto_swing", "clamp_spell_cast",
    "clamp_ws_recovery", "is_below_floor",
    # slow_actions
    "SlowActionId", "SlowActionRule", "SLOW_ACTION_RULES",
    "is_slow_action", "get_rule", "should_halve_recast",
    # animation_cancel
    "ActionPhase", "CancelIntent", "CancelOutcome",
    "CancelResult", "resolve_cancel", "can_cancel",
    # mob_tiers
    "MobTempoTier", "TierProfile", "TIER_PROFILES",
    "ACTIVE_RADIUS_METERS", "ACTIVE_TIER_PARTY_BOUNDS",
    "MobTierState", "classify_tier", "update_state",
    "total_compute_cost", "count_by_tier",
    # zone_density
    "ZoneTier", "ZoneDensityBand", "ZONE_DENSITY_BANDS",
    "TIER_ANCHOR_ZONES", "get_density_band",
    "density_target", "nm_target_count",
    "tier_for_zone", "zone_density_in_band",
    # respawn_timers
    "RespawnCategory", "RespawnBand", "RESPAWN_BANDS",
    "TRASH_RESPAWN_BY_ZONE_TIER", "get_respawn_band",
    "trash_respawn_seconds", "respawn_seconds_for",
    "respawn_is_in_band", "halve_og_respawn",
    # skillchain_ui
    "MB_WINDOW_SECONDS", "MB_DAMAGE_BONUS_MULTIPLIER",
    "SkillchainIndicator", "SkillchainIndicatorPlacement",
    "AutoWsToggle", "make_indicator", "damage_in_mb_window",
]
