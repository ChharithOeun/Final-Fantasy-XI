"""Tests for server.damage_physics — structures + heal + repair + PvP."""
from __future__ import annotations

import pytest

from server.damage_physics import (
    DEFAULT_HEAL_DELAY_S,
    ICONIC_FINE_GIL,
    ICONIC_HONOR_PENALTY,
    OWN_NATION_FINE_GIL,
    OWN_NATION_HONOR_PENALTY,
    REPAIR_NPC_ROSTER,
    STRUCTURE_PRESETS,
    VFX_PRESETS,
    HealingStructure,
    MaterialClass,
    RepairNpc,
    StrikeContext,
    StrikeOutcome,
    StructureRegistry,
    StructureSnapshot,
    VisibleState,
    aoe_damage,
    apply_damage,
    apply_repair,
    can_heal,
    classify_strike,
    filter_broadcastable,
    get_preset,
    get_repair_npc,
    global_registry,
    heal_tick,
    heal_tick_many,
    is_iconic,
    linear_falloff,
    quote_repair,
    reset_global_registry,
    resolve_visible_state,
)


# ----------------------------------------------------------------------
# structure_kinds
# ----------------------------------------------------------------------

class TestStructureKinds:

    def test_preset_table_matches_doc(self):
        # Doc tuning anchors block, exact rows
        assert STRUCTURE_PRESETS["barrel"].hp_max == 100
        assert STRUCTURE_PRESETS["barrel"].heal_rate == 5.0
        assert STRUCTURE_PRESETS["crate_stack"].hp_max == 200
        assert STRUCTURE_PRESETS["wooden_cart"].hp_max == 500
        assert STRUCTURE_PRESETS["lantern_post"].hp_max == 80
        assert STRUCTURE_PRESETS["lantern_post"].heal_rate == 4.0
        assert STRUCTURE_PRESETS["vendor_stall_awning"].heal_rate == 3.0
        assert STRUCTURE_PRESETS["wooden_palisade_segment"].hp_max == 2_000
        assert STRUCTURE_PRESETS["stone_wall_section"].hp_max == 50_000
        assert STRUCTURE_PRESETS["bastok_city_gate"].hp_max == 200_000
        assert STRUCTURE_PRESETS["castle_tower"].hp_max == 1_000_000

    def test_full_heal_seconds(self):
        # Doc anchor: barrel = 20 s
        assert STRUCTURE_PRESETS["barrel"].full_heal_seconds == 20.0
        # crate stack 200 / 5 = 40 s
        assert STRUCTURE_PRESETS["crate_stack"].full_heal_seconds == 40.0
        # wooden palisade 2000 / 8 = 250 s
        assert STRUCTURE_PRESETS["wooden_palisade_segment"].full_heal_seconds == 250.0

    def test_iconic_flagged(self):
        # Doc: '~1% iconic; gates/walls/towers can scar'
        assert is_iconic("stone_wall_section") is True
        assert is_iconic("bastok_city_gate") is True
        assert is_iconic("castle_tower") is True
        assert is_iconic("barrel") is False
        assert is_iconic("crate_stack") is False
        assert is_iconic("nonexistent_kind") is False

    def test_vfx_presets_cover_all_materials(self):
        for mat in MaterialClass:
            assert mat in VFX_PRESETS
            preset = VFX_PRESETS[mat]
            assert preset.break_vfx
            assert preset.heal_vfx
            assert preset.break_sfx

    def test_default_heal_delay_per_material(self):
        # Doc: 'typically 8-15 seconds'
        for mat, delay in DEFAULT_HEAL_DELAY_S.items():
            assert 8.0 <= delay <= 15.0

    def test_iconic_threshold_is_low(self):
        # Doc: 'city walls typically 0.05'
        assert STRUCTURE_PRESETS["stone_wall_section"].permanent_threshold == 0.05
        assert STRUCTURE_PRESETS["bastok_city_gate"].permanent_threshold == 0.05

    def test_get_preset_missing(self):
        assert get_preset("not_a_real_kind") is None


# ----------------------------------------------------------------------
# structure_state — visible state bands
# ----------------------------------------------------------------------

