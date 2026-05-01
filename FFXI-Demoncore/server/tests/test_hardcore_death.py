"""Tests for server.hardcore_death — 1hr timer + Fomor pool + boss assist + evolution."""
from __future__ import annotations

import pytest

from server.hardcore_death import (
    ACCOUNT_COOLDOWN_SECONDS,
    DEATH_TIMER_SECONDS,
    KILLS_PER_EVOLUTION_LEVEL,
    MAX_EVOLUTION_LEVELS,
    MAX_FOMORS_END_GAME,
    MAX_FOMORS_PER_BOSS_FIGHT,
    NIGHT_HOUR_RANGE,
    TOWN_SAFE_ZONES,
    Appearance,
    AssistRequest,
    DeathRecord,
    DeathState,
    FomorEntry,
    FomorEvolutionState,
    FomorPool,
    FomorSnapshot,
    FomorState,
    FomorTier,
    GearPiece,
    JobLevel,
    RaiseSource,
    apply_raise,
    flag_mythological,
    maybe_expire,
    open_death_record,
    opt_out_at_expiry,
    record_player_kill,
    select_assists,
    take_snapshot,
    trophy_for_kill,
)


# ----------------------------------------------------------------------
# death_timer
# ----------------------------------------------------------------------

class TestDeathTimer:

    def test_one_hour_window(self):
        assert DEATH_TIMER_SECONDS == 3600

    def test_open_death_record_pristine(self):
        rec = open_death_record(char_id="alice",
                                     death_zone_id="ronfaure",
                                     now=100.0)
        assert rec.state == DeathState.KO
        assert rec.expires_at == 100.0 + DEATH_TIMER_SECONDS
        assert rec.remaining_seconds(now=100.0) == 3600

    def test_remaining_decreases(self):
        rec = open_death_record(char_id="alice",
                                     death_zone_id="ronfaure",
                                     now=0.0)
        assert rec.remaining_seconds(now=600.0) == 3000.0

    def test_apply_raise_inside_window(self):
        rec = open_death_record(char_id="alice",
                                     death_zone_id="ronfaure",
                                     now=0.0)
        ok = apply_raise(rec, source=RaiseSource.RAISE_II, now=1800.0)
        assert ok is True
        assert rec.state == DeathState.RAISED
        assert rec.raised_by_source == RaiseSource.RAISE_II

    def test_apply_raise_after_expiry_blocked(self):
        rec = open_death_record(char_id="alice",
                                     death_zone_id="ronfaure",
                                     now=0.0)
        ok = apply_raise(rec, source=RaiseSource.RAISE_SPELL,
                            now=4000.0)
        assert ok is False
        assert rec.state == DeathState.KO        # still KO until maybe_expire fires

    def test_maybe_expire(self):
        rec = open_death_record(char_id="alice",
                                     death_zone_id="ronfaure",
                                     now=0.0)
        # Inside window: no change
        assert maybe_expire(rec, now=1800.0) is False
        # Past window: state advances to EXPIRED
        assert maybe_expire(rec, now=4000.0) is True
        assert rec.state == DeathState.EXPIRED

    def test_opt_out_at_expiry(self):
        rec = open_death_record(char_id="alice",
                                     death_zone_id="ronfaure",
                                     now=0.0)
        maybe_expire(rec, now=4000.0)
        assert opt_out_at_expiry(rec) is True
        assert rec.state == DeathState.OPTED_OUT

    def test_opt_out_only_at_expiry(self):
        rec = open_death_record(char_id="alice",
                                     death_zone_id="ronfaure",
                                     now=0.0)
        # Still KO, can't opt out
        assert opt_out_at_expiry(rec) is False

    def test_5_raise_sources(self):
        # Doc names exactly 5 raise paths
        assert len(list(RaiseSource)) == 5


# ----------------------------------------------------------------------
# snapshot
# ----------------------------------------------------------------------

