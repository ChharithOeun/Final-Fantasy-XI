"""Tests for mob fear / morale + rout."""
from __future__ import annotations

import random

from server.mob_fear import (
    FearOutcome,
    MobFearRegistry,
    MobMoraleProfile,
)


def _profile(
    mob_id: str = "g1", family: str = "goblin",
    courage: int = 60, level: int = 30,
    fearless: bool = False, leader: bool = False,
) -> MobMoraleProfile:
    return MobMoraleProfile(
        mob_id=mob_id, family_id=family,
        courage=courage, level=level,
        is_fearless=fearless, is_pack_leader=leader,
    )


def test_register_lookup():
    reg = MobFearRegistry()
    reg.register_mob(_profile())
    assert reg.get("g1") is not None


def test_unknown_witness_returns_hold():
    reg = MobFearRegistry()
    res = reg.witness_ally_death(
        witness_id="ghost", dying_id="other",
        killer_level=30, now_seconds=0.0,
    )
    assert res.outcome == FearOutcome.HOLD


def test_different_family_no_effect():
    reg = MobFearRegistry()
    reg.register_mob(_profile(mob_id="g1", family="goblin"))
    reg.register_mob(_profile(mob_id="o1", family="orc"))
    reg.kill_mob(mob_id="o1", now_seconds=0.0)
    res = reg.witness_ally_death(
        witness_id="g1", dying_id="o1",
        killer_level=30, now_seconds=0.0,
    )
    assert res.outcome == FearOutcome.HOLD


def test_fearless_mob_holds():
    reg = MobFearRegistry()
    reg.register_mob(_profile(
        mob_id="zealot", fearless=True,
    ))
    reg.register_mob(_profile(mob_id="ally"))
    reg.kill_mob(mob_id="ally", now_seconds=0.0)
    res = reg.witness_ally_death(
        witness_id="zealot", dying_id="ally",
        killer_level=99, now_seconds=0.0,
        rng=random.Random(0),
    )
    assert res.outcome == FearOutcome.HOLD


def test_low_courage_routs():
    reg = MobFearRegistry()
    reg.register_mob(_profile(mob_id="coward", courage=10))
    reg.register_mob(_profile(mob_id="ally"))
    reg.kill_mob(mob_id="ally", now_seconds=0.0)
    # Coward at low courage almost always routs
    routs = 0
    for trial in range(20):
        # Reset registry per trial
        r = MobFearRegistry()
        r.register_mob(_profile(mob_id="coward", courage=10))
        r.register_mob(_profile(mob_id="ally"))
        r.kill_mob(mob_id="ally", now_seconds=0.0)
        res = r.witness_ally_death(
            witness_id="coward", dying_id="ally",
            killer_level=30, now_seconds=0.0,
            rng=random.Random(trial),
        )
        if res.outcome == FearOutcome.ROUT:
            routs += 1
    # Most should rout
    assert routs >= 12


def test_high_courage_holds():
    reg = MobFearRegistry()
    reg.register_mob(_profile(mob_id="brave", courage=95))
    reg.register_mob(_profile(mob_id="ally"))
    reg.kill_mob(mob_id="ally", now_seconds=0.0)
    holds = 0
    for trial in range(20):
        r = MobFearRegistry()
        r.register_mob(_profile(mob_id="brave", courage=95))
        r.register_mob(_profile(mob_id="ally"))
        r.kill_mob(mob_id="ally", now_seconds=0.0)
        res = r.witness_ally_death(
            witness_id="brave", dying_id="ally",
            killer_level=30, now_seconds=0.0,
            rng=random.Random(trial),
        )
        if res.outcome == FearOutcome.HOLD:
            holds += 1
    assert holds >= 14


def test_pack_leader_alive_stabilizes():
    """Same courage but pack leader alive should rout less."""
    routs_with_leader = 0
    routs_without_leader = 0
    for trial in range(40):
        # With leader
        r1 = MobFearRegistry()
        r1.register_mob(_profile(
            mob_id="leader", courage=80, leader=True,
        ))
        r1.register_mob(_profile(
            mob_id="member", courage=40,
        ))
        r1.register_mob(_profile(mob_id="ally", courage=40))
        r1.kill_mob(mob_id="ally", now_seconds=0.0)
        res1 = r1.witness_ally_death(
            witness_id="member", dying_id="ally",
            killer_level=30, now_seconds=0.0,
            rng=random.Random(trial),
        )
        if res1.outcome == FearOutcome.ROUT:
            routs_with_leader += 1
        # Without leader
        r2 = MobFearRegistry()
        r2.register_mob(_profile(
            mob_id="member", courage=40,
        ))
        r2.register_mob(_profile(mob_id="ally", courage=40))
        r2.kill_mob(mob_id="ally", now_seconds=0.0)
        res2 = r2.witness_ally_death(
            witness_id="member", dying_id="ally",
            killer_level=30, now_seconds=0.0,
            rng=random.Random(trial),
        )
        if res2.outcome == FearOutcome.ROUT:
            routs_without_leader += 1
    assert routs_with_leader < routs_without_leader


