"""Tests for server.intervention_mb — defensive Magic Burst engine."""
from __future__ import annotations

import pytest

from server.intervention_mb import (
    BASE_AMPLIFICATION,
    DUAL_CAST_DURATION_SECONDS,
    FAMILY_TO_BUFF,
    INTERVENTION_IMMUNITY_DURATION_S,
    INTERVENTION_REGEN_DURATION_S,
    INTERVENTION_WINDOW_SECONDS,
    LIGHT_AMPLIFICATION,
    LIGHT_IMMUNITY_DURATION_S,
    Callout,
    ChainElement,
    DualCastBuffId,
    DualCastManager,
    InterventionWindow,
    SpellFamily,
    amplification_for,
    apply_amplification,
    callout_for,
    failure_grunt,
    is_eligible,
    lands_in_window,
    mob_intervention_callout,
    open_window,
    resolve_intervention,
)


# Window timing
class TestWindow:

    def test_three_second_window(self):
        assert INTERVENTION_WINDOW_SECONDS == 3.0

    def test_open_window(self):
        w = open_window(target_id="tank",
                          chain_element=ChainElement.LIGHT,
                          predicted_mb_damage=8000,
                          now=10.0)
        assert w.opens_at == 10.0
        assert w.expires_at == 13.0
        assert w.is_light()
        assert w.predicted_mb_damage == 8000

    def test_window_negative_damage_rejected(self):
        with pytest.raises(ValueError):
            open_window(target_id="x", chain_element=ChainElement.FUSION,
                          predicted_mb_damage=-1, now=0.0)

    def test_lands_in_window_inside(self):
        w = open_window(target_id="t", chain_element=ChainElement.FUSION,
                          predicted_mb_damage=5000, now=10.0)
        assert lands_in_window(w, land_time=10.0) is True
        assert lands_in_window(w, land_time=12.0) is True
        assert lands_in_window(w, land_time=13.0) is True

    def test_lands_in_window_outside(self):
        w = open_window(target_id="t", chain_element=ChainElement.FUSION,
                          predicted_mb_damage=5000, now=10.0)
        assert lands_in_window(w, land_time=9.9) is False
        assert lands_in_window(w, land_time=13.1) is False

    def test_remaining(self):
        w = open_window(target_id="t", chain_element=ChainElement.FUSION,
                          predicted_mb_damage=5000, now=10.0)
        assert w.remaining(now=10.0) == 3.0
        assert w.remaining(now=11.5) == 1.5
        assert w.remaining(now=14.0) == 0.0

    def test_is_light_false_for_other_elements(self):
        for el in [ChainElement.FUSION, ChainElement.DARKNESS,
                     ChainElement.DISTORTION]:
            w = open_window(target_id="t", chain_element=el,
                              predicted_mb_damage=1, now=0.0)
            assert w.is_light() is False


# Amplification
class TestAmplification:

    def test_base_3x_light_5x(self):
        # Doc: '3.0 base, 5.0 if Light'
        assert BASE_AMPLIFICATION == 3.0
        assert LIGHT_AMPLIFICATION == 5.0

    def test_amplification_for_cure(self):
        assert amplification_for(SpellFamily.CURE,
                                    light_bonus=False) == 3.0
        assert amplification_for(SpellFamily.CURE,
                                    light_bonus=True) == 5.0

    def test_amplification_geo_special(self):
        # GEO is radius-doubling/tripling, not effect amplification
        assert amplification_for(SpellFamily.GEO_LUOPAN,
                                    light_bonus=False) == 2.0
        assert amplification_for(SpellFamily.GEO_LUOPAN,
                                    light_bonus=True) == 3.0

    def test_direct_damage_not_eligible(self):
        # Doc: 'Direct-damage spells (Fire, Blizzard etc) do NOT have
        # an intervention path'
        assert is_eligible(SpellFamily.DIRECT_DAMAGE) is False
        assert amplification_for(SpellFamily.DIRECT_DAMAGE,
                                    light_bonus=True) == 1.0
        assert is_eligible(SpellFamily.CURE) is True

    def test_apply_amplification_cure_iv_light(self):
        # WHM Cure IV with base 1500 on Light chain = 7500 effective
        result = apply_amplification(family=SpellFamily.CURE,
                                          base_effect=1500,
                                          light_bonus=True)
        assert result == 7500.0

    def test_apply_amplification_cure_iv_base(self):
        # Same Cure IV, no Light = 4500
        result = apply_amplification(family=SpellFamily.CURE,
                                          base_effect=1500,
                                          light_bonus=False)
        assert result == 4500.0

    def test_negative_base_rejected(self):
        with pytest.raises(ValueError):
            apply_amplification(family=SpellFamily.CURE,
                                   base_effect=-1, light_bonus=False)


