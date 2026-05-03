"""Mob-on-mob combat — autonomous fights between rival mobs.

Beastmen tribes raid each other. Undead claim territory from
goblins. Pirates hunt sahagin. The world isn't a frozen tableau
waiting for player intervention — it has its own conflicts.

This module models autonomous mob-on-mob engagements:

* When two HOSTILE-TO-EACH-OTHER mob groups are in proximity
  and AT LEAST ONE has aggression-toward-the-other, they
  engage.
* Fights resolve probabilistically based on combined level *
  count of each side, with random variance.
* Survivors loot the dead (loot accrues to the winning side).
* Players who arrive AFTER a fight see corpses; if they help
  finish a wounded survivor they get partial XP credit.

Hostility matrix
----------------
A static `_HOSTILITY` table declares which faction pairs are
mutually hostile. The faction AI in `beastmen_factions` can
mutate this dynamically (alliance / war declaration), but this
module owns the static defaults.

Public surface
--------------
    MobGroup dataclass — a side in a fight
    EngageResult enum
    EngagementOutcome dataclass
    MobVsMobRegistry
        .register_group(group)
        .check_engagement(zone, group_a, group_b, rng)
        .resolve_fight(group_a, group_b, rng)
        .pickup_corpse_xp(player_id, corpse_id, finisher: bool)
"""
from __future__ import annotations

import dataclasses
import enum
import random
import typing as t


# Default hostility map. (a, b) hostile if either ordering is
# in the set. Symmetric.
_HOSTILE_PAIRS: frozenset[tuple[str, str]] = frozenset({
    ("orc", "san_doria"),
    ("orc", "goblin"),
    ("quadav", "bastok"),
    ("quadav", "antica"),
    ("yagudo", "windurst"),
    ("yagudo", "tonberry"),
    ("goblin", "sahagin"),
    ("undead", "goblin"),
    ("undead", "tonberry"),
    ("antica", "mamool_ja"),
    ("troll", "mamool_ja"),
    ("lamia", "merrow"),
    ("pirate", "sahagin"),
    ("pirate", "merrow"),
    ("rogue_automaton", "goblin"),
})


def are_hostile(faction_a: str, faction_b: str) -> bool:
    if faction_a == faction_b:
        return False
    return (
        (faction_a, faction_b) in _HOSTILE_PAIRS
        or (faction_b, faction_a) in _HOSTILE_PAIRS
    )


# Default proximity to engage (tile distance between group
# centroids).
DEFAULT_ENGAGE_RANGE = 25


class EngageResult(str, enum.Enum):
    NONE = "none"
    ENGAGED = "engaged"


class FightWinner(str, enum.Enum):
    SIDE_A = "side_a"
    SIDE_B = "side_b"
    MUTUAL_WIPE = "mutual_wipe"
    DRAW = "draw"            # both sides retreat


@dataclasses.dataclass(frozen=True)
class MobGroup:
    group_id: str
    faction_id: str
    zone_id: str
    centroid_tile: tuple[int, int]
    member_count: int
    avg_level: int
    aggression: int = 50            # 0..100; influences engage chance


@dataclasses.dataclass(frozen=True)
class Corpse:
    corpse_id: str
    faction_id: str
    avg_level: int
    finisher_required: bool = False
    xp_reward_full: int = 100
    looted: bool = False


@dataclasses.dataclass(frozen=True)
class EngagementOutcome:
    accepted: bool
    result: EngageResult
    winner: t.Optional[FightWinner] = None
    side_a_remaining: int = 0
    side_b_remaining: int = 0
    corpses: tuple[Corpse, ...] = ()
    notes: str = ""


@dataclasses.dataclass(frozen=True)
class CorpseXPResult:
    accepted: bool
    xp_awarded: int = 0
    reason: t.Optional[str] = None


def _within_range(
    a: tuple[int, int], b: tuple[int, int], r: int,
) -> bool:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) <= r * r