class TestVisibleState:

    def test_pristine_band(self):
        # 100-75% HP -> pristine
        assert resolve_visible_state(100, 100) == VisibleState.PRISTINE
        assert resolve_visible_state(80, 100) == VisibleState.PRISTINE
        assert resolve_visible_state(75, 100) == VisibleState.PRISTINE

    def test_cracked_band(self):
        # 75-50% HP -> cracked
        assert resolve_visible_state(74, 100) == VisibleState.CRACKED
        assert resolve_visible_state(60, 100) == VisibleState.CRACKED
        assert resolve_visible_state(50, 100) == VisibleState.CRACKED

    def test_battered_band(self):
        # 50-25% HP -> battered
        assert resolve_visible_state(49, 100) == VisibleState.BATTERED
        assert resolve_visible_state(35, 100) == VisibleState.BATTERED
        assert resolve_visible_state(25, 100) == VisibleState.BATTERED

    def test_ruined_band(self):
        # 25-1% HP -> ruined
        assert resolve_visible_state(24, 100) == VisibleState.RUINED
        assert resolve_visible_state(10, 100) == VisibleState.RUINED
        assert resolve_visible_state(1, 100) == VisibleState.RUINED

    def test_destroyed(self):
        # 0% -> destroyed
        assert resolve_visible_state(0, 100) == VisibleState.DESTROYED

    def test_zero_hpmax(self):
        assert resolve_visible_state(0, 0) == VisibleState.DESTROYED
        # Defensive: negative hp_max also resolves to destroyed
        assert resolve_visible_state(-5, 0) == VisibleState.DESTROYED


class TestHealingStructure:

    def test_from_preset_full_hp(self):
        preset = STRUCTURE_PRESETS["barrel"]
        s = HealingStructure.from_preset(
            structure_id="b1", zone_id="bastok_markets",
            position=(0, 0, 0), preset=preset,
        )
        assert s.hp_current == 100
        assert s.hp_max == 100
        assert s.visible_state == VisibleState.PRISTINE
        assert s.heal_rate == 5.0
        assert s.last_hit_at is None
        assert s.permanent is False

    def test_hp_fraction(self):
        preset = STRUCTURE_PRESETS["barrel"]
        s = HealingStructure.from_preset(
            structure_id="b1", zone_id="z", position=(0, 0, 0),
            preset=preset,
        )
        s.hp_current = 50
        assert s.hp_fraction() == 0.5

    def test_post_init_default_pristine(self):
        # Bare construction with no hp_current should fill to hp_max
        s = HealingStructure(
            structure_id="b1", zone_id="z", kind="barrel",
            position=(0, 0, 0), hp_max=100, heal_rate=5.0,
            heal_delay_s=8.0, permanent_threshold=1.0,
        )
        assert s.hp_current == 100
        assert s.visible_state == VisibleState.PRISTINE


# ----------------------------------------------------------------------
# damage_resolver
# ----------------------------------------------------------------------

