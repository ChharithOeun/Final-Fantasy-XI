"""Tests for boss adaptation."""
from __future__ import annotations

from server.boss_adaptation import (
    AdaptationKind,
    BossAdaptationRegistry,
    MagicSchool,
    PlayerEngagementOutcome,
    RESIST_BUMP_PCT,
    DODGE_BUMP_PCT,
)


def _outcome(
    *, boss="fafnir", player="alice", won=True,
    seconds=120, schools=None, ws=(),
    phys=0.0, mag=0.0,
) -> PlayerEngagementOutcome:
    return PlayerEngagementOutcome(
        boss_kind=boss, player_id=player,
        won_or_lost=won, seconds_alive=seconds,
        spell_school_share=schools or {},
        weaponskills_used=ws,
        physical_dmg_share=phys,
        magic_dmg_share=mag,
    )


def test_no_grudge_means_empty_cascade():
    reg = BossAdaptationRegistry()
    res = reg.compute_adaptations(
        boss_kind="fafnir", player_id="alice",
    )
    assert res.adaptations == ()
    assert res.fight_count == 0


def test_record_outcome_creates_grudge():
    reg = BossAdaptationRegistry()
    reg.record_outcome(outcome=_outcome())
    assert reg.has_grudge(
        boss_kind="fafnir", player_id="alice",
    )


def test_dominant_fire_user_triggers_resist():
    reg = BossAdaptationRegistry()
    reg.record_outcome(outcome=_outcome(
        schools={MagicSchool.FIRE: 0.8},
    ))
    reg.record_outcome(outcome=_outcome(
        schools={MagicSchool.FIRE: 0.7},
    ))
    res = reg.compute_adaptations(
        boss_kind="fafnir", player_id="alice",
    )
    fire_resists = [
        a for a in res.adaptations
        if a.kind == AdaptationKind.RESIST_BUMP
        and a.target == "fire"
    ]
    assert len(fire_resists) == 1
    assert fire_resists[0].magnitude_pct == RESIST_BUMP_PCT


def test_repeated_weaponskill_triggers_dodge():
    reg = BossAdaptationRegistry()
    reg.record_outcome(outcome=_outcome(ws=("rampage",)))
    reg.record_outcome(outcome=_outcome(ws=("rampage",)))
    res = reg.compute_adaptations(
        boss_kind="fafnir", player_id="alice",
    )
    rampage_dodges = [
        a for a in res.adaptations
        if a.kind == AdaptationKind.DODGE_BUMP
        and a.target == "rampage"
    ]
    assert len(rampage_dodges) == 1
    assert rampage_dodges[0].magnitude_pct == DODGE_BUMP_PCT


def test_single_use_weaponskill_no_dodge():
    reg = BossAdaptationRegistry()
    reg.record_outcome(outcome=_outcome(ws=("rampage",)))
    res = reg.compute_adaptations(
        boss_kind="fafnir", player_id="alice",
    )
    dodges = [
        a for a in res.adaptations
        if a.kind == AdaptationKind.DODGE_BUMP
    ]
    assert len(dodges) == 0


def test_physical_lean_triggers_counter_pattern():
    reg = BossAdaptationRegistry()
    reg.record_outcome(outcome=_outcome(phys=0.8))
    res = reg.compute_adaptations(
        boss_kind="fafnir", player_id="alice",
    )
    counters = [
        a for a in res.adaptations
        if a.kind == AdaptationKind.COUNTER_PATTERN
        and a.target == "physical_team"
    ]
    assert len(counters) == 1


def test_magic_lean_triggers_silence_pattern():
    reg = BossAdaptationRegistry()
    reg.record_outcome(outcome=_outcome(mag=0.75))
    res = reg.compute_adaptations(
        boss_kind="fafnir", player_id="alice",
    )
    counters = [
        a for a in res.adaptations
        if a.kind == AdaptationKind.COUNTER_PATTERN
        and a.target == "caster_team"
    ]
    assert len(counters) == 1


def test_quick_kill_triggers_hp_buff():
    reg = BossAdaptationRegistry(
        quick_kill_threshold_seconds=60,
    )
    reg.record_outcome(outcome=_outcome(won=True, seconds=30))
    res = reg.compute_adaptations(
        boss_kind="fafnir", player_id="alice",
    )
    hp = [
        a for a in res.adaptations
        if a.kind == AdaptationKind.HP_BUFF
    ]
    assert len(hp) == 1


