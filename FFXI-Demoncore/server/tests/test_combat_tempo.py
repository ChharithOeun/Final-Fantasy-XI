"""Tests for server.combat_tempo — cadence retune + 10x density mitigations."""
from __future__ import annotations

import pytest

from server.combat_tempo import (
    ACTIVE_RADIUS_METERS,
    ACTIVE_TIER_PARTY_BOUNDS,
    FLOOR_VALUES,
    MB_DAMAGE_BONUS_MULTIPLIER,
    MB_WINDOW_SECONDS,
    MIN_AUTO_SWING_S,
    MIN_SPELL_CAST_S,
    MIN_WS_RECOVERY_S,
    RESPAWN_BANDS,
    SLOW_ACTION_RULES,
    TEMPO_TABLE,
    TIER_ANCHOR_ZONES,
    TIER_PROFILES,
    TRASH_RESPAWN_BY_ZONE_TIER,
    ZONE_DENSITY_BANDS,
    ActionPhase,
    AutoWsToggle,
    CancelIntent,
    CancelOutcome,
    FloorMetric,
    MobTempoTier,
    MobTierState,
    RespawnCategory,
    SkillchainIndicator,
    SkillchainIndicatorPlacement,
    SlowActionId,
    TempoMetric,
    ZoneTier,
    can_cancel,
    classify_tier,
    clamp_auto_swing,
    clamp_spell_cast,
    clamp_ws_recovery,
    count_by_tier,
    damage_in_mb_window,
    density_target,
    get_density_band,
    get_floor,
    get_respawn_band,
    get_rule,
    get_tempo_band,
    halve_og_respawn,
    halve_og_value,
    is_below_floor,
    is_in_band,
    is_slow_action,
    make_indicator,
    nm_target_count,
    raise_og_value,
    resolve_cancel,
    respawn_is_in_band,
    respawn_seconds_for,
    should_halve_recast,
    tier_for_zone,
    total_compute_cost,
    trash_respawn_seconds,
    update_state,
    zone_density_in_band,
)


# ----------------------------------------------------------------------
# tempo_presets
# ----------------------------------------------------------------------

class TestTempoPresets:

    def test_table_covers_all_metrics(self):
        for m in TempoMetric:
            assert m in TEMPO_TABLE

    def test_auto_attack_band(self):
        # Doc: 4-7s OG -> 1.5-2.5s Demoncore
        b = get_tempo_band(TempoMetric.AUTO_ATTACK_SWING)
        assert b.og_span == (4.0, 7.0)
        assert b.demoncore_span == (1.5, 2.5)
        assert b.unit == "s"

    def test_skillchain_window(self):
        b = get_tempo_band(TempoMetric.SKILLCHAIN_WINDOW)
        assert b.demoncore_span == (1.5, 3.0)

    def test_player_run_speed_band(self):
        # Doc: 5.0 -> 6.5
        b = get_tempo_band(TempoMetric.PLAYER_RUN_SPEED)
        assert b.demoncore_min == 6.5

    def test_mounted_run_speed_band(self):
        # Doc: 8.0 -> 12-15
        b = get_tempo_band(TempoMetric.MOUNTED_RUN_SPEED)
        assert b.demoncore_span == (12.0, 15.0)

    def test_halve_og_value_clamps_to_band(self):
        # OG auto-attack 5s halved = 2.5 (top of Demoncore band)
        assert halve_og_value(TempoMetric.AUTO_ATTACK_SWING, 5.0) == 2.5
        # OG auto-attack 7s halved = 3.5, clamped down to 2.5
        assert halve_og_value(TempoMetric.AUTO_ATTACK_SWING, 7.0) == 2.5
        # OG WS 1.5s halved = 0.75, in band [0.4, 0.8]
        assert halve_og_value(TempoMetric.WS_CAST, 1.5) == 0.75
        # OG spell 4s halved = 2.0, in band [1.0, 3.0]
        assert halve_og_value(TempoMetric.SPELL_CAST, 4.0) == 2.0

    def test_halve_og_value_floors_below_band(self):
        # OG spell 1s halved = 0.5; below band [1.0, 3.0] -> floor at 1.0
        assert halve_og_value(TempoMetric.SPELL_CAST, 1.0) == 1.0

    def test_halve_og_value_speed_metric_rejected(self):
        with pytest.raises(ValueError):
            halve_og_value(TempoMetric.PLAYER_RUN_SPEED, 5.0)

    def test_raise_og_value_only_speed(self):
        # OG run speed 5 -> Demoncore 6.5 (band has min == max)
        assert raise_og_value(TempoMetric.PLAYER_RUN_SPEED, 5.0) == 6.5
        # OG mounted 8 -> Demoncore 12 (band min)
        assert raise_og_value(TempoMetric.MOUNTED_RUN_SPEED, 8.0) == 12.0

    def test_raise_og_value_rejects_non_speed(self):
        with pytest.raises(ValueError):
            raise_og_value(TempoMetric.AUTO_ATTACK_SWING, 4.0)

    def test_is_in_band_helper(self):
        assert is_in_band(TempoMetric.AUTO_ATTACK_SWING, 2.0) is True
        assert is_in_band(TempoMetric.AUTO_ATTACK_SWING, 4.0) is False
        assert is_in_band(TempoMetric.SPELL_CAST, 1.5) is True