class TestDamageResolver:

    def _barrel(self):
        return HealingStructure.from_preset(
            structure_id="b1", zone_id="bastok_markets",
            position=(0, 0, 0), preset=STRUCTURE_PRESETS["barrel"],
        )

    def test_apply_damage_basic(self):
        s = self._barrel()
        ev = apply_damage(s, amount=30, now=10.0)
        assert ev.amount_dealt == 30
        assert s.hp_current == 70
        assert ev.state_before == VisibleState.PRISTINE
        # 70/100 = 70% -> cracked (75-50 band, 70 included)
        assert ev.state_after == VisibleState.CRACKED
        assert ev.state_changed is True
        assert s.last_hit_at == 10.0

    def test_apply_damage_clamps_at_zero(self):
        s = self._barrel()
        ev = apply_damage(s, amount=999, now=5.0)
        assert s.hp_current == 0
        assert ev.amount_dealt == 100
        assert ev.state_after == VisibleState.DESTROYED

    def test_negative_damage_rejected(self):
        s = self._barrel()
        with pytest.raises(ValueError):
            apply_damage(s, amount=-1, now=0.0)

    def test_permanent_threshold_locks_destroyed(self):
        # Stone wall: threshold 0.05 of 50000 = 2500. Hitting it
        # for 47600 damage leaves 2400 HP, below threshold -> permanent.
        s = HealingStructure.from_preset(
            structure_id="w1", zone_id="bastok_metalworks",
            position=(0, 0, 0),
            preset=STRUCTURE_PRESETS["stone_wall_section"],
        )
        ev = apply_damage(s, amount=47_600, now=100.0)
        assert s.permanent is True
        assert s.hp_current == 0
        assert s.visible_state == VisibleState.DESTROYED
        assert ev.became_permanent is True

    def test_permanent_threshold_no_trigger_above(self):
        # Same wall, only 30000 damage -> 20000 HP, far above threshold
        s = HealingStructure.from_preset(
            structure_id="w1", zone_id="bastok_metalworks",
            position=(0, 0, 0),
            preset=STRUCTURE_PRESETS["stone_wall_section"],
        )
        ev = apply_damage(s, amount=30_000, now=10.0)
        assert s.permanent is False
        assert s.hp_current == 20_000
        assert ev.became_permanent is False

    def test_already_permanent_takes_no_more_damage(self):
        s = HealingStructure.from_preset(
            structure_id="w1", zone_id="bastok_metalworks",
            position=(0, 0, 0),
            preset=STRUCTURE_PRESETS["stone_wall_section"],
        )
        s.permanent = True
        s.hp_current = 0
        ev = apply_damage(s, amount=999, now=5.0)
        assert ev.amount_dealt == 0
        assert s.hp_current == 0

    def test_aoe_damage_radius_filter(self):
        s_inside = HealingStructure.from_preset(
            structure_id="b_in", zone_id="z", position=(0, 0, 0),
            preset=STRUCTURE_PRESETS["barrel"],
        )
        s_edge = HealingStructure.from_preset(
            structure_id="b_edge", zone_id="z", position=(10, 0, 0),
            preset=STRUCTURE_PRESETS["barrel"],
        )
        s_outside = HealingStructure.from_preset(
            structure_id="b_out", zone_id="z", position=(20, 0, 0),
            preset=STRUCTURE_PRESETS["barrel"],
        )
        events = aoe_damage(
            [s_inside, s_edge, s_outside],
            epicenter=(0, 0, 0), radius=10.0,
            damage=50, now=0.0,
        )
        # Inside + edge (distance 10 == radius) hit; outside skipped
        assert len(events) == 2
        ids = {e.structure_id for e in events}
        assert ids == {"b_in", "b_edge"}
        assert s_outside.hp_current == 100
        assert s_inside.hp_current == 50

    def test_aoe_with_linear_falloff(self):
        s_center = HealingStructure.from_preset(
            structure_id="c", zone_id="z", position=(0, 0, 0),
            preset=STRUCTURE_PRESETS["barrel"],
        )
        s_half = HealingStructure.from_preset(
            structure_id="h", zone_id="z", position=(5, 0, 0),
            preset=STRUCTURE_PRESETS["barrel"],
        )
        events = aoe_damage(
            [s_center, s_half],
            epicenter=(0, 0, 0), radius=10.0,
            damage=80, now=0.0, falloff=linear_falloff,
        )
        # Center: full damage 80; half-distance: 80 * 0.5 = 40
        assert s_center.hp_current == 20
        assert s_half.hp_current == 60
        assert len(events) == 2

    def test_aoe_negative_radius_rejected(self):
        with pytest.raises(ValueError):
            aoe_damage([], epicenter=(0, 0, 0), radius=-1.0,
                          damage=1, now=0.0)


# ----------------------------------------------------------------------
# heal_tick
# ----------------------------------------------------------------------

