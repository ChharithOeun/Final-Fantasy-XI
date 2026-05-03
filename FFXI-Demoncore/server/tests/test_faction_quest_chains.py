"""Tests for faction quest chains."""
from __future__ import annotations

import pytest

from server.faction_quest_chains import (
    Alignment,
    ChainReward,
    FactionQuestChainRegistry,
    QuestChain,
    QuestNode,
)
from server.faction_reputation import (
    PlayerFactionReputation,
    ReputationBand,
)


def _simple_chain() -> QuestChain:
    return QuestChain(
        chain_id="bastok_steel",
        label="Steel Republic",
        faction_id="bastok",
        nodes=(
            QuestNode(
                quest_id="q1", label="Enter the Mythril Hall",
                required_band=ReputationBand.NEUTRAL,
                next_quest_ids=("q2",),
            ),
            QuestNode(
                quest_id="q2", label="Forge the Prototype",
                required_band=ReputationBand.NEUTRAL,
                next_quest_ids=("q3a", "q3b"),
            ),
            QuestNode(
                quest_id="q3a", label="Loyal to the Republic",
                branch_alignment=Alignment.LOYALIST,
                next_quest_ids=("q_final",),
            ),
            QuestNode(
                quest_id="q3b", label="Reform the Republic",
                branch_alignment=Alignment.REFORMER,
                next_quest_ids=("q_final",),
            ),
            QuestNode(
                quest_id="q_final",
                label="The Republic's Fate",
                required_band=ReputationBand.FRIENDLY,
            ),
        ),
        entry_node_ids=("q1",),
        completion_node_ids=("q_final",),
        reward=ChainReward(
            title_id="title_steel_hero",
            signature_gear_id="mythril_pin",
            rep_bonus=100, gil=50_000,
        ),
    )


def _rep(faction_value: int = 0) -> PlayerFactionReputation:
    rep = PlayerFactionReputation(player_id="alice")
    rep.set(faction_id="bastok", value=faction_value)
    return rep


def test_register_chain_validates_entry_nodes():
    reg = FactionQuestChainRegistry()
    bad = QuestChain(
        chain_id="bad", label="x", faction_id="bastok",
        nodes=(),
        entry_node_ids=(),
        completion_node_ids=(),
    )
    with pytest.raises(ValueError):
        reg.register_chain(bad)


def test_register_chain_validates_unknown_entry():
    reg = FactionQuestChainRegistry()
    bad = QuestChain(
        chain_id="bad", label="x", faction_id="bastok",
        nodes=(QuestNode(quest_id="q1", label="x"),),
        entry_node_ids=("ghost",),
        completion_node_ids=("q1",),
    )
    with pytest.raises(ValueError):
        reg.register_chain(bad)


def test_register_simple_chain():
    reg = FactionQuestChainRegistry()
    reg.register_chain(_simple_chain())
    assert reg.chain("bastok_steel") is not None
    assert reg.total_chains() == 1


def test_start_chain_unknown():
    reg = FactionQuestChainRegistry()
    res = reg.start_chain(
        player_id="alice", chain_id="ghost", rep=_rep(),
    )
    assert not res.accepted


def test_start_chain_low_rep_rejected():
    reg = FactionQuestChainRegistry()
    chain = QuestChain(
        chain_id="elite", label="x", faction_id="bastok",
        nodes=(QuestNode(
            quest_id="q1", label="x",
            required_band=ReputationBand.ALLIED,
        ),),
        entry_node_ids=("q1",),
        completion_node_ids=("q1",),
    )
    reg.register_chain(chain)
    res = reg.start_chain(
        player_id="alice", chain_id="elite",
        rep=_rep(faction_value=10),  # NEUTRAL
    )
    assert not res.accepted


def test_start_chain_neutral_can_enter():
    reg = FactionQuestChainRegistry()
    reg.register_chain(_simple_chain())
    res = reg.start_chain(
        player_id="alice", chain_id="bastok_steel",
        rep=_rep(),
    )
    assert res.accepted


def test_double_start_rejected():
    reg = FactionQuestChainRegistry()
    reg.register_chain(_simple_chain())
    reg.start_chain(
        player_id="alice", chain_id="bastok_steel",
        rep=_rep(),
    )
    res = reg.start_chain(
        player_id="alice", chain_id="bastok_steel",
        rep=_rep(),
    )
    assert not res.accepted


def test_next_offered_starts_with_entry():
    reg = FactionQuestChainRegistry()
    reg.register_chain(_simple_chain())
    reg.start_chain(
        player_id="alice", chain_id="bastok_steel",
        rep=_rep(),
    )
    offered = reg.next_offered(
        player_id="alice", chain_id="bastok_steel",
        rep=_rep(),
    )
    assert len(offered) == 1
    assert offered[0].quest_id == "q1"


def test_complete_quest_advances():
    reg = FactionQuestChainRegistry()
    reg.register_chain(_simple_chain())
    reg.start_chain(
        player_id="alice", chain_id="bastok_steel",
        rep=_rep(),
    )
    res = reg.complete_quest(
        player_id="alice", chain_id="bastok_steel",
        quest_id="q1",
    )
    assert res.accepted
    offered = reg.next_offered(
        player_id="alice", chain_id="bastok_steel",
        rep=_rep(),
    )
    assert len(offered) == 1
    assert offered[0].quest_id == "q2"