# ----------------------------------------------------------------------
# speed_floors
# ----------------------------------------------------------------------

class TestSpeedFloors:

    def test_floor_constants(self):
        assert MIN_AUTO_SWING_S == 0.8
        assert MIN_SPELL_CAST_S == 0.5
        assert MIN_WS_RECOVERY_S == 0.3

    def test_clamp_auto_swing(self):
        assert clamp_auto_swing(1.5) == 1.5
        # Stacked Haste II + Hasso + Spirit Surge could push below 0.8
        assert clamp_auto_swing(0.4) == 0.8
        assert clamp_auto_swing(0.8) == 0.8

    def test_clamp_spell_cast(self):
        assert clamp_spell_cast(1.0) == 1.0
        assert clamp_spell_cast(0.3) == 0.5
        # Instant-cast (0) preserved
        assert clamp_spell_cast(0.0) == 0.0

    def test_clamp_ws_recovery(self):
        assert clamp_ws_recovery(0.5) == 0.5
        assert clamp_ws_recovery(0.1) == 0.3

    def test_negative_rejected(self):
        with pytest.raises(ValueError):
            clamp_auto_swing(-0.1)
        with pytest.raises(ValueError):
            clamp_spell_cast(-0.1)
        with pytest.raises(ValueError):
            clamp_ws_recovery(-0.1)

    def test_get_floor_lookup(self):
        assert get_floor(FloorMetric.AUTO_SWING) == 0.8
        assert get_floor(FloorMetric.SPELL_CAST) == 0.5
        assert get_floor(FloorMetric.WS_RECOVERY) == 0.3

    def test_is_below_floor(self):
        assert is_below_floor(FloorMetric.AUTO_SWING, 0.4) is True
        assert is_below_floor(FloorMetric.AUTO_SWING, 0.9) is False

    def test_floor_values_complete(self):
        for m in FloorMetric:
            assert m in FLOOR_VALUES


# ----------------------------------------------------------------------
# slow_actions
# ----------------------------------------------------------------------

