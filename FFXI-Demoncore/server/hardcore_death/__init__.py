"""Hardcore death + Fomor resurrection — the defining mechanic.

Per HARDCORE_DEATH.md: 'Permadeath alone is too punishing — it
just makes people stop playing. Permadeath that creates content
turns every loss into a story.'

Module layout:
    death_timer.py - 1-hour KO timer + raise paths + opt-out
    snapshot.py    - frozen character state at fomor conversion
    fomor_pool.py  - pending/active pool + town safety + zone cap
                          + 24h cooldown + day/night cycle
    boss_assist.py - LSB-flagged boss aggros -> request N fomor adds
    evolution.py   - leveling up via player kills + Mythological tier
"""
from .boss_assist import (
    MAX_FOMORS_END_GAME,
    MAX_FOMORS_PER_BOSS_FIGHT,
    AssistRequest,
    AssistResult,
    select_assists,
)
from .death_timer import (
    DEATH_TIMER_SECONDS,
    DeathRecord,
    DeathState,
    RaiseSource,
    apply_raise,
    maybe_expire,
    open_death_record,
    opt_out_at_expiry,
)
from .evolution import (
    KILLS_PER_EVOLUTION_LEVEL,
    MAX_EVOLUTION_LEVELS,
    FomorEvolutionState,
    FomorTier,
    TrophyDrop,
    flag_mythological,
    record_player_kill,
    trophy_for_kill,
)
from .fomor_pool import (
    ACCOUNT_COOLDOWN_SECONDS,
    NIGHT_HOUR_RANGE,
    TOWN_SAFE_ZONES,
    FomorEntry,
    FomorPool,
    FomorState,
)
from .snapshot import (
    Appearance,
    FomorSnapshot,
    GearPiece,
    JobLevel,
    take_snapshot,
)

__all__ = [
    # death_timer
    "DEATH_TIMER_SECONDS", "DeathState", "RaiseSource",
    "DeathRecord", "open_death_record", "apply_raise",
    "maybe_expire", "opt_out_at_expiry",
    # snapshot
    "Appearance", "JobLevel", "GearPiece", "FomorSnapshot",
    "take_snapshot",
    # fomor_pool
    "ACCOUNT_COOLDOWN_SECONDS", "TOWN_SAFE_ZONES",
    "NIGHT_HOUR_RANGE", "FomorState", "FomorEntry", "FomorPool",
    # boss_assist
    "MAX_FOMORS_PER_BOSS_FIGHT", "MAX_FOMORS_END_GAME",
    "AssistRequest", "AssistResult", "select_assists",
    # evolution
    "MAX_EVOLUTION_LEVELS", "KILLS_PER_EVOLUTION_LEVEL",
    "FomorTier", "FomorEvolutionState", "TrophyDrop",
    "record_player_kill", "flag_mythological", "trophy_for_kill",
]
