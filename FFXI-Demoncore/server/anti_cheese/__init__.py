"""Anti-cheese systems.

Three subsystems composed:
1. AFK detection (player not actually playing — macros, bots, AFK toons)
2. Fomor-party spawn-on-AFK (consequence: Fomors attack the AFK toon)
3. Activity-driven mob convergence (anti-bot at instance entrances:
   mobs slowly walk toward areas of high player activity)

Per the user's design: "anyone afk/not moving or acting (or on a macro
loop pretending to be there) a party of Fomors will spawn and start
attacking" + "even if parties are waiting to enter an instance mobs
around the zone would start to gather near player activities, to
prevent bot farming and afk raising".

Public surface:
    AFKDetector
    AFKState
    FomorSpawnPolicy
    ActivityHotspot
    MobConvergenceTracker
"""
from .afk_detector import (
    AFKDetector,
    AFKState,
    PlayerActivity,
)
from .fomor_spawner import (
    FomorParty,
    FomorSpawnPolicy,
)
from .mob_convergence import (
    ActivityHotspot,
    MobConvergenceTracker,
)

__all__ = [
    "AFKDetector",
    "AFKState",
    "PlayerActivity",
    "FomorSpawnPolicy",
    "FomorParty",
    "ActivityHotspot",
    "MobConvergenceTracker",
]
