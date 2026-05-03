"""Faction quest chains — multi-quest narrative arcs.

Distinct from dynamic_quest_gen (NPCs autonomously emit one-off
quests based on need). This module owns the AUTHORED storylines:
the multi-quest arcs that define each faction's character.
Bastok's "Steel Republic" arc; San d'Oria's "Twin Princes"
arc; the Tenshodo's "Smuggler's Crossing"; the Yagudo
"Heretic's Pilgrimage" (an arc only the very disloyal can
walk).

Each chain has:
* 5-15 quests in order, optionally with branches
* Per-quest gates (faction rep band, prereq quest, level)
* A FACTION_REWARD on chain completion (title + signature gear
  + permanent rep bonus)
* An ALIGNMENT (LOYALIST / REFORMER / DISSIDENT) — chains can
  diverge mid-arc into branches that lock the player into one
  alignment

Branch model
------------
A `QuestNode` lists `next_quest_ids`. If multiple are listed,
the chain BRANCHES — accepting one closes off the others. The
player's `ChainProgress` records which branch was chosen.

Public surface
--------------
    Alignment enum (LOYALIST / REFORMER / DISSIDENT / NEUTRAL)
    QuestNode dataclass — one quest in a chain
    QuestChain dataclass — full chain
    ChainProgress dataclass — per-player tracker
    FactionQuestChainRegistry
        .register_chain(chain)
        .start_chain(player_id, chain_id, rep)
        .complete_quest(player_id, chain_id, quest_id)
        .next_offered(player_id, chain_id) -> tuple[QuestNode]
        .completion_reward(player_id, chain_id) -> Reward
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.faction_reputation import (
    PlayerFactionReputation,
    ReputationBand,
)


class Alignment(str, enum.Enum):
    LOYALIST = "loyalist"
    REFORMER = "reformer"
    DISSIDENT = "dissident"
    NEUTRAL = "neutral"


@dataclasses.dataclass(frozen=True)
class QuestNode:
    quest_id: str
    label: str
    required_band: ReputationBand = ReputationBand.NEUTRAL
    required_level: int = 1
    next_quest_ids: tuple[str, ...] = ()
    branch_alignment: Alignment = Alignment.NEUTRAL
    notes: str = ""


@dataclasses.dataclass(frozen=True)
class ChainReward:
    title_id: str = ""
    signature_gear_id: str = ""
    rep_bonus: int = 50
    gil: int = 10_000


@dataclasses.dataclass(frozen=True)
class QuestChain:
    chain_id: str
    label: str
    faction_id: str
    nodes: tuple[QuestNode, ...]        # entry points + nodes
    entry_node_ids: tuple[str, ...]
    completion_node_ids: tuple[str, ...]
    reward: ChainReward = ChainReward()
    notes: str = ""

    def node(self, quest_id: str) -> t.Optional[QuestNode]:
        for n in self.nodes:
            if n.quest_id == quest_id:
                return n
        return None


@dataclasses.dataclass
class ChainProgress:
    player_id: str
    chain_id: str
    completed_quest_ids: list[str] = dataclasses.field(
        default_factory=list,
    )
    chosen_alignment: Alignment = Alignment.NEUTRAL
    completed: bool = False

    def has_completed(self, quest_id: str) -> bool:
        return quest_id in self.completed_quest_ids


_REP_ORDER: tuple[ReputationBand, ...] = (
    ReputationBand.KILL_ON_SIGHT, ReputationBand.HOSTILE,
    ReputationBand.UNFRIENDLY, ReputationBand.NEUTRAL,
    ReputationBand.FRIENDLY, ReputationBand.ALLIED,
    ReputationBand.HERO_OF_THE_FACTION,
)


def _rep_at_least(
    actual: ReputationBand, required: ReputationBand,
) -> bool:
    return _REP_ORDER.index(actual) >= _REP_ORDER.index(required)


@dataclasses.dataclass(frozen=True)
class StartResult:
    accepted: bool
    chain_id: str
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class CompletionResult:
    accepted: bool
    quest_id: str
    chain_completed: bool = False
    reward: t.Optional[ChainReward] = None
    locked_branches: tuple[str, ...] = ()
    reason: t.Optional[str] = None


@dataclasses.dataclass
class FactionQuestChainRegistry:
    _chains: dict[str, QuestChain] = dataclasses.field(
        default_factory=dict,
    )
    _progress: dict[
        tuple[str, str], ChainProgress,
    ] = dataclasses.field(default_factory=dict)
    # Locked next-quest IDs after a branch was chosen
    _locked_branches: dict[
        tuple[str, str], set[str],
    ] = dataclasses.field(default_factory=dict)

    def register_chain(self, chain: QuestChain) -> QuestChain:
        if not chain.entry_node_ids:
            raise ValueError("chain must have entry_node_ids")
        if not chain.completion_node_ids:
            raise ValueError("chain must have completion_node_ids")
        # Sanity: every entry / completion id exists in nodes
        node_ids = {n.quest_id for n in chain.nodes}
        for eid in chain.entry_node_ids:
            if eid not in node_ids:
                raise ValueError(
                    f"entry node {eid} not in nodes",
                )
        for cid in chain.completion_node_ids:
            if cid not in node_ids:
                raise ValueError(
                    f"completion node {cid} not in nodes",
                )
        self._chains[chain.chain_id] = chain
        return chain

    def chain(self, chain_id: str) -> t.Optional[QuestChain]:
        return self._chains.get(chain_id)

    def progress(
        self, *, player_id: str, chain_id: str,
    ) -> t.Optional[ChainProgress]:
        return self._progress.get((player_id, chain_id))

    def start_chain(
        self, *, player_id: str, chain_id: str,
        rep: PlayerFactionReputation,
    ) -> StartResult:
        chain = self._chains.get(chain_id)
        if chain is None:
            return StartResult(False, chain_id, reason="no chain")
        key = (player_id, chain_id)
        if key in self._progress:
            return StartResult(
                False, chain_id,
                reason="chain already started",
            )
        # Check entry rep against the LOWEST-bar entry node
        actual_band = rep.band(chain.faction_id)
        eligible = False
        for eid in chain.entry_node_ids:
            n = chain.node(eid)
            if n is None:
                continue
            if _rep_at_least(actual_band, n.required_band):
                eligible = True
                break
        if not eligible:
            return StartResult(
                False, chain_id,
                reason="rep too low for any entry node",
            )
        self._progress[key] = ChainProgress(
            player_id=player_id, chain_id=chain_id,
        )
        return StartResult(True, chain_id)

    def next_offered(
        self, *, player_id: str, chain_id: str,
        rep: PlayerFactionReputation,
        player_level: int = 99,
    ) -> tuple[QuestNode, ...]:
        chain = self._chains.get(chain_id)
        progress = self.progress(
            player_id=player_id, chain_id=chain_id,
        )
        if chain is None or progress is None:
            return ()
        actual_band = rep.band(chain.faction_id)
        # If no quests completed yet, offer entry nodes (filtered)
        if not progress.completed_quest_ids:
            return tuple(
                n for n in chain.nodes
                if n.quest_id in chain.entry_node_ids
                and _rep_at_least(actual_band, n.required_band)
                and player_level >= n.required_level
            )
        # Otherwise, offer next_quest_ids of the LAST completed
        # quest, minus locked branches.
        last_id = progress.completed_quest_ids[-1]
        last_node = chain.node(last_id)
        if last_node is None:
            return ()
        locked = self._locked_branches.get(
            (player_id, chain_id), set(),
        )
        out: list[QuestNode] = []
        for qid in last_node.next_quest_ids:
            if qid in locked:
                continue
            n = chain.node(qid)
            if n is None:
                continue
            if not _rep_at_least(actual_band, n.required_band):
                continue
            if player_level < n.required_level:
                continue
            out.append(n)
        return tuple(out)

    def complete_quest(
        self, *, player_id: str, chain_id: str,
        quest_id: str,
    ) -> CompletionResult:
        chain = self._chains.get(chain_id)
        progress = self.progress(
            player_id=player_id, chain_id=chain_id,
        )
        if chain is None or progress is None:
            return CompletionResult(
                False, quest_id,
                reason="chain not started",
            )
        node = chain.node(quest_id)
        if node is None:
            return CompletionResult(
                False, quest_id,
                reason="quest not in chain",
            )
        if progress.has_completed(quest_id):
            return CompletionResult(
                False, quest_id,
                reason="already completed",
            )
        progress.completed_quest_ids.append(quest_id)
        # If this node has a non-NEUTRAL alignment, lock the
        # player to it. Also lock the OTHER siblings under the
        # parent.
        locked_now: set[str] = set()
        if node.branch_alignment != Alignment.NEUTRAL:
            progress.chosen_alignment = node.branch_alignment
        # Find parent (any node whose next_quest_ids contains
        # this quest_id) and lock siblings the player did NOT
        # choose.
        for parent in chain.nodes:
            if quest_id in parent.next_quest_ids:
                for sib in parent.next_quest_ids:
                    if sib != quest_id:
                        locked_now.add(sib)
        if locked_now:
            self._locked_branches.setdefault(
                (player_id, chain_id), set(),
            ).update(locked_now)
        # Chain completion check
        chain_done = quest_id in chain.completion_node_ids
        if chain_done:
            progress.completed = True
            return CompletionResult(
                accepted=True, quest_id=quest_id,
                chain_completed=True,
                reward=chain.reward,
                locked_branches=tuple(sorted(locked_now)),
            )
        return CompletionResult(
            accepted=True, quest_id=quest_id,
            locked_branches=tuple(sorted(locked_now)),
        )

    def total_chains(self) -> int:
        return len(self._chains)


__all__ = [
    "Alignment",
    "QuestNode", "ChainReward", "QuestChain",
    "ChainProgress",
    "StartResult", "CompletionResult",
    "FactionQuestChainRegistry",
]
