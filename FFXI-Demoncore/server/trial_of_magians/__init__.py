"""Trial of the Magians — directed weapon trial system.

A weapon at +0 is registered with a Magian Moogle; the moogle hands
out trials with concrete objectives ("kill 100 of family X with this
weapon" / "deal 5000 elemental damage" / "complete a skillchain N
times"). Completing trials levels up the weapon and gates onto the
next trial in the path. End of path = an Empyreal weapon.

Public surface
--------------
    TrialKind enum (kill / damage / skillchain / weapon_skill)
    TrialSpec catalog
    TrialPath chain of trials per weapon
    PlayerTrialProgress
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TrialKind(str, enum.Enum):
    KILL_FAMILY = "kill_family"
    DEAL_ELEMENTAL_DAMAGE = "deal_elemental_damage"
    LAND_SKILLCHAIN = "land_skillchain"
    USE_WEAPON_SKILL = "use_weapon_skill"


@dataclasses.dataclass(frozen=True)
class TrialSpec:
    trial_id: str
    kind: TrialKind
    target: str                      # family name / element / WS name / chain name
    target_count: int
    weapon_family: str               # which weapon line this attaches to


@dataclasses.dataclass(frozen=True)
class TrialPath:
    path_id: str
    weapon_family: str
    label: str
    final_weapon_id: str
    trials: tuple[TrialSpec, ...]    # ordered chain


# Sample paths
ALMACE_PATH = TrialPath(
    path_id="almace_path",
    weapon_family="great_sword",
    label="Almace Empyreal Path",
    final_weapon_id="almace",
    trials=(
        TrialSpec("almace_t1", TrialKind.KILL_FAMILY,
                  target="amphibian", target_count=100,
                  weapon_family="great_sword"),
        TrialSpec("almace_t2", TrialKind.LAND_SKILLCHAIN,
                  target="darkness", target_count=30,
                  weapon_family="great_sword"),
        TrialSpec("almace_t3", TrialKind.DEAL_ELEMENTAL_DAMAGE,
                  target="dark", target_count=50000,
                  weapon_family="great_sword"),
        TrialSpec("almace_t4", TrialKind.USE_WEAPON_SKILL,
                  target="resolution", target_count=200,
                  weapon_family="great_sword"),
    ),
)

CARNWENHAN_PATH = TrialPath(
    path_id="carnwenhan_path",
    weapon_family="dagger",
    label="Carnwenhan Empyreal Path",
    final_weapon_id="carnwenhan",
    trials=(
        TrialSpec("carnwenhan_t1", TrialKind.KILL_FAMILY,
                  target="bird", target_count=100,
                  weapon_family="dagger"),
        TrialSpec("carnwenhan_t2", TrialKind.USE_WEAPON_SKILL,
                  target="mercy_stroke", target_count=150,
                  weapon_family="dagger"),
    ),
)

GANDIVA_PATH = TrialPath(
    path_id="gandiva_path",
    weapon_family="bow",
    label="Gandiva Empyreal Path",
    final_weapon_id="gandiva",
    trials=(
        TrialSpec("gandiva_t1", TrialKind.KILL_FAMILY,
                  target="beast", target_count=100,
                  weapon_family="bow"),
        TrialSpec("gandiva_t2", TrialKind.DEAL_ELEMENTAL_DAMAGE,
                  target="wind", target_count=40000,
                  weapon_family="bow"),
    ),
)

TRIAL_PATHS: tuple[TrialPath, ...] = (
    ALMACE_PATH, CARNWENHAN_PATH, GANDIVA_PATH,
)
PATH_BY_ID: dict[str, TrialPath] = {p.path_id: p for p in TRIAL_PATHS}


@dataclasses.dataclass
class _ActiveTrial:
    trial_id: str
    progress: int = 0
    completed: bool = False


@dataclasses.dataclass
class PlayerTrialProgress:
    player_id: str
    path_id: str
    current_trial_index: int = 0
    active: t.Optional[_ActiveTrial] = None
    completed_trial_ids: set[str] = dataclasses.field(
        default_factory=set,
    )
    path_completed: bool = False

    @property
    def path(self) -> TrialPath:
        return PATH_BY_ID[self.path_id]

    def start_next_trial(self) -> bool:
        if self.path_completed:
            return False
        if self.active is not None and not self.active.completed:
            return False    # already active
        if self.current_trial_index >= len(self.path.trials):
            return False
        spec = self.path.trials[self.current_trial_index]
        self.active = _ActiveTrial(trial_id=spec.trial_id)
        return True

    def report_progress(
        self, *, kind: TrialKind, target: str, amount: int = 1,
    ) -> bool:
        """Tally trial progress when the player does the relevant action.
        Returns True if progress was applied."""
        if self.active is None or self.active.completed:
            return False
        spec_idx = self.current_trial_index
        spec = self.path.trials[spec_idx]
        if spec.kind != kind:
            return False
        if spec.target != target:
            return False
        self.active.progress = min(
            spec.target_count, self.active.progress + amount,
        )
        if self.active.progress >= spec.target_count:
            self.active.completed = True
        return True

    def claim_complete_trial(self) -> t.Optional[str]:
        """Mark the current trial done, advance to the next.
        Returns the completed trial_id, or None if not ready."""
        if self.active is None or not self.active.completed:
            return None
        completed_id = self.active.trial_id
        self.completed_trial_ids.add(completed_id)
        self.active = None
        self.current_trial_index += 1
        if self.current_trial_index >= len(self.path.trials):
            self.path_completed = True
        return completed_id

    def trial_ratio(self) -> float:
        """How far through the active trial we are, in [0..1]."""
        if self.active is None:
            return 0.0
        spec = self.path.trials[self.current_trial_index]
        if spec.target_count == 0:
            return 1.0
        return self.active.progress / spec.target_count


__all__ = [
    "TrialKind", "TrialSpec", "TrialPath",
    "TRIAL_PATHS", "PATH_BY_ID",
    "ALMACE_PATH", "CARNWENHAN_PATH", "GANDIVA_PATH",
    "PlayerTrialProgress",
]
