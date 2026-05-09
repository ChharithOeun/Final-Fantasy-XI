"""Player stage play — write a script, cast it, rehearse, perform.

Players can author short plays, cast their LS-mates or NPCs in
roles, rehearse to raise preparation_score, and stage a public
performance for an audience review. Reviews depend on
script_quality + cast skill + rehearsal preparation.

Lifecycle
    DRAFT         author writing the script
    CAST          roles assigned, ready to rehearse
    REHEARSING    rehearsals raise preparation_score
    PERFORMING    public performance happened
    CLOSED        run ended, review final

Public surface
--------------
    PlayState enum
    Role dataclass (frozen)
    Performance dataclass (frozen)
    Play dataclass (frozen)
    PlayerStagePlaySystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_MAX_REHEARSALS = 10


class PlayState(str, enum.Enum):
    DRAFT = "draft"
    CAST = "cast"
    REHEARSING = "rehearsing"
    PERFORMING = "performing"
    CLOSED = "closed"


@dataclasses.dataclass(frozen=True)
class Role:
    role_id: str
    role_name: str
    actor_id: str
    actor_skill: int  # 1..100


@dataclasses.dataclass(frozen=True)
class Performance:
    performance_id: str
    play_id: str
    audience_size: int
    review_score: int
    performed_day: int


@dataclasses.dataclass(frozen=True)
class Play:
    play_id: str
    title: str
    author_id: str
    num_acts: int
    script_quality: int
    state: PlayState
    rehearsal_count: int
    preparation_score: int
    performance: t.Optional[Performance]


@dataclasses.dataclass
class _PState:
    spec: Play
    roles: dict[str, Role] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class PlayerStagePlaySystem:
    _plays: dict[str, _PState] = dataclasses.field(
        default_factory=dict,
    )
    _next_play: int = 1
    _next_role: int = 1
    _next_perf: int = 1

    def author_play(
        self, *, title: str, author_id: str,
        num_acts: int, script_quality: int,
    ) -> t.Optional[str]:
        if not title or not author_id:
            return None
        if num_acts < 1 or num_acts > 5:
            return None
        if not 1 <= script_quality <= 100:
            return None
        pid = f"play_{self._next_play}"
        self._next_play += 1
        spec = Play(
            play_id=pid, title=title,
            author_id=author_id, num_acts=num_acts,
            script_quality=script_quality,
            state=PlayState.DRAFT,
            rehearsal_count=0, preparation_score=0,
            performance=None,
        )
        self._plays[pid] = _PState(spec=spec)
        return pid

    def cast_role(
        self, *, play_id: str, role_name: str,
        actor_id: str, actor_skill: int,
    ) -> t.Optional[str]:
        if play_id not in self._plays:
            return None
        st = self._plays[play_id]
        if st.spec.state != PlayState.DRAFT:
            return None
        if not role_name or not actor_id:
            return None
        if not 1 <= actor_skill <= 100:
            return None
        # One actor cannot play two roles
        for r in st.roles.values():
            if r.actor_id == actor_id:
                return None
        rid = f"role_{self._next_role}"
        self._next_role += 1
        st.roles[rid] = Role(
            role_id=rid, role_name=role_name,
            actor_id=actor_id, actor_skill=actor_skill,
        )
        return rid

    def lock_cast(self, *, play_id: str) -> bool:
        if play_id not in self._plays:
            return False
        st = self._plays[play_id]
        if st.spec.state != PlayState.DRAFT:
            return False
        if not st.roles:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=PlayState.CAST,
        )
        return True

    def begin_rehearsals(
        self, *, play_id: str,
    ) -> bool:
        if play_id not in self._plays:
            return False
        st = self._plays[play_id]
        if st.spec.state != PlayState.CAST:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=PlayState.REHEARSING,
        )
        return True

    def rehearse(
        self, *, play_id: str,
    ) -> t.Optional[int]:
        """One rehearsal session. Adds +5 prep per
        rehearsal up to a cap; returns new prep total.
        """
        if play_id not in self._plays:
            return None
        st = self._plays[play_id]
        if st.spec.state != PlayState.REHEARSING:
            return None
        if st.spec.rehearsal_count >= _MAX_REHEARSALS:
            return st.spec.preparation_score
        new_count = st.spec.rehearsal_count + 1
        new_prep = st.spec.preparation_score + 5
        st.spec = dataclasses.replace(
            st.spec, rehearsal_count=new_count,
            preparation_score=new_prep,
        )
        return new_prep

    def perform(
        self, *, play_id: str, audience_size: int,
        performed_day: int, seed: int,
    ) -> t.Optional[int]:
        if play_id not in self._plays:
            return None
        st = self._plays[play_id]
        if st.spec.state != PlayState.REHEARSING:
            return None
        if audience_size < 0 or performed_day < 0:
            return None
        avg_skill = (
            sum(r.actor_skill for r in st.roles.values())
            // max(1, len(st.roles))
        )
        variance = (seed % 21) - 10  # -10..+10
        review = (
            st.spec.script_quality
            + avg_skill
            + st.spec.preparation_score
            + variance
        )
        review = max(0, review)
        perf_id = f"perf_{self._next_perf}"
        self._next_perf += 1
        perf = Performance(
            performance_id=perf_id, play_id=play_id,
            audience_size=audience_size,
            review_score=review,
            performed_day=performed_day,
        )
        st.spec = dataclasses.replace(
            st.spec, state=PlayState.PERFORMING,
            performance=perf,
        )
        return review

    def close_run(self, *, play_id: str) -> bool:
        if play_id not in self._plays:
            return False
        st = self._plays[play_id]
        if st.spec.state != PlayState.PERFORMING:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=PlayState.CLOSED,
        )
        return True

    def play(
        self, *, play_id: str,
    ) -> t.Optional[Play]:
        st = self._plays.get(play_id)
        return st.spec if st else None

    def roles(
        self, *, play_id: str,
    ) -> list[Role]:
        st = self._plays.get(play_id)
        if st is None:
            return []
        return list(st.roles.values())


__all__ = [
    "PlayState", "Role", "Performance", "Play",
    "PlayerStagePlaySystem",
]
