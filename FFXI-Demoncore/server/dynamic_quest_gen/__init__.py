"""Dynamic quest generation — NPCs author quests from need state.

There is no hard-coded quest list in Demoncore. NPCs are AI agents
with REAL needs (their lumber stockpile is low, they're worried
about a missing daughter, the beastmen pressure on their nation
just spiked). When the need crosses a threshold, the NPC's AI
publishes a quest. When the need is resolved (player turns in
lumber, or the daughter returns home), the quest is closed —
even mid-flight, even if no player took it.

Need model
----------
Each NPC publishes a `NeedSnapshot` each tick — a typed need with
an urgency score [0..100]. The quest engine consults the snapshot
table and:

* Creates a new `DynamicQuest` if a need crosses GENERATION_THRESHOLD
* Updates the urgency on existing quests
* Closes a quest if the underlying need has dropped below
  RESOLVED_THRESHOLD (need was met by the world, not by the player)
* Expires a quest if its NPC has been silent (no need updates)
  for too long

Quests carry a list of objectives the player can complete
(KILL_COUNT, GATHER_ITEM, ESCORT_NPC, INTERACT, DELIVER), an
expiry timestamp, and a reward bundle. The QuestEngine
exposes the surface the orchestrator wires up:

    engine.publish_need(npc_id, need)
    engine.tick(now_seconds)        — generates / closes quests
    engine.open_quests_for(npc_id)
    engine.player_accept(player_id, quest_id)
    engine.player_progress(player_id, quest_id, objective_idx, +n)
    engine.player_turn_in(player_id, quest_id)

Public surface
--------------
    NeedKind enum
    NeedSnapshot dataclass — what the NPC's AI publishes
    ObjectiveKind enum
    QuestObjective dataclass
    DynamicQuest dataclass
    QuestEngine — the loop
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


GENERATION_THRESHOLD = 60       # urgency to spawn a quest
RESOLVED_THRESHOLD = 20         # urgency below this -> auto-close
NEED_STALE_SECONDS = 60 * 60    # 1 hour real-time silence -> expire
DEFAULT_REWARD_GIL = 500
DEFAULT_REWARD_REPUTATION = 5


class NeedKind(str, enum.Enum):
    LUMBER_LOW = "lumber_low"
    FOOD_LOW = "food_low"
    WATER_LOW = "water_low"
    MEDICINE_LOW = "medicine_low"
    BEASTMEN_PRESSURE = "beastmen_pressure"
    MISSING_PERSON = "missing_person"
    HAUNTING = "haunting"
    PROTEST_BREWING = "protest_brewing"
    PEST_INFESTATION = "pest_infestation"
    OUTPOST_LOST_CONTACT = "outpost_lost_contact"
    PROPHECY_REQUIRES_TASK = "prophecy_requires_task"
    DELIVERY_NEEDED = "delivery_needed"


class ObjectiveKind(str, enum.Enum):
    KILL_COUNT = "kill_count"
    GATHER_ITEM = "gather_item"
    ESCORT_NPC = "escort_npc"
    INTERACT = "interact"          # talk to / lay flowers / pray
    DELIVER = "deliver"


# Mapping from a need to the kinds of objective the NPC's AI
# is most likely to author. The orchestrator can override per-NPC
# but this is the sensible default.
_DEFAULT_OBJECTIVE_KIND: dict[NeedKind, ObjectiveKind] = {
    NeedKind.LUMBER_LOW: ObjectiveKind.GATHER_ITEM,
    NeedKind.FOOD_LOW: ObjectiveKind.GATHER_ITEM,
    NeedKind.WATER_LOW: ObjectiveKind.GATHER_ITEM,
    NeedKind.MEDICINE_LOW: ObjectiveKind.GATHER_ITEM,
    NeedKind.BEASTMEN_PRESSURE: ObjectiveKind.KILL_COUNT,
    NeedKind.MISSING_PERSON: ObjectiveKind.ESCORT_NPC,
    NeedKind.HAUNTING: ObjectiveKind.INTERACT,
    NeedKind.PROTEST_BREWING: ObjectiveKind.INTERACT,
    NeedKind.PEST_INFESTATION: ObjectiveKind.KILL_COUNT,
    NeedKind.OUTPOST_LOST_CONTACT: ObjectiveKind.INTERACT,
    NeedKind.PROPHECY_REQUIRES_TASK: ObjectiveKind.DELIVER,
    NeedKind.DELIVERY_NEEDED: ObjectiveKind.DELIVER,
}


@dataclasses.dataclass(frozen=True)
class NeedSnapshot:
    """What the NPC's AI publishes each tick."""
    npc_id: str
    kind: NeedKind
    urgency: int                # 0..100
    target_id: str = ""         # item / mob / npc id, if any
    target_count: int = 1
    notes: str = ""

    def __post_init__(self) -> None:
        if not (0 <= self.urgency <= 100):
            raise ValueError(
                f"urgency {self.urgency} out of 0-100",
            )


