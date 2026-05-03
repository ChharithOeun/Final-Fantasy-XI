"""NPC career track — promotions, demotions, job changes.

NPCs aren't frozen. The smith's apprentice you met at level 5
becomes the master smith ten game-years later. The captain of
the guard who kept order was demoted after the orcs broke
through; he now drinks at the Steaming Sheep.

Each NPC has a CareerPath (e.g. "knight ladder" or "merchant
ladder"), a current rank, and an experience pool that ticks up
from successful actions and down from failures.

Public surface
--------------
    CareerPath enum
    CareerRank dataclass
    CareerExperienceEvent dataclass
    NPCCareerProfile dataclass
    NPCCareerTrack
        .register_npc(npc_id, path, starting_rank)
        .grant_xp(npc_id, amount, reason)
        .penalize(npc_id, amount, reason)
        .check_promotion(npc_id) -> Optional[promotion delta]
        .check_demotion(npc_id) -> Optional[demotion delta]
        .change_path(npc_id, new_path)  -- mid-life career shift
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default thresholds.
DEFAULT_RANK_XP_STEP = 1000
DEFAULT_DEMOTION_FLOOR = -800
MAX_RANK = 10


class CareerPath(str, enum.Enum):
    KNIGHT_LADDER = "knight_ladder"
    MERCHANT_LADDER = "merchant_ladder"
    SCHOLAR_LADDER = "scholar_ladder"
    SMITH_LADDER = "smith_ladder"
    PRIEST_LADDER = "priest_ladder"
    SPY_LADDER = "spy_ladder"
    BARD_LADDER = "bard_ladder"


# Rank labels per path. Index = rank (0..MAX_RANK).
_RANK_LABELS: dict[CareerPath, list[str]] = {
    CareerPath.KNIGHT_LADDER: [
        "recruit", "footman", "guardsman", "sergeant",
        "lieutenant", "captain", "commander", "marshal",
        "warlord", "general", "lord_marshal",
    ],
    CareerPath.MERCHANT_LADDER: [
        "stallkeep", "vendor", "trader", "broker",
        "dealer", "magnate", "guildmaster", "chairman",
        "consortium_head", "merchant_prince", "trade_baron",
    ],
    CareerPath.SCHOLAR_LADDER: [
        "novice", "student", "scribe", "researcher",
        "lecturer", "doctor", "professor", "dean",
        "magus", "archmagus", "loremaster",
    ],
    CareerPath.SMITH_LADDER: [
        "apprentice", "journeyman", "smith", "master_smith",
        "guild_smith", "weaponsmaster", "ironlord",
        "forgemaster", "anvil_lord", "guildlord",
        "grand_artificer",
    ],
    CareerPath.PRIEST_LADDER: [
        "acolyte", "novice", "deacon", "priest",
        "high_priest", "bishop", "archbishop", "patriarch",
        "luminary", "saint", "ascendant",
    ],
    CareerPath.SPY_LADDER: [
        "informant", "agent", "operative", "handler",
        "spymaster", "shadow", "ghost", "wraith",
        "veil", "void_lord", "cipher",
    ],
    CareerPath.BARD_LADDER: [
        "minstrel", "balladeer", "lute_player", "court_singer",
        "skald", "troubadour", "song_master", "voicemaster",
        "song_lord", "muse", "harmonica",
    ],
}


@dataclasses.dataclass(frozen=True)
class CareerRank:
    path: CareerPath
    rank_index: int                # 0..MAX_RANK
    label: str

    def is_max(self) -> bool:
        return self.rank_index >= MAX_RANK


@dataclasses.dataclass(frozen=True)
class CareerExperienceEvent:
    npc_id: str
    delta: int                     # positive = success, negative = failure
    reason: str = ""
    at_seconds: float = 0.0


@dataclasses.dataclass
class NPCCareerProfile:
    npc_id: str
    path: CareerPath
    rank_index: int = 0
    xp_in_current_rank: int = 0
    times_promoted: int = 0
    times_demoted: int = 0
    last_changed_seconds: float = 0.0


def _label_for(
    path: CareerPath, rank_index: int,
) -> str:
    labels = _RANK_LABELS[path]
    if 0 <= rank_index < len(labels):
        return labels[rank_index]
    return f"{path.value}_rank_{rank_index}"


@dataclasses.dataclass(frozen=True)
class CareerChange:
    npc_id: str
    old_rank: CareerRank
    new_rank: CareerRank
    promotion: bool       # True for promotion, False for demotion
    reason: str = ""


@dataclasses.dataclass
class NPCCareerTrack:
    rank_xp_step: int = DEFAULT_RANK_XP_STEP
    demotion_floor: int = DEFAULT_DEMOTION_FLOOR
    _profiles: dict[str, NPCCareerProfile] = dataclasses.field(
        default_factory=dict,
    )

    def register_npc(
        self, *, npc_id: str, path: CareerPath,
        starting_rank: int = 0,
    ) -> t.Optional[NPCCareerProfile]:
        if npc_id in self._profiles:
            return None
        prof = NPCCareerProfile(
            npc_id=npc_id, path=path,
            rank_index=max(0, min(starting_rank, MAX_RANK)),
        )
        self._profiles[npc_id] = prof
        return prof

    def profile(
        self, npc_id: str,
    ) -> t.Optional[NPCCareerProfile]:
        return self._profiles.get(npc_id)

    def current_rank(
        self, npc_id: str,
    ) -> t.Optional[CareerRank]:
        prof = self._profiles.get(npc_id)
        if prof is None:
            return None
        return CareerRank(
            path=prof.path,
            rank_index=prof.rank_index,
            label=_label_for(prof.path, prof.rank_index),
        )

    def grant_xp(
        self, *, npc_id: str, amount: int,
        reason: str = "", now_seconds: float = 0.0,
    ) -> t.Optional[int]:
        prof = self._profiles.get(npc_id)
        if prof is None or amount <= 0:
            return None
        prof.xp_in_current_rank += amount
        prof.last_changed_seconds = now_seconds
        return prof.xp_in_current_rank

    def penalize(
        self, *, npc_id: str, amount: int,
        reason: str = "", now_seconds: float = 0.0,
    ) -> t.Optional[int]:
        prof = self._profiles.get(npc_id)
        if prof is None or amount <= 0:
            return None
        prof.xp_in_current_rank -= amount
        prof.last_changed_seconds = now_seconds
        return prof.xp_in_current_rank

    def check_promotion(
        self, *, npc_id: str, reason: str = "",
        now_seconds: float = 0.0,
    ) -> t.Optional[CareerChange]:
        prof = self._profiles.get(npc_id)
        if prof is None:
            return None
        if prof.rank_index >= MAX_RANK:
            return None
        if prof.xp_in_current_rank < self.rank_xp_step:
            return None
        old = CareerRank(
            path=prof.path, rank_index=prof.rank_index,
            label=_label_for(prof.path, prof.rank_index),
        )
        prof.rank_index += 1
        prof.xp_in_current_rank -= self.rank_xp_step
        prof.times_promoted += 1
        prof.last_changed_seconds = now_seconds
        new = CareerRank(
            path=prof.path, rank_index=prof.rank_index,
            label=_label_for(prof.path, prof.rank_index),
        )
        return CareerChange(
            npc_id=npc_id, old_rank=old, new_rank=new,
            promotion=True, reason=reason,
        )

    def check_demotion(
        self, *, npc_id: str, reason: str = "",
        now_seconds: float = 0.0,
    ) -> t.Optional[CareerChange]:
        prof = self._profiles.get(npc_id)
        if prof is None:
            return None
        if prof.rank_index <= 0:
            return None
        if prof.xp_in_current_rank > self.demotion_floor:
            return None
        old = CareerRank(
            path=prof.path, rank_index=prof.rank_index,
            label=_label_for(prof.path, prof.rank_index),
        )
        prof.rank_index -= 1
        # Reset xp into a forgiving starting state on demotion
        prof.xp_in_current_rank = 0
        prof.times_demoted += 1
        prof.last_changed_seconds = now_seconds
        new = CareerRank(
            path=prof.path, rank_index=prof.rank_index,
            label=_label_for(prof.path, prof.rank_index),
        )
        return CareerChange(
            npc_id=npc_id, old_rank=old, new_rank=new,
            promotion=False, reason=reason,
        )

    def change_path(
        self, *, npc_id: str, new_path: CareerPath,
        starting_rank: int = 0,
        now_seconds: float = 0.0,
    ) -> bool:
        prof = self._profiles.get(npc_id)
        if prof is None:
            return False
        prof.path = new_path
        prof.rank_index = max(0, min(starting_rank, MAX_RANK))
        prof.xp_in_current_rank = 0
        prof.last_changed_seconds = now_seconds
        return True

    def total_npcs(self) -> int:
        return len(self._profiles)


__all__ = [
    "DEFAULT_RANK_XP_STEP", "DEFAULT_DEMOTION_FLOOR", "MAX_RANK",
    "CareerPath", "CareerRank", "CareerExperienceEvent",
    "NPCCareerProfile", "CareerChange", "NPCCareerTrack",
]
