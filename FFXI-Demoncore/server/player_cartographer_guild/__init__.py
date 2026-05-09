"""Player cartographer guild — registered surveyors of Vana'diel.

A guildmaster founds a cartographer guild. Members must
demonstrate survey skill (a proxy for actually walking
zones) before being inducted. Each member earns a
cartographer_rank that grows with surveys submitted —
NOVICE -> JOURNEYMAN -> MASTER. Ranks gate which map
publications a member can sign as authoritative.

Lifecycle (member)
    APPRENTICE   accepted but unranked
    NOVICE       1+ surveys submitted
    JOURNEYMAN   10+ surveys
    MASTER       50+ surveys

Public surface
--------------
    GuildState enum
    CartographerRank enum
    CartographerGuild dataclass (frozen)
    Member dataclass (frozen)
    PlayerCartographerGuildSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_NOVICE_THRESHOLD = 1
_JOURNEYMAN_THRESHOLD = 10
_MASTER_THRESHOLD = 50
_MIN_SURVEY_SKILL = 30


class GuildState(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class CartographerRank(str, enum.Enum):
    APPRENTICE = "apprentice"
    NOVICE = "novice"
    JOURNEYMAN = "journeyman"
    MASTER = "master"


@dataclasses.dataclass(frozen=True)
class CartographerGuild:
    guild_id: str
    guildmaster_id: str
    name: str
    state: GuildState


@dataclasses.dataclass(frozen=True)
class Member:
    cartographer_id: str
    rank: CartographerRank
    surveys_submitted: int


@dataclasses.dataclass
class _GState:
    spec: CartographerGuild
    members: dict[str, Member] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class PlayerCartographerGuildSystem:
    _guilds: dict[str, _GState] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def found_guild(
        self, *, guildmaster_id: str, name: str,
    ) -> t.Optional[str]:
        if not guildmaster_id or not name:
            return None
        gid = f"cguild_{self._next}"
        self._next += 1
        self._guilds[gid] = _GState(
            spec=CartographerGuild(
                guild_id=gid,
                guildmaster_id=guildmaster_id,
                name=name, state=GuildState.OPEN,
            ),
        )
        return gid

    def induct(
        self, *, guild_id: str, guildmaster_id: str,
        cartographer_id: str, survey_skill: int,
    ) -> bool:
        if guild_id not in self._guilds:
            return False
        st = self._guilds[guild_id]
        if st.spec.state != GuildState.OPEN:
            return False
        if st.spec.guildmaster_id != guildmaster_id:
            return False
        if not cartographer_id:
            return False
        if cartographer_id == guildmaster_id:
            return False
        if cartographer_id in st.members:
            return False
        if survey_skill < _MIN_SURVEY_SKILL:
            return False
        st.members[cartographer_id] = Member(
            cartographer_id=cartographer_id,
            rank=CartographerRank.APPRENTICE,
            surveys_submitted=0,
        )
        return True

    def submit_survey(
        self, *, guild_id: str,
        cartographer_id: str,
    ) -> bool:
        """Member submits one survey to their guild;
        promotes rank if a threshold is crossed."""
        if guild_id not in self._guilds:
            return False
        st = self._guilds[guild_id]
        if st.spec.state != GuildState.OPEN:
            return False
        if cartographer_id not in st.members:
            return False
        m = st.members[cartographer_id]
        new_count = m.surveys_submitted + 1
        new_rank = self._rank_for(new_count)
        st.members[cartographer_id] = (
            dataclasses.replace(
                m, surveys_submitted=new_count,
                rank=new_rank,
            )
        )
        return True

    @staticmethod
    def _rank_for(
        surveys: int,
    ) -> CartographerRank:
        if surveys >= _MASTER_THRESHOLD:
            return CartographerRank.MASTER
        if surveys >= _JOURNEYMAN_THRESHOLD:
            return CartographerRank.JOURNEYMAN
        if surveys >= _NOVICE_THRESHOLD:
            return CartographerRank.NOVICE
        return CartographerRank.APPRENTICE

    def expel(
        self, *, guild_id: str, guildmaster_id: str,
        cartographer_id: str,
    ) -> bool:
        if guild_id not in self._guilds:
            return False
        st = self._guilds[guild_id]
        if st.spec.guildmaster_id != guildmaster_id:
            return False
        if cartographer_id not in st.members:
            return False
        del st.members[cartographer_id]
        return True

    def close(
        self, *, guild_id: str, guildmaster_id: str,
    ) -> bool:
        if guild_id not in self._guilds:
            return False
        st = self._guilds[guild_id]
        if st.spec.guildmaster_id != guildmaster_id:
            return False
        if st.spec.state != GuildState.OPEN:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=GuildState.CLOSED,
        )
        return True

    def guild(
        self, *, guild_id: str,
    ) -> t.Optional[CartographerGuild]:
        st = self._guilds.get(guild_id)
        return st.spec if st else None

    def member(
        self, *, guild_id: str,
        cartographer_id: str,
    ) -> t.Optional[Member]:
        st = self._guilds.get(guild_id)
        if st is None:
            return None
        return st.members.get(cartographer_id)

    def members(
        self, *, guild_id: str,
    ) -> list[Member]:
        st = self._guilds.get(guild_id)
        if st is None:
            return []
        return list(st.members.values())


__all__ = [
    "GuildState", "CartographerRank",
    "CartographerGuild", "Member",
    "PlayerCartographerGuildSystem",
]