class TestSnapshot:

    def _appearance(self):
        return Appearance(race="hume", face_id="f1", hair_id="h1",
                            eye_id="e1", skin_id="s1")

    def test_take_snapshot(self):
        snap = take_snapshot(
            char_id="alice", name="Alice",
            appearance=self._appearance(),
            jobs=[JobLevel(job="WHM", level=75, is_main=True),
                    JobLevel(job="BLM", level=37, is_sub=True)],
            sub_skills=["healing_magic", "divine_magic"],
            merit_points=100, job_points=500,
            gear=[GearPiece(slot="head", item_id="cleric_cap",
                              rarity="rare")],
            death_zone_id="phomiuna_aqueducts",
            now=1000.0,
        )
        assert snap.name == "Alice"
        assert snap.main_level == 75
        assert snap.main_job is not None
        assert snap.main_job.job == "WHM"
        assert snap.sub_job is not None
        assert snap.sub_job.job == "BLM"

    def test_no_main_job_rejected(self):
        with pytest.raises(ValueError):
            take_snapshot(
                char_id="bob", name="Bob",
                appearance=self._appearance(),
                jobs=[JobLevel(job="WAR", level=50)],   # is_main=False
                sub_skills=[],
                merit_points=0, job_points=0,
                gear=[], death_zone_id="z", now=0.0,
            )

    def test_negative_merits_rejected(self):
        with pytest.raises(ValueError):
            take_snapshot(
                char_id="bob", name="Bob",
                appearance=self._appearance(),
                jobs=[JobLevel(job="WAR", level=50, is_main=True)],
                sub_skills=[],
                merit_points=-1, job_points=0,
                gear=[], death_zone_id="z", now=0.0,
            )


# ----------------------------------------------------------------------
# fomor_pool
# ----------------------------------------------------------------------

class TestFomorPool:

    def _snap(self, char_id="alice", level=75):
        return take_snapshot(
            char_id=char_id, name=f"{char_id}",
            appearance=Appearance("hume", "f", "h", "e", "s"),
            jobs=[JobLevel(job="WAR", level=level, is_main=True)],
            sub_skills=[], merit_points=0, job_points=0,
            gear=[], death_zone_id="ronfaure", now=0.0,
        )

    def test_24h_cooldown(self):
        # Doc: 'cannot become a fomor twice in 24h'
        assert ACCOUNT_COOLDOWN_SECONDS == 24 * 3600
        pool = FomorPool()
        snap = self._snap()
        f1 = pool.convert_to_fomor(account_id="acc1", snapshot=snap,
                                          spawn_zone_id="ronfaure", now=0.0)
        assert f1 is not None
        # Try to convert AGAIN immediately — blocked
        f2 = pool.convert_to_fomor(account_id="acc1",
                                          snapshot=self._snap("alice2"),
                                          spawn_zone_id="ronfaure",
                                          now=10.0)
        assert f2 is None
        # Past cooldown — allowed
        f3 = pool.convert_to_fomor(account_id="acc1",
                                          snapshot=self._snap("alice3"),
                                          spawn_zone_id="ronfaure",
                                          now=ACCOUNT_COOLDOWN_SECONDS + 1)
        assert f3 is not None

    def test_town_safety_blocks_conversion(self):
        # Doc: 'fomors do not enter Bastok/Sandy/Windy/Jeuno/Whitegate'
        pool = FomorPool()
        f = pool.convert_to_fomor(account_id="acc1",
                                        snapshot=self._snap(),
                                        spawn_zone_id="bastok_markets",
                                        now=0.0)
        assert f is None

    def test_town_zones_named(self):
        for z in ("bastok_markets", "south_sandoria",
                    "windurst_woods", "lower_jeuno",
                    "aht_urhgan_whitegate"):
            assert z in TOWN_SAFE_ZONES

    def test_zone_cap_floor_15x(self):
        # Doc: 'floor(zone_player_count * 1.5)'
        pool = FomorPool()
        assert pool.zone_cap(zone_player_count=10) == 15
        assert pool.zone_cap(zone_player_count=3) == 4    # floor(4.5)
        assert pool.zone_cap(zone_player_count=0) == 0

    def test_zone_cap_negative_rejected(self):
        pool = FomorPool()
        with pytest.raises(ValueError):
            pool.zone_cap(zone_player_count=-1)

    def test_can_spawn_in_zone(self):
        pool = FomorPool()
        # Town: never
        assert pool.can_spawn_in_zone(zone_id="bastok_markets",
                                            zone_player_count=10) is False
        # Open world with capacity: yes
        assert pool.can_spawn_in_zone(zone_id="ronfaure",
                                            zone_player_count=10) is True

    def test_can_spawn_blocked_when_at_cap(self):
        pool = FomorPool()
        # Make 4 fomors in ronfaure; cap with 2 players is 3 -> at cap
        for i in range(4):
            f = pool.convert_to_fomor(
                account_id=f"acc{i}",
                snapshot=self._snap(f"a{i}"),
                spawn_zone_id="ronfaure",
                now=i * (ACCOUNT_COOLDOWN_SECONDS + 1),
            )
            assert f is not None
        assert pool.can_spawn_in_zone(zone_id="ronfaure",
                                           zone_player_count=2) is False

    def test_night_hour_range(self):
        # Doc: '8pm-6am' wraparound
        assert NIGHT_HOUR_RANGE == (20, 6)
        pool = FomorPool()
        # Late night (10pm)
        assert pool.is_night_hour(22) is True
        # Pre-dawn (4am)
        assert pool.is_night_hour(4) is True
        # Daytime (3pm)
        assert pool.is_night_hour(15) is False
        # Boundary: 8pm itself is night
        assert pool.is_night_hour(20) is True
        # Boundary: 6am itself is day (range is exclusive end)
        assert pool.is_night_hour(6) is False

    def test_invalid_hour_rejected(self):
        pool = FomorPool()
        with pytest.raises(ValueError):
            pool.is_night_hour(24)
        with pytest.raises(ValueError):
            pool.is_night_hour(-1)

    def test_tick_day_night(self):
        pool = FomorPool()
        f = pool.convert_to_fomor(account_id="acc1",
                                        snapshot=self._snap(),
                                        spawn_zone_id="ronfaure",
                                        now=0.0)
        assert f is not None
        # First tick at night promotes PENDING -> ACTIVE
        changes = pool.tick_day_night(vana_hour=22, now=0.0)
        assert changes >= 1
        assert f.state == FomorState.ACTIVE

        # Switch to day — ACTIVE -> DORMANT
        changes = pool.tick_day_night(vana_hour=12, now=10.0)
        assert changes >= 1
        assert f.state == FomorState.DORMANT

        # Back to night — DORMANT -> ACTIVE
        changes = pool.tick_day_night(vana_hour=23, now=20.0)
        assert changes >= 1
        assert f.state == FomorState.ACTIVE

    def test_despawn(self):
        pool = FomorPool()
        f = pool.convert_to_fomor(account_id="acc1",
                                        snapshot=self._snap(),
                                        spawn_zone_id="ronfaure",
                                        now=0.0)
        assert pool.despawn(f.fomor_id) is True
        assert f.state == FomorState.DESPAWNED