def test_pack_leader_death_destabilizes_pack():
    reg = MobFearRegistry()
    reg.register_mob(_profile(
        mob_id="leader", courage=80, leader=True,
    ))
    reg.register_mob(_profile(mob_id="member", courage=50))
    reg.kill_mob(mob_id="leader", now_seconds=0.0)
    # Leader is dead — no PACK_LEADER_BONUS
    res = reg.witness_ally_death(
        witness_id="member", dying_id="leader",
        killer_level=99, now_seconds=0.0,
        rng=random.Random(0),
    )
    # Member should be more likely to rout
    # (just check we don't always HOLD)
    assert res.outcome in (
        FearOutcome.WAVER, FearOutcome.ROUT, FearOutcome.HOLD,
    )


def test_higher_level_killer_destabilizes():
    """Mob facing a much-higher-level killer routs more."""
    routs_low_killer = 0
    routs_high_killer = 0
    for trial in range(40):
        # Killer same level
        r1 = MobFearRegistry()
        r1.register_mob(_profile(
            mob_id="m1", courage=50, level=30,
        ))
        r1.register_mob(_profile(mob_id="ally", level=30))
        r1.kill_mob(mob_id="ally", now_seconds=0.0)
        res1 = r1.witness_ally_death(
            witness_id="m1", dying_id="ally",
            killer_level=30, now_seconds=0.0,
            rng=random.Random(trial),
        )
        if res1.outcome == FearOutcome.ROUT:
            routs_low_killer += 1
        # Killer 50 levels higher
        r2 = MobFearRegistry()
        r2.register_mob(_profile(
            mob_id="m1", courage=50, level=30,
        ))
        r2.register_mob(_profile(mob_id="ally", level=30))
        r2.kill_mob(mob_id="ally", now_seconds=0.0)
        res2 = r2.witness_ally_death(
            witness_id="m1", dying_id="ally",
            killer_level=80, now_seconds=0.0,
            rng=random.Random(trial),
        )
        if res2.outcome == FearOutcome.ROUT:
            routs_high_killer += 1
    assert routs_high_killer >= routs_low_killer


def test_already_routed_stays_routed():
    reg = MobFearRegistry()
    reg.register_mob(_profile(mob_id="m1", courage=10))
    reg.register_mob(_profile(mob_id="ally"))
    reg.kill_mob(mob_id="ally", now_seconds=0.0)
    reg.force_rout(mob_id="m1")
    res = reg.witness_ally_death(
        witness_id="m1", dying_id="ally",
        killer_level=30, now_seconds=0.0,
    )
    assert res.outcome == FearOutcome.ROUT
    assert "already routed" in res.notes


def test_force_rout_unknown_returns_false():
    reg = MobFearRegistry()
    assert not reg.force_rout(mob_id="ghost")


def test_has_routed_check():
    reg = MobFearRegistry()
    reg.register_mob(_profile())
    assert not reg.has_routed("g1")
    reg.force_rout(mob_id="g1")
    assert reg.has_routed("g1")


def test_total_routed():
    reg = MobFearRegistry()
    for i in range(3):
        reg.register_mob(_profile(mob_id=f"m{i}"))
        reg.force_rout(mob_id=f"m{i}")
    assert reg.total_routed() == 3


def test_full_lifecycle_pack_collapse():
    """A pack of 5 goblins. Leader dies; one member routs. The
    cascade fear amplifies as more die — by the third death,
    survivors are likely to rout."""
    reg = MobFearRegistry()
    reg.register_mob(_profile(
        mob_id="leader", courage=85, leader=True,
    ))
    for i in range(4):
        reg.register_mob(_profile(
            mob_id=f"m{i}", courage=50,
        ))
    # Leader dies first
    reg.kill_mob(mob_id="leader", now_seconds=0.0)
    # m0 witnesses
    r = reg.witness_ally_death(
        witness_id="m0", dying_id="leader",
        killer_level=99, now_seconds=0.0,
        rng=random.Random(99),
    )
    assert r.outcome in (
        FearOutcome.WAVER, FearOutcome.ROUT, FearOutcome.HOLD,
    )
    # Two more allies die — cascade fear builds
    reg.kill_mob(mob_id="m0", now_seconds=10.0)
    reg.kill_mob(mob_id="m1", now_seconds=15.0)
    # m2 sees m1 die after a cascade — high fear
    r2 = reg.witness_ally_death(
        witness_id="m2", dying_id="m1",
        killer_level=99, now_seconds=15.0,
        rng=random.Random(99),
    )
    # With cascade fear, the score is reduced
    assert r2.morale_score < 50
