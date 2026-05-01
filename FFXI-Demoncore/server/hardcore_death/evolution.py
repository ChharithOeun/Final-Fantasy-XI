"""Fomor evolution — leveling up via player kills.

Per HARDCORE_DEATH.md open question 1:
    'Fomor evolution. Do fomors level up by killing players? Lean
    toward yes, capped at +5 levels above their original. Let them
    get more dangerous over time.'

Plus the Mythological tier:
    'when a notable player (server-first kill, etc.) dies and
    becomes a fomor, the system flags the spawn as Mythological.
    Stronger, named, bestiary entry. Kill drops a unique trophy.'
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Doc: 'capped at +5 levels above their original'.
MAX_EVOLUTION_LEVELS: int = 5

# How many player kills before a fomor levels up. Tunable; doc
# leans toward 'gets dangerous over time' so we anchor at 3 kills
# per level.
KILLS_PER_EVOLUTION_LEVEL: int = 3


class FomorTier(str, enum.Enum):
    STANDARD = "standard"
    MYTHOLOGICAL = "mythological"


@dataclasses.dataclass
class FomorEvolutionState:
    """Per-fomor counter tracking kills + level deltas."""
    fomor_id: str
    base_level: int                       # main_level at conversion
    player_kills: int = 0
    bonus_levels: int = 0
    tier: FomorTier = FomorTier.STANDARD
    server_first_killer: bool = False     # for Mythological flag
    notable_kills: tuple[str, ...] = ()   # named players killed

    @property
    def effective_level(self) -> int:
        return self.base_level + self.bonus_levels

    def at_evolution_cap(self) -> bool:
        return self.bonus_levels >= MAX_EVOLUTION_LEVELS


def record_player_kill(state: FomorEvolutionState,
                            *,
                            victim_name: str,
                            victim_was_server_first: bool = False,
                            ) -> int:
    """Increment kill counter; bump level if threshold crossed.

    Returns the new bonus_levels value. Level is capped at
    MAX_EVOLUTION_LEVELS.
    """
    state.player_kills += 1

    if victim_was_server_first:
        # Doc Mythological flag: 'server-first kill, etc.'
        state.tier = FomorTier.MYTHOLOGICAL
    if victim_name and victim_name not in state.notable_kills:
        state.notable_kills = state.notable_kills + (victim_name,)

    # Level-up gate
    target_level = state.player_kills // KILLS_PER_EVOLUTION_LEVEL
    target_level = min(target_level, MAX_EVOLUTION_LEVELS)
    if target_level > state.bonus_levels:
        state.bonus_levels = target_level
    return state.bonus_levels


def flag_mythological(state: FomorEvolutionState,
                          *,
                          reason: str = ""
                          ) -> None:
    """Manual flag for the Mythological tier (e.g. owner was a
    notable player at conversion time)."""
    state.tier = FomorTier.MYTHOLOGICAL
    state.server_first_killer = True
    if reason and reason not in state.notable_kills:
        state.notable_kills = state.notable_kills + (reason,)


@dataclasses.dataclass(frozen=True)
class TrophyDrop:
    """Doc: Mythological 'kill drops a unique trophy'."""
    trophy_id: str
    fomor_id: str
    fomor_name: str
    is_unique: bool = True


def trophy_for_kill(*,
                       fomor_id: str,
                       fomor_name: str,
                       state: FomorEvolutionState
                       ) -> t.Optional[TrophyDrop]:
    """Return a unique trophy if the fomor was Mythological tier;
    None otherwise (standard fomors drop normal gear via fomor_gear)."""
    if state.tier != FomorTier.MYTHOLOGICAL:
        return None
    return TrophyDrop(
        trophy_id=f"trophy_mythical_{fomor_id}",
        fomor_id=fomor_id,
        fomor_name=fomor_name,
    )
