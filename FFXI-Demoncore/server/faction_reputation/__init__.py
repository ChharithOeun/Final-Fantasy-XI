"""Per-faction player reputation.

Separate from honor_reputation (which is the player's WORLD-WIDE
moral standing). Faction reputation is per-faction: how do the
Yagudo, the Goblins, the Bastok Mythril Musketeers, the Tenshodo,
each independently feel about this specific player?

The faction's AI agents read the player's faction-rep when
deciding:
* Whether to aggro on sight (negative rep -> attack)
* Whether to offer peaceful interaction (high rep -> open shops,
  share quests, accept negotiation)
* Whether to remember and bring up past deeds (linked to
  entity_memory's per-NPC store, but the faction-level number
  is the aggregate sentiment)

Faction kinds
-------------
There are three flavors of faction:
    BEASTMEN — the 11 tribes from beastmen_factions
    NATION — player nations + Jeuno + Kazham + etc.
    GUILD — Tenshodo, Mythril Musketeers, Magna Carta, crafting
            guilds, mercenary houses

Reputation scale
----------------
The reputation value is in [-1000, +1000] with these bands:
    -1000..-501  KILL_ON_SIGHT
    -500..-201   HOSTILE
    -200..-51    UNFRIENDLY
    -50..+50     NEUTRAL  (default)
    +51..+200    FRIENDLY
    +201..+500   ALLIED
    +501..+1000  HERO_OF_THE_FACTION

Public surface
--------------
    FactionKind enum
    Faction dataclass
    ReputationBand enum
    band_for_value(value) -> ReputationBand
    PlayerFactionReputation
        .adjust(faction_id, delta) / .set(faction_id, value)
        .value(faction_id) / .band(faction_id)
        .can_enter_homeland(faction_id) etc convenience
    FactionRegistry — global; holds Faction definitions
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


REP_MIN = -1000
REP_MAX = 1000


class FactionKind(str, enum.Enum):
    BEASTMEN = "beastmen"
    NATION = "nation"
    GUILD = "guild"


@dataclasses.dataclass(frozen=True)
class Faction:
    faction_id: str
    label: str
    kind: FactionKind
    homeland_zone_id: str = ""
    notes: str = ""


class ReputationBand(str, enum.Enum):
    KILL_ON_SIGHT = "kill_on_sight"
    HOSTILE = "hostile"
    UNFRIENDLY = "unfriendly"
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"
    ALLIED = "allied"
    HERO_OF_THE_FACTION = "hero_of_the_faction"


def band_for_value(value: int) -> ReputationBand:
    if value <= -501:
        return ReputationBand.KILL_ON_SIGHT
    if value <= -201:
        return ReputationBand.HOSTILE
    if value <= -51:
        return ReputationBand.UNFRIENDLY
    if value <= 50:
        return ReputationBand.NEUTRAL
    if value <= 200:
        return ReputationBand.FRIENDLY
    if value <= 500:
        return ReputationBand.ALLIED
    return ReputationBand.HERO_OF_THE_FACTION


# Bands at which the faction will let the player into their
# homeland zone or interact with their guild master.
_FRIENDLY_BANDS: frozenset[ReputationBand] = frozenset({
    ReputationBand.NEUTRAL, ReputationBand.FRIENDLY,
    ReputationBand.ALLIED, ReputationBand.HERO_OF_THE_FACTION,
})

_HOSTILE_BANDS: frozenset[ReputationBand] = frozenset({
    ReputationBand.KILL_ON_SIGHT, ReputationBand.HOSTILE,
})


@dataclasses.dataclass(frozen=True)
class AdjustResult:
    new_value: int
    new_band: ReputationBand
    band_changed: bool
    delta_applied: int


@dataclasses.dataclass
class PlayerFactionReputation:
    player_id: str
    _values: dict[str, int] = dataclasses.field(default_factory=dict)

    def value(self, faction_id: str) -> int:
        return self._values.get(faction_id, 0)

    def band(self, faction_id: str) -> ReputationBand:
        return band_for_value(self.value(faction_id))

    def adjust(
        self, *, faction_id: str, delta: int,
    ) -> AdjustResult:
        prev = self.value(faction_id)
        prev_band = band_for_value(prev)
        new = max(REP_MIN, min(REP_MAX, prev + delta))
        applied = new - prev
        new_band = band_for_value(new)
        self._values[faction_id] = new
        return AdjustResult(
            new_value=new, new_band=new_band,
            band_changed=(new_band != prev_band),
            delta_applied=applied,
        )

    def set(self, *, faction_id: str, value: int) -> AdjustResult:
        clamped = max(REP_MIN, min(REP_MAX, value))
        prev_band = self.band(faction_id)
        self._values[faction_id] = clamped
        new_band = band_for_value(clamped)
        return AdjustResult(
            new_value=clamped, new_band=new_band,
            band_changed=(new_band != prev_band),
            delta_applied=clamped - self.value(faction_id),
        )

    def is_hostile(self, faction_id: str) -> bool:
        return self.band(faction_id) in _HOSTILE_BANDS

    def is_friendly(self, faction_id: str) -> bool:
        return self.band(faction_id) in _FRIENDLY_BANDS

    def can_enter_homeland(self, faction_id: str) -> bool:
        """Player can step into the faction's homeland zone."""
        return not self.is_hostile(faction_id)

    def can_use_vendors(self, faction_id: str) -> bool:
        """NEUTRAL or above. UNFRIENDLY refuses service."""
        b = self.band(faction_id)
        return b in _FRIENDLY_BANDS

    def can_join_alliance(self, faction_id: str) -> bool:
        """Allied+ only — joint operations vs. third parties."""
        b = self.band(faction_id)
        return b in (
            ReputationBand.ALLIED,
            ReputationBand.HERO_OF_THE_FACTION,
        )

    def all_factions_with_rep(self) -> tuple[str, ...]:
        return tuple(self._values.keys())


