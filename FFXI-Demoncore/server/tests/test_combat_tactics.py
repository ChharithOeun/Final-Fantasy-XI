"""Tests for combat tactical advisor."""
from __future__ import annotations

from server.combat_tactics import (
    BattlefieldSnapshot,
    EnemyCandidate,
    Formation,
    Posture,
    TacticalAdvisor,
)
from server.mob_personality import PersonalityVector


def _enemy(eid: str, **kwargs) -> EnemyCandidate:
    base = dict(
        entity_id=eid, threat=50, hp_pct=80,
        is_healer=False, is_caster=False,
        is_low_hp=False, distance=5,
    )
    base.update(kwargs)
    return EnemyCandidate(**base)


def _snapshot(**kwargs) -> BattlefieldSnapshot:
    base = dict(
        self_id="mob_1", self_hp_pct=80,
        allies_total=3, allies_low_hp=0,
        enemies=(_enemy("alice"),),
        ally_morale_pct=80,
        has_2hr_available=False,
        can_call_reinforcements=False,
    )
    base.update(kwargs)
    return BattlefieldSnapshot(**base)


def test_no_enemies_no_target():
    advisor = TacticalAdvisor()
    intent = advisor.recommend(
        personality=PersonalityVector(),
        snapshot=_snapshot(enemies=()),
    )
    assert intent.primary_target_id is None


def test_target_highest_threat_default():
    advisor = TacticalAdvisor()
    intent = advisor.recommend(
        personality=PersonalityVector(cunning=0.3),
        snapshot=_snapshot(
            enemies=(
                _enemy("alice", threat=20),
                _enemy("bob", threat=80),
                _enemy("charlie", threat=50),
            ),
        ),
    )
    assert intent.primary_target_id == "bob"


def test_cunning_targets_healer_first():
    advisor = TacticalAdvisor()
    intent = advisor.recommend(
        personality=PersonalityVector(cunning=0.9),
        snapshot=_snapshot(
            enemies=(
                _enemy("alice_tank", threat=90),
                _enemy("bob_healer", threat=40, is_healer=True),
            ),
        ),
    )
    assert intent.primary_target_id == "bob_healer"


def test_cunning_secures_low_hp_kill():
    advisor = TacticalAdvisor()
    intent = advisor.recommend(
        personality=PersonalityVector(cunning=0.9),
        snapshot=_snapshot(
            enemies=(
                _enemy("alice_tank", threat=90),
                _enemy("bob_dying", threat=40, hp_pct=10,
                        is_low_hp=True),
            ),
        ),
    )
    assert intent.primary_target_id == "bob_dying"


def test_coward_low_hp_retreats():
    advisor = TacticalAdvisor()
    intent = advisor.recommend(
        personality=PersonalityVector(courage=0.2),
        snapshot=_snapshot(self_hp_pct=15),
    )
    assert intent.posture == Posture.RETREAT


def test_brave_low_hp_holds():
    advisor = TacticalAdvisor()
    intent = advisor.recommend(
        personality=PersonalityVector(
            courage=0.95, aggression=0.8,
        ),
        snapshot=_snapshot(self_hp_pct=15),
    )
    # Brave mob doesn't retreat; falls through to focus_fire/spread
    assert intent.posture != Posture.RETREAT


def test_low_morale_loyal_rallies():
    advisor = TacticalAdvisor()
    intent = advisor.recommend(
        personality=PersonalityVector(loyalty=0.9, courage=0.7),
        snapshot=_snapshot(ally_morale_pct=20),
    )
    assert intent.posture == Posture.RALLY


def test_low_morale_disloyal_retreats():
    advisor = TacticalAdvisor()
    intent = advisor.recommend(
        personality=PersonalityVector(loyalty=0.2),
        snapshot=_snapshot(ally_morale_pct=20),
    )
    assert intent.posture == Posture.RETREAT


def test_two_hour_at_low_hp():
    advisor = TacticalAdvisor()
    intent = advisor.recommend(
        personality=PersonalityVector(courage=0.95),
        snapshot=_snapshot(
            self_hp_pct=25, has_2hr_available=True,
        ),
    )
    assert intent.posture == Posture.SPECIAL
    assert intent.should_use_2hr


