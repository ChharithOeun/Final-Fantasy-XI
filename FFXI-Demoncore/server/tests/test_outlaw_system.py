"""Tests for outlaw flag + bounty arithmetic + aggro rules.

Run:  python -m pytest server/tests/test_outlaw_system.py -v
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from outlaw_system import (
    BOUNTY_BASE_PER_LEVEL,
    BOUNTY_PAYOFF_MULTIPLIER,
    BountySnapshot,
    BountyTracker,
    FactionRace,
    KillResult,
    MONASTIC_SECLUSION_SECONDS,
    NATION_WIPE_THRESHOLD,
    OUTLAW_SAFE_HAVENS,
    OutlawAggroRules,
    OutlawStatus,
    REJOINDER_KILL_THRESHOLD,
    REJOINDER_WINDOW_SECONDS,
)
from outlaw_system.aggro_rules import ZoneType, classify_zone


# ----------------------------------------------------------------------
# Cross-race kill: legitimate XP, no outlaw flag
# ----------------------------------------------------------------------

def test_civilized_killing_goblin_is_xp_no_outlaw():
    s = BountySnapshot(actor_id="alice", race=FactionRace.CIVILIZED)
    t = BountyTracker(s)
    result = t.notify_kill(
        victim_id="gob1", victim_race=FactionRace.GOBLIN,
        victim_level=20, now=100,
    )
    assert result.is_same_race is False
    assert result.became_outlaw_now is False
    assert result.bounty_minted == 0
    assert s.status == OutlawStatus.CITIZEN
    assert s.bounty_value == 0


def test_goblin_killing_orc_is_xp_no_outlaw():
    """Inter-tribal beastman war: legitimate XP for the goblin."""
    s = BountySnapshot(actor_id="gob_chief", race=FactionRace.GOBLIN)
    t = BountyTracker(s)
    result = t.notify_kill(
        victim_id="orc1", victim_race=FactionRace.ORC,
        victim_level=30, now=100,
    )
    assert result.is_same_race is False
    assert s.status == OutlawStatus.CITIZEN


# ----------------------------------------------------------------------
# Same-race kill: outlaw flag + bounty
# ----------------------------------------------------------------------

def test_civilized_killing_civilized_flags_outlaw():
    """Player kills another player → outlaw."""
    s = BountySnapshot(actor_id="alice", race=FactionRace.CIVILIZED)
    t = BountyTracker(s)
    result = t.notify_kill(
        victim_id="bob", victim_race=FactionRace.CIVILIZED,
        victim_level=75, now=100,
    )
    assert result.is_same_race is True
    assert result.became_outlaw_now is True
    # Doc example: 1000 × 75 × 1.0 = 75,000 gil first kill
    assert result.bounty_minted == 75_000
    assert s.bounty_value == 75_000
    assert s.status == OutlawStatus.FLAGGED


def test_goblin_killing_goblin_flags_outlaw():
    """A goblin killing another goblin = outlaw goblin."""
    s = BountySnapshot(actor_id="rogue_gob", race=FactionRace.GOBLIN)
    t = BountyTracker(s)
    result = t.notify_kill(
        victim_id="other_gob", victim_race=FactionRace.GOBLIN,
        victim_level=30, now=100,
    )
    assert result.is_same_race is True
    assert s.status == OutlawStatus.FLAGGED


def test_outlaw_vs_outlaw_is_cross_faction():
    """Per the doc: 'outlaw vs outlaw is the most LEGAL PvP available.'"""
    s = BountySnapshot(actor_id="bandit_a", race=FactionRace.OUTLAW)
    t = BountyTracker(s)
    result = t.notify_kill(
        victim_id="bandit_b", victim_race=FactionRace.OUTLAW,
        victim_level=70, now=100,
    )
    assert result.is_same_race is False
    assert s.status == OutlawStatus.CITIZEN


# ----------------------------------------------------------------------
# Bounty arithmetic & escalation premium
# ----------------------------------------------------------------------

def test_second_kill_escalation_premium():
    """Doc example: 'Second kill that day: 80-level victim →
    1000 × 80 × 1.25 = 100,000 gil bounty (escalation premium)'"""
    s = BountySnapshot(actor_id="alice", race=FactionRace.CIVILIZED)
    t = BountyTracker(s)
    t.notify_kill(victim_id="bob", victim_race=FactionRace.CIVILIZED,
                   victim_level=75, now=100)
    result = t.notify_kill(
        victim_id="carol", victim_race=FactionRace.CIVILIZED,
        victim_level=80, now=200,
    )
    # 1000 × 80 × (1 + 1*0.25) = 100,000
    assert result.bounty_minted == 100_000
    assert s.bounty_value == 175_000   # 75k + 100k


