"""Mermaid faction — sworn enemies of the Sahagin.

The mermaids are an ancient seafaring people who built
shrines, libraries, and pearl gardens across the deep
long before the Sahagin began their raids. Sahagin terror
ops have ground that civilization down — most mermaid
shrines are now ruins, most pearl gardens looted, most
mermaid songs forgotten. What's left is a furious,
hardened people who will give anything to anyone who
hurts the Sahagin.

For players, helping the mermaids is the cleanest path
into the underwater endgame: defending their last
shrines, recovering looted relics, killing Sahagin who
have wronged them. Reputation grants escalating
BLESSINGS — songs, sigils, and prayers that carry into
combat.

Per-player reputation in [-100, +100]. Hostile to mermaids
(rep <= -25) closes off the friendly NPCs entirely;
revered (rep >= +75) unlocks the highest-tier blessings
and a mermaid Trust escort.

Public surface
--------------
    MermaidStanding enum
    Blessing dataclass (frozen)
    MermaidFaction
        .reputation_of(player_id) -> int
        .adjust_reputation(player_id, delta,
                           sahagin_kill=False,
                           shrine_defended=False)
        .standing_of(player_id) -> MermaidStanding
        .blessings_unlocked(player_id) -> tuple[Blessing, ...]
        .can_invoke_trust(player_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class MermaidStanding(str, enum.Enum):
    HOSTILE = "hostile"        # rep <= -25
    DISTRUSTED = "distrusted"  # -24..0
    NEUTRAL = "neutral"        # 1..24
    TRUSTED = "trusted"        # 25..49
    HONORED = "honored"        # 50..74
    REVERED = "revered"        # 75..100


REPUTATION_FLOOR = -100
REPUTATION_CEILING = 100
HOSTILE_THRESHOLD = -25
TRUSTED_THRESHOLD = 25
HONORED_THRESHOLD = 50
REVERED_THRESHOLD = 75

# bonus rep gained for actions specifically against the Sahagin
SAHAGIN_KILL_BONUS = 2
SHRINE_DEFENDED_BONUS = 5


@dataclasses.dataclass(frozen=True)
class Blessing:
    blessing_id: str
    name: str
    min_standing: MermaidStanding
    description: str


_CATALOG: tuple[Blessing, ...] = (
    Blessing(
        blessing_id="songs_of_the_tide",
        name="Songs of the Tide",
        min_standing=MermaidStanding.TRUSTED,
        description="Restore HoT while moving in current.",
    ),
    Blessing(
        blessing_id="pearl_sigil",
        name="Pearl Sigil",
        min_standing=MermaidStanding.HONORED,
        description="Sahagin take +25% damage from you.",
    ),
    Blessing(
        blessing_id="sirens_oath",
        name="Siren's Oath",
        min_standing=MermaidStanding.REVERED,
        description=(
            "Once per day, summon mermaid escort Trust "
            "for 90s; stuns Sahagin within 20 yalms."
        ),
    ),
)


def _standing_for(rep: int) -> MermaidStanding:
    if rep <= HOSTILE_THRESHOLD:
        return MermaidStanding.HOSTILE
    if rep >= REVERED_THRESHOLD:
        return MermaidStanding.REVERED
    if rep >= HONORED_THRESHOLD:
        return MermaidStanding.HONORED
    if rep >= TRUSTED_THRESHOLD:
        return MermaidStanding.TRUSTED
    if rep >= 1:
        return MermaidStanding.NEUTRAL
    return MermaidStanding.DISTRUSTED


_STANDING_RANK: dict[MermaidStanding, int] = {
    MermaidStanding.HOSTILE: 0,
    MermaidStanding.DISTRUSTED: 1,
    MermaidStanding.NEUTRAL: 2,
    MermaidStanding.TRUSTED: 3,
    MermaidStanding.HONORED: 4,
    MermaidStanding.REVERED: 5,
}


@dataclasses.dataclass
class MermaidFaction:
    _reputation: dict[str, int] = dataclasses.field(default_factory=dict)

    def reputation_of(self, *, player_id: str) -> int:
        return self._reputation.get(player_id, 0)

    def adjust_reputation(
        self, *, player_id: str,
        delta: int,
        sahagin_kill: bool = False,
        shrine_defended: bool = False,
    ) -> int:
        if not player_id:
            return 0
        bonus = 0
        if sahagin_kill:
            bonus += SAHAGIN_KILL_BONUS
        if shrine_defended:
            bonus += SHRINE_DEFENDED_BONUS
        cur = self._reputation.get(player_id, 0)
        new = max(
            REPUTATION_FLOOR,
            min(REPUTATION_CEILING, cur + delta + bonus),
        )
        self._reputation[player_id] = new
        return new

    def standing_of(
        self, *, player_id: str,
    ) -> MermaidStanding:
        return _standing_for(self.reputation_of(player_id=player_id))

    def blessings_unlocked(
        self, *, player_id: str,
    ) -> tuple[Blessing, ...]:
        standing = self.standing_of(player_id=player_id)
        rank = _STANDING_RANK[standing]
        out = [
            b for b in _CATALOG
            if _STANDING_RANK[b.min_standing] <= rank
        ]
        return tuple(out)

    def can_invoke_trust(self, *, player_id: str) -> bool:
        return self.standing_of(
            player_id=player_id,
        ) == MermaidStanding.REVERED


__all__ = [
    "MermaidStanding", "Blessing", "MermaidFaction",
    "HOSTILE_THRESHOLD", "TRUSTED_THRESHOLD",
    "HONORED_THRESHOLD", "REVERED_THRESHOLD",
    "SAHAGIN_KILL_BONUS", "SHRINE_DEFENDED_BONUS",
]