class TestSlowActions:

    def test_six_carve_outs(self):
        # Doc names exactly 6: Raise / Tractor / Reraise /
        # Teleport / boss enrage / crafting
        assert len(SLOW_ACTION_RULES) == 6
        assert SlowActionId.RAISE in SLOW_ACTION_RULES
        assert SlowActionId.TRACTOR in SLOW_ACTION_RULES
        assert SlowActionId.RERAISE in SLOW_ACTION_RULES
        assert SlowActionId.TELEPORT in SLOW_ACTION_RULES
        assert SlowActionId.BOSS_ENRAGE in SLOW_ACTION_RULES
        assert SlowActionId.CRAFTING_SYNTH in SLOW_ACTION_RULES

    def test_all_slow_actions_skip_recast_halve(self):
        for rule in SLOW_ACTION_RULES.values():
            assert rule.skip_recast_halve is True

    def test_raise_kept_long(self):
        # Doc: 'long, weighty'
        rule = get_rule("raise")
        assert rule.cast_time_seconds >= 8.0
        assert rule.interruptible is True

    def test_teleport_long_interruptable(self):
        # Doc: '8-10s, interruptable'
        rule = get_rule("teleport")
        assert 8.0 <= rule.cast_time_seconds <= 12.0
        assert rule.interruptible is True

    def test_boss_enrage_no_cast(self):
        # Phase-fire, not cast
        rule = get_rule("boss_enrage")
        assert rule.cast_time_seconds == 0.0
        assert rule.interruptible is False

    def test_is_slow_action(self):
        assert is_slow_action("raise") is True
        assert is_slow_action("cure_iv") is False

    def test_should_halve_recast_default(self):
        # Normal action -> halve
        assert should_halve_recast("cure_iv") is True

    def test_should_halve_recast_slow(self):
        # Slow action -> skip
        assert should_halve_recast("raise") is False

    def test_should_halve_recast_keystone(self):
        # Even non-slow action skips if keystone=True
        assert should_halve_recast("warp", keystone=True) is False

    def test_get_rule_unknown_raises(self):
        with pytest.raises(ValueError):
            get_rule("not_a_slow_action")


# ----------------------------------------------------------------------
# animation_cancel
# ----------------------------------------------------------------------

class TestAnimationCancel:

    def test_auto_attack_startup_to_ws(self):
        result = resolve_cancel(
            phase=ActionPhase.AUTO_ATTACK_STARTUP,
            intent=CancelIntent.INITIATE_WS,
        )
        assert result.outcome == CancelOutcome.COMMITTED_TO_NEW
        assert result.new_phase == ActionPhase.WS_STARTUP
        assert result.bonus_lost is False

    def test_auto_attack_startup_to_move(self):
        result = resolve_cancel(
            phase=ActionPhase.AUTO_ATTACK_STARTUP,
            intent=CancelIntent.MOVE,
        )
        assert result.outcome == CancelOutcome.COMMITTED_TO_NEW
        assert result.new_phase is None

    def test_auto_attack_startup_to_spell(self):
        result = resolve_cancel(
            phase=ActionPhase.AUTO_ATTACK_STARTUP,
            intent=CancelIntent.INITIATE_SPELL,
        )
        assert result.outcome == CancelOutcome.COMMITTED_TO_NEW
        assert result.new_phase == ActionPhase.SPELL_CAST

    def test_ws_recovery_to_move_loses_bonus(self):
        # Doc: 'lose the WS bonus damage'
        result = resolve_cancel(
            phase=ActionPhase.WS_RECOVERY,
            intent=CancelIntent.MOVE,
        )
        assert result.outcome == CancelOutcome.LOST_BONUS
        assert result.bonus_lost is True

    def test_spell_cast_to_move_interrupted(self):
        # Doc: 'interrupts the spell, like always'
        result = resolve_cancel(
            phase=ActionPhase.SPELL_CAST,
            intent=CancelIntent.MOVE,
        )
        assert result.outcome == CancelOutcome.INTERRUPTED
        assert result.bonus_lost is False

    def test_high_commit_phase_rejected(self):
        # WS_ACTIVE shouldn't be cancelable
        result = resolve_cancel(
            phase=ActionPhase.WS_ACTIVE,
            intent=CancelIntent.MOVE,
        )
        assert result.outcome == CancelOutcome.REJECTED

    def test_spell_resolve_rejected(self):
        # Once the spell fires it can't be unfired
        result = resolve_cancel(
            phase=ActionPhase.SPELL_RESOLVE,
            intent=CancelIntent.MOVE,
        )
        assert result.outcome == CancelOutcome.REJECTED

    def test_can_cancel_helper(self):
        assert can_cancel(ActionPhase.AUTO_ATTACK_STARTUP) is True
        assert can_cancel(ActionPhase.WS_RECOVERY) is True
        assert can_cancel(ActionPhase.SPELL_CAST) is True
        assert can_cancel(ActionPhase.WS_ACTIVE) is False
        assert can_cancel(ActionPhase.SPELL_RESOLVE) is False