class TestHealTick:

    def _hit_barrel(self, *, hp_after=70, hit_at=10.0):
        s = HealingStructure.from_preset(
            structure_id="b1", zone_id="z", position=(0, 0, 0),
            preset=STRUCTURE_PRESETS["barrel"],
        )
        s.hp_current = hp_after
        s.last_hit_at = hit_at
        s.visible_state = resolve_visible_state(hp_after, s.hp_max)
        return s

    def test_can_heal_blocked_inside_delay(self):
        s = self._hit_barrel(hit_at=10.0)
        # delay = 8 s, current time 12 s -> only 2s elapsed -> blocked
        assert can_heal(s, now=12.0) is False

    def test_can_heal_after_delay(self):
        s = self._hit_barrel(hit_at=10.0)
        assert can_heal(s, now=18.0) is True
        assert can_heal(s, now=20.0) is True

    def test_can_heal_blocked_when_full(self):
        s = self._hit_barrel(hp_after=100, hit_at=10.0)
        assert can_heal(s, now=999.0) is False

    def test_can_heal_blocked_when_permanent(self):
        s = self._hit_barrel()
        s.permanent = True
        assert can_heal(s, now=999.0) is False

    def test_heal_tick_basic(self):
        s = self._hit_barrel(hp_after=70, hit_at=10.0)
        # Wait past delay (10 + 8 = 18); tick 1 second more
        ev = heal_tick(s, now=19.0, dt=1.0)
        # heal_rate=5 * dt=1 -> +5 HP
        assert ev.healed_amount == 5
        assert s.hp_current == 75
        assert ev.state_after == VisibleState.PRISTINE   # 75 == pristine boundary
        assert ev.state_changed is True

    def test_heal_tick_no_state_change(self):
        s = self._hit_barrel(hp_after=70, hit_at=10.0)
        ev = heal_tick(s, now=18.5, dt=0.5)
        # +2.5 -> rounds to 73; still cracked
        assert s.hp_current == 73 or s.hp_current == 72
        assert ev.state_changed is False

    def test_heal_caps_at_max(self):
        s = self._hit_barrel(hp_after=98, hit_at=10.0)
        ev = heal_tick(s, now=18.0, dt=10.0)
        # Would heal +50, capped at 100
        assert s.hp_current == 100
        # last_hit_at cleared once fully healed
        assert s.last_hit_at is None

    def test_heal_tick_blocked_inside_delay(self):
        s = self._hit_barrel(hp_after=70, hit_at=10.0)
        ev = heal_tick(s, now=12.0, dt=1.0)
        assert ev.healed_amount == 0
        assert ev.state_changed is False
        assert s.hp_current == 70

    def test_filter_broadcastable(self):
        s1 = self._hit_barrel(hp_after=70, hit_at=10.0)
        s2 = self._hit_barrel(hp_after=70, hit_at=10.0)
        s2.structure_id = "b2"
        # First tick: small dt within delay -> no heal
        events = heal_tick_many([s1, s2], now=12.0, dt=1.0)
        assert filter_broadcastable(events) == []

    def test_heal_tick_negative_dt(self):
        s = self._hit_barrel()
        with pytest.raises(ValueError):
            heal_tick(s, now=99.0, dt=-1.0)


# ----------------------------------------------------------------------
# repair_npc
# ----------------------------------------------------------------------

