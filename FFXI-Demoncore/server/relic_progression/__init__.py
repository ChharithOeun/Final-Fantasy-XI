"""Relic weapon progression — staged upgrade path.

Each relic weapon (Excalibur, Ragnarok, Apocalypse, etc.) has a
fixed stage chain. Each stage has a currency cost (mythril
beastcoins, ancient beastcoins, byne bills, etc.) and a trial
requirement (kill N of family X). Completing both unlocks the
next stage; the weapon's stats step up.

Public surface
--------------
    RelicTier enum (BASE -> FINAL after multiple stages)
    RelicStage immutable: stage_id, costs, trial requirement
    RELIC_CATALOG sample weapons
    RelicProgress per-(player, weapon)
        .pay_currency / .record_trial_kill
        .can_advance / .advance_stage
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class RelicTier(int, enum.Enum):
    BASE = 0           # the +0 weapon
    PLUS_1 = 1
    PLUS_2 = 2
    AFTERGLOW = 3      # +3 stage
    PLUS_4 = 4
    FINAL = 5          # 119 stage


@dataclasses.dataclass(frozen=True)
class RelicStage:
    stage_id: str
    from_tier: RelicTier
    to_tier: RelicTier
    currency_id: str
    currency_amount: int
    trial_family: str           # mob family the trial targets
    trial_kill_count: int
    description: str = ""


@dataclasses.dataclass(frozen=True)
class RelicWeapon:
    weapon_id: str
    name: str
    job: str                    # job that wields it
    stages: tuple[RelicStage, ...]


RELIC_CATALOG: tuple[RelicWeapon, ...] = (
    RelicWeapon(
        weapon_id="excalibur", name="Excalibur", job="paladin",
        stages=(
            RelicStage("excalibur_plus1", RelicTier.BASE, RelicTier.PLUS_1,
                       currency_id="mythril_beastcoin",
                       currency_amount=300,
                       trial_family="orc", trial_kill_count=300),
            RelicStage("excalibur_plus2", RelicTier.PLUS_1, RelicTier.PLUS_2,
                       currency_id="ancient_beastcoin",
                       currency_amount=300,
                       trial_family="quadav", trial_kill_count=300),
            RelicStage("excalibur_afterglow", RelicTier.PLUS_2,
                       RelicTier.AFTERGLOW,
                       currency_id="riftborn_boulder",
                       currency_amount=15,
                       trial_family="dragon", trial_kill_count=50),
        ),
    ),
    RelicWeapon(
        weapon_id="ragnarok", name="Ragnarok", job="dark_knight",
        stages=(
            RelicStage("ragnarok_plus1", RelicTier.BASE, RelicTier.PLUS_1,
                       currency_id="mythril_beastcoin",
                       currency_amount=300,
                       trial_family="quadav", trial_kill_count=300),
            RelicStage("ragnarok_plus2", RelicTier.PLUS_1, RelicTier.PLUS_2,
                       currency_id="ancient_beastcoin",
                       currency_amount=300,
                       trial_family="yagudo", trial_kill_count=300),
        ),
    ),
    RelicWeapon(
        weapon_id="apocalypse", name="Apocalypse", job="dark_knight",
        stages=(
            RelicStage("apocalypse_plus1", RelicTier.BASE, RelicTier.PLUS_1,
                       currency_id="mythril_beastcoin",
                       currency_amount=300,
                       trial_family="undead", trial_kill_count=300),
        ),
    ),
)

WEAPON_BY_ID: dict[str, RelicWeapon] = {
    w.weapon_id: w for w in RELIC_CATALOG
}


@dataclasses.dataclass
class RelicProgress:
    """Per-(player, weapon) progression state."""
    player_id: str
    weapon_id: str
    current_tier: RelicTier = RelicTier.BASE
    currency_paid: int = 0
    trial_kills: int = 0

    def _next_stage(self) -> t.Optional[RelicStage]:
        weapon = WEAPON_BY_ID[self.weapon_id]
        for stage in weapon.stages:
            if stage.from_tier == self.current_tier:
                return stage
        return None

    def pay_currency(self, *, currency_id: str, amount: int) -> int:
        """Pay currency toward the active stage. Returns amount accepted
        (may be 0 if currency mismatch or stage finished)."""
        if amount < 0:
            raise ValueError("amount must be >= 0")
        stage = self._next_stage()
        if stage is None:
            return 0
        if currency_id != stage.currency_id:
            return 0
        remaining = stage.currency_amount - self.currency_paid
        if remaining <= 0:
            return 0
        accepted = min(amount, remaining)
        self.currency_paid += accepted
        return accepted

    def record_trial_kill(self, *, family: str) -> bool:
        stage = self._next_stage()
        if stage is None:
            return False
        if family != stage.trial_family:
            return False
        if self.trial_kills >= stage.trial_kill_count:
            return False
        self.trial_kills += 1
        return True

    def can_advance(self) -> bool:
        stage = self._next_stage()
        if stage is None:
            return False
        return (
            self.currency_paid >= stage.currency_amount
            and self.trial_kills >= stage.trial_kill_count
        )

    def advance_stage(self) -> t.Optional[RelicStage]:
        if not self.can_advance():
            return None
        stage = self._next_stage()
        assert stage is not None
        self.current_tier = stage.to_tier
        self.currency_paid = 0
        self.trial_kills = 0
        return stage

    def is_complete(self) -> bool:
        return self._next_stage() is None


__all__ = [
    "RelicTier", "RelicStage", "RelicWeapon",
    "RELIC_CATALOG", "WEAPON_BY_ID",
    "RelicProgress",
]