# ----------------------------------------------------------------------
# mob_tiers
# ----------------------------------------------------------------------

class TestMobTiers:

    def test_three_tiers_present(self):
        assert MobTempoTier.HERO in TIER_PROFILES
        assert MobTempoTier.ACTIVE in TIER_PROFILES
        assert MobTempoTier.AMBIENT in TIER_PROFILES

    def test_classify_targeted_is_hero(self):
        # Even very far, a targeted mob is HERO tier
        assert classify_tier(
            is_current_target=True,
            closest_player_distance_m=999.0,
        ) == MobTempoTier.HERO

    def test_classify_close_active(self):
        assert classify_tier(
            is_current_target=False,
            closest_player_distance_m=50.0,
        ) == MobTempoTier.ACTIVE

    def test_classify_at_boundary_active(self):
        # 80m exactly -> ACTIVE per <= comparison
        assert classify_tier(
            is_current_target=False,
            closest_player_distance_m=ACTIVE_RADIUS_METERS,
        ) == MobTempoTier.ACTIVE

    def test_classify_far_ambient(self):
        assert classify_tier(
            is_current_target=False,
            closest_player_distance_m=ACTIVE_RADIUS_METERS + 0.1,
        ) == MobTempoTier.AMBIENT

    def test_negative_distance_rejected(self):
        with pytest.raises(ValueError):
            classify_tier(is_current_target=False,
                            closest_player_distance_m=-1.0)

    def test_promote_demote(self):
        s = MobTierState(mob_id="m1")
        assert s.current_tier == MobTempoTier.AMBIENT
        # Player approaches -> promote ACTIVE
        changed, t = update_state(
            s, is_current_target=False,
            closest_player_distance_m=40.0)
        assert changed is True
        assert t == MobTempoTier.ACTIVE
        # Player target-locks -> promote HERO
        changed, t = update_state(
            s, is_current_target=True,
            closest_player_distance_m=10.0)
        assert changed is True
        assert t == MobTempoTier.HERO
        # Player drops target + walks away -> demote AMBIENT
        changed, t = update_state(
            s, is_current_target=False,
            closest_player_distance_m=200.0)
        assert changed is True
        assert t == MobTempoTier.AMBIENT

    def test_total_compute_cost(self):
        states = [
            MobTierState(mob_id="hero", current_tier=MobTempoTier.HERO),
            MobTierState(mob_id="a1", current_tier=MobTempoTier.ACTIVE),
            MobTierState(mob_id="a2", current_tier=MobTempoTier.ACTIVE),
            MobTierState(mob_id="amb", current_tier=MobTempoTier.AMBIENT),
        ]
        # 1.0 + 0.40 + 0.40 + 0.05 = 1.85
        cost = total_compute_cost(states)
        assert abs(cost - 1.85) < 1e-9

    def test_count_by_tier(self):
        states = [
            MobTierState(mob_id="a", current_tier=MobTempoTier.ACTIVE),
            MobTierState(mob_id="b", current_tier=MobTempoTier.ACTIVE),
            MobTierState(mob_id="c", current_tier=MobTempoTier.AMBIENT),
        ]
        counts = count_by_tier(states)
        assert counts[MobTempoTier.ACTIVE] == 2
        assert counts[MobTempoTier.AMBIENT] == 1
        assert counts[MobTempoTier.HERO] == 0

    def test_active_party_bounds(self):
        # Doc: '2-15 in combat radius'
        assert ACTIVE_TIER_PARTY_BOUNDS == (2, 15)

    def test_active_radius_80m(self):
        assert ACTIVE_RADIUS_METERS == 80.0


