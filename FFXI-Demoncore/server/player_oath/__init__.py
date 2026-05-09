"""Player oath — sworn promises with honor consequences.

Players publicly swear oaths: "I will not enter Bastok for 30
days", "I will craft 10 swords for the Sandoria militia",
"I will not loot any player corpses for a season". Oaths can
have witnesses (other players who confirm the swearing). When
an oath is fulfilled, the swearer earns honor; when it's
broken, they lose honor and the breach is publicly logged.

Oaths range from solemn lifetime vows (becoming a teetotaler)
to short-term goals (no fishing for 7 days). The mechanic is
simple — the social weight is what makes it real.

Lifecycle
    SWORN        oath active, must be fulfilled by deadline
    FULFILLED    swearer reported success on or before deadline
    BROKEN       swearer reported breach, or deadline passed
                 without fulfillment

Public surface
--------------
    OathState enum
    OathKind enum
    Oath dataclass (frozen)
    PlayerOathSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_FULFILL_HONOR_GAIN = 30
_BREAK_HONOR_PENALTY = 60


class OathKind(str, enum.Enum):
    ABSTAIN = "abstain"          # I will NOT do X
    PERFORM = "perform"          # I WILL do X
    SUFFER = "suffer"            # I will accept X
    PROTECT = "protect"          # I will protect X


class OathState(str, enum.Enum):
    SWORN = "sworn"
    FULFILLED = "fulfilled"
    BROKEN = "broken"


@dataclasses.dataclass(frozen=True)
class Oath:
    oath_id: str
    swearer_id: str
    kind: OathKind
    description: str
    sworn_day: int
    deadline_day: int
    state: OathState
    resolved_day: int
    witnesses: tuple[str, ...]
    honor_delta: int


@dataclasses.dataclass
class PlayerOathSystem:
    _oaths: dict[str, Oath] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def swear(
        self, *, swearer_id: str, kind: OathKind,
        description: str, sworn_day: int,
        deadline_day: int,
        witnesses: tuple[str, ...] = (),
    ) -> t.Optional[str]:
        if not swearer_id or not description:
            return None
        if sworn_day < 0:
            return None
        if deadline_day <= sworn_day:
            return None
        # Witnesses must be distinct and not include
        # the swearer
        if swearer_id in witnesses:
            return None
        if len(set(witnesses)) != len(witnesses):
            return None
        oid = f"oath_{self._next}"
        self._next += 1
        self._oaths[oid] = Oath(
            oath_id=oid, swearer_id=swearer_id,
            kind=kind, description=description,
            sworn_day=sworn_day,
            deadline_day=deadline_day,
            state=OathState.SWORN,
            resolved_day=0, witnesses=witnesses,
            honor_delta=0,
        )
        return oid

    def fulfill(
        self, *, oath_id: str, swearer_id: str,
        current_day: int,
    ) -> t.Optional[int]:
        """Returns the honor gained, or None if
        invalid."""
        if oath_id not in self._oaths:
            return None
        o = self._oaths[oath_id]
        if o.state != OathState.SWORN:
            return None
        if o.swearer_id != swearer_id:
            return None
        if current_day < o.sworn_day:
            return None
        if current_day > o.deadline_day:
            return None
        self._oaths[oath_id] = dataclasses.replace(
            o, state=OathState.FULFILLED,
            resolved_day=current_day,
            honor_delta=_FULFILL_HONOR_GAIN,
        )
        return _FULFILL_HONOR_GAIN

    def break_oath(
        self, *, oath_id: str, current_day: int,
    ) -> t.Optional[int]:
        """Anyone can report a broken oath
        (witnesses, the swearer themselves, the
        passing of the deadline). Returns honor
        penalty (negative)."""
        if oath_id not in self._oaths:
            return None
        o = self._oaths[oath_id]
        if o.state != OathState.SWORN:
            return None
        if current_day < o.sworn_day:
            return None
        self._oaths[oath_id] = dataclasses.replace(
            o, state=OathState.BROKEN,
            resolved_day=current_day,
            honor_delta=-_BREAK_HONOR_PENALTY,
        )
        return -_BREAK_HONOR_PENALTY

    def auto_expire(
        self, *, oath_id: str, current_day: int,
    ) -> bool:
        """If deadline has passed without
        fulfillment, mark broken automatically.
        """
        if oath_id not in self._oaths:
            return False
        o = self._oaths[oath_id]
        if o.state != OathState.SWORN:
            return False
        if current_day <= o.deadline_day:
            return False
        self._oaths[oath_id] = dataclasses.replace(
            o, state=OathState.BROKEN,
            resolved_day=current_day,
            honor_delta=-_BREAK_HONOR_PENALTY,
        )
        return True

    def oath(
        self, *, oath_id: str,
    ) -> t.Optional[Oath]:
        return self._oaths.get(oath_id)

    def active_oaths(
        self, *, swearer_id: str,
    ) -> list[Oath]:
        return [
            o for o in self._oaths.values()
            if (
                o.swearer_id == swearer_id
                and o.state == OathState.SWORN
            )
        ]

    def lifetime_honor_delta(
        self, *, swearer_id: str,
    ) -> int:
        return sum(
            o.honor_delta for o in self._oaths.values()
            if o.swearer_id == swearer_id
        )

    def fulfilled_oaths(
        self, *, swearer_id: str,
    ) -> list[Oath]:
        return [
            o for o in self._oaths.values()
            if (
                o.swearer_id == swearer_id
                and o.state == OathState.FULFILLED
            )
        ]


__all__ = [
    "OathKind", "OathState", "Oath",
    "PlayerOathSystem",
]