class TestRepairNpc:

    def _wall(self, hp_current=20_000):
        s = HealingStructure.from_preset(
            structure_id="w1", zone_id="bastok_metalworks",
            position=(0, 0, 0),
            preset=STRUCTURE_PRESETS["stone_wall_section"],
        )
        s.hp_current = hp_current
        return s

    def test_voinaut_quote_proportional(self):
        npc = REPAIR_NPC_ROSTER["voinaut"]
        s = self._wall(hp_current=25_000)  # 50% missing
        quote = quote_repair(npc, s, material="stone_brick")
        assert quote.fully_repairable is True
        # gil = ceil(0.5 * 120) = 60
        assert quote.gil_cost == 60
        assert quote.hp_missing == 25_000

    def test_quote_full_hp_no_charge(self):
        npc = REPAIR_NPC_ROSTER["voinaut"]
        s = self._wall(hp_current=50_000)
        quote = quote_repair(npc, s, material="stone_brick")
        assert quote.gil_cost == 0
        assert quote.fully_repairable is True

    def test_repair_unsupported_material(self):
        npc = REPAIR_NPC_ROSTER["pellah"]   # wood + cloth only
        s = self._wall(hp_current=20_000)
        quote = quote_repair(npc, s, material="stone_brick")
        assert quote.gil_cost == 0
        assert quote.refusal_reason is not None
        assert "doesn't work" in quote.refusal_reason

    def test_apply_repair_full(self):
        npc = REPAIR_NPC_ROSTER["voinaut"]
        s = self._wall(hp_current=25_000)
        quote = quote_repair(npc, s, material="stone_brick")
        success, reason, hp_restored = apply_repair(
            npc, s, gil_paid=quote.gil_cost,
            material="stone_brick", now=0.0,
        )
        assert success is True
        assert s.hp_current == 50_000
        assert hp_restored == 25_000

    def test_apply_repair_partial(self):
        npc = REPAIR_NPC_ROSTER["voinaut"]
        s = self._wall(hp_current=25_000)
        # Pay half — restore half of missing
        success, reason, hp_restored = apply_repair(
            npc, s, gil_paid=30, material="stone_brick", now=0.0,
        )
        assert success is True
        # 50% of 60 gil = 50% of 25000 hp = 12500
        assert hp_restored == 12_500
        assert s.hp_current == 37_500

    def test_apply_repair_zero_gil_rejected(self):
        npc = REPAIR_NPC_ROSTER["voinaut"]
        s = self._wall(hp_current=25_000)
        success, reason, hp_restored = apply_repair(
            npc, s, gil_paid=0, material="stone_brick", now=0.0,
        )
        assert success is False
        assert hp_restored == 0

    def test_permanent_blocks_normal_npc(self):
        npc = REPAIR_NPC_ROSTER["voinaut"]
        s = self._wall(hp_current=0)
        s.permanent = True
        quote = quote_repair(npc, s, material="stone_brick")
        assert quote.fully_repairable is False
        assert "permanent" in quote.refusal_reason

    def test_permanent_unlock_allows_repair(self):
        npc = RepairNpc(
            npc_id="emergency",
            name="Emergency",
            nation="bastok",
            home_zone="bastok_metalworks",
            crafts_supported=("stone_brick",),
            skill_level=99,
            unlock_permanent_repair=True,
        )
        s = self._wall(hp_current=0)
        s.permanent = True
        quote = quote_repair(npc, s, material="stone_brick")
        assert quote.fully_repairable is True

    def test_restricted_kind_below_skill(self):
        # Voinaut is skill 72; restricted_kinds_min_skill is 60.
        # Override with low-skill clone.
        low = RepairNpc(
            npc_id="apprentice",
            name="Apprentice",
            nation="bastok",
            home_zone="bastok_metalworks",
            crafts_supported=("stone_brick", "stone_carved"),
            skill_level=40,
            restricted_kinds=("bastok_city_gate",),
            restricted_kinds_min_skill=60,
        )
        gate = HealingStructure.from_preset(
            structure_id="g1", zone_id="bastok_metalworks",
            position=(0, 0, 0),
            preset=STRUCTURE_PRESETS["bastok_city_gate"],
        )
        gate.hp_current = 100_000
        quote = quote_repair(low, gate, material="stone_carved")
        assert quote.refusal_reason is not None
        assert "skill level 60" in quote.refusal_reason

    def test_get_repair_npc_lookup(self):
        assert get_repair_npc("voinaut") is not None
        assert get_repair_npc("not_exists") is None


# ----------------------------------------------------------------------
# pvp_rules
# ----------------------------------------------------------------------