# ----------------------------------------------------------------------
# zone_density
# ----------------------------------------------------------------------

class TestZoneDensity:

    def test_four_tiers_complete(self):
        for t in ZoneTier:
            assert t in ZONE_DENSITY_BANDS

    def test_newbie_500_800(self):
        b = get_density_band(ZoneTier.NEWBIE)
        assert b.min_mobs == 500
        assert b.max_mobs == 800
        assert b.nm_density_multiplier == 1.0

    def test_mid_tier_800_1500(self):
        b = get_density_band(ZoneTier.MID_TIER)
        assert b.min_mobs == 800
        assert b.max_mobs == 1500

    def test_high_tier_1500_2500(self):
        b = get_density_band(ZoneTier.HIGH_TIER)
        assert b.min_mobs == 1500
        assert b.max_mobs == 2500

    def test_endgame_5x_nm_density(self):
        b = get_density_band(ZoneTier.END_GAME)
        assert b.nm_density_multiplier == 5.0
        assert b.min_mobs >= 2000

    def test_density_target_midpoint(self):
        # newbie midpoint = (500 + 800) / 2 = 650
        assert density_target(ZoneTier.NEWBIE) == 650
        # mid-tier (800 + 1500) // 2 = 1150
        assert density_target(ZoneTier.MID_TIER) == 1150

    def test_zone_density_in_band(self):
        assert zone_density_in_band(ZoneTier.NEWBIE, 600) is True
        assert zone_density_in_band(ZoneTier.NEWBIE, 1000) is False

    def test_nm_target_count(self):
        # 4 base * 5x mult (end-game) = 20
        assert nm_target_count(ZoneTier.END_GAME, base_nm_count=4) == 20
        # 4 base * 1x mult (newbie) = 4
        assert nm_target_count(ZoneTier.NEWBIE, base_nm_count=4) == 4

    def test_nm_target_count_negative_rejected(self):
        with pytest.raises(ValueError):
            nm_target_count(ZoneTier.NEWBIE, base_nm_count=-1)

    def test_tier_for_zone_anchors(self):
        assert tier_for_zone("ronfaure_west") == ZoneTier.NEWBIE
        assert tier_for_zone("jugner_forest") == ZoneTier.MID_TIER
        assert tier_for_zone("beadeaux_outer") == ZoneTier.HIGH_TIER
        assert tier_for_zone("dynamis_jeuno") == ZoneTier.END_GAME
        # Unknown -> mid-tier default
        assert tier_for_zone("absolutely_unheard_of_zone") == ZoneTier.MID_TIER

    def test_tier_anchor_zones_named(self):
        assert "ronfaure" in TIER_ANCHOR_ZONES[ZoneTier.NEWBIE]
        assert "sky" in TIER_ANCHOR_ZONES[ZoneTier.END_GAME]


# ----------------------------------------------------------------------
# respawn_timers
# ----------------------------------------------------------------------

