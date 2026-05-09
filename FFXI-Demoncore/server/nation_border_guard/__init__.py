"""Nation border guard — zone-edge posts and intercepts.

While nation_army handles the standing military force,
nation_border_guard handles the day-to-day work of
watching the border: GUARD POSTS at zone edges, PATROL
SHIFTS through the day-night cycle, and SMUGGLER
INTERCEPTS — caught contraband and the gil/rep
consequences.

Each post sits at a zone-zone boundary (or city gate)
and has a guard count that determines its detection
strength. Patrols run on shifts (DAY / NIGHT /
GRAVEYARD); each shift has assigned guards, and a
shift with too few guards has reduced effectiveness
(the caller can read this for spawn-rate tuning).

Smuggler intercepts log the catch: who was carrying,
what, value, when, which post.

Public surface
--------------
    Shift enum
    PostState enum
    GuardPost dataclass (frozen)
    PatrolShift dataclass (frozen)
    SmugglerIntercept dataclass (frozen)
    NationBorderGuardSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_MIN_SHIFT_GUARDS = 2


class Shift(str, enum.Enum):
    DAY = "day"
    NIGHT = "night"
    GRAVEYARD = "graveyard"


class PostState(str, enum.Enum):
    OPERATIONAL = "operational"
    UNDERMANNED = "undermanned"
    ABANDONED = "abandoned"


@dataclasses.dataclass(frozen=True)
class GuardPost:
    post_id: str
    nation_id: str
    zone_a: str
    zone_b: str
    guard_count: int
    state: PostState


@dataclasses.dataclass(frozen=True)
class PatrolShift:
    post_id: str
    shift: Shift
    assigned_guards: int


@dataclasses.dataclass(frozen=True)
class SmugglerIntercept:
    intercept_id: str
    post_id: str
    smuggler_id: str
    contraband: str
    value_gil: int
    intercepted_day: int
    shift: Shift


@dataclasses.dataclass
class NationBorderGuardSystem:
    _posts: dict[str, GuardPost] = dataclasses.field(
        default_factory=dict,
    )
    _shifts: dict[tuple[str, Shift], PatrolShift] = (
        dataclasses.field(default_factory=dict)
    )
    _intercepts: dict[str, SmugglerIntercept] = (
        dataclasses.field(default_factory=dict)
    )
    _next_int: int = 1

    def _refresh_post_state(self, post_id: str) -> None:
        p = self._posts[post_id]
        if p.state == PostState.ABANDONED:
            return
        if p.guard_count <= 0:
            new_state = PostState.ABANDONED
        elif p.guard_count < _MIN_SHIFT_GUARDS * 3:
            new_state = PostState.UNDERMANNED
        else:
            new_state = PostState.OPERATIONAL
        if new_state != p.state:
            self._posts[post_id] = (
                dataclasses.replace(p, state=new_state)
            )

    def establish_post(
        self, *, post_id: str, nation_id: str,
        zone_a: str, zone_b: str, guard_count: int,
    ) -> bool:
        if not post_id or not nation_id:
            return False
        if not zone_a or not zone_b:
            return False
        if zone_a == zone_b:
            return False
        if guard_count < 0:
            return False
        if post_id in self._posts:
            return False
        self._posts[post_id] = GuardPost(
            post_id=post_id, nation_id=nation_id,
            zone_a=zone_a, zone_b=zone_b,
            guard_count=guard_count,
            state=PostState.OPERATIONAL,
        )
        self._refresh_post_state(post_id)
        return True

    def reinforce_post(
        self, *, post_id: str, additional_guards: int,
    ) -> bool:
        if post_id not in self._posts:
            return False
        if additional_guards <= 0:
            return False
        p = self._posts[post_id]
        if p.state == PostState.ABANDONED:
            return False
        self._posts[post_id] = dataclasses.replace(
            p, guard_count=(
                p.guard_count + additional_guards
            ),
        )
        self._refresh_post_state(post_id)
        return True

    def lose_guards(
        self, *, post_id: str, lost: int,
    ) -> bool:
        if post_id not in self._posts:
            return False
        if lost <= 0:
            return False
        p = self._posts[post_id]
        if p.state == PostState.ABANDONED:
            return False
        self._posts[post_id] = dataclasses.replace(
            p, guard_count=max(0, p.guard_count - lost),
        )
        self._refresh_post_state(post_id)
        return True

    def assign_shift(
        self, *, post_id: str, shift: Shift,
        assigned_guards: int,
    ) -> bool:
        if post_id not in self._posts:
            return False
        if assigned_guards < 0:
            return False
        p = self._posts[post_id]
        if assigned_guards > p.guard_count:
            return False
        self._shifts[(post_id, shift)] = PatrolShift(
            post_id=post_id, shift=shift,
            assigned_guards=assigned_guards,
        )
        return True

    def shift_effectiveness_pct(
        self, *, post_id: str, shift: Shift,
    ) -> int:
        sh = self._shifts.get((post_id, shift))
        if sh is None:
            return 0
        if sh.assigned_guards >= _MIN_SHIFT_GUARDS:
            return 100
        if sh.assigned_guards == 0:
            return 0
        return 50

    def record_intercept(
        self, *, post_id: str, smuggler_id: str,
        contraband: str, value_gil: int,
        intercepted_day: int, shift: Shift,
    ) -> t.Optional[str]:
        if post_id not in self._posts:
            return None
        if not smuggler_id or not contraband:
            return None
        if value_gil < 0 or intercepted_day < 0:
            return None
        p = self._posts[post_id]
        if p.state == PostState.ABANDONED:
            return None
        iid = f"int_{self._next_int}"
        self._next_int += 1
        self._intercepts[iid] = SmugglerIntercept(
            intercept_id=iid, post_id=post_id,
            smuggler_id=smuggler_id,
            contraband=contraband,
            value_gil=value_gil,
            intercepted_day=intercepted_day,
            shift=shift,
        )
        return iid

    def post(
        self, *, post_id: str,
    ) -> t.Optional[GuardPost]:
        return self._posts.get(post_id)

    def posts_for(
        self, *, nation_id: str,
    ) -> list[GuardPost]:
        return [
            p for p in self._posts.values()
            if p.nation_id == nation_id
        ]

    def posts_at(
        self, *, zone: str,
    ) -> list[GuardPost]:
        return [
            p for p in self._posts.values()
            if (p.zone_a == zone or p.zone_b == zone)
        ]

    def intercepts_at(
        self, *, post_id: str,
    ) -> list[SmugglerIntercept]:
        return [
            i for i in self._intercepts.values()
            if i.post_id == post_id
        ]

    def intercepts_of(
        self, *, smuggler_id: str,
    ) -> list[SmugglerIntercept]:
        return [
            i for i in self._intercepts.values()
            if i.smuggler_id == smuggler_id
        ]


__all__ = [
    "Shift", "PostState", "GuardPost", "PatrolShift",
    "SmugglerIntercept", "NationBorderGuardSystem",
]