def test_completing_unknown_quest_rejected():
    reg = FactionQuestChainRegistry()
    reg.register_chain(_simple_chain())
    reg.start_chain(
        player_id="alice", chain_id="bastok_steel",
        rep=_rep(),
    )
    res = reg.complete_quest(
        player_id="alice", chain_id="bastok_steel",
        quest_id="ghost",
    )
    assert not res.accepted


def test_completing_quest_twice_rejected():
    reg = FactionQuestChainRegistry()
    reg.register_chain(_simple_chain())
    reg.start_chain(
        player_id="alice", chain_id="bastok_steel",
        rep=_rep(),
    )
    reg.complete_quest(
        player_id="alice", chain_id="bastok_steel",
        quest_id="q1",
    )
    res = reg.complete_quest(
        player_id="alice", chain_id="bastok_steel",
        quest_id="q1",
    )
    assert not res.accepted


def test_branching_locks_other_branch():
    """Choosing q3a locks q3b (and vice versa)."""
    reg = FactionQuestChainRegistry()
    reg.register_chain(_simple_chain())
    reg.start_chain(
        player_id="alice", chain_id="bastok_steel",
        rep=_rep(),
    )
    reg.complete_quest(
        player_id="alice", chain_id="bastok_steel",
        quest_id="q1",
    )
    reg.complete_quest(
        player_id="alice", chain_id="bastok_steel",
        quest_id="q2",
    )
    # Now offered: q3a + q3b
    offered = reg.next_offered(
        player_id="alice", chain_id="bastok_steel",
        rep=_rep(),
    )
    ids = {o.quest_id for o in offered}
    assert ids == {"q3a", "q3b"}
    # Choose q3a — alignment locked to LOYALIST
    res = reg.complete_quest(
        player_id="alice", chain_id="bastok_steel",
        quest_id="q3a",
    )
    assert res.accepted
    assert "q3b" in res.locked_branches
    progress = reg.progress(
        player_id="alice", chain_id="bastok_steel",
    )
    assert progress.chosen_alignment == Alignment.LOYALIST
    # q3b is no longer offerable
    offered_after = reg.next_offered(
        player_id="alice", chain_id="bastok_steel",
        rep=_rep(),
    )
    ids_after = {o.quest_id for o in offered_after}
    assert "q3b" not in ids_after


def test_chain_completion_grants_reward():
    reg = FactionQuestChainRegistry()
    reg.register_chain(_simple_chain())
    reg.start_chain(
        player_id="alice", chain_id="bastok_steel",
        rep=_rep(faction_value=100),  # FRIENDLY for q_final
    )
    for q in ("q1", "q2", "q3a"):
        reg.complete_quest(
            player_id="alice", chain_id="bastok_steel",
            quest_id=q,
        )
    res = reg.complete_quest(
        player_id="alice", chain_id="bastok_steel",
        quest_id="q_final",
    )
    assert res.accepted
    assert res.chain_completed
    assert res.reward is not None
    assert res.reward.title_id == "title_steel_hero"


def test_next_offered_filters_low_level():
    reg = FactionQuestChainRegistry()
    chain = QuestChain(
        chain_id="lvl_chain", label="x", faction_id="bastok",
        nodes=(
            QuestNode(
                quest_id="q1", label="x",
                required_level=50,
            ),
        ),
        entry_node_ids=("q1",),
        completion_node_ids=("q1",),
    )
    reg.register_chain(chain)
    reg.start_chain(
        player_id="alice", chain_id="lvl_chain", rep=_rep(),
    )
    offered = reg.next_offered(
        player_id="alice", chain_id="lvl_chain",
        rep=_rep(), player_level=20,
    )
    assert offered == ()


def test_next_offered_filters_low_rep():
    """Chain entry was OK but a downstream node demands FRIENDLY+."""
    reg = FactionQuestChainRegistry()
    reg.register_chain(_simple_chain())
    reg.start_chain(
        player_id="alice", chain_id="bastok_steel",
        rep=_rep(),
    )
    for q in ("q1", "q2", "q3a"):
        reg.complete_quest(
            player_id="alice", chain_id="bastok_steel",
            quest_id=q,
        )
    # q_final demands FRIENDLY+; alice still NEUTRAL
    offered = reg.next_offered(
        player_id="alice", chain_id="bastok_steel",
        rep=_rep(),
    )
    assert offered == ()


def test_full_lifecycle_alice_walks_loyalist_arc():
    """Alice plays the loyalist branch end-to-end and earns the
    Steel Hero title."""
    reg = FactionQuestChainRegistry()
    reg.register_chain(_simple_chain())
    rep = _rep(faction_value=100)   # FRIENDLY
    reg.start_chain(
        player_id="alice", chain_id="bastok_steel", rep=rep,
    )
    for q in ("q1", "q2", "q3a"):
        reg.complete_quest(
            player_id="alice", chain_id="bastok_steel",
            quest_id=q,
        )
    final = reg.complete_quest(
        player_id="alice", chain_id="bastok_steel",
        quest_id="q_final",
    )
    assert final.chain_completed
    progress = reg.progress(
        player_id="alice", chain_id="bastok_steel",
    )
    assert progress.completed
    assert progress.chosen_alignment == Alignment.LOYALIST
    assert "q3b" in reg._locked_branches.get(
        ("alice", "bastok_steel"), set(),
    )
