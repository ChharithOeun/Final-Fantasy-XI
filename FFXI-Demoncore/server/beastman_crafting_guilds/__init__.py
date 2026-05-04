"""Beastman crafting guilds — race-tinted crafting recipes.

Each beastman race has its own GUILD HALL with a charter that
mirrors a hume craft, but with race-bent recipes and exclusive
materials. These guild halls live inside the beastman cities
and grant rank-based access to higher tier recipes.

Guild kinds (race-flavored):
  YAGUDO_FORGE    - shoji-paper armor, beak-blade smithing
  QUADAV_STONEWORK- petriform armor, mineral lapidary
  LAMIA_LOOM      - serpentscale fabric, kelp dyes
  ORC_BUTCHERY    - brutebone weapons, leatherwork

Each RECIPE has:
  - tier (NOVICE → APPRENTICE → JOURNEYMAN → ARTISAN → MASTER)
  - input materials (item_id -> qty)
  - output (item_id, qty)
  - skill_required
  - exclusive flag (race-locked vs cross-race tradeable)

Players join one or more guilds, gain SKILL through crafting,
and unlock higher-tier recipes by skill threshold + rank.

Public surface
--------------
    GuildKind enum
    RecipeTier enum
    GuildRank enum     APPRENTICE → JOURNEYMAN → MASTER
    Recipe dataclass
    CraftResult dataclass
    BeastmanCraftingGuilds
        .register_recipe(guild, recipe_id, tier, inputs,
                         output_id, output_qty, skill_required,
                         exclusive_to_race)
        .join_guild(player_id, guild, race)
        .craft(player_id, guild, recipe_id, available)
        .skill_in(player_id, guild)
        .promote(player_id, guild)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.beastman_playable_races import BeastmanRace


class GuildKind(str, enum.Enum):
    YAGUDO_FORGE = "yagudo_forge"
    QUADAV_STONEWORK = "quadav_stonework"
    LAMIA_LOOM = "lamia_loom"
    ORC_BUTCHERY = "orc_butchery"


class RecipeTier(str, enum.Enum):
    NOVICE = "novice"
    APPRENTICE = "apprentice"
    JOURNEYMAN = "journeyman"
    ARTISAN = "artisan"
    MASTER = "master"


class GuildRank(str, enum.Enum):
    APPRENTICE = "apprentice"
    JOURNEYMAN = "journeyman"
    MASTER = "master"


_TIER_SKILL_FLOOR: dict[RecipeTier, int] = {
    RecipeTier.NOVICE: 0,
    RecipeTier.APPRENTICE: 25,
    RecipeTier.JOURNEYMAN: 60,
    RecipeTier.ARTISAN: 85,
    RecipeTier.MASTER: 100,
}


_TIER_SKILL_GAIN: dict[RecipeTier, int] = {
    RecipeTier.NOVICE: 3,
    RecipeTier.APPRENTICE: 2,
    RecipeTier.JOURNEYMAN: 2,
    RecipeTier.ARTISAN: 1,
    RecipeTier.MASTER: 1,
}


_RANK_SKILL_FLOOR: dict[GuildRank, int] = {
    GuildRank.APPRENTICE: 0,
    GuildRank.JOURNEYMAN: 50,
    GuildRank.MASTER: 95,
}


_GUILD_RACE: dict[GuildKind, BeastmanRace] = {
    GuildKind.YAGUDO_FORGE: BeastmanRace.YAGUDO,
    GuildKind.QUADAV_STONEWORK: BeastmanRace.QUADAV,
    GuildKind.LAMIA_LOOM: BeastmanRace.LAMIA,
    GuildKind.ORC_BUTCHERY: BeastmanRace.ORC,
}


@dataclasses.dataclass(frozen=True)
class Recipe:
    recipe_id: str
    guild: GuildKind
    tier: RecipeTier
    inputs: tuple[tuple[str, int], ...]
    output_id: str
    output_qty: int
    skill_required: int
    exclusive_to_race: bool


@dataclasses.dataclass
class _Membership:
    guild: GuildKind
    skill: int = 0
    rank: GuildRank = GuildRank.APPRENTICE


@dataclasses.dataclass(frozen=True)
class CraftResult:
    accepted: bool
    output_id: str
    output_qty: int
    new_skill: int
    consumed: tuple[tuple[str, int], ...] = ()
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class PromoteResult:
    accepted: bool
    new_rank: GuildRank
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanCraftingGuilds:
    _recipes: dict[str, Recipe] = dataclasses.field(
        default_factory=dict,
    )
    _members: dict[
        tuple[str, GuildKind], _Membership,
    ] = dataclasses.field(default_factory=dict)
    _player_race: dict[str, BeastmanRace] = dataclasses.field(
        default_factory=dict,
    )

    def register_recipe(
        self, *, recipe_id: str,
        guild: GuildKind,
        tier: RecipeTier,
        inputs: tuple[tuple[str, int], ...],
        output_id: str,
        output_qty: int,
        skill_required: int,
        exclusive_to_race: bool = True,
    ) -> t.Optional[Recipe]:
        if recipe_id in self._recipes:
            return None
        if output_qty <= 0:
            return None
        if skill_required < _TIER_SKILL_FLOOR[tier]:
            return None
        for _, qty in inputs:
            if qty <= 0:
                return None
        r = Recipe(
            recipe_id=recipe_id,
            guild=guild, tier=tier,
            inputs=inputs,
            output_id=output_id,
            output_qty=output_qty,
            skill_required=skill_required,
            exclusive_to_race=exclusive_to_race,
        )
        self._recipes[recipe_id] = r
        return r

    def join_guild(
        self, *, player_id: str,
        guild: GuildKind,
        race: BeastmanRace,
    ) -> bool:
        # Lock player race on first join, enforce on later joins
        existing = self._player_race.get(player_id)
        if existing is not None and existing != race:
            return False
        if (player_id, guild) in self._members:
            return False
        self._player_race[player_id] = race
        self._members[(player_id, guild)] = _Membership(guild=guild)
        return True

    def craft(
        self, *, player_id: str,
        guild: GuildKind,
        recipe_id: str,
        available: dict[str, int],
    ) -> CraftResult:
        recipe = self._recipes.get(recipe_id)
        if recipe is None or recipe.guild != guild:
            return CraftResult(
                False, "", 0, 0, reason="unknown recipe",
            )
        member = self._members.get((player_id, guild))
        if member is None:
            return CraftResult(
                False, "", 0, 0, reason="not in guild",
            )
        if recipe.exclusive_to_race:
            race = self._player_race[player_id]
            if race != _GUILD_RACE[guild]:
                return CraftResult(
                    False, "", 0, member.skill,
                    reason="race-locked recipe",
                )
        if member.skill < recipe.skill_required:
            return CraftResult(
                False, "", 0, member.skill,
                reason="insufficient skill",
            )
        for item_id, qty in recipe.inputs:
            if available.get(item_id, 0) < qty:
                return CraftResult(
                    False, "", 0, member.skill,
                    reason=f"missing material:{item_id}",
                )
        # Consume materials, update skill (capped at 100)
        member.skill = min(
            100,
            member.skill + _TIER_SKILL_GAIN[recipe.tier],
        )
        return CraftResult(
            accepted=True,
            output_id=recipe.output_id,
            output_qty=recipe.output_qty,
            new_skill=member.skill,
            consumed=recipe.inputs,
        )

    def skill_in(
        self, *, player_id: str, guild: GuildKind,
    ) -> int:
        m = self._members.get((player_id, guild))
        if m is None:
            return 0
        return m.skill

    def rank_in(
        self, *, player_id: str, guild: GuildKind,
    ) -> t.Optional[GuildRank]:
        m = self._members.get((player_id, guild))
        if m is None:
            return None
        return m.rank

    def promote(
        self, *, player_id: str, guild: GuildKind,
    ) -> PromoteResult:
        m = self._members.get((player_id, guild))
        if m is None:
            return PromoteResult(
                False, GuildRank.APPRENTICE,
                reason="not in guild",
            )
        order = [
            GuildRank.APPRENTICE,
            GuildRank.JOURNEYMAN,
            GuildRank.MASTER,
        ]
        idx = order.index(m.rank)
        if idx >= len(order) - 1:
            return PromoteResult(
                False, m.rank, reason="already master",
            )
        next_rank = order[idx + 1]
        if m.skill < _RANK_SKILL_FLOOR[next_rank]:
            return PromoteResult(
                False, m.rank, reason="insufficient skill",
            )
        m.rank = next_rank
        return PromoteResult(accepted=True, new_rank=next_rank)

    def total_recipes(self) -> int:
        return len(self._recipes)


__all__ = [
    "GuildKind", "RecipeTier", "GuildRank",
    "Recipe", "CraftResult", "PromoteResult",
    "BeastmanCraftingGuilds",
]