@dataclasses.dataclass
class MobVsMobRegistry:
    engage_range_tiles: int = DEFAULT_ENGAGE_RANGE
    _groups: dict[str, MobGroup] = dataclasses.field(
        default_factory=dict,
    )
    _corpses: dict[str, Corpse] = dataclasses.field(
        default_factory=dict,
    )
    _corpse_xp_paid: set[
        tuple[str, str],   # (player_id, corpse_id)
    ] = dataclasses.field(default_factory=set)
    _next_corpse_id: int = 0

    def register_group(self, group: MobGroup) -> MobGroup:
        self._groups[group.group_id] = group
        return group

    def get_group(
        self, group_id: str,
    ) -> t.Optional[MobGroup]:
        return self._groups.get(group_id)

    def check_engagement(
        self, *, group_a_id: str, group_b_id: str,
        rng: t.Optional[random.Random] = None,
    ) -> EngagementOutcome:
        rng = rng or random.Random()
        a = self._groups.get(group_a_id)
        b = self._groups.get(group_b_id)
        if a is None or b is None:
            return EngagementOutcome(
                accepted=False, result=EngageResult.NONE,
                notes="unknown group",
            )
        if a.zone_id != b.zone_id:
            return EngagementOutcome(
                accepted=False, result=EngageResult.NONE,
                notes="not in same zone",
            )
        if not are_hostile(a.faction_id, b.faction_id):
            return EngagementOutcome(
                accepted=False, result=EngageResult.NONE,
                notes="not hostile",
            )
        if not _within_range(
            a.centroid_tile, b.centroid_tile,
            self.engage_range_tiles,
        ):
            return EngagementOutcome(
                accepted=False, result=EngageResult.NONE,
                notes="not in range",
            )
        # Engage chance scales with combined aggression
        chance = (a.aggression + b.aggression) / 2
        if rng.randint(1, 100) > chance:
            return EngagementOutcome(
                accepted=False, result=EngageResult.NONE,
                notes="aggression check failed",
            )
        return EngagementOutcome(
            accepted=True, result=EngageResult.ENGAGED,
            notes="hostile groups in range",
        )

    def resolve_fight(
        self, *, group_a_id: str, group_b_id: str,
        rng: t.Optional[random.Random] = None,
    ) -> EngagementOutcome:
        """Compute the fight outcome. Returns survivors + corpses."""
        rng = rng or random.Random()
        a = self._groups.get(group_a_id)
        b = self._groups.get(group_b_id)
        if a is None or b is None:
            return EngagementOutcome(
                accepted=False, result=EngageResult.NONE,
                notes="unknown group",
            )
        # Power = level * count, +/- 30% variance
        power_a = (
            a.avg_level * a.member_count
            * rng.uniform(0.85, 1.15)
        )
        power_b = (
            b.avg_level * b.member_count
            * rng.uniform(0.85, 1.15)
        )
        if abs(power_a - power_b) / max(power_a, power_b, 1) < 0.05:
            # Very close powers -> both retreat
            winner = FightWinner.DRAW
            survivors_a = a.member_count
            survivors_b = b.member_count
            corpses: list[Corpse] = []
        else:
            ratio = power_a / max(1.0, power_b)
            if ratio > 1:
                winner = FightWinner.SIDE_A
                # Loser loses 60-100% of members
                losses_b = int(round(b.member_count * (
                    0.6 + 0.4 * min(1.0, (ratio - 1.0))
                )))
                survivors_b = max(0, b.member_count - losses_b)
                # Winner takes 10-30% losses
                losses_a = int(round(
                    a.member_count * rng.uniform(0.1, 0.3),
                ))
                survivors_a = max(0, a.member_count - losses_a)
            else:
                winner = FightWinner.SIDE_B
                ratio_b = 1.0 / ratio
                losses_a = int(round(a.member_count * (
                    0.6 + 0.4 * min(1.0, (ratio_b - 1.0))
                )))
                survivors_a = max(0, a.member_count - losses_a)
                losses_b = int(round(
                    b.member_count * rng.uniform(0.1, 0.3),
                ))
                survivors_b = max(0, b.member_count - losses_b)
            # Corpses generated
            corpses = []
            for grp, losses in (
                (a, a.member_count - survivors_a),
                (b, b.member_count - survivors_b),
            ):
                for _ in range(losses):
                    cid = f"corpse_{self._next_corpse_id}"
                    self._next_corpse_id += 1
                    c = Corpse(
                        corpse_id=cid, faction_id=grp.faction_id,
                        avg_level=grp.avg_level,
                        xp_reward_full=grp.avg_level * 10,
                    )
                    self._corpses[cid] = c
                    corpses.append(c)
            # Mutual wipe check
            if survivors_a == 0 and survivors_b == 0:
                winner = FightWinner.MUTUAL_WIPE
        # Update groups with new member counts
        if survivors_a == 0:
            self._groups.pop(group_a_id, None)
        else:
            self._groups[group_a_id] = dataclasses.replace(
                a, member_count=survivors_a,
            )
        if survivors_b == 0:
            self._groups.pop(group_b_id, None)
        else:
            self._groups[group_b_id] = dataclasses.replace(
                b, member_count=survivors_b,
            )
        return EngagementOutcome(
            accepted=True, result=EngageResult.ENGAGED,
            winner=winner,
            side_a_remaining=survivors_a,
            side_b_remaining=survivors_b,
            corpses=tuple(corpses),
        )

    def pickup_corpse_xp(
        self, *, player_id: str, corpse_id: str,
        was_finisher: bool = False,
    ) -> CorpseXPResult:
        c = self._corpses.get(corpse_id)
        if c is None:
            return CorpseXPResult(
                accepted=False, reason="no such corpse",
            )
        key = (player_id, corpse_id)
        if key in self._corpse_xp_paid:
            return CorpseXPResult(
                accepted=False, reason="already credited",
            )
        # Finisher = found a survivor and finished it -> full xp
        # Non-finisher = found a corpse cold -> 25% xp
        xp = c.xp_reward_full if was_finisher else (
            c.xp_reward_full // 4
        )
        self._corpse_xp_paid.add(key)
        return CorpseXPResult(accepted=True, xp_awarded=xp)

    def total_groups(self) -> int:
        return len(self._groups)

    def total_corpses(self) -> int:
        return len(self._corpses)


__all__ = [
    "DEFAULT_ENGAGE_RANGE",
    "EngageResult", "FightWinner",
    "are_hostile",
    "MobGroup", "Corpse",
    "EngagementOutcome", "CorpseXPResult",
    "MobVsMobRegistry",
]