@dataclasses.dataclass
class QuestObjective:
    kind: ObjectiveKind
    target_id: str
    target_count: int = 1
    progress: int = 0

    @property
    def completed(self) -> bool:
        return self.progress >= self.target_count


@dataclasses.dataclass
class QuestReward:
    gil: int = DEFAULT_REWARD_GIL
    reputation_delta: int = DEFAULT_REWARD_REPUTATION
    item_id: str = ""
    item_count: int = 0


@dataclasses.dataclass
class DynamicQuest:
    quest_id: str
    npc_id: str
    need_kind: NeedKind
    title: str
    objectives: list[QuestObjective]
    reward: QuestReward
    created_at_seconds: float
    expires_at_seconds: float
    accepted_by: t.Optional[str] = None  # player_id
    completed: bool = False
    cancelled: bool = False

    def is_active(self, *, now_seconds: float) -> bool:
        if self.completed or self.cancelled:
            return False
        return now_seconds < self.expires_at_seconds

    def all_objectives_done(self) -> bool:
        return all(o.completed for o in self.objectives)


@dataclasses.dataclass(frozen=True)
class TurnInResult:
    accepted: bool
    reward: t.Optional[QuestReward] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class QuestEngine:
    quest_lifetime_seconds: float = 60 * 60 * 24    # 24 game-hours
    _needs: dict[
        tuple[str, NeedKind], NeedSnapshot,
    ] = dataclasses.field(default_factory=dict)
    _last_publish: dict[
        tuple[str, NeedKind], float,
    ] = dataclasses.field(default_factory=dict)
    _quests: dict[str, DynamicQuest] = dataclasses.field(
        default_factory=dict,
    )
    _quest_by_need: dict[
        tuple[str, NeedKind], str,
    ] = dataclasses.field(default_factory=dict)
    _next_quest_id: int = 0

    def publish_need(
        self, *, snapshot: NeedSnapshot, now_seconds: float = 0.0,
    ) -> None:
        key = (snapshot.npc_id, snapshot.kind)
        self._needs[key] = snapshot
        self._last_publish[key] = now_seconds

    def tick(self, *, now_seconds: float) -> dict[str, int]:
        """Generate / close / expire quests based on current
        snapshot table. Returns a dict of counters."""
        generated = 0
        closed = 0
        expired = 0
        # Generation pass
        for key, snap in list(self._needs.items()):
            existing_qid = self._quest_by_need.get(key)
            if (
                snap.urgency >= GENERATION_THRESHOLD
                and existing_qid is None
            ):
                q = self._generate_quest(snap, now_seconds)
                self._quests[q.quest_id] = q
                self._quest_by_need[key] = q.quest_id
                generated += 1
            # Auto-close on resolution
            if (
                snap.urgency <= RESOLVED_THRESHOLD
                and existing_qid is not None
            ):
                q = self._quests.get(existing_qid)
                if q and not q.completed:
                    q.cancelled = True
                    closed += 1
                del self._quest_by_need[key]
        # Expiry pass — quests whose NPCs went silent
        for qid, q in list(self._quests.items()):
            key = (q.npc_id, q.need_kind)
            silent_for = (
                now_seconds - self._last_publish.get(key, 0.0)
            )
            if silent_for > NEED_STALE_SECONDS:
                if not q.completed and not q.cancelled:
                    q.cancelled = True
                    expired += 1
                self._quest_by_need.pop(key, None)
            elif now_seconds >= q.expires_at_seconds and not q.completed:
                q.cancelled = True
                expired += 1
                self._quest_by_need.pop(key, None)
        return {
            "generated": generated,
            "closed_resolved": closed,
            "expired": expired,
        }

    def _generate_quest(
        self, snap: NeedSnapshot, now_seconds: float,
    ) -> DynamicQuest:
        oid = _DEFAULT_OBJECTIVE_KIND[snap.kind]
        objectives = [
            QuestObjective(
                kind=oid, target_id=snap.target_id,
                target_count=snap.target_count,
            ),
        ]
        title = _quest_title_for(snap)
        reward = _reward_for(snap)
        qid = f"dq_{self._next_quest_id}"
        self._next_quest_id += 1
        return DynamicQuest(
            quest_id=qid, npc_id=snap.npc_id,
            need_kind=snap.kind, title=title,
            objectives=objectives, reward=reward,
            created_at_seconds=now_seconds,
            expires_at_seconds=(
                now_seconds + self.quest_lifetime_seconds
            ),
        )

    def open_quests_for(
        self, *, npc_id: str, now_seconds: float = 0.0,
    ) -> tuple[DynamicQuest, ...]:
        return tuple(
            q for q in self._quests.values()
            if q.npc_id == npc_id
            and q.is_active(now_seconds=now_seconds)
        )

    def all_open_quests(
        self, *, now_seconds: float = 0.0,
    ) -> tuple[DynamicQuest, ...]:
        return tuple(
            q for q in self._quests.values()
            if q.is_active(now_seconds=now_seconds)
        )

    def player_accept(
        self, *, player_id: str, quest_id: str,
    ) -> bool:
        q = self._quests.get(quest_id)
        if q is None or q.completed or q.cancelled:
            return False
        if q.accepted_by is not None:
            return q.accepted_by == player_id
        q.accepted_by = player_id
        return True

    def player_progress(
        self, *, player_id: str, quest_id: str,
        objective_idx: int, delta: int = 1,
    ) -> bool:
        q = self._quests.get(quest_id)
        if (
            q is None or q.accepted_by != player_id
            or q.completed or q.cancelled
        ):
            return False
        if not (0 <= objective_idx < len(q.objectives)):
            return False
        obj = q.objectives[objective_idx]
        obj.progress = min(obj.target_count, obj.progress + delta)
        return True

    def player_turn_in(
        self, *, player_id: str, quest_id: str,
    ) -> TurnInResult:
        q = self._quests.get(quest_id)
        if q is None:
            return TurnInResult(False, reason="no such quest")
        if q.accepted_by != player_id:
            return TurnInResult(
                False, reason="quest not accepted by this player",
            )
        if q.completed:
            return TurnInResult(False, reason="already completed")
        if q.cancelled:
            return TurnInResult(False, reason="quest cancelled")
        if not q.all_objectives_done():
            return TurnInResult(False, reason="objectives incomplete")
        q.completed = True
        return TurnInResult(True, reward=q.reward)

    def total_quests(self) -> int:
        return len(self._quests)