# Dual cast
class TestDualCast:

    def test_30s_duration(self):
        assert DUAL_CAST_DURATION_SECONDS == 30.0

    def test_grant_cure_unlocks_dual_cure(self):
        m = DualCastManager()
        b = m.grant(caster_id="whm", family=SpellFamily.CURE, now=10.0)
        assert b.buff_id == DualCastBuffId.DUAL_CAST_CURE
        assert b.expires_at == 40.0

    def test_grant_curaga_uses_cure_buff(self):
        # Doc: Cure family covers Cure / Curaga / -na / Erase
        m = DualCastManager()
        b = m.grant(caster_id="whm", family=SpellFamily.CURAGA, now=0.0)
        assert b.buff_id == DualCastBuffId.DUAL_CAST_CURE

    def test_grant_geo_unlocks_luopan_doubled(self):
        m = DualCastManager()
        b = m.grant(caster_id="geo", family=SpellFamily.GEO_LUOPAN,
                      now=0.0)
        assert b.buff_id == DualCastBuffId.LUOPAN_RADIUS_DOUBLED

    def test_grant_tank_unlocks_enmity_spike(self):
        m = DualCastManager()
        b = m.grant(caster_id="pld", family=SpellFamily.TANK_FLASH,
                      now=0.0)
        assert b.buff_id == DualCastBuffId.TANK_ENMITY_SPIKE

    def test_is_active_for(self):
        m = DualCastManager()
        m.grant(caster_id="whm", family=SpellFamily.CURE, now=10.0)
        assert m.is_active_for(caster_id="whm",
                                  family=SpellFamily.CURE,
                                  now=20.0) is True
        # Past expiry
        assert m.is_active_for(caster_id="whm",
                                  family=SpellFamily.CURE,
                                  now=99.0) is False

    def test_grant_refreshes_same_buff(self):
        m = DualCastManager()
        m.grant(caster_id="whm", family=SpellFamily.CURE, now=0.0)
        m.grant(caster_id="whm", family=SpellFamily.CURE, now=15.0)
        # Refreshed at 15+30=45
        assert m.is_active_for(caster_id="whm",
                                  family=SpellFamily.CURE,
                                  now=44.0) is True

    def test_active_buffs_set(self):
        m = DualCastManager()
        m.grant(caster_id="rdm", family=SpellFamily.CURE, now=0.0)
        m.grant(caster_id="rdm", family=SpellFamily.RDM_ENHANCING,
                  now=0.0)
        active = m.active_buffs(caster_id="rdm", now=10.0)
        assert DualCastBuffId.DUAL_CAST_CURE in active
        assert DualCastBuffId.DUAL_CAST_ENHANCE in active

    def test_expire_all(self):
        m = DualCastManager()
        m.grant(caster_id="x", family=SpellFamily.CURE, now=0.0)
        removed = m.expire_all(now=99.0)
        assert removed == 1

    def test_direct_damage_has_no_buff(self):
        m = DualCastManager()
        with pytest.raises(ValueError):
            m.grant(caster_id="x", family=SpellFamily.DIRECT_DAMAGE,
                       now=0.0)


# Callouts
class TestCallouts:

    def test_cure_base_callout(self):
        c = callout_for(family=SpellFamily.CURE, light_bonus=False)
        assert c.line == "Magic Burst — Cure!"
        assert c.is_light_bonus is False

    def test_cure_light_callout(self):
        c = callout_for(family=SpellFamily.CURE, light_bonus=True)
        assert c.line == "MAGIC BURST — CURE V!"
        assert c.is_light_bonus is True

    def test_curaga_callout(self):
        c = callout_for(family=SpellFamily.CURAGA, light_bonus=False)
        assert "Curaga" in c.line

    def test_blm_debuff_with_label(self):
        # Doc: 'Magic Burst — Bio!' / 'Magic Burst — Slow!'
        c = callout_for(family=SpellFamily.BLM_DEBUFF,
                          light_bonus=False, spell_label="Slow")
        assert c.line == "Magic Burst — Slow!"

    def test_tank_flash_burst_uppercase(self):
        c = callout_for(family=SpellFamily.TANK_FLASH,
                          light_bonus=False, spell_label="FLASH")
        assert c.line == "FLASH BURST!"

    def test_geo_light_luopan_burst(self):
        c = callout_for(family=SpellFamily.GEO_LUOPAN,
                          light_bonus=True, spell_label="Indi-Refresh")
        # Doc: 'LUOPAN BURST!' on Light
        assert c.line == "LUOPAN BURST!"

    def test_failure_grunt(self):
        c = failure_grunt(SpellFamily.CURE)
        assert c.is_failure is True
        assert "frustration" in c.line

    def test_mob_intervention_callout(self):
        # Doc: 'A Quadav Healer shouts "[gruff Quadav speech] Cure
        # burst!" in their canonical mob voice'
        line = mob_intervention_callout(mob_class="quadav_healer",
                                              family=SpellFamily.CURE,
                                              light_bonus=False)
        assert "[quadav_healer voice]" in line
        assert "burst" in line.lower()

    def test_mob_light_callout_uppercase(self):
        line = mob_intervention_callout(mob_class="dragon_priest",
                                              family=SpellFamily.CURE,
                                              light_bonus=True)
        assert "BURST" in line


