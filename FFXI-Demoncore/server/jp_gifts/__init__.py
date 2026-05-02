"""Job Point gift tree (post-Genkai progression).

After hitting level 99 + clearing the final genkai a player
spends Job Points on a per-job gift tree. Gifts are unlocked
at cumulative-spent thresholds (100/300/500/700/1000/1200/...).
Each gift is a permanent passive bonus that ONLY applies while
that job is the active main job.

The tree is per-job. JP earned on WAR doesn't unlock RDM gifts.

Public surface
--------------
    JobId enum (subset; matches existing job_change usage)
    Gift dataclass
    GIFT_TREE per job: ordered list of (threshold, gift)
    PlayerJpProgress
        .add_jp(job, amount)
        .total_jp(job)
        .unlocked_gifts(job) -> tuple[Gift, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class JobId(str, enum.Enum):
    WAR = "warrior"
    MNK = "monk"
    WHM = "white_mage"
    BLM = "black_mage"
    RDM = "red_mage"
    THF = "thief"
    PLD = "paladin"
    DRK = "dark_knight"
    NIN = "ninja"


@dataclasses.dataclass(frozen=True)
class Gift:
    gift_id: str
    label: str
    bonus_kind: str         # "stat" / "skill" / "trait"
    magnitude: int


# Each job has 6 sample gifts unlocked at thresholds.
# Real FFXI has ~30+ tiers; this slice is enough to stress-test
# the unlock mechanism.
GIFT_TREE: dict[JobId, list[tuple[int, Gift]]] = {
    JobId.WAR: [
        (100, Gift("war_attack_bonus", "Attack +10", "stat", 10)),
        (300, Gift("war_str_bonus", "STR +5", "stat", 5)),
        (500, Gift("war_double_atk", "Double Atk +2%", "trait", 2)),
        (700, Gift("war_axe_skill", "Axe Skill +5", "skill", 5)),
        (1000, Gift("war_aggressor_2", "Aggressor +2 Acc", "trait", 2)),
        (1500, Gift("war_max_hp", "Max HP +50", "stat", 50)),
    ],
    JobId.MNK: [
        (100, Gift("mnk_h2h_skill", "H2H Skill +5", "skill", 5)),
        (300, Gift("mnk_str_bonus", "STR +5", "stat", 5)),
        (500, Gift("mnk_kick_attacks", "Kick Attacks +2%", "trait", 2)),
        (700, Gift("mnk_chakra_boost", "Chakra +5%", "trait", 5)),
        (1000, Gift("mnk_critical_atk", "Crit Atk +2%", "trait", 2)),
        (1500, Gift("mnk_max_hp", "Max HP +50", "stat", 50)),
    ],
    JobId.WHM: [
        (100, Gift("whm_cure_potency", "Cure Potency +2%", "trait", 2)),
        (300, Gift("whm_mnd_bonus", "MND +5", "stat", 5)),
        (500, Gift("whm_divine_skill", "Divine Skill +5", "skill", 5)),
        (700, Gift("whm_max_mp", "Max MP +30", "stat", 30)),
        (1000, Gift("whm_holy_potency", "Holy Potency +5%", "trait", 5)),
        (1500, Gift("whm_auto_regen", "Auto-Regen +1", "trait", 1)),
    ],
    JobId.BLM: [
        (100, Gift("blm_int_bonus", "INT +5", "stat", 5)),
        (300, Gift("blm_elemental_skill",
                    "Elemental Skill +5", "skill", 5)),
        (500, Gift("blm_max_mp", "Max MP +30", "stat", 30)),
        (700, Gift("blm_burst_pot", "Burst Bonus +5%", "trait", 5)),
        (1000, Gift("blm_resist_silence",
                     "Silence Resist +10", "trait", 10)),
        (1500, Gift("blm_mp_returns",
                     "MP Returns +1%", "trait", 1)),
    ],
    JobId.RDM: [
        (100, Gift("rdm_int_bonus", "INT +5", "stat", 5)),
        (300, Gift("rdm_enhancing", "Enhancing Skill +5", "skill", 5)),
        (500, Gift("rdm_enfeebling", "Enfeebling Skill +5", "skill", 5)),
        (700, Gift("rdm_haste_potency",
                    "Haste Potency +5%", "trait", 5)),
        (1000, Gift("rdm_dispel_chance",
                     "Dispel Chance +5%", "trait", 5)),
        (1500, Gift("rdm_fast_cast",
                     "Fast Cast +2%", "trait", 2)),
    ],
    JobId.THF: [
        (100, Gift("thf_dex_bonus", "DEX +5", "stat", 5)),
        (300, Gift("thf_dagger_skill",
                    "Dagger Skill +5", "skill", 5)),
        (500, Gift("thf_treasure_hunter",
                    "TH +1", "trait", 1)),
        (700, Gift("thf_critical_atk",
                    "Crit Atk +2%", "trait", 2)),
        (1000, Gift("thf_evasion_bonus",
                     "Evasion +10", "stat", 10)),
        (1500, Gift("thf_steal_chance",
                     "Steal Chance +5%", "trait", 5)),
    ],
    JobId.PLD: [
        (100, Gift("pld_max_hp", "Max HP +50", "stat", 50)),
        (300, Gift("pld_shield_skill",
                    "Shield Skill +5", "skill", 5)),
        (500, Gift("pld_mnd_bonus", "MND +5", "stat", 5)),
        (700, Gift("pld_def_bonus", "Defense +20", "stat", 20)),
        (1000, Gift("pld_invincible_def",
                     "Invincible +5% Def Bonus", "trait", 5)),
        (1500, Gift("pld_cure_potency",
                     "Cure Potency +2%", "trait", 2)),
    ],
    JobId.DRK: [
        (100, Gift("drk_attack_bonus", "Attack +10", "stat", 10)),
        (300, Gift("drk_dark_skill",
                    "Dark Magic Skill +5", "skill", 5)),
        (500, Gift("drk_str_bonus", "STR +5", "stat", 5)),
        (700, Gift("drk_drain_potency",
                    "Drain Potency +5%", "trait", 5)),
        (1000, Gift("drk_blood_weapon",
                     "Blood Weapon +5%", "trait", 5)),
        (1500, Gift("drk_souleater",
                     "Souleater Damage +5%", "trait", 5)),
    ],
    JobId.NIN: [
        (100, Gift("nin_dex_bonus", "DEX +5", "stat", 5)),
        (300, Gift("nin_ninjutsu_skill",
                    "Ninjutsu Skill +5", "skill", 5)),
        (500, Gift("nin_dual_wield",
                    "Dual Wield +2%", "trait", 2)),
        (700, Gift("nin_subtle_blow",
                    "Subtle Blow +5", "trait", 5)),
        (1000, Gift("nin_evasion_bonus",
                     "Evasion +10", "stat", 10)),
        (1500, Gift("nin_utsusemi_pot",
                     "Utsusemi Recast -1s", "trait", 1)),
    ],
}


@dataclasses.dataclass
class PlayerJpProgress:
    player_id: str
    _jp_by_job: dict[JobId, int] = dataclasses.field(default_factory=dict)

    def total_jp(self, job: JobId) -> int:
        return self._jp_by_job.get(job, 0)

    def add_jp(self, *, job: JobId, amount: int) -> bool:
        if amount <= 0:
            return False
        self._jp_by_job[job] = self._jp_by_job.get(job, 0) + amount
        return True

    def unlocked_gifts(self, *, job: JobId) -> tuple[Gift, ...]:
        total = self.total_jp(job)
        tree = GIFT_TREE.get(job, [])
        return tuple(g for threshold, g in tree if total >= threshold)

    def is_gift_unlocked(self, *, job: JobId, gift_id: str) -> bool:
        return any(
            g.gift_id == gift_id for g in self.unlocked_gifts(job=job)
        )


__all__ = [
    "JobId", "Gift", "GIFT_TREE",
    "PlayerJpProgress",
]