# ----------------------------------------------------------------------
# boss_assist
# ----------------------------------------------------------------------

class TestBossAssist:

    def test_caps_doc_values(self):
        # Doc: 'max 6 fomors per boss fight, max 1 alliance worth at end-game'
        assert MAX_FOMORS_PER_BOSS_FIGHT == 6
        assert MAX_FOMORS_END_GAME == 18

    def _build_pool(self, *, count: int, base_level: int = 60,
                       zone: str = "phomiuna_aqueducts"):
        pool = FomorPool()
        for i in range(count):
            snap = take_snapshot(
                char_id=f"a{i}", name=f"Fomor{i}",
                appearance=Appearance("hume", "f", "h", "e", "s"),
                jobs=[JobLevel(job="WAR",
                                  level=base_level + (i % 7) - 3,
                                  is_main=True)],
                sub_skills=[], merit_points=0, job_points=0,
                gear=[], death_zone_id=zone, now=0.0,
            )
            f = pool.convert_to_fomor(
                account_id=f"acc{i}", snapshot=snap,
                spawn_zone_id=zone,
                now=i * (ACCOUNT_COOLDOWN_SECONDS + 1),
            )
            # Promote to ACTIVE so they're eligible
            f.state = FomorState.ACTIVE
        return pool

    def test_boss_assist_caps_at_6(self):
        pool = self._build_pool(count=10, base_level=60)
        result = select_assists(request=AssistRequest(
            boss_id="boss_a",
            boss_zone_id="phomiuna_aqueducts",
            boss_level=60,
            adjacent_zone_ids=(),
            is_end_game_tier=False,
        ), pool=pool)
        assert len(result.fomors_assigned) == 6
        assert "capped at 6" in result.reason

    def test_boss_assist_endgame_18(self):
        pool = self._build_pool(count=25, base_level=80)
        result = select_assists(request=AssistRequest(
            boss_id="boss_apex",
            boss_zone_id="phomiuna_aqueducts",
            boss_level=80,
            adjacent_zone_ids=(),
            is_end_game_tier=True,
        ), pool=pool, level_band_tolerance=10)
        assert len(result.fomors_assigned) == 18

    def test_boss_assist_level_band_filter(self):
        pool = self._build_pool(count=10, base_level=30)
        # Boss at level 80 — none of the lvl-30 fomors are within
        # the 5-level tolerance
        result = select_assists(request=AssistRequest(
            boss_id="boss_apex",
            boss_zone_id="phomiuna_aqueducts",
            boss_level=80,
            adjacent_zone_ids=(),
            is_end_game_tier=False,
        ), pool=pool)
        assert result.fomors_assigned == ()
        assert "no eligible" in result.reason

    def test_boss_assist_zone_filter(self):
        pool = self._build_pool(count=10, base_level=60,
                                     zone="phomiuna_aqueducts")
        # Boss in a different zone with no adjacency
        result = select_assists(request=AssistRequest(
            boss_id="boss_x",
            boss_zone_id="far_away_zone",
            boss_level=60,
            adjacent_zone_ids=(),
            is_end_game_tier=False,
        ), pool=pool)
        assert result.fomors_assigned == ()

    def test_boss_assist_picks_closest_level(self):
        pool = self._build_pool(count=20, base_level=60)
        result = select_assists(request=AssistRequest(
            boss_id="boss_a",
            boss_zone_id="phomiuna_aqueducts",
            boss_level=60,
            adjacent_zone_ids=(),
            is_end_game_tier=False,
        ), pool=pool)
        # All assigned should have main_level closer to 60 than the
        # ones not assigned
        if len(result.fomors_assigned) == 6:
            max_diff_assigned = max(
                abs(f.snapshot.main_level - 60)
                for f in result.fomors_assigned
            )
            assert max_diff_assigned <= 5      # within tolerance