class TestPvpRules:

    def _barrel(self):
        return HealingStructure.from_preset(
            structure_id="b1", zone_id="bastok_markets",
            position=(0, 0, 0), preset=STRUCTURE_PRESETS["barrel"],
        )

    def _wall(self):
        return HealingStructure.from_preset(
            structure_id="w1", zone_id="bastok_metalworks",
            position=(0, 0, 0),
            preset=STRUCTURE_PRESETS["stone_wall_section"],
        )

    def test_mob_aoe_normal_blocked(self):
        s = self._barrel()
        ctx = StrikeContext(
            attacker_id="cleric_brother",
            attacker_nation="beastman",
            attacker_is_outlaw=False,
            attacker_in_nation_vs_nation_period=False,
            structure_nation="bastok",
            is_mob_attack=True,
            is_besieged_event=False,
        )
        ruling = classify_strike(s, ctx=ctx)
        assert ruling.outcome == StrikeOutcome.BLOCKED_MOB_AOE_NORMAL
        assert ruling.apply_damage is False

    def test_besieged_mob_attack_applies(self):
        s = self._barrel()
        ctx = StrikeContext(
            attacker_id="quadav_raider",
            attacker_nation="beastman",
            attacker_is_outlaw=False,
            attacker_in_nation_vs_nation_period=False,
            structure_nation="bastok",
            is_mob_attack=True,
            is_besieged_event=True,
        )
        ruling = classify_strike(s, ctx=ctx)
        assert ruling.outcome == StrikeOutcome.APPLY
        assert ruling.apply_damage is True

    def test_own_nation_player_costs_honor(self):
        s = self._barrel()
        ctx = StrikeContext(
            attacker_id="player_a", attacker_nation="bastok",
            attacker_is_outlaw=False,
            attacker_in_nation_vs_nation_period=False,
            structure_nation="bastok",
            is_mob_attack=False, is_besieged_event=False,
        )
        ruling = classify_strike(s, ctx=ctx)
        assert ruling.apply_damage is True
        assert ruling.honor_delta == OWN_NATION_HONOR_PENALTY
        assert ruling.fine_gil == OWN_NATION_FINE_GIL
        assert ruling.iconic_alert is False

    def test_own_nation_iconic_iconic_alert(self):
        s = self._wall()
        ctx = StrikeContext(
            attacker_id="player_b", attacker_nation="bastok",
            attacker_is_outlaw=False,
            attacker_in_nation_vs_nation_period=False,
            structure_nation="bastok",
            is_mob_attack=False, is_besieged_event=False,
        )
        ruling = classify_strike(s, ctx=ctx)
        assert ruling.iconic_alert is True
        assert ruling.bounty_priority == "high"
        assert ruling.honor_delta == ICONIC_HONOR_PENALTY
        assert ruling.fine_gil == ICONIC_FINE_GIL

    def test_foreign_player_non_outlaw_blocked(self):
        s = self._barrel()
        ctx = StrikeContext(
            attacker_id="player_c", attacker_nation="san_doria",
            attacker_is_outlaw=False,
            attacker_in_nation_vs_nation_period=False,
            structure_nation="bastok",
            is_mob_attack=False, is_besieged_event=False,
        )
        ruling = classify_strike(s, ctx=ctx)
        assert ruling.outcome == StrikeOutcome.BLOCKED_NON_OUTLAW_FOREIGN
        assert ruling.apply_damage is False

    def test_outlaw_foreign_non_iconic_low_bounty(self):
        s = self._barrel()
        ctx = StrikeContext(
            attacker_id="player_d", attacker_nation="san_doria",
            attacker_is_outlaw=True,
            attacker_in_nation_vs_nation_period=False,
            structure_nation="bastok",
            is_mob_attack=False, is_besieged_event=False,
        )
        ruling = classify_strike(s, ctx=ctx)
        assert ruling.outcome == StrikeOutcome.APPLY
        assert ruling.bounty_priority == "low"

    def test_outlaw_foreign_iconic_high_bounty(self):
        s = self._wall()
        ctx = StrikeContext(
            attacker_id="player_e", attacker_nation="san_doria",
            attacker_is_outlaw=True,
            attacker_in_nation_vs_nation_period=False,
            structure_nation="bastok",
            is_mob_attack=False, is_besieged_event=False,
        )
        ruling = classify_strike(s, ctx=ctx)
        assert ruling.outcome == StrikeOutcome.APPLY
        assert ruling.iconic_alert is True
        assert ruling.bounty_priority == "high"

    def test_nation_vs_nation_period_allows_foreign(self):
        s = self._barrel()
        ctx = StrikeContext(
            attacker_id="player_f", attacker_nation="san_doria",
            attacker_is_outlaw=False,
            attacker_in_nation_vs_nation_period=True,
            structure_nation="bastok",
            is_mob_attack=False, is_besieged_event=False,
        )
        ruling = classify_strike(s, ctx=ctx)
        assert ruling.outcome == StrikeOutcome.APPLY