def test_loyal_supports_low_hp_allies():
    advisor = TacticalAdvisor()
    intent = advisor.recommend(
        personality=PersonalityVector(loyalty=0.9),
        snapshot=_snapshot(allies_low_hp=3),
    )
    assert intent.posture == Posture.SUPPORT


def test_aggressive_brave_focus_fires():
    advisor = TacticalAdvisor()
    intent = advisor.recommend(
        personality=PersonalityVector(
            aggression=0.85, courage=0.85,
        ),
        snapshot=_snapshot(self_hp_pct=80, ally_morale_pct=80),
    )
    assert intent.posture == Posture.FOCUS_FIRE


def test_solo_no_allies_solo_formation():
    advisor = TacticalAdvisor()
    intent = advisor.recommend(
        personality=PersonalityVector(),
        snapshot=_snapshot(allies_total=0),
    )
    assert intent.formation == Formation.SOLO


def test_cunning_flanks():
    advisor = TacticalAdvisor()
    intent = advisor.recommend(
        personality=PersonalityVector(
            cunning=0.85, aggression=0.5,
        ),
        snapshot=_snapshot(),
    )
    assert intent.formation == Formation.FLANK


def test_coward_low_hp_back_rank():
    advisor = TacticalAdvisor()
    intent = advisor.recommend(
        personality=PersonalityVector(courage=0.3, aggression=0.4),
        snapshot=_snapshot(self_hp_pct=40),
    )
    assert intent.formation == Formation.REAR


def test_aggressive_courageous_front():
    advisor = TacticalAdvisor()
    intent = advisor.recommend(
        personality=PersonalityVector(
            aggression=0.85, courage=0.85, cunning=0.3,
        ),
        snapshot=_snapshot(self_hp_pct=70),
    )
    assert intent.formation == Formation.FRONT


def test_outnumbered_loyal_calls_reinforcements():
    advisor = TacticalAdvisor()
    intent = advisor.recommend(
        personality=PersonalityVector(loyalty=0.8),
        snapshot=_snapshot(
            allies_total=1, can_call_reinforcements=True,
            enemies=(
                _enemy("a"), _enemy("b"), _enemy("c"),
                _enemy("d"),
            ),
        ),
    )
    assert intent.should_call_reinforcements


def test_disloyal_does_not_call_reinforcements():
    advisor = TacticalAdvisor()
    intent = advisor.recommend(
        personality=PersonalityVector(loyalty=0.2),
        snapshot=_snapshot(
            allies_total=1, can_call_reinforcements=True,
            enemies=(_enemy("a"), _enemy("b"), _enemy("c"),
                       _enemy("d")),
        ),
    )
    assert not intent.should_call_reinforcements


def test_intent_includes_notes():
    advisor = TacticalAdvisor()
    intent = advisor.recommend(
        personality=PersonalityVector(),
        snapshot=_snapshot(),
    )
    assert intent.notes  # non-empty
    assert "posture" in intent.notes


def test_full_lifecycle_boss_pops_2hr_and_ai_focuses_healer():
    """A BOSS at low HP with 2hr ready, high cunning. Tactic
    advisor recommends SPECIAL posture, target the healer, FLANK
    formation."""
    advisor = TacticalAdvisor()
    intent = advisor.recommend(
        personality=PersonalityVector(
            aggression=0.7, courage=0.9,
            cunning=0.85, loyalty=0.5,
        ),
        snapshot=_snapshot(
            self_hp_pct=20,
            has_2hr_available=True,
            allies_total=2,
            enemies=(
                _enemy("tank_alice", threat=95, is_healer=False),
                _enemy("healer_bob", threat=40, is_healer=True),
                _enemy("dps_charlie", threat=70),
            ),
        ),
    )
    assert intent.posture == Posture.SPECIAL
    assert intent.should_use_2hr
    assert intent.primary_target_id == "healer_bob"
