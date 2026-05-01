"""Fomor party spawn-on-AFK.

When AFKDetector flags a player as CONFIRMED, this module decides
whether to spawn a Fomor party near them and what composition.

Per the user's design: aggressive in dungeons or at night anywhere.
Less aggressive in daytime cities. Standing at instance entrance is
treated as 'in dungeon territory' since that's the bot-farming
location to defend against.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SpawnDecision(str, enum.Enum):
    SPAWN_FOMOR_PARTY = "spawn_fomor_party"
    DELAY = "delay"           # not aggressive enough yet
    SKIP = "skip"             # safe location; no spawn


@dataclasses.dataclass
class FomorParty:
    """A Fomor party slated to spawn near an AFK target."""
    target_player_id: str
    pack_size: int                    # 3-6 fomors
    target_position: tuple[float, float, float]
    spawn_radius_cm: float = 1500.0   # how close to the target
    fomor_levels: t.Optional[list[int]] = None  # null = match player level
    aggressive_immediately: bool = True


# Tuning
DEFAULT_FOMOR_PACK_SIZE_MIN = 3
DEFAULT_FOMOR_PACK_SIZE_MAX = 6
ENRAGE_LOCATION_TYPES = {"dungeon", "instance_entrance", "raid_lobby"}


class FomorSpawnPolicy:
    """Decides spawn-or-not + pack size based on context.

    Inputs (via decide()):
        - player_state: from AFKDetector (must be CONFIRMED to spawn)
        - location_type: "city" / "open_world" / "dungeon" /
          "instance_entrance" / "raid_lobby" / "sanctuary"
        - is_night: in-game time-of-day
        - player_position: (x, y, z) cm
        - player_level: for matching pack difficulty
    """

    def decide(self, *,
                player_id: str,
                afk_confirmed: bool,
                location_type: str,
                is_night: bool,
                player_position: tuple[float, float, float],
                player_level: int) -> SpawnDecision:
        if not afk_confirmed:
            return SpawnDecision.DELAY

        if location_type == "sanctuary":
            return SpawnDecision.SKIP

        # Aggressive contexts: dungeons + instance lobbies always
        # spawn fomors, regardless of in-game time.
        if location_type in ENRAGE_LOCATION_TYPES:
            return SpawnDecision.SPAWN_FOMOR_PARTY

        # Cities + open world: only at night
        if is_night:
            return SpawnDecision.SPAWN_FOMOR_PARTY

        # Daytime cities + safe open-world areas: don't spawn yet
        return SpawnDecision.DELAY

    def build_party(self, *,
                     player_id: str,
                     player_position: tuple[float, float, float],
                     player_level: int,
                     location_type: str,
                     is_night: bool,
                     pack_size: t.Optional[int] = None) -> FomorParty:
        """Construct a FomorParty record. The LSB / orchestrator
        actually instantiates the fomors in the world."""
        if pack_size is None:
            # Larger packs at night or in dungeons
            base = DEFAULT_FOMOR_PACK_SIZE_MIN
            if location_type in ENRAGE_LOCATION_TYPES:
                base = DEFAULT_FOMOR_PACK_SIZE_MAX
            elif is_night:
                base = (DEFAULT_FOMOR_PACK_SIZE_MIN
                         + DEFAULT_FOMOR_PACK_SIZE_MAX) // 2
            pack_size = base

        # Match the player's level (or slightly above for instance lobbies)
        target_level = player_level
        if location_type in ENRAGE_LOCATION_TYPES:
            target_level = player_level + 2

        return FomorParty(
            target_player_id=player_id,
            pack_size=pack_size,
            target_position=player_position,
            fomor_levels=[target_level] * pack_size,
            aggressive_immediately=True,
        )