class TestRespawnTimers:

    def test_four_categories_present(self):
        for c in RespawnCategory:
            assert c in RESPAWN_BANDS

    def test_trash_default_10_min(self):
        # Doc: '10 minutes is the sweet spot for most tiers'
        b = get_respawn_band(RespawnCategory.TRASH)
        assert b.default_seconds == 10 * 60

    def test_trash_band_1_to_15_min(self):
        b = get_respawn_band(RespawnCategory.TRASH)
        assert b.min_seconds == 60
        assert b.max_seconds == 15 * 60

    def test_nm_standard_band(self):
        b = get_respawn_band(RespawnCategory.NM_STANDARD)
        assert b.min_seconds == 30 * 60
        assert b.max_seconds == 2 * 3600

    def test_nm_tough_band(self):
        b = get_respawn_band(RespawnCategory.NM_TOUGH)
        assert b.min_seconds == 4 * 3600
        assert b.max_seconds == 12 * 3600

    def test_hnm_24hr_with_pop(self):
        b = get_respawn_band(RespawnCategory.HNM)
        assert b.default_seconds == 24 * 3600
        assert b.has_pop_condition is True

    def test_trash_per_zone_tier(self):
        # Doc: 'newbie leans 5, end-game leans 15'
        assert TRASH_RESPAWN_BY_ZONE_TIER[ZoneTier.NEWBIE] == 5 * 60
        assert TRASH_RESPAWN_BY_ZONE_TIER[ZoneTier.END_GAME] == 15 * 60

    def test_trash_respawn_seconds_function(self):
        assert trash_respawn_seconds(ZoneTier.NEWBIE) == 5 * 60
        assert trash_respawn_seconds(ZoneTier.MID_TIER) == 10 * 60

    def test_respawn_seconds_for_trash_uses_zone(self):
        # Trash respects zone tier
        assert respawn_seconds_for(RespawnCategory.TRASH,
                                       zone_tier=ZoneTier.NEWBIE) == 300

    def test_respawn_seconds_for_nm_ignores_zone(self):
        # NMs use band default; zone tier is irrelevant
        assert respawn_seconds_for(RespawnCategory.NM_STANDARD) == 60 * 60

    def test_respawn_is_in_band(self):
        assert respawn_is_in_band(RespawnCategory.TRASH, 600) is True
        assert respawn_is_in_band(RespawnCategory.TRASH, 30) is False

    def test_halve_og_respawn(self):
        # OG 4hr -> halved 2hr
        assert halve_og_respawn(4 * 3600) == 2 * 3600
        # OG 30s -> halved would be 15s, floored at 60s
        assert halve_og_respawn(30) == 60

    def test_halve_og_respawn_negative(self):
        with pytest.raises(ValueError):
            halve_og_respawn(-1)


# ----------------------------------------------------------------------
# skillchain_ui
# ----------------------------------------------------------------------

class TestSkillchainUi:

    def test_mb_window_15s(self):
        # Doc: 'Tighter Magic Burst window (1.5s)'
        assert MB_WINDOW_SECONDS == 1.5

    def test_mb_damage_bonus_exists(self):
        # Doc: 'fat damage bonus inside it'
        assert MB_DAMAGE_BONUS_MULTIPLIER > 1.0

    def test_make_indicator(self):
        ind = make_indicator(target_id="goblin_a",
                                chain_element="fire",
                                countdown_seconds=2.0)
        assert ind.target_id == "goblin_a"
        assert ind.chain_element == "fire"
        assert ind.placement == SkillchainIndicatorPlacement.TARGET_OF_TARGET
        assert ind.is_multi_character is False

    def test_make_indicator_multi_char(self):
        ind = make_indicator(target_id="hnm",
                                chain_element="distortion",
                                countdown_seconds=1.0,
                                multi_character=True)
        assert ind.is_multi_character is True

    def test_make_indicator_negative_rejected(self):
        with pytest.raises(ValueError):
            make_indicator(target_id="x", chain_element="fire",
                              countdown_seconds=-0.1)

    def test_damage_in_mb_window_inside(self):
        in_w, scaled = damage_in_mb_window(100.0, elapsed_seconds=1.0)
        assert in_w is True
        assert scaled == 100.0 * MB_DAMAGE_BONUS_MULTIPLIER

    def test_damage_in_mb_window_at_boundary(self):
        # elapsed == window -> still inside
        in_w, scaled = damage_in_mb_window(
            100.0, elapsed_seconds=MB_WINDOW_SECONDS)
        assert in_w is True

    def test_damage_in_mb_window_outside(self):
        in_w, scaled = damage_in_mb_window(100.0, elapsed_seconds=2.0)
        assert in_w is False
        assert scaled == 100.0

    def test_damage_in_mb_window_negative(self):
        with pytest.raises(ValueError):
            damage_in_mb_window(100.0, elapsed_seconds=-0.1)

    def test_auto_ws_toggle_matches_specific_partner(self):
        toggle = AutoWsToggle(actor_id="me",
                                  partner_actor_id="cid",
                                  ws_id="vorpal_blade")
        assert toggle.matches_opener(opener_actor_id="cid") is True
        assert toggle.matches_opener(opener_actor_id="other") is False

    def test_auto_ws_toggle_any_partner(self):
        toggle = AutoWsToggle(actor_id="me",
                                  partner_actor_id=None,
                                  ws_id="vorpal_blade")
        assert toggle.matches_opener(opener_actor_id="any") is True

    def test_auto_ws_toggle_inactive(self):
        toggle = AutoWsToggle(actor_id="me", partner_actor_id="cid",
                                  ws_id="ws", active=False)
        assert toggle.matches_opener(opener_actor_id="cid") is False

    def test_auto_ws_toggle_no_ws_set(self):
        toggle = AutoWsToggle(actor_id="me", partner_actor_id=None,
                                  ws_id=None)
        assert toggle.matches_opener(opener_actor_id="any") is False