# Resolver — full pipeline
class TestResolver:

    def _window(self, *, light=False, dmg=8000, now=10.0):
        el = ChainElement.LIGHT if light else ChainElement.DISTORTION
        return open_window(target_id="tank",
                              chain_element=el,
                              predicted_mb_damage=dmg,
                              now=now)

    def test_cure_intervention_in_window(self):
        m = DualCastManager()
        w = self._window(dmg=8000)
        result = resolve_intervention(
            window=w, family=SpellFamily.CURE,
            base_effect=1500, caster_id="whm",
            land_time=12.0, dual_cast_manager=m,
        )
        assert result.succeeded is True
        # 8000 damage cancelled entirely
        assert result.mb_damage_cancelled == 8000
        # 1500 base * 3x = 4500
        assert result.amplified_effect == 4500.0
        # Regen 30s applied
        assert result.regen_applied_seconds == 30.0
        # Dual-cast cure unlocked
        assert result.dual_cast_unlocked == DualCastBuffId.DUAL_CAST_CURE
        assert m.is_active_for(caster_id="whm",
                                  family=SpellFamily.CURE,
                                  now=12.0) is True

    def test_cure_intervention_light_5x(self):
        m = DualCastManager()
        w = self._window(light=True, dmg=8000)
        result = resolve_intervention(
            window=w, family=SpellFamily.CURE,
            base_effect=1500, caster_id="whm",
            land_time=11.0, dual_cast_manager=m,
        )
        assert result.succeeded is True
        # Light: 1500 * 5 = 7500
        assert result.amplified_effect == 7500.0
        # Regen V * 2 stack -> 60s
        assert result.regen_applied_seconds == 60.0
        assert result.callout.line == "MAGIC BURST — CURE V!"

    def test_failed_outside_window(self):
        m = DualCastManager()
        w = self._window(dmg=8000)
        result = resolve_intervention(
            window=w, family=SpellFamily.CURE,
            base_effect=1500, caster_id="whm",
            land_time=14.0,                  # past expires_at 13
            dual_cast_manager=m,
        )
        assert result.succeeded is False
        assert result.mb_damage_cancelled == 0
        assert result.regen_applied_seconds == 0.0
        assert result.dual_cast_unlocked is None
        assert result.callout.is_failure is True
        # No dual cast granted
        assert m.is_active_for(caster_id="whm",
                                  family=SpellFamily.CURE,
                                  now=14.0) is False

    def test_direct_damage_rejected(self):
        m = DualCastManager()
        w = self._window(dmg=8000)
        result = resolve_intervention(
            window=w, family=SpellFamily.DIRECT_DAMAGE,
            base_effect=2000, caster_id="blm",
            land_time=12.0, dual_cast_manager=m,
        )
        assert result.succeeded is False
        assert "offensive MB pipeline" in result.reason

    def test_na_spell_immunity_30s_base(self):
        m = DualCastManager()
        w = self._window(dmg=5000)
        result = resolve_intervention(
            window=w, family=SpellFamily.NA_SPELL,
            base_effect=1.0, caster_id="whm",
            land_time=11.0, dual_cast_manager=m,
            spell_label="Paralyna",
        )
        assert result.succeeded is True
        assert result.immunity_applied_seconds == 30.0
        assert result.party_cleanse_applied is False

    def test_na_spell_light_60s_party_cleanse(self):
        m = DualCastManager()
        w = self._window(light=True, dmg=5000)
        result = resolve_intervention(
            window=w, family=SpellFamily.NA_SPELL,
            base_effect=1.0, caster_id="whm",
            land_time=11.0, dual_cast_manager=m,
            spell_label="Paralyna",
        )
        assert result.succeeded is True
        assert result.immunity_applied_seconds == 60.0
        assert result.party_cleanse_applied is True

    def test_geo_luopan_unlocks_radius_double(self):
        m = DualCastManager()
        w = self._window(dmg=5000)
        result = resolve_intervention(
            window=w, family=SpellFamily.GEO_LUOPAN,
            base_effect=10.0, caster_id="geo",      # radius
            land_time=11.0, dual_cast_manager=m,
            spell_label="Indi-Refresh",
        )
        assert result.succeeded is True
        # 10m radius * 2 = 20m
        assert result.amplified_effect == 20.0
        assert result.dual_cast_unlocked == DualCastBuffId.LUOPAN_RADIUS_DOUBLED

    def test_tank_flash_enmity_spike(self):
        m = DualCastManager()
        w = self._window(dmg=8000)
        result = resolve_intervention(
            window=w, family=SpellFamily.TANK_FLASH,
            base_effect=100.0, caster_id="pld",     # enmity
            land_time=11.0, dual_cast_manager=m,
            spell_label="FLASH",
        )
        assert result.succeeded is True
        # Enmity 100 * 3x = 300 base
        assert result.amplified_effect == 300.0
        assert result.dual_cast_unlocked == DualCastBuffId.TANK_ENMITY_SPIKE
        assert result.callout.line == "FLASH BURST!"