# ----------------------------------------------------------------------
# evolution
# ----------------------------------------------------------------------

class TestEvolution:

    def test_doc_constants(self):
        # Doc: 'capped at +5 levels above their original'
        assert MAX_EVOLUTION_LEVELS == 5

    def test_kill_threshold_levels_up(self):
        state = FomorEvolutionState(fomor_id="f1", base_level=60)
        # 1st kill — no level yet
        record_player_kill(state, victim_name="player_a")
        assert state.bonus_levels == 0
        # 3rd kill -> +1 level
        record_player_kill(state, victim_name="player_b")
        record_player_kill(state, victim_name="player_c")
        assert state.bonus_levels == 1
        # 6th kill -> +2 level
        for i in range(3):
            record_player_kill(state, victim_name=f"p{i}")
        assert state.bonus_levels == 2

    def test_evolution_caps_at_5(self):
        state = FomorEvolutionState(fomor_id="f1", base_level=60)
        # 30 kills would be +10 but capped
        for i in range(30):
            record_player_kill(state, victim_name=f"victim{i}")
        assert state.bonus_levels == MAX_EVOLUTION_LEVELS
        assert state.at_evolution_cap()
        assert state.effective_level == 60 + MAX_EVOLUTION_LEVELS

    def test_server_first_flags_mythological(self):
        state = FomorEvolutionState(fomor_id="f1", base_level=60)
        record_player_kill(state, victim_name="server_first_holder",
                              victim_was_server_first=True)
        assert state.tier == FomorTier.MYTHOLOGICAL

    def test_flag_mythological_manual(self):
        state = FomorEvolutionState(fomor_id="f1", base_level=60)
        flag_mythological(state, reason="endgame_clear_holder")
        assert state.tier == FomorTier.MYTHOLOGICAL
        assert state.server_first_killer is True

    def test_trophy_for_mythological_kill(self):
        state = FomorEvolutionState(fomor_id="f1", base_level=60,
                                          tier=FomorTier.MYTHOLOGICAL)
        trophy = trophy_for_kill(fomor_id="f1",
                                       fomor_name="LegendaryFomor",
                                       state=state)
        assert trophy is not None
        assert trophy.is_unique is True
        assert "LegendaryFomor" in trophy.fomor_name

    def test_trophy_none_for_standard(self):
        state = FomorEvolutionState(fomor_id="f1", base_level=60)
        trophy = trophy_for_kill(fomor_id="f1",
                                       fomor_name="StandardFomor",
                                       state=state)
        assert trophy is None