def test_third_kill_continues_escalation():
    """Doc example: third kill of a 70-lvl victim with 2 prior 24h
    kills → 1000 × 70 × 1.5 = 105,000."""
    s = BountySnapshot(actor_id="alice", race=FactionRace.CIVILIZED)
    t = BountyTracker(s)
    t.notify_kill(victim_id="b", victim_race=FactionRace.CIVILIZED,
                   victim_level=75, now=100)
    t.notify_kill(victim_id="c", victim_race=FactionRace.CIVILIZED,
                   victim_level=80, now=200)
    result = t.notify_kill(
        victim_id="d", victim_race=FactionRace.CIVILIZED,
        victim_level=70, now=300,
    )
    assert result.bounty_minted == 105_000


def test_kill_history_prunes_after_24h():
    """24h+ old kills no longer escalate the next bounty."""
    s = BountySnapshot(actor_id="alice", race=FactionRace.CIVILIZED)
    t = BountyTracker(s)
    t.notify_kill(victim_id="b", victim_race=FactionRace.CIVILIZED,
                   victim_level=75, now=0)
    # 25 hours later: prior kill should have aged out
    result = t.notify_kill(
        victim_id="c", victim_race=FactionRace.CIVILIZED,
        victim_level=80, now=25 * 3600,
    )
    # First-kill rate again: 1000 × 80 × 1 = 80_000
    assert result.bounty_minted == 80_000


def test_bounty_minted_bigger_for_higher_level_victim():
    s = BountySnapshot(actor_id="a", race=FactionRace.CIVILIZED)
    t = BountyTracker(s)
    r1 = t.notify_kill(victim_id="v1", victim_race=FactionRace.CIVILIZED,
                        victim_level=20, now=0)
    s2 = BountySnapshot(actor_id="b", race=FactionRace.CIVILIZED)
    t2 = BountyTracker(s2)
    r2 = t2.notify_kill(victim_id="v1", victim_race=FactionRace.CIVILIZED,
                         victim_level=99, now=0)
    assert r2.bounty_minted > r1.bounty_minted * 4


# ----------------------------------------------------------------------
# Anti-spawn-camp: rejoinder mechanic
# ----------------------------------------------------------------------

def test_rejoinder_triggers_after_three_kills_of_same_victim():
    s = BountySnapshot(actor_id="alice", race=FactionRace.CIVILIZED)
    t = BountyTracker(s)
    # First 3 kills of same victim within 4h: no rejoinder yet
    for i in range(3):
        result = t.notify_kill(
            victim_id="bob", victim_race=FactionRace.CIVILIZED,
            victim_level=50, now=i * 3600,
        )
        assert result.rejoinder_applied is False

    # 4th kill within window: rejoinder fires
    result = t.notify_kill(
        victim_id="bob", victim_race=FactionRace.CIVILIZED,
        victim_level=50, now=3 * 3600 + 1,
    )
    assert result.rejoinder_applied is True
    assert result.victim_tracker_active is True


def test_rejoinder_doubles_bounty():
    """Rejoinder (anti-grief) doubles the bounty premium."""
    s = BountySnapshot(actor_id="alice", race=FactionRace.CIVILIZED)
    t = BountyTracker(s)
    for i in range(3):
        t.notify_kill(victim_id="bob", victim_race=FactionRace.CIVILIZED,
                       victim_level=50, now=i * 1000)
    # Normal escalation (3 prior in 24h): 1.75x. With rejoinder: 3.5x.
    result = t.notify_kill(
        victim_id="bob", victim_race=FactionRace.CIVILIZED,
        victim_level=50, now=3 * 1000 + 1,
    )
    expected = int(BOUNTY_BASE_PER_LEVEL * 50 * 1.75 * 2.0)
    assert result.bounty_minted == expected


def test_rejoinder_history_prunes_after_window():
    """After the 4-hour window, the per-victim history clears."""
    s = BountySnapshot(actor_id="alice", race=FactionRace.CIVILIZED)
    t = BountyTracker(s)
    for i in range(3):
        t.notify_kill(victim_id="bob", victim_race=FactionRace.CIVILIZED,
                       victim_level=50, now=i * 60)
    # 5 hours later: history should have pruned, no rejoinder
    result = t.notify_kill(
        victim_id="bob", victim_race=FactionRace.CIVILIZED,
        victim_level=50, now=5 * 3600,
    )
    assert result.rejoinder_applied is False


# ----------------------------------------------------------------------
# Anti-nation-wipe
# ----------------------------------------------------------------------

