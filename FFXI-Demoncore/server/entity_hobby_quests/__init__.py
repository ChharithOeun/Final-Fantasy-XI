"""Entity hobby quests — NPCs need help with their hobby.

NPCs occasionally need items or services for their hobby:
Volker's lost his lucky lure and won't fish without it,
Naji's calligraphy ink ran dry and he can't replenish until
the next caravan, the Goblin Smithy's anvil cracked and he
needs a replacement. These needs become small player-facing
quests — the player who delivers earns relationship credit
and sometimes a hobby-secret unlock (Volker shares his secret
spot, Naji teaches a calligraphy flourish).

Lifecycle (per quest)
    NEED        NPC has a need, no player accepted yet
    ACCEPTED    a player took the quest
    DELIVERED   player turned in the requested item/service
    EXPIRED     deadline passed without delivery

Public surface
--------------
    QuestState enum
    HobbyNeed dataclass (frozen)
    EntityHobbyQuestsSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.entity_hobbies import HobbyKind


_BASE_RELATIONSHIP_GAIN = 10
_RARE_NEED_BONUS = 25


class QuestState(str, enum.Enum):
    NEED = "need"
    ACCEPTED = "accepted"
    DELIVERED = "delivered"
    EXPIRED = "expired"


@dataclasses.dataclass(frozen=True)
class HobbyNeed:
    quest_id: str
    npc_id: str
    hobby: HobbyKind
    requested_item: str
    is_rare: bool
    posted_day: int
    deadline_day: int
    state: QuestState
    accepted_by: str
    delivered_day: int
    relationship_gain: int
    secret_unlocked: str   # blank if no secret


@dataclasses.dataclass
class EntityHobbyQuestsSystem:
    _quests: dict[str, HobbyNeed] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def post_need(
        self, *, npc_id: str, hobby: HobbyKind,
        requested_item: str, posted_day: int,
        deadline_day: int, is_rare: bool = False,
        secret_on_delivery: str = "",
    ) -> t.Optional[str]:
        if not npc_id or not requested_item:
            return None
        if posted_day < 0:
            return None
        if deadline_day <= posted_day:
            return None
        qid = f"quest_{self._next}"
        self._next += 1
        self._quests[qid] = HobbyNeed(
            quest_id=qid, npc_id=npc_id, hobby=hobby,
            requested_item=requested_item,
            is_rare=is_rare, posted_day=posted_day,
            deadline_day=deadline_day,
            state=QuestState.NEED, accepted_by="",
            delivered_day=0, relationship_gain=0,
            secret_unlocked=secret_on_delivery,
        )
        return qid

    def accept(
        self, *, quest_id: str, player_id: str,
    ) -> bool:
        if quest_id not in self._quests:
            return False
        q = self._quests[quest_id]
        if q.state != QuestState.NEED:
            return False
        if not player_id or player_id == q.npc_id:
            return False
        self._quests[quest_id] = dataclasses.replace(
            q, state=QuestState.ACCEPTED,
            accepted_by=player_id,
        )
        return True

    def deliver(
        self, *, quest_id: str, player_id: str,
        current_day: int,
    ) -> t.Optional[int]:
        """Returns relationship gain on success."""
        if quest_id not in self._quests:
            return None
        q = self._quests[quest_id]
        if q.state != QuestState.ACCEPTED:
            return None
        if q.accepted_by != player_id:
            return None
        if current_day < q.posted_day:
            return None
        if current_day > q.deadline_day:
            return None
        gain = _BASE_RELATIONSHIP_GAIN
        if q.is_rare:
            gain += _RARE_NEED_BONUS
        self._quests[quest_id] = dataclasses.replace(
            q, state=QuestState.DELIVERED,
            delivered_day=current_day,
            relationship_gain=gain,
        )
        return gain

    def auto_expire(
        self, *, quest_id: str, current_day: int,
    ) -> bool:
        if quest_id not in self._quests:
            return False
        q = self._quests[quest_id]
        if q.state not in (
            QuestState.NEED, QuestState.ACCEPTED,
        ):
            return False
        if current_day <= q.deadline_day:
            return False
        self._quests[quest_id] = dataclasses.replace(
            q, state=QuestState.EXPIRED,
        )
        return True

    def secret_for(
        self, *, quest_id: str, player_id: str,
    ) -> t.Optional[str]:
        """Returns the secret string if delivered
        and player is the deliverer; empty string
        means the quest had no secret."""
        if quest_id not in self._quests:
            return None
        q = self._quests[quest_id]
        if q.state != QuestState.DELIVERED:
            return None
        if q.accepted_by != player_id:
            return None
        return q.secret_unlocked

    def quest(
        self, *, quest_id: str,
    ) -> t.Optional[HobbyNeed]:
        return self._quests.get(quest_id)

    def open_needs_for(
        self, *, npc_id: str,
    ) -> list[HobbyNeed]:
        return [
            q for q in self._quests.values()
            if q.npc_id == npc_id
            and q.state == QuestState.NEED
        ]

    def player_history(
        self, *, player_id: str,
    ) -> list[HobbyNeed]:
        return [
            q for q in self._quests.values()
            if q.accepted_by == player_id
        ]


__all__ = [
    "QuestState", "HobbyNeed",
    "EntityHobbyQuestsSystem",
]