def _quest_title_for(snap: NeedSnapshot) -> str:
    base_titles: dict[NeedKind, str] = {
        NeedKind.LUMBER_LOW: "Stockpiling timber",
        NeedKind.FOOD_LOW: "Stocking the larder",
        NeedKind.WATER_LOW: "Securing fresh water",
        NeedKind.MEDICINE_LOW: "Restocking the apothecary",
        NeedKind.BEASTMEN_PRESSURE: "Pushing back the raid",
        NeedKind.MISSING_PERSON: "A missing soul",
        NeedKind.HAUNTING: "Quieting the haunting",
        NeedKind.PROTEST_BREWING: "Calming unrest",
        NeedKind.PEST_INFESTATION: "Clearing the infestation",
        NeedKind.OUTPOST_LOST_CONTACT: "Silent outpost",
        NeedKind.PROPHECY_REQUIRES_TASK: "An old prophecy stirs",
        NeedKind.DELIVERY_NEEDED: "An urgent delivery",
    }
    return base_titles.get(snap.kind, snap.kind.value)


def _reward_for(snap: NeedSnapshot) -> QuestReward:
    # Reward scales with urgency — desperate needs pay more.
    gil = DEFAULT_REWARD_GIL + snap.urgency * 20
    rep = DEFAULT_REWARD_REPUTATION + snap.urgency // 10
    return QuestReward(gil=gil, reputation_delta=rep)


__all__ = [
    "GENERATION_THRESHOLD", "RESOLVED_THRESHOLD",
    "NEED_STALE_SECONDS",
    "NeedKind", "NeedSnapshot",
    "ObjectiveKind", "QuestObjective", "QuestReward",
    "DynamicQuest", "TurnInResult", "QuestEngine",
]