# ----------------------------------------------------------------------
# registry — spawn / spatial / tick / persistence
# ----------------------------------------------------------------------

class TestRegistry:

    def test_spawn_and_zone_lookup(self):
        reg = StructureRegistry()
        b = reg.spawn_structure(
            zone_id="bastok_markets", kind="barrel",
            position=(10, 0, 0),
        )
        assert b.zone_id == "bastok_markets"
        assert len(reg) == 1
        assert reg.structures_in_zone("bastok_markets") == [b]
        assert reg.get(b.structure_id) is b

    def test_spawn_unknown_kind_raises(self):
        reg = StructureRegistry()
        with pytest.raises(ValueError):
            reg.spawn_structure(zone_id="z", kind="not_a_kind",
                                  position=(0, 0, 0))

    def test_spawn_duplicate_id_raises(self):
        reg = StructureRegistry()
        reg.spawn_structure(zone_id="z", kind="barrel",
                              position=(0, 0, 0), structure_id="b1")
        with pytest.raises(ValueError):
            reg.spawn_structure(zone_id="z", kind="barrel",
                                  position=(1, 0, 0),
                                  structure_id="b1")

    def test_remove_structure(self):
        reg = StructureRegistry()
        b = reg.spawn_structure(zone_id="z", kind="barrel",
                                  position=(0, 0, 0))
        assert reg.remove(b.structure_id) is True
        assert len(reg) == 0
        assert reg.remove(b.structure_id) is False

    def test_structures_in_radius(self):
        reg = StructureRegistry()
        a = reg.spawn_structure(zone_id="z", kind="barrel",
                                  position=(0, 0, 0))
        b = reg.spawn_structure(zone_id="z", kind="barrel",
                                  position=(3, 4, 0))   # dist 5
        c = reg.spawn_structure(zone_id="z", kind="barrel",
                                  position=(20, 0, 0))
        # other zone — should never be returned
        d = reg.spawn_structure(zone_id="other", kind="barrel",
                                  position=(0, 0, 0))
        in_range = reg.structures_in_radius(
            zone_id="z", point=(0, 0, 0), radius=5.0,
        )
        ids = {s.structure_id for s in in_range}
        assert a.structure_id in ids
        assert b.structure_id in ids
        assert c.structure_id not in ids
        assert d.structure_id not in ids

    def test_radius_negative(self):
        reg = StructureRegistry()
        with pytest.raises(ValueError):
            reg.structures_in_radius(zone_id="z", point=(0, 0, 0),
                                       radius=-1.0)

    def test_tick_all_only_broadcasts_state_changes(self):
        reg = StructureRegistry()
        s = reg.spawn_structure(zone_id="z", kind="barrel",
                                  position=(0, 0, 0))
        s.hp_current = 70
        s.last_hit_at = 0.0
        s.visible_state = VisibleState.CRACKED
        # Past the heal_delay, tick a full second
        events = reg.tick_all(now=10.0, dt=1.0, broadcast_only=True)
        # 70 + 5 = 75 -> stage shifts to pristine -> broadcast
        assert len(events) == 1
        assert events[0].state_changed is True
        assert events[0].state_after == VisibleState.PRISTINE

    def test_tick_zone_isolated(self):
        reg = StructureRegistry()
        a = reg.spawn_structure(zone_id="zoneA", kind="barrel",
                                  position=(0, 0, 0))
        b = reg.spawn_structure(zone_id="zoneB", kind="barrel",
                                  position=(0, 0, 0))
        a.hp_current = 70; a.last_hit_at = 0.0
        a.visible_state = VisibleState.CRACKED
        b.hp_current = 70; b.last_hit_at = 0.0
        b.visible_state = VisibleState.CRACKED
        events = reg.tick_zone(zone_id="zoneA", now=10.0, dt=1.0,
                                  broadcast_only=False)
        assert len(events) == 1
        assert events[0].structure_id == a.structure_id

    def test_snapshot_and_restore(self):
        reg = StructureRegistry()
        s = reg.spawn_structure(zone_id="z", kind="stone_wall_section",
                                  position=(0, 0, 0),
                                  structure_id="wall1")
        s.hp_current = 30_000
        s.visible_state = VisibleState.BATTERED
        s.last_hit_at = 50.0
        snaps = reg.snapshot()
        assert len(snaps) == 1

        reg2 = StructureRegistry()
        n = reg2.restore(snaps)
        assert n == 1
        restored = reg2.get("wall1")
        assert restored is not None
        assert restored.hp_current == 30_000
        assert restored.visible_state == VisibleState.BATTERED
        assert restored.last_hit_at == 50.0
        # heal_rate / hp_max came from the preset
        assert restored.hp_max == 50_000

    def test_restore_skips_unknown_kind(self):
        reg = StructureRegistry()
        snap = StructureSnapshot(
            structure_id="x", zone_id="z", kind="phantom_kind",
            position=(0, 0, 0), hp_current=0,
            visible_state="destroyed", last_hit_at=None,
            permanent=False,
        )
        n = reg.restore([snap])
        assert n == 0

    def test_global_registry_singleton(self):
        reset_global_registry()
        a = global_registry()
        b = global_registry()
        assert a is b
        a.spawn_structure(zone_id="z", kind="barrel",
                            position=(0, 0, 0))
        assert len(global_registry()) == 1
        reset_global_registry()
        assert len(global_registry()) == 0