# ----------------------------------------------------------------------
# Composition: tuning pipeline end-to-end
# ----------------------------------------------------------------------

class TestComposition:

    def test_full_tuning_pass(self):
        """Build-order step 5 tuning pipeline:

        For each metric the doc lists, run the OG -> halve -> floor
        chain and verify the result is sensible.
        """
        # Auto-attack: OG 5s -> halve -> 2.5 (top of band)
        # Then through the speed-floor 0.8: still 2.5
        v = halve_og_value(TempoMetric.AUTO_ATTACK_SWING, 5.0)
        v = clamp_auto_swing(v)
        assert v == 2.5

        # Some hyperbolic OG spell at 5s gets halved to 2.5
        v = halve_og_value(TempoMetric.SPELL_CAST, 5.0)
        v = clamp_spell_cast(v)
        assert v == 2.5

        # WS recovery isn't a tempo metric directly, but the floor
        # is independently asserted: a 0.1s stacked-buff value gets
        # raised to 0.3.
        assert clamp_ws_recovery(0.1) == 0.3

    def test_zone_tier_to_density_to_nm(self):
        # End-game zone with 4 base NMs
        tier = tier_for_zone("dynamis_xarcabard")
        assert tier == ZoneTier.END_GAME
        target = density_target(tier)
        assert target >= 2000
        nms = nm_target_count(tier, base_nm_count=4)
        assert nms == 20

    def test_mob_tier_compute_budget_under_density(self):
        # 1 hero + 14 active + 985 ambient (close to a newbie zone
        # capacity) — verify total compute stays under a sensible cap.
        states = [MobTierState(mob_id="hero",
                                  current_tier=MobTempoTier.HERO)]
        states += [MobTierState(mob_id=f"a{i}",
                                   current_tier=MobTempoTier.ACTIVE)
                     for i in range(14)]
        states += [MobTierState(mob_id=f"amb{i}",
                                   current_tier=MobTempoTier.AMBIENT)
                     for i in range(985)]
        cost = total_compute_cost(states)
        # 1.0 + 14*0.4 + 985*0.05 = 1.0 + 5.6 + 49.25 = 55.85
        assert abs(cost - 55.85) < 1e-9

    def test_slow_action_bypasses_halve(self):
        # Raise stays slow, fastcast halver skips it
        assert should_halve_recast("raise") is False
        # Same for boss enrage
        assert should_halve_recast("boss_enrage") is False
        # Cure IV gets halved
        assert should_halve_recast("cure_iv") is True

    def test_cancel_into_ws_during_mb_window_chain(self):
        # Hero scenario: player canceled auto-attack into WS at the
        # peak of a chain -> committed_to_new and damage in window
        cancel = resolve_cancel(
            phase=ActionPhase.AUTO_ATTACK_STARTUP,
            intent=CancelIntent.INITIATE_WS,
        )
        assert cancel.outcome == CancelOutcome.COMMITTED_TO_NEW
        in_w, dmg = damage_in_mb_window(150.0, elapsed_seconds=0.5)
        assert in_w is True
        assert dmg == 195.0   # 150 * 1.30
