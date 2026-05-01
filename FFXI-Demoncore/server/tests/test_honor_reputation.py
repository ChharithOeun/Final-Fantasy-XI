"""Tests for the Honor + Reputation dual-gauge engine.

Run:  python -m pytest server/tests/test_honor_reputation.py -v
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from honor_reputation import (
    GLOBAL_NATION_KEY,
    HonorRepTracker,
    MoralAct,
    MoralityGauges,
    QuestDisposition,
    ReputationTier,
)
from honor_reputation.tracker import (
    HONOR_DEFAULT,
    HONOR_THRESHOLD_REFUSED,
    PILGRIMAGE_COOLDOWN_SECONDS,
    PILGRIMAGE_HONOR_GAIN,
    REP_DEFAULT,
    tier_of,
)


# ----------------------------------------------------------------------
# Defaults + gauge initialization
# ----------------------------------------------------------------------

def test_new_character_starts_neutral():
    g = MoralityGauges(actor_id="alice")
    assert g.honor == HONOR_DEFAULT
    for nation in ("bastok", "sandoria", "windurst", "ahturhgan", GLOBAL_NATION_KEY):
        assert g.rep_per_nation[nation] == REP_DEFAULT


def test_default_disposition_is_welcomed():
    t = HonorRepTracker(MoralityGauges(actor_id="alice"))
    assert t.quest_acceptance_disposition() == QuestDisposition.WELCOMED
    assert t.can_enter_city("bastok") is True
    assert t.can_teleport_to("jeuno") is True


# ----------------------------------------------------------------------
# Reputation tier mapping
# ----------------------------------------------------------------------

@pytest.mark.parametrize("rep, expected_tier", [
    (-1500, ReputationTier.PARIAH),
    (-1000, ReputationTier.PARIAH),
    (-500, ReputationTier.DESPISED),
    (-200, ReputationTier.NEUTRAL),     # boundary inclusive
    (0, ReputationTier.NEUTRAL),
    (200, ReputationTier.NEUTRAL),      # boundary inclusive
    (500, ReputationTier.LIKED),
    (999, ReputationTier.LIKED),
    (1000, ReputationTier.LOVED),
    (2999, ReputationTier.LOVED),
    (3000, ReputationTier.LEGENDARY),
    (5000, ReputationTier.LEGENDARY),
])
def test_reputation_tier_mapping(rep, expected_tier):
    assert tier_of(rep) == expected_tier


# ----------------------------------------------------------------------
# Honor mutations
# ----------------------------------------------------------------------

def test_same_race_kill_deliberate_drops_honor_below_refused():
    g = MoralityGauges(actor_id="alice", honor=300)
    t = HonorRepTracker(g)
    t.apply_act(MoralAct.SAME_RACE_KILL_DELIBERATE, was_witnessed=True,
                 nation="bastok")
    assert g.honor == 100   # 300 - 200
    # Now refused entry to gated cities
    assert t.can_enter_city("bastok") is False


def test_unwitnessed_theft_only_dings_honor():
    g = MoralityGauges(actor_id="alice")
    t = HonorRepTracker(g)
    t.apply_act(MoralAct.THEFT_FROM_NPC, was_witnessed=False, nation="bastok")
    assert g.honor == HONOR_DEFAULT - 30
    # Rep untouched (the unwitnessed branch is 0)
    assert g.rep_per_nation["bastok"] == REP_DEFAULT


def test_witnessed_theft_dings_both():
    g = MoralityGauges(actor_id="alice")
    t = HonorRepTracker(g)
    t.apply_act(MoralAct.THEFT_FROM_NPC, was_witnessed=True, nation="bastok")
    assert g.honor == HONOR_DEFAULT - 30
    assert g.rep_per_nation["bastok"] == -100
    # Global gets half-strength echo
    assert g.rep_per_nation[GLOBAL_NATION_KEY] == -50


def test_heroic_deed_lifts_both():
    g = MoralityGauges(actor_id="alice", honor=400)
    t = HonorRepTracker(g)
    t.apply_act(MoralAct.HEROIC_DEED, was_witnessed=True, nation="sandoria")
    assert g.honor == 600
    assert g.rep_per_nation["sandoria"] == 200
    assert g.rep_per_nation[GLOBAL_NATION_KEY] == 100


def test_honor_clamps_at_floor_and_ceiling():
    g = MoralityGauges(actor_id="alice", honor=100)
    t = HonorRepTracker(g)
    # 4 deliberate same-race kills: would put us at -700
    for _ in range(4):
        t.apply_act(MoralAct.SAME_RACE_KILL_DELIBERATE, was_witnessed=False)
    assert g.honor == 0   # clamped


def test_honor_ceiling_clamp():
    g = MoralityGauges(actor_id="alice", honor=900)
    t = HonorRepTracker(g)
    t.apply_act(MoralAct.HEROIC_DEED, was_witnessed=True)
    assert g.honor == 1000   # +200 ceiling-clamped from 900


def test_magnitude_scales_act():
    """A 1m gil theft should hit harder than a 10k theft."""
    g = MoralityGauges(actor_id="alice")
    t = HonorRepTracker(g)
    t.apply_act(MoralAct.THEFT_FROM_NPC, was_witnessed=True, magnitude=3.0)
    assert g.honor == HONOR_DEFAULT - 90   # 30 * 3
    # Witnessed theft, global default
    assert g.rep_per_nation[GLOBAL_NATION_KEY] == -300


# ----------------------------------------------------------------------
# Gates (entry / teleport / mog house)
# ----------------------------------------------------------------------

def test_low_honor_blocks_city_gates():
    g = MoralityGauges(actor_id="alice", honor=150)
    t = HonorRepTracker(g)
    assert t.can_enter_city("bastok") is False
    assert t.can_enter_city("sandoria") is False
    assert t.can_enter_city("jeuno") is False


def test_low_honor_allows_safe_havens():
    g = MoralityGauges(actor_id="alice", honor=50)
    t = HonorRepTracker(g)
    assert t.can_enter_city("norg") is True
    assert t.can_enter_city("selbina") is True
    assert t.can_enter_city("mhaura") is True


def test_overland_zones_have_no_gate():
    g = MoralityGauges(actor_id="alice", honor=50)
    t = HonorRepTracker(g)
    assert t.can_enter_city("south_gustaberg") is True


def test_low_honor_blocks_major_teleport_but_wilderness_ok():
    g = MoralityGauges(actor_id="alice", honor=100)
    t = HonorRepTracker(g)
    # Wilderness markers always work
    assert t.can_teleport_to("holla") is True
    assert t.can_teleport_to("dem") is True
    assert t.can_teleport_to("mea") is True
    # Major cities: refused
    assert t.can_teleport_to("bastok") is False
    assert t.can_teleport_to("jeuno") is False


def test_bounty_hunter_pass_overrides_gate():
    g = MoralityGauges(actor_id="alice", honor=100,
                       bounty_hunter_pass_until=10_000)
    t = HonorRepTracker(g)
    assert t.can_enter_city("bastok", now=5000) is True
    # After expiry, locked out again
    assert t.can_enter_city("bastok", now=20_000) is False


def test_courier_pass_overrides_teleport():
    g = MoralityGauges(actor_id="alice", honor=100,
                       courier_pass_until=10_000)
    t = HonorRepTracker(g)
    assert t.can_teleport_to("jeuno", now=5000) is True


def test_mog_house_gates_at_200():
    assert HonorRepTracker(MoralityGauges(actor_id="a", honor=199)
                          ).mog_house_accessible() is False
    assert HonorRepTracker(MoralityGauges(actor_id="a", honor=200)
                          ).mog_house_accessible() is True


# ----------------------------------------------------------------------
# Vendor disposition
# ----------------------------------------------------------------------

def test_vendor_default_neutral_disposition():
    t = HonorRepTracker(MoralityGauges(actor_id="alice"))
    allowed, mult = t.vendor_will_sell("bastok")
    assert allowed is True
    assert mult == 1.0


def test_vendor_loyal_customer_discount():
    g = MoralityGauges(actor_id="alice")
    g.rep_per_nation["bastok"] = 500   # Liked tier
    t = HonorRepTracker(g)
    allowed, mult = t.vendor_will_sell("bastok")
    assert allowed is True
    assert mult == pytest.approx(0.95)


def test_vendor_refuses_low_honor():
    g = MoralityGauges(actor_id="alice", honor=100)
    t = HonorRepTracker(g)
    allowed, mult = t.vendor_will_sell("bastok")
    assert allowed is False


def test_vendor_refuses_despised_rep():
    g = MoralityGauges(actor_id="alice")
    g.rep_per_nation["bastok"] = -500   # despised
    t = HonorRepTracker(g)
    allowed, _ = t.vendor_will_sell("bastok")
    assert allowed is False


def test_safe_haven_vendor_charges_markup():
    g = MoralityGauges(actor_id="alice", honor=100)   # even outlaw
    t = HonorRepTracker(g)
    allowed, mult = t.vendor_will_sell("norg")
    assert allowed is True
    assert mult == pytest.approx(1.20)


# ----------------------------------------------------------------------
# Auction house disposition
# ----------------------------------------------------------------------

def test_ah_default():
    t = HonorRepTracker(MoralityGauges(actor_id="alice"))
    d = t.auction_house_disposition()
    assert d["can_buy"] is True
    assert d["slot_count_factor"] == 1.0


def test_ah_low_honor_can_list_not_buy():
    t = HonorRepTracker(MoralityGauges(actor_id="alice", honor=50))
    d = t.auction_house_disposition()
    assert d["can_list"] is True
    assert d["can_buy"] is False


def test_ah_despised_global_caps_slot_count():
    g = MoralityGauges(actor_id="alice")
    g.rep_per_nation[GLOBAL_NATION_KEY] = -500
    t = HonorRepTracker(g)
    d = t.auction_house_disposition()
    assert d["slot_count_factor"] == pytest.approx(1/3)


# ----------------------------------------------------------------------
# Quest disposition
# ----------------------------------------------------------------------

def test_quest_disposition_three_tiers():
    assert HonorRepTracker(MoralityGauges(actor_id="a", honor=100)
                          ).quest_acceptance_disposition() == QuestDisposition.REFUSED
    assert HonorRepTracker(MoralityGauges(actor_id="a", honor=400)
                          ).quest_acceptance_disposition() == QuestDisposition.WATCHED
    assert HonorRepTracker(MoralityGauges(actor_id="a", honor=800)
                          ).quest_acceptance_disposition() == QuestDisposition.WELCOMED


# ----------------------------------------------------------------------
# Recovery paths
# ----------------------------------------------------------------------

def test_donation_lifts_rep():
    g = MoralityGauges(actor_id="alice")
    t = HonorRepTracker(g)
    gained = t.donate_to_treasury(gil=400_000, nation="bastok")
    # 400k / 20k = 20 rep
    assert gained == 20
    assert g.rep_per_nation["bastok"] == 20


def test_donation_below_threshold_no_change():
    g = MoralityGauges(actor_id="alice")
    t = HonorRepTracker(g)
    gained = t.donate_to_treasury(gil=10_000, nation="bastok")
    assert gained == 0
    assert g.rep_per_nation["bastok"] == 0


def test_loyal_customer_slow_gain():
    g = MoralityGauges(actor_id="alice")
    t = HonorRepTracker(g)
    gain = t.loyal_customer_spend(gil=350_000, nation="bastok")
    assert gain == 3   # 350k / 100k = 3 rep
    assert g.rep_per_nation["bastok"] == 3


def test_pilgrimage_lifts_honor_once_per_year():
    g = MoralityGauges(actor_id="alice", honor=400)
    t = HonorRepTracker(g)
    assert t.pilgrimage_complete(now=1_000_000) is True
    assert g.honor == 400 + PILGRIMAGE_HONOR_GAIN

    # Try again 6 months later: cooldown
    assert t.pilgrimage_complete(now=1_000_000 + 180 * 86400) is False
    assert g.honor == 400 + PILGRIMAGE_HONOR_GAIN

    # 1+ year later: allowed
    assert t.pilgrimage_complete(now=1_000_000 + PILGRIMAGE_COOLDOWN_SECONDS + 1) is True


def test_rep_decays_toward_neutral_only():
    g = MoralityGauges(actor_id="alice")
    g.rep_per_nation["bastok"] = -500
    g.rep_per_nation["sandoria"] = 800
    t = HonorRepTracker(g)
    t.daily_decay(days_elapsed=10)
    assert g.rep_per_nation["bastok"] == -490
    assert g.rep_per_nation["sandoria"] == 790


def test_rep_decay_does_not_overshoot_zero():
    g = MoralityGauges(actor_id="alice")
    g.rep_per_nation["bastok"] = -3
    t = HonorRepTracker(g)
    t.daily_decay(days_elapsed=100)
    assert g.rep_per_nation["bastok"] == 0


def test_honor_does_not_decay():
    g = MoralityGauges(actor_id="alice", honor=200)
    t = HonorRepTracker(g)
    t.daily_decay(days_elapsed=365)
    # Honor never moves from time alone
    assert g.honor == 200


# ----------------------------------------------------------------------
# Outlaw flow
# ----------------------------------------------------------------------

def test_becoming_outlaw_crashes_rep_only_lightly_dings_honor():
    g = MoralityGauges(actor_id="alice")
    t = HonorRepTracker(g)
    t.apply_act(MoralAct.BECAME_OUTLAW, was_witnessed=True, nation="bastok")
    assert g.honor == HONOR_DEFAULT - 100
    assert g.rep_per_nation["bastok"] == -500
    # Half-echo to global
    assert g.rep_per_nation[GLOBAL_NATION_KEY] == -250
    # Now: pariah behavior
    assert t.reputation_tier("bastok") == ReputationTier.DESPISED


def test_safe_haven_check():
    t = HonorRepTracker(MoralityGauges(actor_id="alice"))
    assert t.is_in_safe_haven("Norg") is True   # case-insensitive
    assert t.is_in_safe_haven("selbina") is True
    assert t.is_in_safe_haven("bastok") is False


# ----------------------------------------------------------------------
# Multi-nation: rep is per-nation
# ----------------------------------------------------------------------

def test_rep_changes_per_nation_independent():
    """Heroism in Bastok shouldn't lift Sandoria's rep proportionally."""
    g = MoralityGauges(actor_id="alice")
    t = HonorRepTracker(g)
    t.apply_act(MoralAct.HEROIC_DEED, was_witnessed=True, nation="bastok")
    assert g.rep_per_nation["bastok"] == 200
    # Sandoria only sees the global echo, not the full hit
    assert g.rep_per_nation["sandoria"] == 0
    assert g.rep_per_nation[GLOBAL_NATION_KEY] == 100


def test_quest_completion_rep_only():
    g = MoralityGauges(actor_id="alice")
    t = HonorRepTracker(g)
    t.apply_act(MoralAct.QUEST_COMPLETED, nation="bastok")
    assert g.honor == HONOR_DEFAULT
    assert g.rep_per_nation["bastok"] == 5
