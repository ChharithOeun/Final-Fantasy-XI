"""Master Trials — merit-rewarding training trials.

Per-job objective lists that the player completes to earn merit
points + cosmetic rewards. Each trial is repeatable (with rate-
limit cooldown) so high-end players can use them as a steady
merit drip while soloing or running with parties.

Trial shapes:
    KILL_FAMILY    — kill N mobs of a specific family/tier
    KILL_NM        — kill a specific NM N times
    DEAL_DAMAGE_WS — accumulate N damage with a weapon skill
    LAND_SPELL     — land a tier-V+ spell N times
    PARTICIPATE    — complete N runs of a named instance

Public surface
--------------
    TrialKind enum
    TrialReward dataclass
    MasterTrial dataclass / TRIAL_CATALOG
    PlayerMasterTrials
        .progress(trial_id, amount) -> ProgressResult
        .claim_complete(trial_id) -> ClaimResult
        .reset_for_repeat(trial_id) -> bool   (after cooldown)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# A trial cooldown is a Vana'diel day: 24 vana hours.
TRIAL_COOLDOWN_VANA_HOURS = 24


class TrialKind(str, enum.Enum):
    KILL_FAMILY = "kill_family"
    KILL_NM = "kill_nm"
    DEAL_DAMAGE_WS = "deal_damage_ws"
    LAND_SPELL = "land_spell"
    PARTICIPATE = "participate"


@dataclasses.dataclass(frozen=True)
class TrialReward:
    merit_points: int
    cosmetic_item_id: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class MasterTrial:
    trial_id: str
    job: str           # "warrior" / "white_mage" / etc, or "*"
    kind: TrialKind
    target: str        # mob family / NM id / WS name / spell id
    quantity: int
    reward: TrialReward
    label: str = ""


# Sample trial catalog covering 6 jobs × 3 trials = 18 entries
def _t(job: str, kind: TrialKind, target: str, qty: int,
        merits: int, cosmetic: t.Optional[str], label: str
        ) -> MasterTrial:
    return MasterTrial(
        trial_id=f"trial_{job}_{kind.value}_{target}".replace(" ", "_"),
        job=job, kind=kind, target=target, quantity=qty,
        reward=TrialReward(merit_points=merits,
                            cosmetic_item_id=cosmetic),
        label=label,
    )


TRIAL_CATALOG: tuple[MasterTrial, ...] = (
    _t("warrior", TrialKind.KILL_FAMILY, "orc", 50, 5, None,
        "Slay 50 orcs"),
    _t("warrior", TrialKind.DEAL_DAMAGE_WS, "raging_rush",
        500_000, 10, "warrior_aggressive_cape",
        "Deal 500k damage with Raging Rush"),
    _t("warrior", TrialKind.KILL_NM, "fafnir", 1, 15,
        "warrior_dragonslayer_belt",
        "Defeat Fafnir"),
    _t("monk", TrialKind.KILL_FAMILY, "elemental", 30, 5, None,
        "Defeat 30 elementals (Hand-to-Hand training)"),
    _t("monk", TrialKind.DEAL_DAMAGE_WS, "asuran_fists",
        300_000, 10, "monk_centennial_belt",
        "Deal 300k damage with Asuran Fists"),
    _t("monk", TrialKind.PARTICIPATE, "limbus_apollyon", 5, 12,
        "monk_apollyon_legion_belt",
        "Complete 5 Apollyon Limbus runs"),
    _t("white_mage", TrialKind.LAND_SPELL, "cure_v", 100, 8,
        "whm_healing_charm", "Land Cure V 100 times"),
    _t("white_mage", TrialKind.KILL_FAMILY, "undead", 40, 6, None,
        "Defeat 40 undead with Banish"),
    _t("white_mage", TrialKind.PARTICIPATE, "salvage_runs", 3, 10,
        "whm_arch_band",
        "Complete 3 Salvage runs as healer"),
    _t("black_mage", TrialKind.LAND_SPELL, "fire_v", 75, 8,
        "blm_archmages_charm", "Land Fire V 75 times"),
    _t("black_mage", TrialKind.DEAL_DAMAGE_WS,
        "magic_burst_skillchain", 1_000_000, 12,
        "blm_magic_burst_belt",
        "Burst for 1m damage in skillchain windows"),
    _t("black_mage", TrialKind.KILL_NM, "khimaira_t3", 3, 15, None,
        "Defeat Khimaira T3 three times"),
    _t("red_mage", TrialKind.LAND_SPELL, "dispel_ii", 50, 6,
        "rdm_enfeeble_charm", "Successfully dispel 50 buffs"),
    _t("red_mage", TrialKind.DEAL_DAMAGE_WS, "vorpal_blade",
        200_000, 8, None,
        "Deal 200k damage with Vorpal Blade"),
    _t("red_mage", TrialKind.PARTICIPATE, "voidwatch_runs", 5, 10,
        "rdm_voidcore_belt", "Complete 5 Voidwatch runs"),
    _t("thief", TrialKind.KILL_FAMILY, "crab", 40, 5, None,
        "Defeat 40 crabs with Sneak Attack"),
    _t("thief", TrialKind.DEAL_DAMAGE_WS, "rudras_storm",
        400_000, 12, "thf_assassins_belt",
        "Deal 400k damage with Rudra's Storm"),
    _t("thief", TrialKind.KILL_NM, "shikiri_warden", 1, 15,
        "thf_treasure_belt", "Defeat Shikiri Warden"),
)


TRIAL_BY_ID: dict[str, MasterTrial] = {
    t.trial_id: t for t in TRIAL_CATALOG
}


@dataclasses.dataclass(frozen=True)
class ProgressResult:
    accepted: bool
    progress: int = 0
    target: int = 0
    completed: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ClaimResult:
    accepted: bool
    merit_points_awarded: int = 0
    cosmetic_item_id: t.Optional[str] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class _TrialState:
    progress: int = 0
    completed: bool = False
    claimed: bool = False
    on_cooldown_until_vana_hour: int = -1


@dataclasses.dataclass
class PlayerMasterTrials:
    player_id: str
    _state: dict[str, _TrialState] = dataclasses.field(default_factory=dict)

    def _get(self, trial_id: str) -> _TrialState:
        s = self._state.get(trial_id)
        if s is None:
            s = _TrialState()
            self._state[trial_id] = s
        return s

    def progress(
        self, *, trial_id: str, amount: int = 1,
        current_vana_hour: int = 0,
    ) -> ProgressResult:
        trial = TRIAL_BY_ID.get(trial_id)
        if trial is None:
            return ProgressResult(False, reason="unknown trial")
        s = self._get(trial_id)
        if s.completed and not s.claimed:
            return ProgressResult(
                False, progress=s.progress, target=trial.quantity,
                completed=True, reason="claim required",
            )
        if (s.on_cooldown_until_vana_hour > 0
                and current_vana_hour < s.on_cooldown_until_vana_hour):
            return ProgressResult(False, reason="trial on cooldown")
        s.progress = min(s.progress + max(0, amount), trial.quantity)
        if s.progress >= trial.quantity:
            s.completed = True
        return ProgressResult(
            accepted=True, progress=s.progress,
            target=trial.quantity, completed=s.completed,
        )

    def claim_complete(self, *, trial_id: str) -> ClaimResult:
        trial = TRIAL_BY_ID.get(trial_id)
        if trial is None:
            return ClaimResult(False, reason="unknown trial")
        s = self._get(trial_id)
        if not s.completed:
            return ClaimResult(False, reason="trial not complete")
        if s.claimed:
            return ClaimResult(False, reason="already claimed")
        s.claimed = True
        return ClaimResult(
            accepted=True,
            merit_points_awarded=trial.reward.merit_points,
            cosmetic_item_id=trial.reward.cosmetic_item_id,
        )

    def reset_for_repeat(
        self, *, trial_id: str, current_vana_hour: int,
    ) -> bool:
        s = self._state.get(trial_id)
        if s is None or not s.claimed:
            return False
        s.progress = 0
        s.completed = False
        s.claimed = False
        s.on_cooldown_until_vana_hour = (
            current_vana_hour + TRIAL_COOLDOWN_VANA_HOURS
        )
        return True


__all__ = [
    "TRIAL_COOLDOWN_VANA_HOURS",
    "TrialKind", "TrialReward", "MasterTrial",
    "TRIAL_CATALOG", "TRIAL_BY_ID",
    "ProgressResult", "ClaimResult",
    "PlayerMasterTrials",
]
