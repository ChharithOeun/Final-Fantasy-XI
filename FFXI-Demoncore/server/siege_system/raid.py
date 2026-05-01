"""Raid composition + reward distribution.

Per SIEGE_CAMPAIGN.md attack composition:
    Small raid:  50-100 beastmen, mostly basic, ~30 min event
    Medium raid: 200-400 beastmen, multiple NMs, ~60 min event
    Major siege: 500+ beastmen + NMs + boss, 90-180 min event

Reward distribution per the doc:
    XP scaled by tier of beastmen killed
    Defense Medal (unique participation token)
    Reputation gain in the defended nation (+200 to +500)
    Honor gain for high-contribution defenders
    Chance at unique drops from beastman bosses
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class RaidSize(str, enum.Enum):
    SMALL = "small"
    MEDIUM = "medium"
    MAJOR = "major"


@dataclasses.dataclass
class RaidComposition:
    raid_size: RaidSize
    beastmen_count: int
    nm_count: int
    has_boss: bool
    duration_minutes: int


@dataclasses.dataclass
class RaidReward:
    xp: int
    defense_medals: int
    nation_rep_gain: int
    honor_gain: int
    bonus_drop_chance: float        # 0..1
    raid_size: RaidSize


# Reward bases per raid size
DEFENSE_MEDAL_BASE = {
    RaidSize.SMALL: 1,
    RaidSize.MEDIUM: 3,
    RaidSize.MAJOR: 5,
}
REP_GAIN_BASE = {
    RaidSize.SMALL: 200,
    RaidSize.MEDIUM: 350,
    RaidSize.MAJOR: 500,
}
HONOR_HIGH_CONTRIB_THRESHOLD = 0.20    # >=20% contribution = "high"
HONOR_GAIN_HIGH_CONTRIB = 50           # +50 honor for heroic defense


class RaidComposer:
    """Builds RaidComposition from a vulnerability score (0..100)."""

    def compose(self, vulnerability_score: float) -> RaidComposition:
        """Lower score (well-defended nation) = smaller raid.
        Higher score (vulnerable nation) = bigger raid.

        However per the doc: a long-untouched, well-doing nation
        attracts the BIG raid when it does come. We honor the simple
        version here — vulnerability scales the raid size — and let
        the caller layer additional 'long-quiet bonus' modifiers.
        """
        v = max(0.0, min(100.0, vulnerability_score))

        if v < 35:
            return RaidComposition(
                raid_size=RaidSize.SMALL,
                beastmen_count=75,         # midpoint of 50-100
                nm_count=1,
                has_boss=False,
                duration_minutes=30,
            )
        if v < 70:
            return RaidComposition(
                raid_size=RaidSize.MEDIUM,
                beastmen_count=300,        # midpoint of 200-400
                nm_count=4,
                has_boss=False,
                duration_minutes=60,
            )
        return RaidComposition(
            raid_size=RaidSize.MAJOR,
            beastmen_count=600,
            nm_count=8,
            has_boss=True,
            duration_minutes=120,
        )


class RaidRewardDistributor:
    """Computes per-defender rewards from a raid outcome."""

    def reward_defender(self,
                         *,
                         raid_size: RaidSize,
                         beastmen_killed: int,
                         nm_killed: int,
                         contribution_pct: float) -> RaidReward:
        """Compute one defender's reward.

        contribution_pct - 0.0..1.0; share of total damage / kills
                            attributed to this defender.
        """
        contribution_pct = max(0.0, min(1.0, contribution_pct))

        # XP: 1000 per beastman + 5000 per NM, scaled by contribution.
        xp = int((beastmen_killed * 1000 + nm_killed * 5000) * contribution_pct)

        # Defense Medals: base for participation, scaled by raid size
        medals = DEFENSE_MEDAL_BASE[raid_size]
        # High-contribution defenders get an extra medal in major raids
        if raid_size == RaidSize.MAJOR and contribution_pct >= HONOR_HIGH_CONTRIB_THRESHOLD:
            medals += 1

        # Reputation: base for raid size, scaled mildly by contribution
        rep_gain = int(REP_GAIN_BASE[raid_size]
                        * (0.5 + 0.5 * contribution_pct))

        # Honor: only granted to high-contribution defenders
        honor_gain = (HONOR_GAIN_HIGH_CONTRIB
                      if contribution_pct >= HONOR_HIGH_CONTRIB_THRESHOLD
                      else 0)

        # Bonus drops: small base + scaled by raid size + contribution
        bonus_drop_chance = {
            RaidSize.SMALL: 0.05,
            RaidSize.MEDIUM: 0.10,
            RaidSize.MAJOR: 0.20,
        }[raid_size] * (0.5 + 0.5 * contribution_pct)

        return RaidReward(
            xp=xp,
            defense_medals=medals,
            nation_rep_gain=rep_gain,
            honor_gain=honor_gain,
            bonus_drop_chance=bonus_drop_chance,
            raid_size=raid_size,
        )
