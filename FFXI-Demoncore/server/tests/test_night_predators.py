"""Tests for night_predators."""
from __future__ import annotations

from server.night_predators import (
    ActivityKind,
    MoonPhase,
    NightPredatorRegistry,
    TimeOfDay,
)


def _setup():
    r = NightPredatorRegistry()
    r.register_predator(
        predator_id="dire_bat", zone_id="ronfaure",
        kind=ActivityKind.NOCTURNAL, weight=10,
    )
    r.register_predator(
        predator_id="meadow_rabbit", zone_id="ronfaure",
        kind=ActivityKind.DIURNAL, weight=5,
    )
    r.register_predator(
        predator_id="twilight_moth", zone_id="ronfaure",
        kind=ActivityKind.CREPUSCULAR, weight=3,
    )
    r.register_predator(
        predator_id="moon_wolf", zone_id="ronfaure",
        kind=ActivityKind.LUNAR_FULL, weight=20,
    )
    r.register_predator(
        predator_id="shadow_serpent", zone_id="ronfaure",
        kind=ActivityKind.LUNAR_NEW, weight=20,
    )
    r.register_predator(
        predator_id="rats", zone_id="ronfaure",
        kind=ActivityKind.ALWAYS, weight=1,
    )
    return r


def test_register_predator_happy():
    r = _setup()
    assert r.total_predators() == 6


def test_register_blank_id_blocked():
    r = NightPredatorRegistry()
    out = r.register_predator(
        predator_id="", zone_id="z",
        kind=ActivityKind.NOCTURNAL,
    )
    assert out is False


def test_register_blank_zone_blocked():
    r = NightPredatorRegistry()
    out = r.register_predator(
        predator_id="x", zone_id="",
        kind=ActivityKind.NOCTURNAL,
    )
    assert out is False


def test_zero_weight_blocked():
    r = NightPredatorRegistry()
    out = r.register_predator(
        predator_id="x", zone_id="z",
        kind=ActivityKind.NOCTURNAL, weight=0,
    )
    assert out is False


def test_duplicate_predator_blocked():
    r = _setup()
    again = r.register_predator(
        predator_id="dire_bat", zone_id="z",
        kind=ActivityKind.NOCTURNAL,
    )
    assert again is False


def test_diurnal_at_day():
    r = _setup()
    out = r.eligible_in(
        zone_id="ronfaure", time_of_day=TimeOfDay.DAY,
        moon_phase=MoonPhase.WAXING,
    )
    ids = {p.predator_id for p in out}
    assert "meadow_rabbit" in ids
    assert "dire_bat" not in ids


def test_nocturnal_at_night():
    r = _setup()
    out = r.eligible_in(
        zone_id="ronfaure", time_of_day=TimeOfDay.NIGHT,
        moon_phase=MoonPhase.WAXING,
    )
    ids = {p.predator_id for p in out}
    assert "dire_bat" in ids
    assert "meadow_rabbit" not in ids


def test_crepuscular_at_dusk():
    r = _setup()
    out = r.eligible_in(
        zone_id="ronfaure", time_of_day=TimeOfDay.DUSK,
        moon_phase=MoonPhase.WAXING,
    )
    ids = {p.predator_id for p in out}
    assert "twilight_moth" in ids


def test_crepuscular_at_dawn():
    r = _setup()
    out = r.eligible_in(
        zone_id="ronfaure", time_of_day=TimeOfDay.DAWN,
        moon_phase=MoonPhase.WAXING,
    )
    ids = {p.predator_id for p in out}
    assert "twilight_moth" in ids


def test_lunar_full_only_at_full_night():
    r = _setup()
    full_night = r.eligible_in(
        zone_id="ronfaure", time_of_day=TimeOfDay.NIGHT,
        moon_phase=MoonPhase.FULL,
    )
    assert "moon_wolf" in {p.predator_id for p in full_night}

    full_day = r.eligible_in(
        zone_id="ronfaure", time_of_day=TimeOfDay.DAY,
        moon_phase=MoonPhase.FULL,
    )
    assert "moon_wolf" not in {p.predator_id for p in full_day}


def test_lunar_new_only_at_new_night():
    r = _setup()
    new_night = r.eligible_in(
        zone_id="ronfaure", time_of_day=TimeOfDay.NIGHT,
        moon_phase=MoonPhase.NEW,
    )
    assert "shadow_serpent" in {
        p.predator_id for p in new_night
    }


def test_always_active_anytime():
    r = _setup()
    for tod in TimeOfDay:
        for mp in MoonPhase:
            out = r.eligible_in(
                zone_id="ronfaure", time_of_day=tod,
                moon_phase=mp,
            )
            ids = {p.predator_id for p in out}
            assert "rats" in ids


def test_zone_isolation():
    r = _setup()
    r.register_predator(
        predator_id="other_bat", zone_id="other",
        kind=ActivityKind.NOCTURNAL, weight=1,
    )
    out = r.eligible_in(
        zone_id="ronfaure", time_of_day=TimeOfDay.NIGHT,
        moon_phase=MoonPhase.WAXING,
    )
    assert "other_bat" not in {p.predator_id for p in out}


def test_ranked_pool_descending_weight():
    r = _setup()
    out = r.ranked_pool(
        zone_id="ronfaure", time_of_day=TimeOfDay.NIGHT,
        moon_phase=MoonPhase.FULL,
    )
    weights = [w for (_, w) in out]
    assert weights == sorted(weights, reverse=True)


def test_ranked_pool_returns_weight_pairs():
    r = _setup()
    out = r.ranked_pool(
        zone_id="ronfaure", time_of_day=TimeOfDay.DAY,
        moon_phase=MoonPhase.WAXING,
    )
    # rats (1) + meadow_rabbit (5)
    assert len(out) == 2
    assert all(isinstance(w, int) for (_, w) in out)


def test_lunar_full_at_day_inactive():
    r = _setup()
    out = r.eligible_in(
        zone_id="ronfaure", time_of_day=TimeOfDay.DAY,
        moon_phase=MoonPhase.FULL,
    )
    ids = {p.predator_id for p in out}
    assert "moon_wolf" not in ids


def test_six_activity_kinds():
    assert len(list(ActivityKind)) == 6


def test_four_time_of_day():
    assert len(list(TimeOfDay)) == 4


def test_four_moon_phases():
    assert len(list(MoonPhase)) == 4
