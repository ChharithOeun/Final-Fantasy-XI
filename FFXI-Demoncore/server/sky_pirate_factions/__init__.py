"""Sky pirate factions — aerial faction registry.

Surface and underwater have organized factions; the sky
needs the same. Three factions canonical to the FFXI
universe (mapped to demoncore aerial scope):

  CORSAIRS_OF_THE_GALE   — Tarutaru-flag fast skiff fleet,
                           focused on raiding cargo runs at
                           LOW/MID bands.
  IRON_WING_DOMINION     — Bastok-aligned militaristic
                           zeppelin fleet at MID/HIGH bands;
                           hunts the Corsairs.
  WYVERN_LORDS           — Half-pirate / half-cult dragon
                           riders at HIGH/STRATOSPHERE;
                           neutral until provoked, then
                           overwhelming.

Each player has per-faction reputation in [-100, +100].
Hostile factions attack on sight. Each faction has a
PREFERRED_BANDS set — they only spawn aerial encounters in
those bands.

Public surface
--------------
    SkyFaction enum
    FactionProfile dataclass (frozen)
    SkyPirateFactions
        .get_profile(faction) -> FactionProfile
        .reputation_of(player_id, faction) -> int
        .adjust_reputation(player_id, faction, delta)
        .is_hostile(player_id, faction) -> bool
        .factions_active_at(band) -> tuple[SkyFaction, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SkyFaction(str, enum.Enum):
    CORSAIRS_OF_THE_GALE = "corsairs_of_the_gale"
    IRON_WING_DOMINION = "iron_wing_dominion"
    WYVERN_LORDS = "wyvern_lords"


HOSTILE_REPUTATION_THRESHOLD = -25
REPUTATION_FLOOR = -100
REPUTATION_CEILING = 100


@dataclasses.dataclass(frozen=True)
class FactionProfile:
    faction: SkyFaction
    name: str
    flagship_class: str
    preferred_bands: frozenset[int]
    rival: t.Optional[SkyFaction]


_PROFILES: dict[SkyFaction, FactionProfile] = {
    SkyFaction.CORSAIRS_OF_THE_GALE: FactionProfile(
        faction=SkyFaction.CORSAIRS_OF_THE_GALE,
        name="Corsairs of the Gale",
        flagship_class="skiff",
        preferred_bands=frozenset({1, 2}),
        rival=SkyFaction.IRON_WING_DOMINION,
    ),
    SkyFaction.IRON_WING_DOMINION: FactionProfile(
        faction=SkyFaction.IRON_WING_DOMINION,
        name="Iron Wing Dominion",
        flagship_class="dreadnought",
        preferred_bands=frozenset({2, 3}),
        rival=SkyFaction.CORSAIRS_OF_THE_GALE,
    ),
    SkyFaction.WYVERN_LORDS: FactionProfile(
        faction=SkyFaction.WYVERN_LORDS,
        name="Wyvern Lords",
        flagship_class="dragon_mount",
        preferred_bands=frozenset({3, 4}),
        rival=None,  # neutral until provoked
    ),
}


@dataclasses.dataclass
class SkyPirateFactions:
    # player_id -> {faction: rep}
    _reputation: dict[str, dict[SkyFaction, int]] = dataclasses.field(
        default_factory=dict,
    )

    def get_profile(
        self, *, faction: SkyFaction,
    ) -> FactionProfile:
        return _PROFILES[faction]

    def reputation_of(
        self, *, player_id: str, faction: SkyFaction,
    ) -> int:
        return self._reputation.get(player_id, {}).get(faction, 0)

    def adjust_reputation(
        self, *, player_id: str,
        faction: SkyFaction, delta: int,
    ) -> int:
        if not player_id:
            return 0
        per = self._reputation.setdefault(player_id, {})
        cur = per.get(faction, 0)
        new = max(REPUTATION_FLOOR, min(REPUTATION_CEILING, cur + delta))
        per[faction] = new
        # rival faction reputation moves opposite (smaller magnitude)
        profile = _PROFILES[faction]
        if profile.rival is not None:
            rival_cur = per.get(profile.rival, 0)
            per[profile.rival] = max(
                REPUTATION_FLOOR,
                min(REPUTATION_CEILING, rival_cur - (delta // 2)),
            )
        return new

    def is_hostile(
        self, *, player_id: str, faction: SkyFaction,
    ) -> bool:
        rep = self.reputation_of(player_id=player_id, faction=faction)
        return rep <= HOSTILE_REPUTATION_THRESHOLD

    def factions_active_at(
        self, *, band: int,
    ) -> tuple[SkyFaction, ...]:
        return tuple(
            f for f, p in _PROFILES.items()
            if band in p.preferred_bands
        )


__all__ = [
    "SkyFaction", "FactionProfile", "SkyPirateFactions",
    "HOSTILE_REPUTATION_THRESHOLD",
    "REPUTATION_FLOOR", "REPUTATION_CEILING",
]