def test_nation_wipe_triggers_at_5_npc_kills_per_day():
    s = BountySnapshot(actor_id="alice", race=FactionRace.CIVILIZED)
    t = BountyTracker(s)
    for i in range(NATION_WIPE_THRESHOLD - 1):
        result = t.notify_kill(
            victim_id=f"npc_{i}", victim_race=FactionRace.CIVILIZED,
            victim_level=50, victim_is_npc=True, victim_nation="bastok",
            now=i * 60,
        )
        assert result.nation_wipe_aggro_triggered is False

    # 5th kill: triggers nation-wipe escalation
    result = t.notify_kill(
        victim_id="npc_5", victim_race=FactionRace.CIVILIZED,
        victim_level=50, victim_is_npc=True, victim_nation="bastok",
        now=NATION_WIPE_THRESHOLD * 60,
    )
    assert result.nation_wipe_aggro_triggered is True


def test_nation_wipe_isolated_per_nation():
    """Killing in one nation doesn't escalate aggro in another."""
    s = BountySnapshot(actor_id="alice", race=FactionRace.CIVILIZED)
    t = BountyTracker(s)
    for i in range(5):
        t.notify_kill(victim_id=f"npc_{i}", victim_race=FactionRace.CIVILIZED,
                       victim_level=50, victim_is_npc=True,
                       victim_nation="bastok", now=i * 60)
    # First kill in Sandy: not yet escalated
    result = t.notify_kill(
        victim_id="sandy_npc", victim_race=FactionRace.CIVILIZED,
        victim_level=50, victim_is_npc=True, victim_nation="sandoria",
        now=10_000,
    )
    assert result.nation_wipe_aggro_triggered is False


# ----------------------------------------------------------------------
# Cleanse paths: payoff / pardon / monastic
# ----------------------------------------------------------------------

def test_pay_off_bounty_at_2x():
    s = BountySnapshot(actor_id="alice", race=FactionRace.CIVILIZED)
    t = BountyTracker(s)
    t.notify_kill(victim_id="b", victim_race=FactionRace.CIVILIZED,
                   victim_level=75, now=0)   # 75k bounty
    cost = t.payoff_cost()
    assert cost == 150_000   # 2x

    cleared = t.pay_off_bounty(gil_paid=149_999)
    assert cleared is False
    assert s.bounty_value == 75_000

    cleared = t.pay_off_bounty(gil_paid=cost)
    assert cleared is True
    assert s.bounty_value == 0
    assert s.status == OutlawStatus.PARDONED


def test_pardon_quest_clears_status():
    s = BountySnapshot(actor_id="alice", race=FactionRace.CIVILIZED)
    t = BountyTracker(s)
    t.notify_kill(victim_id="b", victim_race=FactionRace.CIVILIZED,
                   victim_level=75, now=0)
    t.complete_pardon_quest()
    assert s.status == OutlawStatus.PARDONED
    assert s.bounty_value == 0
    assert s.pardon_quest_completed is True


def test_monastic_seclusion_30_days_clears():
    s = BountySnapshot(actor_id="alice", race=FactionRace.CIVILIZED)
    t = BountyTracker(s)
    t.notify_kill(victim_id="b", victim_race=FactionRace.CIVILIZED,
                   victim_level=75, now=100)
    t.begin_monastic_seclusion(now=100)
    # 29 days later: still flagged
    assert t.check_monastic_seclusion(now=100 + 29 * 86400) is False
    assert s.status == OutlawStatus.FLAGGED
    # 30+ days later: cleared
    assert t.check_monastic_seclusion(
        now=100 + MONASTIC_SECLUSION_SECONDS + 1) is True
    assert s.status == OutlawStatus.PARDONED


# ----------------------------------------------------------------------
# Bounty board visibility
# ----------------------------------------------------------------------

def test_low_bounty_not_on_board():
    s = BountySnapshot(actor_id="alice", race=FactionRace.CIVILIZED,
                       status=OutlawStatus.FLAGGED, bounty_value=10_000)
    t = BountyTracker(s)
    assert t.is_on_bounty_board() is False


def test_high_bounty_on_board():
    s = BountySnapshot(actor_id="alice", race=FactionRace.CIVILIZED,
                       status=OutlawStatus.FLAGGED, bounty_value=100_000)
    t = BountyTracker(s)
    assert t.is_on_bounty_board() is True


def test_pardoned_actor_not_on_board():
    s = BountySnapshot(actor_id="alice", race=FactionRace.CIVILIZED,
                       status=OutlawStatus.PARDONED, bounty_value=0)
    t = BountyTracker(s)
    assert t.is_on_bounty_board() is False


# ----------------------------------------------------------------------
# Zone classification + aggro rules
# ----------------------------------------------------------------------

def test_zone_classification():
    assert classify_zone("bastok")[0] == ZoneType.NATION_CITY
    assert classify_zone("Norg")[0] == ZoneType.SAFE_HAVEN
    assert classify_zone("selbina")[0] == ZoneType.SAFE_HAVEN
    assert classify_zone("whitegate")[0] == ZoneType.WHITEGATE
    assert classify_zone("south_gustaberg")[0] == ZoneType.OPEN_WORLD
    assert classify_zone("davoi")[0] == ZoneType.BEASTMAN_STRONGHOLD