# ----------------------------------------------------------------------
# Composition: full siege scenario end-to-end
# ----------------------------------------------------------------------

class TestSiegeScenario:
    """A worked example: Quadav AoE during a Besieged event hits a
    stone wall section, the wall stages down, then heals back over
    time once the attack stops."""

    def test_quadav_besieged_hits_wall_then_heals(self):
        reg = StructureRegistry()
        wall = reg.spawn_structure(
            zone_id="north_gustaberg",
            kind="stone_wall_section",
            position=(100, 0, 0),
            structure_id="north_wall_a",
        )
        assert wall.visible_state == VisibleState.PRISTINE

        # Quadav siege boss aoes the wall
        ctx = StrikeContext(
            attacker_id="quadav_warlord",
            attacker_nation="beastman",
            attacker_is_outlaw=False,
            attacker_in_nation_vs_nation_period=False,
            structure_nation="bastok",
            is_mob_attack=True,
            is_besieged_event=True,
        )
        ruling = classify_strike(wall, ctx=ctx)
        assert ruling.apply_damage is True

        # Apply 38000 damage — wall drops to 12000 HP (24%) -> ruined
        ev = apply_damage(wall, amount=38_000, now=100.0)
        assert wall.hp_current == 12_000
        assert wall.visible_state == VisibleState.RUINED
        assert wall.permanent is False
        assert ev.state_before == VisibleState.PRISTINE
        assert ev.state_after == VisibleState.RUINED

        # ~7 minutes pass — past 15s heal_delay; tick a 400-second
        # window so heal accumulates 30 * 400 = 12000 HP back to 24000
        # (48% -> battered)
        events = reg.tick_all(now=520.0, dt=400.0, broadcast_only=True)
        assert wall.hp_current == 24_000
        assert wall.visible_state == VisibleState.BATTERED
        assert len(events) == 1
        assert events[0].state_after == VisibleState.BATTERED

    def test_iconic_wall_pushed_past_threshold_scars(self):
        reg = StructureRegistry()
        wall = reg.spawn_structure(
            zone_id="metalworks", kind="bastok_city_gate",
            position=(0, 0, 0),
        )
        # Smash to 5% HP — past threshold
        # threshold_hp = 0.05 * 200000 = 10000; new_hp = 5000 < 10000
        apply_damage(wall, amount=195_000, now=10.0)
        assert wall.permanent is True
        assert wall.visible_state == VisibleState.DESTROYED

        # Healing tick does nothing — permanent is set
        ev = heal_tick(wall, now=999.0, dt=999.0)
        assert ev.healed_amount == 0
        assert wall.hp_current == 0
