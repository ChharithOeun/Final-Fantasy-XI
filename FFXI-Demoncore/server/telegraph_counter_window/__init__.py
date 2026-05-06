"""Telegraph counter window — perfect counters open vulnerability.

If a player CORRECTLY counters a telegraphed boss ability
within its window — block, parry, dodge, dispel, intervene
— the boss takes a small enmity loss AND opens a brief
vulnerability_windows window for the counterer's party.

This is the system that rewards skill expression. A
player who reads the boss without GEO/BRD support, sees
the gesture, and blocks the cone in time gets:
    - 12% of the would-be damage refunded as TP
    - 6 seconds of POSITIONAL vulnerability on the boss
      (1.5x amp), useable by any party member
    - boss enmity reduced by enmity_loss_per_counter (so
      the tank can recover)

A FAILED counter (player blocked early or late, dodged
the wrong direction) wastes the cooldown and does NOT
open a window. Counter timing is therefore real skill,
not a button mash.

Counter kinds (mapped to canonical FFXI mechanics):
    BLOCK       - PLD shield-block timing
    PARRY       - SAM/MNK parry-stance reaction
    DODGE       - THF/DNC sidestep
    DISPEL      - RDM/SCH dispel mid-cast
    INTERVENE   - PLD Sentinel/Cover into the AOE
    INTERRUPT   - WAR/MNK stun on the wind-up

Public surface
--------------
    CounterKind enum
    CounterAttempt dataclass (frozen)
    CounterResult dataclass (frozen)
    TelegraphCounterWindow
        .register_window(boss_id, fight_id, ability_id,
                         opens_at, expires_at, valid_kinds)
        .attempt_counter(boss_id, fight_id, ability_id,
                         counter_kind, player_id, now_seconds)
            -> CounterResult
        .total_counters(player_id) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class CounterKind(str, enum.Enum):
    BLOCK = "block"
    PARRY = "parry"
    DODGE = "dodge"
    DISPEL = "dispel"
    INTERVENE = "intervene"
    INTERRUPT = "interrupt"


# Reward tuning
TP_REFUND_PCT_OF_PREVENTED = 12
VULN_WINDOW_SECONDS = 6
VULN_AMPLIFIER = 1.5
ENMITY_LOSS_PER_COUNTER = 200


@dataclasses.dataclass(frozen=True)
class CounterAttempt:
    boss_id: str
    fight_id: str
    ability_id: str
    counter_kind: CounterKind
    player_id: str


@dataclasses.dataclass(frozen=True)
class CounterResult:
    accepted: bool
    success: bool = False
    tp_refunded: int = 0
    vuln_window_seconds: int = 0
    vuln_amplifier: float = 1.0
    enmity_loss: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class _Window:
    boss_id: str
    fight_id: str
    ability_id: str
    opens_at: int
    expires_at: int
    prevented_damage: int
    valid_kinds: tuple[CounterKind, ...]
    consumed: bool = False


@dataclasses.dataclass
class TelegraphCounterWindow:
    _windows: dict[tuple[str, str, str], _Window] = dataclasses.field(
        default_factory=dict,
    )
    _player_counters: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )

    def register_window(
        self, *, boss_id: str, fight_id: str, ability_id: str,
        opens_at: int, expires_at: int,
        prevented_damage: int,
        valid_kinds: t.Iterable[CounterKind],
    ) -> bool:
        if not boss_id or not fight_id or not ability_id:
            return False
        if expires_at <= opens_at:
            return False
        if prevented_damage <= 0:
            return False
        kinds = tuple(valid_kinds)
        if not kinds:
            return False
        key = (boss_id, fight_id, ability_id)
        if key in self._windows and not self._windows[key].consumed:
            return False
        self._windows[key] = _Window(
            boss_id=boss_id, fight_id=fight_id, ability_id=ability_id,
            opens_at=opens_at, expires_at=expires_at,
            prevented_damage=prevented_damage,
            valid_kinds=kinds,
        )
        return True

    def attempt_counter(
        self, *, boss_id: str, fight_id: str, ability_id: str,
        counter_kind: CounterKind, player_id: str,
        now_seconds: int,
    ) -> CounterResult:
        if not player_id:
            return CounterResult(False, reason="blank player")
        key = (boss_id, fight_id, ability_id)
        w = self._windows.get(key)
        if w is None:
            return CounterResult(
                False, reason="no telegraphed ability",
            )
        if w.consumed:
            return CounterResult(
                False, reason="already countered",
            )
        if now_seconds < w.opens_at:
            return CounterResult(
                False, reason="too early",
            )
        if now_seconds >= w.expires_at:
            return CounterResult(
                False, reason="too late",
            )
        if counter_kind not in w.valid_kinds:
            return CounterResult(
                False, reason="wrong counter kind",
            )
        # success — consume window, accumulate counters
        w.consumed = True
        self._player_counters[player_id] = (
            self._player_counters.get(player_id, 0) + 1
        )
        tp_refunded = (
            w.prevented_damage * TP_REFUND_PCT_OF_PREVENTED
        ) // 100
        return CounterResult(
            accepted=True, success=True,
            tp_refunded=tp_refunded,
            vuln_window_seconds=VULN_WINDOW_SECONDS,
            vuln_amplifier=VULN_AMPLIFIER,
            enmity_loss=ENMITY_LOSS_PER_COUNTER,
        )

    def total_counters(self, *, player_id: str) -> int:
        return self._player_counters.get(player_id, 0)

    def is_window_active(
        self, *, boss_id: str, fight_id: str, ability_id: str,
        now_seconds: int,
    ) -> bool:
        w = self._windows.get((boss_id, fight_id, ability_id))
        if w is None or w.consumed:
            return False
        return w.opens_at <= now_seconds < w.expires_at


__all__ = [
    "CounterKind", "CounterAttempt", "CounterResult",
    "TelegraphCounterWindow",
    "TP_REFUND_PCT_OF_PREVENTED",
    "VULN_WINDOW_SECONDS", "VULN_AMPLIFIER",
    "ENMITY_LOSS_PER_COUNTER",
]