def test_safe_haven_no_guard_aggro():
    rules = OutlawAggroRules()
    aggro = rules.should_npc_aggro(
        zone="norg", npc_faction=FactionRace.CIVILIZED,
        npc_role="guard",
        target_status=OutlawStatus.FLAGGED,
        target_race=FactionRace.CIVILIZED,
    )
    assert aggro is False


def test_nation_city_guards_aggro_outlaws():
    rules = OutlawAggroRules()
    aggro = rules.should_npc_aggro(
        zone="bastok", npc_faction=FactionRace.CIVILIZED,
        npc_role="guard",
        target_status=OutlawStatus.FLAGGED,
        target_race=FactionRace.CIVILIZED,
    )
    assert aggro is True


def test_nation_city_guards_dont_aggro_citizens():
    rules = OutlawAggroRules()
    aggro = rules.should_npc_aggro(
        zone="bastok", npc_faction=FactionRace.CIVILIZED,
        npc_role="guard",
        target_status=OutlawStatus.CITIZEN,
        target_race=FactionRace.CIVILIZED,
    )
    assert aggro is False


def test_nation_city_civilians_dont_aggro_outlaws():
    rules = OutlawAggroRules()
    aggro = rules.should_npc_aggro(
        zone="bastok", npc_faction=FactionRace.CIVILIZED,
        npc_role="civilian",
        target_status=OutlawStatus.FLAGGED,
        target_race=FactionRace.CIVILIZED,
    )
    assert aggro is False


def test_open_world_outlaw_open_season():
    """In open zones, outlaws are aggroed by everyone."""
    rules = OutlawAggroRules()
    for npc_faction in (FactionRace.GOBLIN, FactionRace.CIVILIZED):
        aggro = rules.should_npc_aggro(
            zone="south_gustaberg", npc_faction=npc_faction,
            npc_role="civilian",
            target_status=OutlawStatus.FLAGGED,
            target_race=FactionRace.CIVILIZED,
        )
        assert aggro is True


def test_beastman_stronghold_aggros_cross_race():
    """Davoi orcs aggro a hume regardless of outlaw status."""
    rules = OutlawAggroRules()
    aggro = rules.should_npc_aggro(
        zone="davoi", npc_faction=FactionRace.ORC,
        npc_role="tribe",
        target_status=OutlawStatus.CITIZEN,
        target_race=FactionRace.CIVILIZED,
    )
    assert aggro is True


def test_beastman_stronghold_same_race_outlaw():
    """A goblin outlaw entering a goblin stronghold gets aggroed
    (they're a free agent, no auto-shelter)."""
    rules = OutlawAggroRules()
    # Use a generic stronghold-named zone to keep things simple
    aggro = rules.should_npc_aggro(
        zone="davoi", npc_faction=FactionRace.ORC,
        npc_role="tribe",
        target_status=OutlawStatus.FLAGGED,
        target_race=FactionRace.ORC,
    )
    assert aggro is True


def test_beastman_stronghold_same_race_citizen_safe():
    """An orc citizen entering an orc stronghold: no aggro."""
    rules = OutlawAggroRules()
    aggro = rules.should_npc_aggro(
        zone="davoi", npc_faction=FactionRace.ORC,
        npc_role="tribe",
        target_status=OutlawStatus.CITIZEN,
        target_race=FactionRace.ORC,
    )
    assert aggro is False


def test_safe_haven_zone_line_blocked_in_combat():
    """Anti-mid-fight-escape: can't zone-line into Norg in combat."""
    rules = OutlawAggroRules()
    assert rules.is_safe_zone_line_target(
        target_zone="norg", actor_in_combat=True) is False
    assert rules.is_safe_zone_line_target(
        target_zone="norg", actor_in_combat=False) is True
    # Non-safe-haven targets always allowed
    assert rules.is_safe_zone_line_target(
        target_zone="south_gustaberg", actor_in_combat=True) is True


# ----------------------------------------------------------------------
# Helper queries
# ----------------------------------------------------------------------

def test_kills_in_24h_rolling_count():
    s = BountySnapshot(actor_id="alice", race=FactionRace.CIVILIZED)
    t = BountyTracker(s)
    for i in range(3):
        t.notify_kill(victim_id=f"v{i}", victim_race=FactionRace.CIVILIZED,
                       victim_level=50, now=i * 100)
    assert t.kills_in_24h(now=300) == 3
    # 25 hours later: pruned
    assert t.kills_in_24h(now=25 * 3600) == 0


def test_safe_havens_set_matches_doc():
    assert OUTLAW_SAFE_HAVENS == {"norg", "selbina", "mhaura"}