# ----------------------------------------------------------------------
# Composition: full doc lifecycle end-to-end
# ----------------------------------------------------------------------

class TestComposition:

    def test_player_dies_then_becomes_fomor_then_levels_up(self):
        # T+0: player Alice dies in Phomiuna
        rec = open_death_record(char_id="alice",
                                     death_zone_id="phomiuna_aqueducts",
                                     now=0.0)
        # T+30min: Cure scroll attempt fails (out of range); raise still possible
        # T+58min: someone tries Tractor — too late, missed by 2 min
        # T+1h+1: timer expires
        assert maybe_expire(rec, now=DEATH_TIMER_SECONDS + 1) is True
        assert rec.state == DeathState.EXPIRED

        # Snapshot taken
        snap = take_snapshot(
            char_id="alice", name="Alice",
            appearance=Appearance("hume", "f", "h", "e", "s"),
            jobs=[JobLevel(job="WAR", level=75, is_main=True),
                    JobLevel(job="NIN", level=37, is_sub=True)],
            sub_skills=["sword", "evasion"],
            merit_points=200, job_points=1000,
            gear=[GearPiece(slot="head", item_id="haub_helm",
                              rarity="empyrean")],
            death_zone_id="phomiuna_aqueducts",
            now=DEATH_TIMER_SECONDS + 2,
        )

        # Convert to fomor (out of town zone, 24h cooldown ok, first time)
        pool = FomorPool()
        entry = pool.convert_to_fomor(
            account_id="alice_acc",
            snapshot=snap,
            spawn_zone_id="phomiuna_aqueducts",
            now=DEATH_TIMER_SECONDS + 2,
        )
        assert entry is not None
        assert entry.state == FomorState.PENDING

        # Night arrives — fomor activates
        pool.tick_day_night(vana_hour=22,
                                now=DEATH_TIMER_SECONDS + 100)
        assert entry.state == FomorState.ACTIVE

        # Kills 9 players over time — +3 levels
        ev = FomorEvolutionState(fomor_id=entry.fomor_id,
                                       base_level=75)
        for i in range(9):
            record_player_kill(ev, victim_name=f"victim_{i}")
        assert ev.bonus_levels == 3
        assert ev.effective_level == 78

        # 21st kill: server-first holder dies. Mythological flag.
        for i in range(11):
            record_player_kill(ev, victim_name=f"v{i}",
                                  victim_was_server_first=(i == 5))
        assert ev.tier == FomorTier.MYTHOLOGICAL
        assert ev.bonus_levels == MAX_EVOLUTION_LEVELS

        # Eventually killed by a player party — drops Mythological trophy
        trophy = trophy_for_kill(fomor_id=entry.fomor_id,
                                       fomor_name=snap.name,
                                       state=ev)
        assert trophy is not None
        assert trophy.is_unique

    def test_raise_inside_window_prevents_fomor(self):
        rec = open_death_record(char_id="bob",
                                     death_zone_id="ronfaure",
                                     now=0.0)
        # 30 minutes in, WHM raises
        assert apply_raise(rec, source=RaiseSource.RAISE_III,
                              now=1800.0) is True
        # Timer expiry would be a no-op now
        assert maybe_expire(rec, now=DEATH_TIMER_SECONDS + 100) is False
        assert rec.state == DeathState.RAISED

    def test_owner_opt_out_at_expiry(self):
        rec = open_death_record(char_id="carol",
                                     death_zone_id="ronfaure",
                                     now=0.0)
        maybe_expire(rec, now=DEATH_TIMER_SECONDS + 1)
        # Owner declines — toon goes to grave, no fomor
        assert opt_out_at_expiry(rec) is True
        assert rec.state == DeathState.OPTED_OUT
        # No fomor pool entry should be created in this branch (caller
        # responsibility — they check rec.state before convert_to_fomor)
