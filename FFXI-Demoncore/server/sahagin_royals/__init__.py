"""Sahagin Royals — the King and Queen of King's Brood.

Two named NMs that rule the Sahagin Kingdom from inside
the capital. Both are Drowned-King-tier monsters with
ruthless mechanics: they pre-emptively *summon* their
strike teams to harass attackers, they call in raids
from resistance cells across the sea while you fight
them, and they have shared HP-link enrage thresholds
where killing one without the other in range causes
the survivor to triple in damage out of grief and rage.

Outcome state machine (per royal):
    ALIVE -> WOUNDED (50% hp) -> ENRAGED (25% hp) -> DEAD

If only KING dies: SUCCESSION_CRISIS — Queen rules but
weaker; raids decline; Kingdom enters CIVIL WAR for 7 days.
If only QUEEN dies: same, mirrored.
If BOTH die in the same fight (within DUAL_KILL_WINDOW):
    KINGDOM_SHATTERED — capital permanently falls; all
    resistance cells become independent factions; the
    server gets the announcement.

Public surface
--------------
    Royal enum
    RoyalState enum
    KingdomState enum
    SahaginRoyals
        .set_royal(royal, hp_max, name, now_seconds)
        .damage_royal(royal, amount, attacker_id, now_seconds)
            -> RoyalDamageResult
        .royal_state(royal) -> RoyalState
        .kingdom_state(now_seconds) -> KingdomState
        .both_dead_in_window() -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Royal(str, enum.Enum):
    KING = "king"
    QUEEN = "queen"


class RoyalState(str, enum.Enum):
    ABSENT = "absent"          # not yet placed
    ALIVE = "alive"            # > 50% hp
    WOUNDED = "wounded"        # 25..50%
    ENRAGED = "enraged"        # < 25%, last stand
    DEAD = "dead"


class KingdomState(str, enum.Enum):
    HEALTHY = "healthy"           # both royals alive
    CIVIL_WAR = "civil_war"       # one royal dead, other alive (7d)
    SHATTERED = "shattered"       # both dead within DUAL_KILL_WINDOW


# kill the second royal within this many seconds = SHATTERED
DUAL_KILL_WINDOW_SECONDS = 60
# how long civil war lasts before the survivor stabilizes
CIVIL_WAR_DURATION_SECONDS = 7 * 24 * 3_600
# enrage damage multiplier when widowed
WIDOW_ENRAGE_MULTIPLIER = 3


@dataclasses.dataclass
class _RoyalState:
    royal: Royal
    name: str
    hp_max: int = 0
    hp: int = 0
    state: RoyalState = RoyalState.ABSENT
    died_at: t.Optional[int] = None


@dataclasses.dataclass(frozen=True)
class RoyalDamageResult:
    accepted: bool
    royal_state: t.Optional[RoyalState] = None
    royal_dead: bool = False
    kingdom_state: t.Optional[KingdomState] = None
    widow_enrage_active: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class SahaginRoyals:
    _royals: dict[Royal, _RoyalState] = dataclasses.field(default_factory=dict)

    def set_royal(
        self, *, royal: Royal,
        hp_max: int,
        name: str,
        now_seconds: int = 0,
    ) -> bool:
        if hp_max <= 0 or not name:
            return False
        if royal in self._royals:
            return False  # already set this run
        self._royals[royal] = _RoyalState(
            royal=royal, name=name,
            hp_max=hp_max, hp=hp_max,
            state=RoyalState.ALIVE,
        )
        return True

    def damage_royal(
        self, *, royal: Royal,
        amount: int,
        attacker_id: str,
        now_seconds: int,
    ) -> RoyalDamageResult:
        r = self._royals.get(royal)
        if r is None:
            return RoyalDamageResult(False, reason="royal not present")
        if r.state == RoyalState.DEAD:
            return RoyalDamageResult(
                False, reason="already dead",
                royal_state=RoyalState.DEAD,
            )
        if amount <= 0:
            return RoyalDamageResult(False, reason="bad damage")
        # widow enrage applies when the OTHER royal is already dead
        widow_enrage = self._is_widow_enrage_active()
        # advance state from current hp/threshold
        prior_state = r.state
        r.hp = max(0, r.hp - amount)
        if r.hp == 0:
            r.state = RoyalState.DEAD
            r.died_at = now_seconds
            return RoyalDamageResult(
                accepted=True, royal_state=RoyalState.DEAD,
                royal_dead=True,
                kingdom_state=self.kingdom_state(now_seconds=now_seconds),
                widow_enrage_active=widow_enrage,
            )
        # still alive
        frac = r.hp / r.hp_max
        if frac < 0.25:
            r.state = RoyalState.ENRAGED
        elif frac < 0.50:
            r.state = RoyalState.WOUNDED
        else:
            r.state = RoyalState.ALIVE
        return RoyalDamageResult(
            accepted=True, royal_state=r.state,
            royal_dead=False,
            kingdom_state=self.kingdom_state(now_seconds=now_seconds),
            widow_enrage_active=widow_enrage,
        )

    def royal_state(self, *, royal: Royal) -> RoyalState:
        r = self._royals.get(royal)
        return r.state if r else RoyalState.ABSENT

    def kingdom_state(
        self, *, now_seconds: int,
    ) -> KingdomState:
        king = self._royals.get(Royal.KING)
        queen = self._royals.get(Royal.QUEEN)
        king_dead = king is not None and king.state == RoyalState.DEAD
        queen_dead = queen is not None and queen.state == RoyalState.DEAD
        if king_dead and queen_dead:
            # SHATTERED iff deaths happened within window
            assert king is not None and queen is not None
            assert king.died_at is not None and queen.died_at is not None
            gap = abs(king.died_at - queen.died_at)
            if gap <= DUAL_KILL_WINDOW_SECONDS:
                return KingdomState.SHATTERED
            # otherwise we just stayed in CIVIL_WAR until 2nd kill;
            # the second death starts a new (shorter) crisis
            return KingdomState.CIVIL_WAR
        if king_dead != queen_dead:
            return KingdomState.CIVIL_WAR
        return KingdomState.HEALTHY

    def both_dead_in_window(self) -> bool:
        king = self._royals.get(Royal.KING)
        queen = self._royals.get(Royal.QUEEN)
        if king is None or queen is None:
            return False
        if king.state != RoyalState.DEAD or queen.state != RoyalState.DEAD:
            return False
        assert king.died_at is not None and queen.died_at is not None
        return abs(king.died_at - queen.died_at) <= DUAL_KILL_WINDOW_SECONDS

    def _is_widow_enrage_active(self) -> bool:
        """One royal dead, the other still alive -> enrage stack."""
        king = self._royals.get(Royal.KING)
        queen = self._royals.get(Royal.QUEEN)
        if king is None or queen is None:
            return False
        states = (king.state, queen.state)
        return (
            (RoyalState.DEAD in states)
            and (RoyalState.DEAD not in (
                king.state if king.state != queen.state else queen.state,
            ) or True)
            and not (
                king.state == RoyalState.DEAD
                and queen.state == RoyalState.DEAD
            )
        ) and any(s == RoyalState.DEAD for s in states)


__all__ = [
    "Royal", "RoyalState", "KingdomState",
    "RoyalDamageResult", "SahaginRoyals",
    "DUAL_KILL_WINDOW_SECONDS",
    "CIVIL_WAR_DURATION_SECONDS",
    "WIDOW_ENRAGE_MULTIPLIER",
]