# --------------------------------------------------------------------
# Faction catalog — sample seed
# --------------------------------------------------------------------
def _build_faction_catalog() -> tuple[Faction, ...]:
    return (
        # Beastmen tribes (lined up with beastmen_factions module)
        Faction("orc", "Orcish Empire", FactionKind.BEASTMEN,
                homeland_zone_id="ranguemont_pass"),
        Faction("quadav", "Quadav Confederacy", FactionKind.BEASTMEN,
                homeland_zone_id="palborough_mines"),
        Faction("yagudo", "Yagudo Theomilitary",
                FactionKind.BEASTMEN,
                homeland_zone_id="castle_oztroja"),
        Faction("goblin", "Goblin Mercantile",
                FactionKind.BEASTMEN,
                homeland_zone_id="movalpolos"),
        Faction("sahagin", "Sahagin Sea-Lords",
                FactionKind.BEASTMEN, homeland_zone_id="sea_serpent_grotto"),
        Faction("tonberry", "Tonberry Recluse",
                FactionKind.BEASTMEN,
                homeland_zone_id="kuftal_tunnel"),
        Faction("antica", "Antica Hivemind",
                FactionKind.BEASTMEN, homeland_zone_id="garlaige_citadel"),
        Faction("mamool_ja", "Mamool Ja Savagery",
                FactionKind.BEASTMEN, homeland_zone_id="periqia"),
        Faction("troll", "Troll Mercenaries",
                FactionKind.BEASTMEN, homeland_zone_id="grauberg"),
        Faction("lamia", "Lamia Coven",
                FactionKind.BEASTMEN, homeland_zone_id="halvung"),
        Faction("merrow", "Merrow", FactionKind.BEASTMEN,
                homeland_zone_id="cirdas_caverns"),
        # Nations
        Faction("bastok", "Bastok Republic",
                FactionKind.NATION, homeland_zone_id="bastok_markets"),
        Faction("san_doria", "Kingdom of San d'Oria",
                FactionKind.NATION, homeland_zone_id="south_san_doria"),
        Faction("windurst", "Federation of Windurst",
                FactionKind.NATION, homeland_zone_id="windurst_waters"),
        Faction("jeuno", "Grand Duchy of Jeuno",
                FactionKind.NATION, homeland_zone_id="ru_lude_gardens"),
        Faction("kazham", "Kazham Mithra",
                FactionKind.NATION, homeland_zone_id="kazham"),
        # Guilds
        Faction("tenshodo", "Tenshodo Mercantile",
                FactionKind.GUILD, homeland_zone_id="lower_jeuno"),
        Faction("mythril_musketeers", "Mythril Musketeers",
                FactionKind.GUILD, homeland_zone_id="bastok_metalworks"),
        Faction("crafters_guild_smithing", "Smithing Guild",
                FactionKind.GUILD, homeland_zone_id="bastok_metalworks"),
        Faction("crafters_guild_alchemy", "Alchemy Guild",
                FactionKind.GUILD, homeland_zone_id="bastok_markets"),
        Faction("crafters_guild_woodworking", "Woodworking Guild",
                FactionKind.GUILD, homeland_zone_id="northern_san_doria"),
        Faction("magna_carta", "Magna Carta", FactionKind.GUILD,
                homeland_zone_id="ru_lude_gardens"),
    )


@dataclasses.dataclass
class FactionRegistry:
    _factions: dict[str, Faction] = dataclasses.field(
        default_factory=dict,
    )

    def __post_init__(self) -> None:
        for f in _build_faction_catalog():
            self._factions[f.faction_id] = f

    def get(self, faction_id: str) -> t.Optional[Faction]:
        return self._factions.get(faction_id)

    def by_kind(self, kind: FactionKind) -> tuple[Faction, ...]:
        return tuple(
            f for f in self._factions.values() if f.kind == kind
        )

    def all_factions(self) -> tuple[Faction, ...]:
        return tuple(self._factions.values())

    def total(self) -> int:
        return len(self._factions)

    def register(self, faction: Faction) -> Faction:
        self._factions[faction.faction_id] = faction
        return faction


__all__ = [
    "REP_MIN", "REP_MAX",
    "FactionKind", "Faction",
    "ReputationBand", "band_for_value",
    "AdjustResult", "PlayerFactionReputation",
    "FactionRegistry",
]
