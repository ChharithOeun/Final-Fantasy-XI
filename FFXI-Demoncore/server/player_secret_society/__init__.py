"""Player secret society — covenant orders with oaths.

Beyond linkshells (publicly known guilds) lie SECRET
SOCIETIES: hidden orders of players bound by oath. A
society has hidden membership, ranked tiers, oath
covenants, and access to society-only quest chains.
Initiation requires a sponsor; betrayal is recorded
and the apostate cannot rejoin the same society.

Society rank ladder (caller can author beyond, but
default is 5 ranks):
    INITIATE -> ACOLYTE -> ADEPT -> MASTER ->
    GRANDMASTER

Oath kinds (free-form, but conventional):
    SECRECY        never speak society name in public
    LOYALTY        defend other members from PvP
    SACRIFICE      donate share of gil quarterly
    KNOWLEDGE      share recipes/spells found

Public surface
--------------
    Rank enum
    MembershipState enum
    Society dataclass (frozen)
    Membership dataclass (frozen)
    PlayerSecretSocietySystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Rank(str, enum.Enum):
    INITIATE = "initiate"
    ACOLYTE = "acolyte"
    ADEPT = "adept"
    MASTER = "master"
    GRANDMASTER = "grandmaster"


class MembershipState(str, enum.Enum):
    INDUCTED = "inducted"
    DEPARTED = "departed"
    APOSTATE = "apostate"
    DECEASED = "deceased"


_RANK_ORDER = [
    Rank.INITIATE, Rank.ACOLYTE, Rank.ADEPT,
    Rank.MASTER, Rank.GRANDMASTER,
]


@dataclasses.dataclass(frozen=True)
class Society:
    society_id: str
    name: str
    founder_id: str
    founded_day: int
    oath_kinds: tuple[str, ...]
    grandmaster_id: str


@dataclasses.dataclass(frozen=True)
class Membership:
    society_id: str
    player_id: str
    sponsor_id: str
    rank: Rank
    inducted_day: int
    state: MembershipState
    state_changed_day: t.Optional[int]


@dataclasses.dataclass
class PlayerSecretSocietySystem:
    _societies: dict[str, Society] = (
        dataclasses.field(default_factory=dict)
    )
    _memberships: dict[
        tuple[str, str], Membership
    ] = dataclasses.field(default_factory=dict)

    def found(
        self, *, society_id: str, name: str,
        founder_id: str, founded_day: int,
        oath_kinds: t.Sequence[str],
    ) -> bool:
        if not society_id or not name:
            return False
        if not founder_id:
            return False
        if not oath_kinds:
            return False
        if founded_day < 0:
            return False
        if society_id in self._societies:
            return False
        self._societies[society_id] = Society(
            society_id=society_id, name=name,
            founder_id=founder_id,
            founded_day=founded_day,
            oath_kinds=tuple(oath_kinds),
            grandmaster_id=founder_id,
        )
        # Founder is an INDUCTED Grandmaster
        self._memberships[
            (society_id, founder_id)
        ] = Membership(
            society_id=society_id,
            player_id=founder_id,
            sponsor_id=founder_id,
            rank=Rank.GRANDMASTER,
            inducted_day=founded_day,
            state=MembershipState.INDUCTED,
            state_changed_day=None,
        )
        return True

    def induct(
        self, *, society_id: str, player_id: str,
        sponsor_id: str, now_day: int,
    ) -> bool:
        if society_id not in self._societies:
            return False
        if not player_id or not sponsor_id:
            return False
        if player_id == sponsor_id:
            return False
        sponsor_key = (society_id, sponsor_id)
        if sponsor_key not in self._memberships:
            return False
        sponsor = self._memberships[sponsor_key]
        if sponsor.state != MembershipState.INDUCTED:
            return False
        if sponsor.rank == Rank.INITIATE:
            return False
        # Block apostate rejoining
        member_key = (society_id, player_id)
        existing = self._memberships.get(member_key)
        if existing is not None:
            if existing.state == (
                MembershipState.APOSTATE
            ):
                return False
            if existing.state == (
                MembershipState.INDUCTED
            ):
                return False
        self._memberships[member_key] = Membership(
            society_id=society_id,
            player_id=player_id,
            sponsor_id=sponsor_id,
            rank=Rank.INITIATE,
            inducted_day=now_day,
            state=MembershipState.INDUCTED,
            state_changed_day=None,
        )
        return True

    def promote(
        self, *, society_id: str, player_id: str,
    ) -> bool:
        key = (society_id, player_id)
        if key not in self._memberships:
            return False
        m = self._memberships[key]
        if m.state != MembershipState.INDUCTED:
            return False
        try:
            idx = _RANK_ORDER.index(m.rank)
        except ValueError:
            return False
        if idx + 1 >= len(_RANK_ORDER):
            return False
        new_rank = _RANK_ORDER[idx + 1]
        # Only one GRANDMASTER per society
        if new_rank == Rank.GRANDMASTER:
            for k, mm in self._memberships.items():
                if (k[0] == society_id
                        and mm.rank
                        == Rank.GRANDMASTER
                        and mm.state
                        == MembershipState.INDUCTED):
                    return False
        self._memberships[key] = dataclasses.replace(
            m, rank=new_rank,
        )
        if new_rank == Rank.GRANDMASTER:
            soc = self._societies[society_id]
            self._societies[society_id] = (
                dataclasses.replace(
                    soc, grandmaster_id=player_id,
                )
            )
        return True

    def depart(
        self, *, society_id: str, player_id: str,
        now_day: int,
    ) -> bool:
        key = (society_id, player_id)
        if key not in self._memberships:
            return False
        m = self._memberships[key]
        if m.state != MembershipState.INDUCTED:
            return False
        self._memberships[key] = dataclasses.replace(
            m, state=MembershipState.DEPARTED,
            state_changed_day=now_day,
        )
        return True

    def mark_apostate(
        self, *, society_id: str, player_id: str,
        now_day: int,
    ) -> bool:
        key = (society_id, player_id)
        if key not in self._memberships:
            return False
        m = self._memberships[key]
        if m.state != MembershipState.INDUCTED:
            return False
        self._memberships[key] = dataclasses.replace(
            m, state=MembershipState.APOSTATE,
            state_changed_day=now_day,
        )
        return True

    def mark_deceased(
        self, *, society_id: str, player_id: str,
        now_day: int,
    ) -> bool:
        key = (society_id, player_id)
        if key not in self._memberships:
            return False
        m = self._memberships[key]
        if m.state == MembershipState.DECEASED:
            return False
        self._memberships[key] = dataclasses.replace(
            m, state=MembershipState.DECEASED,
            state_changed_day=now_day,
        )
        return True

    def members_of(
        self, *, society_id: str,
    ) -> list[Membership]:
        return [
            m for k, m in self._memberships.items()
            if (k[0] == society_id
                and m.state
                == MembershipState.INDUCTED)
        ]

    def membership(
        self, *, society_id: str, player_id: str,
    ) -> t.Optional[Membership]:
        return self._memberships.get(
            (society_id, player_id),
        )

    def societies_of(
        self, *, player_id: str,
    ) -> list[Society]:
        out: list[Society] = []
        for k, m in self._memberships.items():
            if k[1] != player_id:
                continue
            if m.state != MembershipState.INDUCTED:
                continue
            out.append(self._societies[k[0]])
        return out

    def society(
        self, *, society_id: str,
    ) -> t.Optional[Society]:
        return self._societies.get(society_id)


__all__ = [
    "Rank", "MembershipState", "Society",
    "Membership", "PlayerSecretSocietySystem",
]
