"""Tests for skillchain_suggest."""
from __future__ import annotations

from server.skillchain_suggest import (
    ChainTier,
    Element,
    SkillchainSuggest,
)


def _seed(s: SkillchainSuggest):
    s.register_ws(
        ws_id="rampage", label="Rampage",
        primary_element=Element.EARTH,
        min_tp=1000, level_required=66,
    )
    s.register_ws(
        ws_id="raging_rush", label="Raging Rush",
        primary_element=Element.FIRE,
        min_tp=1000, level_required=70,
    )
    s.register_ws(
        ws_id="metatron_torment",
        label="Metatron Torment",
        primary_element=Element.LIGHT,
        secondary_element=Element.WIND,
        min_tp=1000, level_required=99,
    )
    s.register_ws(
        ws_id="catastrophe", label="Catastrophe",
        primary_element=Element.DARK,
        min_tp=1000, level_required=70,
    )


def test_register_ws():
    s = SkillchainSuggest()
    _seed(s)
    assert s.total_ws() == 4


def test_register_double_rejected():
    s = SkillchainSuggest()
    _seed(s)
    assert not s.register_ws(
        ws_id="rampage", label="x",
        primary_element=Element.FIRE,
    )


def test_grant_ws_unknown_rejected():
    s = SkillchainSuggest()
    assert not s.grant_ws(
        player_id="alice", ws_id="ghost",
    )


def test_observe_chain_unknown_rejected():
    s = SkillchainSuggest()
    assert not s.observe_chain(
        player_id="alice", prev_ws_id="ghost",
    )


def test_no_chain_no_suggestions():
    s = SkillchainSuggest()
    _seed(s)
    s.grant_ws(
        player_id="alice", ws_id="raging_rush",
        current_tp=1000, level=99,
    )
    assert s.suggestions_for(player_id="alice") == ()


def test_fire_then_earth_makes_liquefaction():
    s = SkillchainSuggest()
    _seed(s)
    s.grant_ws(
        player_id="alice", ws_id="raging_rush",
        current_tp=1000, level=99,
    )
    s.grant_ws(
        player_id="alice", ws_id="rampage",
        current_tp=1000, level=99,
    )
    s.observe_chain(
        player_id="alice", prev_ws_id="raging_rush",
    )
    suggestions = s.suggestions_for(player_id="alice")
    assert len(suggestions) == 1
    assert suggestions[0].ws_id == "rampage"
    assert suggestions[0].chain_element == "liquefaction"
    assert suggestions[0].tier == ChainTier.LV1


def test_dark_then_light_makes_darkness_lv3():
    s = SkillchainSuggest()
    _seed(s)
    s.grant_ws(
        player_id="alice", ws_id="catastrophe",
        current_tp=1000, level=99,
    )
    s.grant_ws(
        player_id="alice", ws_id="metatron_torment",
        current_tp=1000, level=99,
    )
    s.observe_chain(
        player_id="alice", prev_ws_id="catastrophe",
    )
    suggestions = s.suggestions_for(player_id="alice")
    light_hit = next(
        sug for sug in suggestions
        if sug.ws_id == "metatron_torment"
    )
    assert light_hit.tier == ChainTier.LV3
    assert light_hit.chain_element == "darkness"


def test_no_pair_yields_empty():
    s = SkillchainSuggest()
    s.register_ws(
        ws_id="ws_a", label="A",
        primary_element=Element.FIRE,
    )
    s.register_ws(
        ws_id="ws_b", label="B",
        primary_element=Element.FIRE,
    )
    s.grant_ws(
        player_id="alice", ws_id="ws_a",
        current_tp=1000, level=99,
    )
    s.grant_ws(
        player_id="alice", ws_id="ws_b",
        current_tp=1000, level=99,
    )
    s.observe_chain(
        player_id="alice", prev_ws_id="ws_a",
    )
    # FIRE + FIRE = no pair
    assert s.suggestions_for(player_id="alice") == ()


def test_tp_below_threshold_marks_infeasible():
    s = SkillchainSuggest()
    _seed(s)
    s.grant_ws(
        player_id="alice", ws_id="raging_rush",
        current_tp=1000, level=99,
    )
    s.grant_ws(
        player_id="alice", ws_id="rampage",
        current_tp=500, level=99,
    )
    s.observe_chain(
        player_id="alice", prev_ws_id="raging_rush",
    )
    suggestions = s.suggestions_for(player_id="alice")
    assert not suggestions[0].feasible
    assert suggestions[0].needed_tp == 500


def test_level_below_required_marks_infeasible():
    s = SkillchainSuggest()
    _seed(s)
    s.grant_ws(
        player_id="alice", ws_id="raging_rush",
        current_tp=1000, level=99,
    )
    s.grant_ws(
        player_id="alice", ws_id="rampage",
        current_tp=1000, level=50,
    )
    s.observe_chain(
        player_id="alice", prev_ws_id="raging_rush",
    )
    suggestions = s.suggestions_for(player_id="alice")
    assert not suggestions[0].feasible