# Composition: doc-canonical 8-second Maat scenario beat
class TestComposition:

    def test_cure_iv_save_8000_damage_wipe(self):
        """Doc opener: 'A boss-grade NIN closes Distortion on your tank,
        the enemy BLM is winding up Blizzard IV in the burst window —
        that's ~8000 damage incoming on a 5500-HP tank. It's a wipe.'

        WHM Cure IV lands in the window -> tank takes 0 damage,
        gets healed at 3x (assume Cure IV base 1500 -> 4500), and
        gets Regen V 30s. Dual-cast cure unlocks."""
        m = DualCastManager()
        w = open_window(target_id="tank",
                          chain_element=ChainElement.DISTORTION,
                          predicted_mb_damage=8000,
                          now=0.0)
        # Cure IV cast time 3.5s — would land at 3.5s, just past the
        # 3s window. The doc says 'must start at the moment of chain
        # detonation' and is hard. Let's say WHM started early
        # (predicting the chain) so it lands at 2.5s, in window.
        result = resolve_intervention(
            window=w, family=SpellFamily.CURE,
            base_effect=1500, caster_id="whm_hero",
            land_time=2.5, dual_cast_manager=m,
        )
        assert result.succeeded
        assert result.mb_damage_cancelled == 8000
        assert result.amplified_effect == 4500.0
        assert result.regen_applied_seconds == 30.0
        assert result.dual_cast_unlocked == DualCastBuffId.DUAL_CAST_CURE
        # WHM now has 30s of dual-cast cure available
        assert m.is_active_for(caster_id="whm_hero",
                                  family=SpellFamily.CURE, now=10.0) is True

    def test_quadav_healer_blocks_player_chain(self):
        """Doc mob-symmetry: 'When the player party chains a Quadav
        Helmsman... adjacent mob Quadav Healer sees the chain element
        halo, begins casting Cure IV on the Helmsman'."""
        m = DualCastManager()
        # Player chain on Quadav Helmsman
        w = open_window(target_id="quadav_helmsman",
                          chain_element=ChainElement.FUSION,
                          predicted_mb_damage=4000,
                          now=10.0)
        # Quadav Healer Cure IV lands in window
        result = resolve_intervention(
            window=w, family=SpellFamily.CURE,
            base_effect=800, caster_id="quadav_healer",
            land_time=11.5, dual_cast_manager=m,
        )
        assert result.succeeded
        # Player chain damage cancelled
        assert result.mb_damage_cancelled == 4000
        # Quadav Healer now has dual-cast cure
        assert m.is_active_for(caster_id="quadav_healer",
                                  family=SpellFamily.CURE,
                                  now=11.5) is True

    def test_failed_cure_v_too_slow(self):
        # Cure V cast 5s — WHM didn't predict, started at chain close.
        # Lands at 5s (past 3s window).
        m = DualCastManager()
        w = open_window(target_id="tank",
                          chain_element=ChainElement.DISTORTION,
                          predicted_mb_damage=8000,
                          now=0.0)
        result = resolve_intervention(
            window=w, family=SpellFamily.CURE,
            base_effect=2500, caster_id="whm",
            land_time=5.0, dual_cast_manager=m,
        )
        assert not result.succeeded
        assert result.mb_damage_cancelled == 0
        # Tank takes the hit