def test_long_kill_no_hp_buff():
    reg = BossAdaptationRegistry()
    reg.record_outcome(outcome=_outcome(won=True, seconds=600))
    res = reg.compute_adaptations(
        boss_kind="fafnir", player_id="alice",
    )
    hp = [
        a for a in res.adaptations
        if a.kind == AdaptationKind.HP_BUFF
    ]
    assert len(hp) == 0


def test_two_wins_triggers_enrage_cut():
    reg = BossAdaptationRegistry()
    reg.record_outcome(outcome=_outcome(won=True, seconds=300))
    reg.record_outcome(outcome=_outcome(won=True, seconds=300))
    res = reg.compute_adaptations(
        boss_kind="fafnir", player_id="alice",
    )
    enrage = [
        a for a in res.adaptations
        if a.kind == AdaptationKind.ENRAGE_TIMER_CUT
    ]
    assert len(enrage) == 1


def test_one_win_no_enrage_cut():
    reg = BossAdaptationRegistry()
    reg.record_outcome(outcome=_outcome(won=True, seconds=300))
    res = reg.compute_adaptations(
        boss_kind="fafnir", player_id="alice",
    )
    enrage = [
        a for a in res.adaptations
        if a.kind == AdaptationKind.ENRAGE_TIMER_CUT
    ]
    assert len(enrage) == 0


def test_per_player_grudges_isolated():
    reg = BossAdaptationRegistry()
    reg.record_outcome(outcome=_outcome(player="alice"))
    reg.record_outcome(outcome=_outcome(player="bob"))
    assert reg.total_grudges() == 2
    a = reg.compute_adaptations(
        boss_kind="fafnir", player_id="alice",
    )
    b = reg.compute_adaptations(
        boss_kind="fafnir", player_id="bob",
    )
    assert a.fight_count == 1
    assert b.fight_count == 1


def test_per_boss_grudges_isolated():
    reg = BossAdaptationRegistry()
    reg.record_outcome(outcome=_outcome(boss="fafnir"))
    reg.record_outcome(outcome=_outcome(boss="kingbehemoth"))
    assert reg.total_grudges() == 2


def test_reset_clears_grudge():
    reg = BossAdaptationRegistry()
    reg.record_outcome(outcome=_outcome())
    assert reg.reset(
        boss_kind="fafnir", player_id="alice",
    )
    assert not reg.has_grudge(
        boss_kind="fafnir", player_id="alice",
    )


def test_reset_unknown_returns_false():
    reg = BossAdaptationRegistry()
    assert not reg.reset(
        boss_kind="ghost", player_id="x",
    )


def test_max_adaptations_cap():
    reg = BossAdaptationRegistry(max_adaptations_per_grudge=2)
    reg.record_outcome(outcome=_outcome(
        schools={MagicSchool.FIRE: 0.8}, won=True,
        seconds=30, phys=0.7,
        ws=("rampage",),
    ))
    reg.record_outcome(outcome=_outcome(
        schools={MagicSchool.FIRE: 0.7}, won=True,
        seconds=30, phys=0.7,
        ws=("rampage",),
    ))
    res = reg.compute_adaptations(
        boss_kind="fafnir", player_id="alice",
    )
    assert len(res.adaptations) == 2


def test_full_engagement_history_produces_diverse_adaptations():
    reg = BossAdaptationRegistry()
    reg.record_outcome(outcome=_outcome(
        schools={MagicSchool.FIRE: 0.8},
        ws=("ruinator",), won=True, seconds=45,
        phys=0.7,
    ))
    reg.record_outcome(outcome=_outcome(
        schools={MagicSchool.FIRE: 0.6},
        ws=("ruinator",), won=True, seconds=50,
        phys=0.65,
    ))
    res = reg.compute_adaptations(
        boss_kind="fafnir", player_id="alice",
    )
    kinds = {a.kind for a in res.adaptations}
    assert AdaptationKind.RESIST_BUMP in kinds
    assert AdaptationKind.DODGE_BUMP in kinds
    assert AdaptationKind.COUNTER_PATTERN in kinds
    assert AdaptationKind.HP_BUFF in kinds
    assert AdaptationKind.ENRAGE_TIMER_CUT in kinds
    assert res.fight_count == 2
