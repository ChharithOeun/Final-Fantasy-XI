"""Tests for autonomous beastmen faction AI."""
from __future__ import annotations

from server.beastmen_factions import (
    BeastmenTribe,
    DiplomaticStance,
    FactionAIRegistry,
    PlayerNation,
    Stance,
)


def test_registry_seeds_every_tribe():
    reg = FactionAIRegistry()
    for tribe in BeastmenTribe:
        assert reg.state_of(tribe).tribe == tribe
        assert reg.stance_for(tribe) == Stance.CONTAIN


def test_default_rivals_seeded():
    reg = FactionAIRegistry()
    # Orcs hate San d'Oria, Quadav hate Bastok, Yagudo hate Windy
    assert (
        reg.state_of(BeastmenTribe.ORC).stance_toward(
            PlayerNation.SAN_DORIA
        ) == DiplomaticStance.HOSTILE
    )
    assert (
        reg.state_of(BeastmenTribe.QUADAV).stance_toward(
            PlayerNation.BASTOK
        ) == DiplomaticStance.HOSTILE
    )
    assert (
        reg.state_of(BeastmenTribe.YAGUDO).stance_toward(
            PlayerNation.WINDURST
        ) == DiplomaticStance.HOSTILE
    )


def test_post_stance_changes_posture():
    reg = FactionAIRegistry()
    res = reg.post_stance(
        tribe=BeastmenTribe.ORC, stance=Stance.RAID,
    )
    assert res.accepted
    assert reg.stance_for(BeastmenTribe.ORC) == Stance.RAID


def test_retreat_to_war_blocked():
    """Tribes can't jump from RETREAT directly to WAR — need to
    reorganize through CONTAIN or RAID first."""
    reg = FactionAIRegistry()
    reg.post_stance(
        tribe=BeastmenTribe.GOBLIN, stance=Stance.RETREAT,
    )
    res = reg.post_stance(
        tribe=BeastmenTribe.GOBLIN, stance=Stance.WAR,
    )
    assert not res.accepted


def test_retreat_to_contain_then_war_works():
    reg = FactionAIRegistry()
    reg.post_stance(
        tribe=BeastmenTribe.GOBLIN, stance=Stance.RETREAT,
    )
    reg.post_stance(
        tribe=BeastmenTribe.GOBLIN, stance=Stance.CONTAIN,
    )
    res = reg.post_stance(
        tribe=BeastmenTribe.GOBLIN, stance=Stance.WAR,
    )
    assert res.accepted


def test_declare_war_makes_target_top_threat():
    reg = FactionAIRegistry()
    res = reg.declare_war(
        tribe=BeastmenTribe.QUADAV, target=PlayerNation.JEUNO,
    )
    assert res.accepted
    assert reg.stance_for(BeastmenTribe.QUADAV) == Stance.WAR
    threats = reg.threat_ranking(BeastmenTribe.QUADAV)
    assert threats[0] == PlayerNation.JEUNO


def test_declare_war_against_self_rejected():
    reg = FactionAIRegistry()
    res = reg.declare_war(
        tribe=BeastmenTribe.ORC, target=BeastmenTribe.ORC,
    )
    assert not res.accepted


def test_declare_war_on_other_tribe():
    """Tribes can war OTHER tribes too — beastmen civil war."""
    reg = FactionAIRegistry()
    res = reg.declare_war(
        tribe=BeastmenTribe.ORC, target=BeastmenTribe.GOBLIN,
    )
    assert res.accepted
    threats = reg.threat_ranking(BeastmenTribe.ORC)
    assert BeastmenTribe.GOBLIN in threats


def test_broker_peace_pulls_back_from_war():
    reg = FactionAIRegistry()
    reg.declare_war(
        tribe=BeastmenTribe.YAGUDO, target=PlayerNation.WINDURST,
    )
    res = reg.broker_peace(
        tribe=BeastmenTribe.YAGUDO, target=PlayerNation.WINDURST,
    )
    assert res.accepted
    assert reg.stance_for(BeastmenTribe.YAGUDO) == Stance.CONTAIN
    threats = reg.threat_ranking(BeastmenTribe.YAGUDO)
    assert PlayerNation.WINDURST not in threats


def test_broker_peace_can_set_allied():
    reg = FactionAIRegistry()
    reg.broker_peace(
        tribe=BeastmenTribe.MAMOOL_JA, target=BeastmenTribe.TROLL,
        new_diplomatic=DiplomaticStance.ALLIED,
    )
    state = reg.state_of(BeastmenTribe.MAMOOL_JA)
    assert state.stance_toward(BeastmenTribe.TROLL) == DiplomaticStance.ALLIED


def test_commit_force_records_dispatch():
    reg = FactionAIRegistry()
    force = reg.commit_force(
        tribe=BeastmenTribe.ORC, target_zone_id="ronfaure_west",
        troop_count=12, now_seconds=100.0,
        notes="raid party for siege test",
    )
    assert force.troop_count == 12
    assert reg.total_committed_troops(BeastmenTribe.ORC) == 12


def test_commit_force_accumulates():
    reg = FactionAIRegistry()
    reg.commit_force(
        tribe=BeastmenTribe.QUADAV, target_zone_id="north_gustaberg",
        troop_count=8,
    )
    reg.commit_force(
        tribe=BeastmenTribe.QUADAV, target_zone_id="palborough_mines",
        troop_count=15,
    )
    assert reg.total_committed_troops(BeastmenTribe.QUADAV) == 23


def test_summary_lists_all_tribes():
    reg = FactionAIRegistry()
    summary = reg.summary()
    assert len(summary) == len(BeastmenTribe)
    for tribe in BeastmenTribe:
        assert tribe in summary


def test_tribes_at_war_filters():
    reg = FactionAIRegistry()
    reg.declare_war(
        tribe=BeastmenTribe.ORC, target=PlayerNation.SAN_DORIA,
    )
    reg.declare_war(
        tribe=BeastmenTribe.YAGUDO, target=BeastmenTribe.QUADAV,
    )
    at_war = set(reg.tribes_at_war())
    assert BeastmenTribe.ORC in at_war
    assert BeastmenTribe.YAGUDO in at_war
    assert BeastmenTribe.GOBLIN not in at_war


def test_full_lifecycle_war_and_peace():
    """Faction AI escalates Yagudo to war, dispatches forces,
    then brokers peace once player nation pays tribute."""
    reg = FactionAIRegistry()
    reg.declare_war(
        tribe=BeastmenTribe.YAGUDO, target=PlayerNation.WINDURST,
        now_seconds=0.0,
    )
    reg.commit_force(
        tribe=BeastmenTribe.YAGUDO, target_zone_id="east_sarutabaruta",
        troop_count=20, now_seconds=10.0,
    )
    reg.commit_force(
        tribe=BeastmenTribe.YAGUDO, target_zone_id="meriphataud",
        troop_count=25, now_seconds=20.0,
    )
    assert reg.total_committed_troops(BeastmenTribe.YAGUDO) == 45
    # Player nation pays tribute -> peace
    res = reg.broker_peace(
        tribe=BeastmenTribe.YAGUDO, target=PlayerNation.WINDURST,
        new_diplomatic=DiplomaticStance.WARY, now_seconds=200.0,
    )
    assert res.accepted
    state = reg.state_of(BeastmenTribe.YAGUDO)
    assert state.stance_toward(
        PlayerNation.WINDURST,
    ) == DiplomaticStance.WARY
