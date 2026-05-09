"""Entity rivalry — NPC-on-NPC rivalries.

Some NPCs and named monsters carry long-running rivalries
with other NPCs/mobs — political, professional, personal. The
Goblin Smithy NM resents the Mythril Madame. Volker grumbles
about Iron Eater. These aren't combat conflicts — they're
slow-burn antagonisms with public flavor that players can
witness, take sides on, or escalate via guild contracts.

States move from SIMMERING (light tension) to FEUDING (active
animosity, frequent confrontations) and ultimately RESOLVED
(reconciliation, defeat, or death of one party). Players who
witness rivalry events earn small fame; players who take a
side gain rep with that side and lose rep with the other.

Public surface
--------------
    RivalryState enum
    Rivalry dataclass (frozen)
    EntityRivalrySystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_FEUD_THRESHOLD = 5      # incidents to escalate
_RECONCILE_HONOR_GAIN = 25


class RivalryState(str, enum.Enum):
    SIMMERING = "simmering"
    FEUDING = "feuding"
    RESOLVED = "resolved"


@dataclasses.dataclass(frozen=True)
class Rivalry:
    rivalry_id: str
    entity_a: str
    entity_b: str
    description: str
    state: RivalryState
    incidents_count: int
    a_supporters: tuple[str, ...]
    b_supporters: tuple[str, ...]
    resolution: str       # "reconciled" / "a_won" / "b_won" / ""


def _canonical(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


@dataclasses.dataclass
class EntityRivalrySystem:
    _rivalries: dict[str, Rivalry] = dataclasses.field(
        default_factory=dict,
    )
    _index: dict[
        tuple[str, str], str
    ] = dataclasses.field(default_factory=dict)
    _next: int = 1

    def declare_rivalry(
        self, *, entity_a: str, entity_b: str,
        description: str,
    ) -> t.Optional[str]:
        if not entity_a or not entity_b:
            return None
        if entity_a == entity_b:
            return None
        if not description:
            return None
        ca, cb = _canonical(entity_a, entity_b)
        if (ca, cb) in self._index:
            return None
        rid = f"rivalry_{self._next}"
        self._next += 1
        self._rivalries[rid] = Rivalry(
            rivalry_id=rid, entity_a=ca, entity_b=cb,
            description=description,
            state=RivalryState.SIMMERING,
            incidents_count=0,
            a_supporters=(), b_supporters=(),
            resolution="",
        )
        self._index[(ca, cb)] = rid
        return rid

    def record_incident(
        self, *, entity_a: str, entity_b: str,
    ) -> bool:
        ca, cb = _canonical(entity_a, entity_b)
        if (ca, cb) not in self._index:
            return False
        rid = self._index[(ca, cb)]
        r = self._rivalries[rid]
        if r.state == RivalryState.RESOLVED:
            return False
        new_count = r.incidents_count + 1
        new_state = r.state
        if (
            r.state == RivalryState.SIMMERING
            and new_count >= _FEUD_THRESHOLD
        ):
            new_state = RivalryState.FEUDING
        self._rivalries[rid] = dataclasses.replace(
            r, incidents_count=new_count,
            state=new_state,
        )
        return True

    def take_side(
        self, *, rivalry_id: str, supporter_id: str,
        side_with: str,
    ) -> bool:
        if rivalry_id not in self._rivalries:
            return False
        r = self._rivalries[rivalry_id]
        if r.state == RivalryState.RESOLVED:
            return False
        if not supporter_id:
            return False
        if supporter_id in (r.entity_a, r.entity_b):
            return False
        if side_with not in (r.entity_a, r.entity_b):
            return False
        # Player can side with at most one party per
        # rivalry; flipping requires unsupporting first
        if (
            supporter_id in r.a_supporters
            or supporter_id in r.b_supporters
        ):
            return False
        if side_with == r.entity_a:
            new_a = r.a_supporters + (supporter_id,)
            self._rivalries[rivalry_id] = (
                dataclasses.replace(
                    r, a_supporters=new_a,
                )
            )
        else:
            new_b = r.b_supporters + (supporter_id,)
            self._rivalries[rivalry_id] = (
                dataclasses.replace(
                    r, b_supporters=new_b,
                )
            )
        return True

    def reconcile(
        self, *, rivalry_id: str,
    ) -> t.Optional[int]:
        """Mediated peace. Returns honor gain for
        each supporter on either side."""
        if rivalry_id not in self._rivalries:
            return None
        r = self._rivalries[rivalry_id]
        if r.state == RivalryState.RESOLVED:
            return None
        self._rivalries[rivalry_id] = dataclasses.replace(
            r, state=RivalryState.RESOLVED,
            resolution="reconciled",
        )
        return _RECONCILE_HONOR_GAIN

    def settle_by_victory(
        self, *, rivalry_id: str, victor_id: str,
    ) -> bool:
        if rivalry_id not in self._rivalries:
            return False
        r = self._rivalries[rivalry_id]
        if r.state == RivalryState.RESOLVED:
            return False
        if victor_id == r.entity_a:
            res = "a_won"
        elif victor_id == r.entity_b:
            res = "b_won"
        else:
            return False
        self._rivalries[rivalry_id] = dataclasses.replace(
            r, state=RivalryState.RESOLVED,
            resolution=res,
        )
        return True

    def rivalry(
        self, *, rivalry_id: str,
    ) -> t.Optional[Rivalry]:
        return self._rivalries.get(rivalry_id)

    def rivalries_of(
        self, *, entity_id: str,
    ) -> list[Rivalry]:
        return [
            r for r in self._rivalries.values()
            if entity_id in (r.entity_a, r.entity_b)
        ]

    def supporter_lookup(
        self, *, supporter_id: str,
    ) -> list[Rivalry]:
        return [
            r for r in self._rivalries.values()
            if (
                supporter_id in r.a_supporters
                or supporter_id in r.b_supporters
            )
        ]


__all__ = [
    "RivalryState", "Rivalry", "EntityRivalrySystem",
]
