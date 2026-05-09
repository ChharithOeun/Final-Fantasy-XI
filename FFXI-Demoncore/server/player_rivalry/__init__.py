"""Player rivalry — formally declared rivalries with combat tally.

Two players who keep running into each other can
formally DECLARE a rivalry. While active, every PvP
encounter between them is recorded with its outcome —
who hit whom, who won the duel/skirmish, on what day,
in what zone. The tally builds a permanent stats line:
"You vs Naji: 12-8-3 (W-L-D)".

Rivalries can be SETTLED (tally locked, both bow out),
ENDED_BY_PERMADEATH (one party died), or DISSOLVED by
either party unilaterally with a small Honor cost
(rage-quitting a rivalry isn't free).

Public surface
--------------
    RivalryState enum
    EncounterOutcome enum (CHALLENGER_WIN /
                           TARGET_WIN / DRAW)
    RivalryEncounter dataclass (frozen)
    Rivalry dataclass (frozen)
    PlayerRivalrySystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class RivalryState(str, enum.Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    SETTLED = "settled"
    ENDED_BY_PERMADEATH = "ended_by_permadeath"
    DISSOLVED = "dissolved"


class EncounterOutcome(str, enum.Enum):
    CHALLENGER_WIN = "challenger_win"
    TARGET_WIN = "target_win"
    DRAW = "draw"


@dataclasses.dataclass(frozen=True)
class RivalryEncounter:
    encounter_id: str
    rivalry_id: str
    occurred_day: int
    zone: str
    outcome: EncounterOutcome
    note: str


@dataclasses.dataclass(frozen=True)
class Rivalry:
    rivalry_id: str
    challenger: str
    target: str
    proposed_day: int
    accepted_day: t.Optional[int]
    ended_day: t.Optional[int]
    state: RivalryState
    challenger_wins: int
    target_wins: int
    draws: int


@dataclasses.dataclass
class _RState:
    spec: Rivalry
    encounters: list[RivalryEncounter] = (
        dataclasses.field(default_factory=list)
    )


def _ordered(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)


@dataclasses.dataclass
class PlayerRivalrySystem:
    _rivalries: dict[str, _RState] = (
        dataclasses.field(default_factory=dict)
    )
    _next_id: int = 1
    _next_enc: int = 1

    def declare(
        self, *, challenger: str, target: str,
        proposed_day: int,
    ) -> t.Optional[str]:
        if not challenger or not target:
            return None
        if challenger == target:
            return None
        if proposed_day < 0:
            return None
        # Block parallel active rivalry between same
        # pair (in either direction)
        for st in self._rivalries.values():
            if st.spec.state in (
                RivalryState.PROPOSED,
                RivalryState.ACTIVE,
            ):
                pair_a = _ordered(
                    st.spec.challenger,
                    st.spec.target,
                )
                pair_b = _ordered(
                    challenger, target,
                )
                if pair_a == pair_b:
                    return None
        rid = f"rival_{self._next_id}"
        self._next_id += 1
        spec = Rivalry(
            rivalry_id=rid,
            challenger=challenger, target=target,
            proposed_day=proposed_day,
            accepted_day=None, ended_day=None,
            state=RivalryState.PROPOSED,
            challenger_wins=0, target_wins=0,
            draws=0,
        )
        self._rivalries[rid] = _RState(spec=spec)
        return rid

    def accept(
        self, *, rivalry_id: str, now_day: int,
    ) -> bool:
        if rivalry_id not in self._rivalries:
            return False
        st = self._rivalries[rivalry_id]
        if st.spec.state != RivalryState.PROPOSED:
            return False
        if now_day < st.spec.proposed_day:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=RivalryState.ACTIVE,
            accepted_day=now_day,
        )
        return True

    def record_encounter(
        self, *, rivalry_id: str,
        outcome: EncounterOutcome, zone: str,
        occurred_day: int, note: str = "",
    ) -> t.Optional[str]:
        if rivalry_id not in self._rivalries:
            return None
        if not zone or occurred_day < 0:
            return None
        st = self._rivalries[rivalry_id]
        if st.spec.state != RivalryState.ACTIVE:
            return None
        eid = f"renc_{self._next_enc}"
        self._next_enc += 1
        st.encounters.append(RivalryEncounter(
            encounter_id=eid,
            rivalry_id=rivalry_id,
            occurred_day=occurred_day,
            zone=zone, outcome=outcome, note=note,
        ))
        cw = st.spec.challenger_wins
        tw = st.spec.target_wins
        dr = st.spec.draws
        if outcome == EncounterOutcome.CHALLENGER_WIN:
            cw += 1
        elif outcome == EncounterOutcome.TARGET_WIN:
            tw += 1
        else:
            dr += 1
        st.spec = dataclasses.replace(
            st.spec, challenger_wins=cw,
            target_wins=tw, draws=dr,
        )
        return eid

    def settle(
        self, *, rivalry_id: str, now_day: int,
    ) -> bool:
        if rivalry_id not in self._rivalries:
            return False
        st = self._rivalries[rivalry_id]
        if st.spec.state != RivalryState.ACTIVE:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=RivalryState.SETTLED,
            ended_day=now_day,
        )
        return True

    def end_by_permadeath(
        self, *, rivalry_id: str, now_day: int,
    ) -> bool:
        if rivalry_id not in self._rivalries:
            return False
        st = self._rivalries[rivalry_id]
        if st.spec.state not in (
            RivalryState.PROPOSED,
            RivalryState.ACTIVE,
        ):
            return False
        st.spec = dataclasses.replace(
            st.spec,
            state=RivalryState.ENDED_BY_PERMADEATH,
            ended_day=now_day,
        )
        return True

    def dissolve(
        self, *, rivalry_id: str, now_day: int,
    ) -> bool:
        if rivalry_id not in self._rivalries:
            return False
        st = self._rivalries[rivalry_id]
        if st.spec.state not in (
            RivalryState.PROPOSED,
            RivalryState.ACTIVE,
        ):
            return False
        st.spec = dataclasses.replace(
            st.spec, state=RivalryState.DISSOLVED,
            ended_day=now_day,
        )
        return True

    def rivalry(
        self, *, rivalry_id: str,
    ) -> t.Optional[Rivalry]:
        if rivalry_id not in self._rivalries:
            return None
        return self._rivalries[rivalry_id].spec

    def encounters(
        self, *, rivalry_id: str,
    ) -> list[RivalryEncounter]:
        if rivalry_id not in self._rivalries:
            return []
        return list(
            self._rivalries[rivalry_id].encounters,
        )

    def rivalries_for(
        self, *, player_id: str,
    ) -> list[Rivalry]:
        return [
            st.spec for st in self._rivalries.values()
            if (st.spec.challenger == player_id
                or st.spec.target == player_id)
        ]


__all__ = [
    "RivalryState", "EncounterOutcome",
    "RivalryEncounter", "Rivalry",
    "PlayerRivalrySystem",
]
