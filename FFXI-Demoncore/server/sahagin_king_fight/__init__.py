"""Sahagin King fight — RUN/BLU/DRG with two wyrm pets.

VORRAK THE DROWNER — King of the Sahagin. He fights as a
RUN/BLU/DRG hybrid: Runic enchantments soak burst damage,
Blue Magic spells punish casters, Dragoon jumps hit the
back line. He has TWO permanently-bonded drowned wyrm
pets (analogous to DRG's wyvern but always twins). Killing
either pet enrages the other. Killing both has him jump
to mid-arena and SP "Spirit Surge" → Revives both.

Every 3 game-minutes during the fight, he raises a horn
and SUMMONS A SAHAGIN FOMOR PARTY of 6 to assist him.
The fomor party scales by his current HP percent — the
lower his HP, the deadlier the party comp.

Public surface
--------------
    KingPhase enum
    KingFightResult dataclass (frozen)
    SahaginKingFight
        .start(fight_id, hp_max, now_seconds)
        .tick_summons(fight_id, now_seconds) -> tuple[str, ...]
        .damage_king(fight_id, amount, now_seconds)
            -> KingFightResult
        .damage_pet(fight_id, pet_idx, amount)
            -> KingFightResult
        .pet_alive_count(fight_id) -> int
        .king_hp(fight_id) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class KingPhase(str, enum.Enum):
    NOT_STARTED = "not_started"
    PHASE_1 = "phase_1"        # both pets alive
    ENRAGED_LONE_PET = "enraged_lone_pet"   # one pet dead
    SPIRIT_SURGE = "spirit_surge"   # 2hr revive cast incoming
    DEAD = "dead"


# fomor party summon cadence
FOMOR_SUMMON_INTERVAL_SECONDS = 3 * 60
FOMOR_PARTY_SIZE = 6
PHASE_1_HP_THRESHOLD = 0.50    # below 50% drg jumps activate
ENRAGED_LONE_DAMAGE_BUFF = 1.5
SPIRIT_SURGE_HP_THRESHOLD = 0.10   # at 10% hp triggers SP cast
SPIRIT_SURGE_CAST_SECONDS = 30     # if not interrupted, both pets revive

# fomor party comp grades by king hp_pct band
def _fomor_comp_for_hp_pct(pct: float) -> tuple[str, ...]:
    if pct >= 0.66:
        return ("warden", "soldier", "soldier", "scout", "soldier", "scout")
    if pct >= 0.33:
        return (
            "warden", "swordsman", "swordsman",
            "harlequin", "soldier", "scout",
        )
    return (
        "warlord", "swordsman", "swordsman",
        "harlequin", "darkblade", "darkblade",
    )


@dataclasses.dataclass
class _Pet:
    pet_id: str
    hp_max: int
    hp: int

    @property
    def alive(self) -> bool:
        return self.hp > 0


@dataclasses.dataclass
class _KingFightState:
    fight_id: str
    hp_max: int
    hp: int
    started_at: int
    last_summon_at: int
    phase: KingPhase
    pets: list[_Pet]
    spirit_surge_started_at: t.Optional[int] = None
    summon_count: int = 0


@dataclasses.dataclass(frozen=True)
class KingFightResult:
    accepted: bool
    king_hp_after: int = 0
    phase: t.Optional[KingPhase] = None
    pets_alive: int = 0
    spirit_surge_pending: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class SahaginKingFight:
    _fights: dict[str, _KingFightState] = dataclasses.field(default_factory=dict)

    def start(
        self, *, fight_id: str,
        hp_max: int,
        now_seconds: int,
    ) -> bool:
        if not fight_id or fight_id in self._fights:
            return False
        if hp_max <= 0:
            return False
        pets = [
            _Pet(pet_id=f"{fight_id}_wyrm_a", hp_max=hp_max // 4, hp=hp_max // 4),
            _Pet(pet_id=f"{fight_id}_wyrm_b", hp_max=hp_max // 4, hp=hp_max // 4),
        ]
        self._fights[fight_id] = _KingFightState(
            fight_id=fight_id, hp_max=hp_max, hp=hp_max,
            started_at=now_seconds,
            last_summon_at=now_seconds,
            phase=KingPhase.PHASE_1,
            pets=pets,
        )
        return True

    def tick_summons(
        self, *, fight_id: str, now_seconds: int,
    ) -> tuple[str, ...]:
        f = self._fights.get(fight_id)
        if f is None or f.phase == KingPhase.DEAD:
            return ()
        if (now_seconds - f.last_summon_at) < FOMOR_SUMMON_INTERVAL_SECONDS:
            return ()
        # advance the summon clock; ONE summon per tick (don't spam if late)
        f.last_summon_at = now_seconds
        f.summon_count += 1
        pct = f.hp / f.hp_max if f.hp_max else 0.0
        return _fomor_comp_for_hp_pct(pct)

    def damage_king(
        self, *, fight_id: str,
        amount: int,
        now_seconds: int,
    ) -> KingFightResult:
        f = self._fights.get(fight_id)
        if f is None:
            return KingFightResult(False, reason="unknown fight")
        if f.phase == KingPhase.DEAD:
            return KingFightResult(False, reason="king dead")
        if amount <= 0:
            return KingFightResult(False, reason="bad damage")
        # widow-style enrage from lost pet
        if f.phase == KingPhase.ENRAGED_LONE_PET:
            # in a full sim the buff would scale king's outgoing dmg;
            # here we just note via state
            pass
        f.hp = max(0, f.hp - amount)
        spirit_surge_pending = False
        if f.hp == 0:
            f.phase = KingPhase.DEAD
        elif (
            (f.hp / f.hp_max) <= SPIRIT_SURGE_HP_THRESHOLD
            and f.phase != KingPhase.SPIRIT_SURGE
            and f.spirit_surge_started_at is None
        ):
            f.phase = KingPhase.SPIRIT_SURGE
            f.spirit_surge_started_at = now_seconds
            spirit_surge_pending = True
        return KingFightResult(
            accepted=True,
            king_hp_after=f.hp,
            phase=f.phase,
            pets_alive=sum(1 for p in f.pets if p.alive),
            spirit_surge_pending=spirit_surge_pending,
        )

    def damage_pet(
        self, *, fight_id: str,
        pet_idx: int,
        amount: int,
    ) -> KingFightResult:
        f = self._fights.get(fight_id)
        if f is None or f.phase == KingPhase.DEAD:
            return KingFightResult(False, reason="invalid fight")
        if pet_idx < 0 or pet_idx >= len(f.pets):
            return KingFightResult(False, reason="bad pet idx")
        pet = f.pets[pet_idx]
        if not pet.alive:
            return KingFightResult(False, reason="pet dead")
        if amount <= 0:
            return KingFightResult(False, reason="bad damage")
        pet.hp = max(0, pet.hp - amount)
        # if exactly one pet died -> ENRAGED_LONE_PET
        alive = sum(1 for p in f.pets if p.alive)
        if alive == 1 and f.phase == KingPhase.PHASE_1:
            f.phase = KingPhase.ENRAGED_LONE_PET
        return KingFightResult(
            accepted=True,
            king_hp_after=f.hp,
            phase=f.phase,
            pets_alive=alive,
        )

    def pet_alive_count(self, *, fight_id: str) -> int:
        f = self._fights.get(fight_id)
        if f is None:
            return 0
        return sum(1 for p in f.pets if p.alive)

    def king_hp(self, *, fight_id: str) -> int:
        f = self._fights.get(fight_id)
        return f.hp if f else 0


__all__ = [
    "KingPhase", "KingFightResult", "SahaginKingFight",
    "FOMOR_SUMMON_INTERVAL_SECONDS", "FOMOR_PARTY_SIZE",
    "PHASE_1_HP_THRESHOLD", "ENRAGED_LONE_DAMAGE_BUFF",
    "SPIRIT_SURGE_HP_THRESHOLD", "SPIRIT_SURGE_CAST_SECONDS",
]
