"""Sneak / Invisible / Deodorize / Spectral Jig — stealth buffs.

Each canonical FFXI mob aggros via one or more SENSES:
    SIGHT  — defeated by Invisible
    SOUND  — defeated by Sneak
    SCENT  — defeated by Deodorize (some mobs)
    BLOOD  — low-HP detection (no buff defeats this; you must heal up)
    MAGIC  — magic aggro (no buff defeats this; pause casting)
    TRUE   — sees through everything (NMs, gods, chained mobs)

Stealth buffs are independent (you can have all three up at once).
Each has a duration timer and breaks if you take an aggressive
action (Sneak breaks on melee/JA, Invisible breaks on ANY action
including spells/items).

Public surface
--------------
    SenseKind enum (SIGHT/SOUND/SCENT/BLOOD/MAGIC/TRUE)
    StealthBuff enum (SNEAK/INVISIBLE/DEODORIZE/SPECTRAL_JIG)
    MobDetection dataclass (which senses a mob has)
    PlayerStealth state
        .apply(buff, expires_at)
        .break_on_action(action_kind)
        .can_be_seen_by(mob_detection, hp_pct, casting) -> bool
        .tick(now)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SenseKind(str, enum.Enum):
    SIGHT = "sight"
    SOUND = "sound"
    SCENT = "scent"
    BLOOD = "blood"
    MAGIC = "magic"
    TRUE = "true"


class StealthBuff(str, enum.Enum):
    SNEAK = "sneak"                 # sound aggro -> defeated
    INVISIBLE = "invisible"         # sight aggro -> defeated
    DEODORIZE = "deodorize"         # scent aggro -> defeated
    SPECTRAL_JIG = "spectral_jig"   # DNC: sneak + invis bundled


# Which sense each buff defeats. Spectral Jig defeats two.
_BUFF_DEFEATS: dict[StealthBuff, frozenset[SenseKind]] = {
    StealthBuff.SNEAK: frozenset({SenseKind.SOUND}),
    StealthBuff.INVISIBLE: frozenset({SenseKind.SIGHT}),
    StealthBuff.DEODORIZE: frozenset({SenseKind.SCENT}),
    StealthBuff.SPECTRAL_JIG: frozenset({SenseKind.SOUND,
                                          SenseKind.SIGHT}),
}


# Which actions break which buffs.
_BUFF_ACTION_BREAK: dict[StealthBuff, frozenset[str]] = {
    StealthBuff.SNEAK: frozenset({"melee", "ja", "weaponskill",
                                    "ranged_attack"}),
    StealthBuff.INVISIBLE: frozenset({"melee", "ja", "weaponskill",
                                        "ranged_attack", "spell",
                                        "item_use", "trade"}),
    StealthBuff.DEODORIZE: frozenset({"melee", "weaponskill",
                                        "ja"}),
    StealthBuff.SPECTRAL_JIG: frozenset({"melee", "ja",
                                           "weaponskill",
                                           "ranged_attack",
                                           "spell"}),
}


@dataclasses.dataclass(frozen=True)
class MobDetection:
    mob_id: str
    senses: frozenset[SenseKind]
    bloodlust_threshold_pct: int = 50    # blood aggro below this HP%

    def has_true_sight(self) -> bool:
        return SenseKind.TRUE in self.senses


@dataclasses.dataclass
class _ActiveBuff:
    kind: StealthBuff
    expires_at: float


@dataclasses.dataclass
class PlayerStealth:
    player_id: str
    _buffs: list[_ActiveBuff] = dataclasses.field(default_factory=list)

    @property
    def active_buffs(self) -> tuple[StealthBuff, ...]:
        return tuple(b.kind for b in self._buffs)

    def apply(self, *, buff: StealthBuff, expires_at: float) -> bool:
        # Re-applying refreshes the timer
        self._buffs = [b for b in self._buffs if b.kind != buff]
        self._buffs.append(_ActiveBuff(kind=buff, expires_at=expires_at))
        return True

    def remove(self, *, buff: StealthBuff) -> bool:
        before = len(self._buffs)
        self._buffs = [b for b in self._buffs if b.kind != buff]
        return len(self._buffs) != before

    def tick(self, *, now: float) -> int:
        before = len(self._buffs)
        self._buffs = [b for b in self._buffs if b.expires_at > now]
        return before - len(self._buffs)

    def break_on_action(self, *, action_kind: str) -> tuple[StealthBuff, ...]:
        """Process an action and break any buffs sensitive to it.
        Returns the tuple of buffs that broke."""
        broken: list[StealthBuff] = []
        keep: list[_ActiveBuff] = []
        for b in self._buffs:
            if action_kind in _BUFF_ACTION_BREAK.get(b.kind, frozenset()):
                broken.append(b.kind)
            else:
                keep.append(b)
        self._buffs = keep
        return tuple(broken)

    def defeated_senses(self) -> frozenset[SenseKind]:
        out: set[SenseKind] = set()
        for b in self._buffs:
            out |= _BUFF_DEFEATS.get(b.kind, frozenset())
        return frozenset(out)

    def can_be_seen_by(
        self, *, mob: MobDetection, hp_pct: int = 100,
        is_casting: bool = False,
    ) -> bool:
        """Will the mob aggro? True iff at least one of its senses
        catches us through our active buffs."""
        if mob.has_true_sight():
            return True
        defeated = self.defeated_senses()
        for sense in mob.senses:
            if sense == SenseKind.TRUE:
                return True
            if sense == SenseKind.BLOOD:
                if hp_pct <= mob.bloodlust_threshold_pct:
                    return True
                continue
            if sense == SenseKind.MAGIC:
                if is_casting:
                    return True
                continue
            if sense not in defeated:
                return True
        return False


__all__ = [
    "SenseKind", "StealthBuff",
    "MobDetection", "PlayerStealth",
]