def test_higher_tier_sorts_first():
    s = SkillchainSuggest()
    _seed(s)
    s.grant_ws(
        player_id="alice", ws_id="catastrophe",
        current_tp=1000, level=99,
    )
    s.grant_ws(
        player_id="alice", ws_id="rampage",
        current_tp=1000, level=99,
    )
    s.grant_ws(
        player_id="alice", ws_id="metatron_torment",
        current_tp=1000, level=99,
    )
    # rampage = EARTH, prev = DARK. EARTH+DARK = gravitation LV2.
    # metatron_torment = LIGHT/WIND, prev=DARK.
    # DARK+LIGHT = darkness LV3.
    s.observe_chain(
        player_id="alice", prev_ws_id="catastrophe",
    )
    suggestions = s.suggestions_for(player_id="alice")
    # darkness LV3 should be first
    assert suggestions[0].ws_id == "metatron_torment"


def test_feasible_before_infeasible_in_same_tier():
    """Vary level_required so one same-tier candidate is
    feasible and the other is not — feasible should sort first."""
    s = SkillchainSuggest()
    s.register_ws(
        ws_id="hot", label="hot",
        primary_element=Element.FIRE,
    )
    s.register_ws(
        ws_id="cool_a", label="A",
        primary_element=Element.LIGHTNING,
        min_tp=1000, level_required=50,
    )
    s.register_ws(
        ws_id="cool_b", label="B",
        primary_element=Element.LIGHTNING,
        min_tp=1000, level_required=99,
    )
    s.grant_ws(
        player_id="alice", ws_id="hot",
        current_tp=1000, level=70,
    )
    s.grant_ws(
        player_id="alice", ws_id="cool_a",
        current_tp=1000, level=70,
    )
    s.grant_ws(
        player_id="alice", ws_id="cool_b",
        current_tp=1000, level=70,
    )
    s.observe_chain(
        player_id="alice", prev_ws_id="hot",
    )
    suggestions = s.suggestions_for(player_id="alice")
    feasibles = [sug.feasible for sug in suggestions]
    assert feasibles == [True, False]


def test_clear_window():
    s = SkillchainSuggest()
    _seed(s)
    s.grant_ws(
        player_id="alice", ws_id="raging_rush",
        current_tp=1000, level=99,
    )
    s.observe_chain(
        player_id="alice", prev_ws_id="raging_rush",
    )
    assert s.clear_window(player_id="alice")
    assert s.suggestions_for(player_id="alice") == ()


def test_clear_no_window_returns_false():
    s = SkillchainSuggest()
    _seed(s)
    s.grant_ws(
        player_id="alice", ws_id="raging_rush",
        current_tp=1000, level=99,
    )
    assert not s.clear_window(player_id="alice")


def test_update_state():
    s = SkillchainSuggest()
    _seed(s)
    s.grant_ws(
        player_id="alice", ws_id="raging_rush",
        current_tp=200, level=99,
    )
    s.update_state(player_id="alice", current_tp=1500)
    s.grant_ws(
        player_id="alice", ws_id="rampage",
        current_tp=1500, level=99,
    )
    s.observe_chain(
        player_id="alice", prev_ws_id="raging_rush",
    )
    sug = s.suggestions_for(player_id="alice")[0]
    assert sug.feasible


def test_update_state_unknown_player():
    s = SkillchainSuggest()
    assert not s.update_state(
        player_id="ghost", current_tp=1000,
    )


def test_secondary_element_match():
    """metatron_torment has secondary WIND. WIND+EARTH should
    not pair (no entry), but WIND+LIGHTNING (impaction) does."""
    s = SkillchainSuggest()
    _seed(s)
    s.register_ws(
        ws_id="thunderclap", label="Thunderclap",
        primary_element=Element.LIGHTNING,
    )
    s.grant_ws(
        player_id="alice", ws_id="thunderclap",
        current_tp=1000, level=99,
    )
    s.grant_ws(
        player_id="alice", ws_id="metatron_torment",
        current_tp=1000, level=99,
    )
    s.observe_chain(
        player_id="alice", prev_ws_id="thunderclap",
    )
    sugs = s.suggestions_for(player_id="alice")
    # metatron_torment secondary WIND + LIGHTNING = impaction LV1
    assert any(
        sg.chain_element == "impaction" for sg in sugs
    )


def test_self_match_skipped():
    s = SkillchainSuggest()
    _seed(s)
    s.grant_ws(
        player_id="alice", ws_id="rampage",
        current_tp=1000, level=99,
    )
    s.observe_chain(
        player_id="alice", prev_ws_id="rampage",
    )
    sugs = s.suggestions_for(player_id="alice")
    # Same WS as previous is skipped
    assert all(sg.ws_id != "rampage" for sg in sugs)
