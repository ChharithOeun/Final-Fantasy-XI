"""Combat tactics — the layer between mob_personality and combat.

mob_personality answers "what kind of mind is this?" but in the
moment of combat the AI also needs to choose:

* Who to attack (target priority)
* What formation to hold (front line / flanks / back ranks)
* Whether to focus-fire or spread damage
* When to retreat / call reinforcements / use a 2hr / parley
* Which spell / WS to commit

Those decisions are personality-INFORMED but not personality-
DETERMINED — a coward can still hold the line if there's
nowhere to flee. So this module exposes a TACTICAL DECISION
surface that takes the personality vector + battlefield state
and returns a TacticalIntent.

The orchestrator's per-mob AI agent ultimately decides — this
module is the deterministic recommendation system the AI
consults (and may override). Helper used by the AI prompt
assembly to seed the recommendation.

Inputs the tactics layer reads
------------------------------
* PersonalityVector (from mob_personality)
* BattlefieldSnapshot:
    - allies (count, low_hp_count)
    - enemies (target candidates with threat & hp)
    - self_hp_pct, ally_morale_pct
    - has_2hr_available, has_reinforcements_callable

Output
------
A TacticalIntent dataclass with:
* primary_target_id (None if no good target)
* formation (FRONT / FLANK / REAR / SOLO)
* posture (FOCUS_FIRE / SPREAD / SUPPORT / RETREAT / RALLY /
           SPECIAL)
* should_use_2hr (bool + recommended ability if any)
* should_call_reinforcements (bool)
* notes (string the orchestrator can dump into prompt)

Public surface
--------------
    Formation enum
    Posture enum
    EnemyCandidate dataclass
    BattlefieldSnapshot dataclass
    TacticalIntent dataclass
    TacticalAdvisor
        .recommend(personality, snapshot) -> TacticalIntent
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.mob_personality import PersonalityVector


class Formation(str, enum.Enum):
    FRONT = "front"
    FLANK = "flank"
    REAR = "rear"
    SOLO = "solo"


class Posture(str, enum.Enum):
    FOCUS_FIRE = "focus_fire"
    SPREAD = "spread"
    SUPPORT = "support"
    RETREAT = "retreat"
    RALLY = "rally"
    SPECIAL = "special"        # commit a 2hr or signature attack


@dataclasses.dataclass(frozen=True)
class EnemyCandidate:
    entity_id: str
    threat: int                # 0..100, hate value
    hp_pct: int                # 0..100
    is_healer: bool = False
    is_caster: bool = False
    is_low_hp: bool = False    # under 25%
    distance: int = 0          # tile units


@dataclasses.dataclass(frozen=True)
class BattlefieldSnapshot:
    self_id: str
    self_hp_pct: int
    allies_total: int
    allies_low_hp: int
    enemies: tuple[EnemyCandidate, ...]
    ally_morale_pct: int = 100
    has_2hr_available: bool = False
    can_call_reinforcements: bool = False


@dataclasses.dataclass(frozen=True)
class TacticalIntent:
    primary_target_id: t.Optional[str]
    formation: Formation
    posture: Posture
    should_use_2hr: bool = False
    should_call_reinforcements: bool = False
    notes: str = ""


# Thresholds — values are the most useful for tuning later.
RETREAT_HP_THRESHOLD = 20      # under this HP%, cowardly mobs flee
LOW_HP_2HR_THRESHOLD = 30      # bosses pop 2hr below this HP%
LOW_MORALE_RETREAT = 30
HIGH_LOYALTY_FORWARD = 0.7
HIGH_CUNNING_HEALER_PRIORITY = 0.6


def _pick_target(
    personality: PersonalityVector,
    enemies: tuple[EnemyCandidate, ...],
) -> t.Optional[EnemyCandidate]:
    if not enemies:
        return None
    # CUNNING > 0.6: prefer healers, then casters, then low-HP
    if personality.cunning >= HIGH_CUNNING_HEALER_PRIORITY:
        healers = [e for e in enemies if e.is_healer]
        if healers:
            return max(healers, key=lambda e: e.threat)
        casters = [e for e in enemies if e.is_caster]
        if casters:
            return max(casters, key=lambda e: e.threat)
        low_hp = [e for e in enemies if e.is_low_hp]
        if low_hp:
            # Secure the kill
            return min(low_hp, key=lambda e: e.hp_pct)
    # Default: highest threat
    return max(enemies, key=lambda e: e.threat)


def _choose_posture(
    personality: PersonalityVector,
    snapshot: BattlefieldSnapshot,
) -> Posture:
    # 1) Retreat is the OUTERMOST trigger.
    if (
        snapshot.self_hp_pct < RETREAT_HP_THRESHOLD
        and personality.courage < 0.4
    ):
        return Posture.RETREAT
    if snapshot.ally_morale_pct < LOW_MORALE_RETREAT:
        # Loyal mobs RALLY, others RETREAT
        if personality.loyalty >= HIGH_LOYALTY_FORWARD:
            return Posture.RALLY
        return Posture.RETREAT
    # 2) 2hr commitment
    if (
        snapshot.has_2hr_available
        and snapshot.self_hp_pct < LOW_HP_2HR_THRESHOLD
    ):
        return Posture.SPECIAL
    # 3) Lots of low-HP allies + high loyalty -> SUPPORT (heal, cover)
    if (
        snapshot.allies_low_hp >= 2
        and personality.loyalty >= HIGH_LOYALTY_FORWARD
    ):
        return Posture.SUPPORT
    # 4) Aggression + courage -> focus fire
    if (
        personality.aggression >= 0.6
        and personality.courage >= 0.5
    ):
        return Posture.FOCUS_FIRE
    # 5) Otherwise SPREAD (cautious, distribute damage)
    return Posture.SPREAD


def _choose_formation(
    personality: PersonalityVector,
    snapshot: BattlefieldSnapshot,
) -> Formation:
    # Solo wanderers
    if snapshot.allies_total == 0:
        return Formation.SOLO
    # Cunning + low-aggression preferentially flank
    if (
        personality.cunning >= 0.7
        and personality.aggression < 0.7
    ):
        return Formation.FLANK
    # Low courage and low HP back rank
    if (
        personality.courage < 0.4
        and snapshot.self_hp_pct < 50
    ):
        return Formation.REAR
    # High aggression / courage -> front
    if (
        personality.aggression >= 0.6
        and personality.courage >= 0.6
    ):
        return Formation.FRONT
    return Formation.FLANK


@dataclasses.dataclass
class TacticalAdvisor:
    def recommend(
        self, *, personality: PersonalityVector,
        snapshot: BattlefieldSnapshot,
    ) -> TacticalIntent:
        target = _pick_target(personality, snapshot.enemies)
        posture = _choose_posture(personality, snapshot)
        formation = _choose_formation(personality, snapshot)
        # 2hr trigger lined up with SPECIAL posture
        use_2hr = posture == Posture.SPECIAL
        # Loyal + outnumbered mobs call for help
        outnumbered = len(snapshot.enemies) > snapshot.allies_total + 1
        call_reinforcements = (
            snapshot.can_call_reinforcements
            and outnumbered
            and personality.loyalty >= 0.5
        )
        notes = (
            f"posture={posture.value}, formation={formation.value};"
            f" hp={snapshot.self_hp_pct}, morale="
            f"{snapshot.ally_morale_pct}"
        )
        return TacticalIntent(
            primary_target_id=target.entity_id if target else None,
            formation=formation,
            posture=posture,
            should_use_2hr=use_2hr,
            should_call_reinforcements=call_reinforcements,
            notes=notes,
        )


__all__ = [
    "RETREAT_HP_THRESHOLD", "LOW_HP_2HR_THRESHOLD",
    "LOW_MORALE_RETREAT",
    "Formation", "Posture",
    "EnemyCandidate", "BattlefieldSnapshot", "TacticalIntent",
    "TacticalAdvisor",
]
