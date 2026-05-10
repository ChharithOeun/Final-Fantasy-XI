"""Tests for ambient_soundscape."""
from __future__ import annotations

import pytest

from server.ambient_soundscape import (
    AmbientLayer,
    AmbientSoundscapeSystem,
    LayerKind,
    OneShotSchedule,
    SoundscapeBed,
    TimeOfDay,
    Weather,
    populate_default_beds,
)


def _layer(
    lid="l1",
    kind=LayerKind.MID_TEXTURE,
    sample="a.ogg",
    gain=-12.0,
    pan=0.0,
    loop=True,
    attenuation=0.0,
    interval_min=0.0,
    interval_max=0.0,
):
    return AmbientLayer(
        layer_id=lid,
        sample_uri=sample,
        gain_db=gain,
        kind=kind,
        loop=loop,
        interval_s_min=interval_min,
        interval_s_max=interval_max,
        pan_lr=pan,
        distance_attenuation_m=attenuation,
    )


def _bed(
    bid="b1",
    zid="z",
    layers=None,
    tod=TimeOfDay.ALL,
    weather=Weather.ALL,
):
    return SoundscapeBed(
        bed_id=bid,
        zone_id=zid,
        layers=tuple(layers) if layers else (_layer(),),
        time_of_day_variant=tod,
        weather_variant=weather,
    )


# ---- enums ----

def test_layer_kind_count_five():
    assert len(list(LayerKind)) == 5


def test_time_of_day_includes_all():
    assert TimeOfDay.ALL in list(TimeOfDay)


def test_weather_includes_six_plus_all():
    assert len(list(Weather)) >= 7


# ---- register ----

def test_register_bed():
    s = AmbientSoundscapeSystem()
    s.register_bed(_bed())
    assert s.bed_count() == 1


def test_register_empty_bed_id():
    s = AmbientSoundscapeSystem()
    with pytest.raises(ValueError):
        s.register_bed(_bed(bid=""))


def test_register_empty_zone():
    s = AmbientSoundscapeSystem()
    with pytest.raises(ValueError):
        s.register_bed(_bed(zid=""))


def test_register_no_layers():
    s = AmbientSoundscapeSystem()
    with pytest.raises(ValueError):
        s.register_bed(SoundscapeBed(
            bed_id="b", zone_id="z",
            layers=(),
            time_of_day_variant=TimeOfDay.ALL,
            weather_variant=Weather.ALL,
        ))


def test_register_duplicate_bed():
    s = AmbientSoundscapeSystem()
    s.register_bed(_bed())
    with pytest.raises(ValueError):
        s.register_bed(_bed())


def test_register_layer_empty_id():
    s = AmbientSoundscapeSystem()
    with pytest.raises(ValueError):
        s.register_bed(_bed(layers=[_layer(lid="")]))


def test_register_layer_empty_sample():
    s = AmbientSoundscapeSystem()
    with pytest.raises(ValueError):
        s.register_bed(_bed(layers=[_layer(sample="")]))


def test_register_layer_gain_too_loud():
    s = AmbientSoundscapeSystem()
    with pytest.raises(ValueError):
        s.register_bed(_bed(layers=[_layer(gain=20.0)]))


def test_register_layer_gain_too_quiet():
    s = AmbientSoundscapeSystem()
    with pytest.raises(ValueError):
        s.register_bed(_bed(layers=[_layer(gain=-99.0)]))


def test_register_layer_pan_out_of_range():
    s = AmbientSoundscapeSystem()
    with pytest.raises(ValueError):
        s.register_bed(_bed(layers=[_layer(pan=2.0)]))


def test_register_layer_negative_attenuation():
    s = AmbientSoundscapeSystem()
    with pytest.raises(ValueError):
        s.register_bed(_bed(layers=[
            _layer(kind=LayerKind.SPATIAL_POINT,
                   attenuation=-1.0),
        ]))


def test_register_one_shot_zero_interval():
    s = AmbientSoundscapeSystem()
    with pytest.raises(ValueError):
        s.register_bed(_bed(layers=[
            _layer(
                kind=LayerKind.ONE_SHOT, loop=False,
                interval_min=0.0, interval_max=10.0,
            ),
        ]))


def test_register_one_shot_max_below_min():
    s = AmbientSoundscapeSystem()
    with pytest.raises(ValueError):
        s.register_bed(_bed(layers=[
            _layer(
                kind=LayerKind.ONE_SHOT, loop=False,
                interval_min=20.0, interval_max=10.0,
            ),
        ]))


def test_get_bed_unknown():
    s = AmbientSoundscapeSystem()
    with pytest.raises(KeyError):
        s.get_bed("missing")


# ---- bed_for ----

def test_bed_for_exact_match():
    s = AmbientSoundscapeSystem()
    s.register_bed(_bed(
        bid="day_clear", tod=TimeOfDay.DAY,
        weather=Weather.CLEAR,
    ))
    b = s.bed_for("z", TimeOfDay.DAY, Weather.CLEAR)
    assert b.bed_id == "day_clear"


def test_bed_for_falls_back_to_all():
    s = AmbientSoundscapeSystem()
    s.register_bed(_bed(
        bid="any", tod=TimeOfDay.ALL, weather=Weather.ALL,
    ))
    b = s.bed_for("z", TimeOfDay.NIGHT, Weather.RAIN)
    assert b.bed_id == "any"


def test_bed_for_prefers_specific_over_all():
    s = AmbientSoundscapeSystem()
    s.register_bed(_bed(
        bid="any", tod=TimeOfDay.ALL, weather=Weather.ALL,
    ))
    s.register_bed(_bed(
        bid="rain", tod=TimeOfDay.ALL, weather=Weather.RAIN,
    ))
    b = s.bed_for("z", TimeOfDay.NIGHT, Weather.RAIN)
    assert b.bed_id == "rain"


def test_bed_for_prefers_weather_over_tod():
    s = AmbientSoundscapeSystem()
    s.register_bed(_bed(
        bid="rain", tod=TimeOfDay.ALL, weather=Weather.RAIN,
    ))
    s.register_bed(_bed(
        bid="night", tod=TimeOfDay.NIGHT, weather=Weather.ALL,
    ))
    b = s.bed_for("z", TimeOfDay.NIGHT, Weather.RAIN)
    # weather match scores 8, tod match scores 4
    assert b.bed_id == "rain"


def test_bed_for_unknown_zone():
    s = AmbientSoundscapeSystem()
    with pytest.raises(KeyError):
        s.bed_for("nope", TimeOfDay.DAY, Weather.CLEAR)


# ---- playlist_for ----

def test_playlist_for_returns_all_layers():
    s = AmbientSoundscapeSystem()
    s.register_bed(_bed(
        layers=[
            _layer(lid="a", kind=LayerKind.LOW_FREQ_HUM),
            _layer(lid="b", kind=LayerKind.MID_TEXTURE),
        ],
    ))
    pl = s.playlist_for(
        "z", (0.0, 0.0, 0.0),
        TimeOfDay.DAY, Weather.CLEAR,
    )
    layer_ids = {lid for lid, g in pl}
    assert layer_ids == {"a", "b"}


def test_playlist_for_spatial_attenuates():
    s = AmbientSoundscapeSystem()
    s.register_bed(_bed(
        layers=[_layer(
            lid="anvil", kind=LayerKind.SPATIAL_POINT,
            gain=0.0, attenuation=10.0,
        )],
    ))
    # listener 5m from source -> 50% along attenuation curve
    pl = s.playlist_for(
        "z", (5.0, 0.0, 0.0),
        TimeOfDay.DAY, Weather.CLEAR,
    )
    assert len(pl) == 1
    layer_id, gain = pl[0]
    assert layer_id == "anvil"
    # 0 - 60 * 0.5 = -30
    assert gain == pytest.approx(-30.0)


def test_playlist_for_spatial_culled_at_radius():
    s = AmbientSoundscapeSystem()
    s.register_bed(_bed(
        layers=[
            _layer(
                lid="anvil", kind=LayerKind.SPATIAL_POINT,
                gain=0.0, attenuation=10.0,
            ),
            _layer(
                lid="hum", kind=LayerKind.LOW_FREQ_HUM,
                gain=-10.0,
            ),
        ],
    ))
    pl = s.playlist_for(
        "z", (50.0, 0.0, 0.0),
        TimeOfDay.DAY, Weather.CLEAR,
    )
    layer_ids = {lid for lid, g in pl}
    # Anvil is silent (out of range); hum still present.
    assert "hum" in layer_ids
    assert "anvil" not in layer_ids


# ---- schedule_next_one_shot ----

def test_schedule_next_one_shot_returns_eta():
    s = AmbientSoundscapeSystem()
    s.register_bed(_bed(
        layers=[_layer(
            lid="cry", kind=LayerKind.ONE_SHOT, loop=False,
            interval_min=10.0, interval_max=30.0,
        )],
    ))
    sched = s.schedule_next_one_shot("z", 100.0)
    assert len(sched) == 1
    assert isinstance(sched[0], OneShotSchedule)
    # midpoint is 20
    assert sched[0].eta_seconds == pytest.approx(120.0)


def test_schedule_next_one_shot_no_one_shots():
    s = AmbientSoundscapeSystem()
    s.register_bed(_bed(
        layers=[_layer(kind=LayerKind.MID_TEXTURE)],
    ))
    sched = s.schedule_next_one_shot("z", 0.0)
    assert sched == ()


def test_schedule_next_one_shot_unknown_zone_empty():
    s = AmbientSoundscapeSystem()
    sched = s.schedule_next_one_shot("nope", 0.0)
    assert sched == ()


# ---- beds_with_weather ----

def test_beds_with_weather_filters():
    s = AmbientSoundscapeSystem()
    s.register_bed(_bed(bid="a", weather=Weather.RAIN))
    s.register_bed(_bed(bid="b", weather=Weather.CLEAR))
    rain = s.beds_with_weather(Weather.RAIN)
    assert len(rain) == 1
    assert rain[0].bed_id == "a"


def test_beds_with_weather_empty():
    s = AmbientSoundscapeSystem()
    assert s.beds_with_weather(Weather.SANDSTORM) == ()


# ---- beds_for_zone ----

def test_beds_for_zone_returns_all():
    s = AmbientSoundscapeSystem()
    s.register_bed(_bed(bid="a", tod=TimeOfDay.DAY))
    s.register_bed(_bed(bid="b", tod=TimeOfDay.NIGHT))
    beds = s.beds_for_zone("z")
    assert len(beds) == 2


# ---- default beds ----

def test_default_beds_count_at_least_twelve():
    s = AmbientSoundscapeSystem()
    n = populate_default_beds(s)
    assert n >= 12


def test_default_beds_bastok_mines_present():
    s = AmbientSoundscapeSystem()
    populate_default_beds(s)
    b = s.bed_for("bastok_mines", TimeOfDay.DAY, Weather.CLEAR)
    assert b.zone_id == "bastok_mines"


def test_default_beds_bastok_markets_day_vs_night():
    s = AmbientSoundscapeSystem()
    populate_default_beds(s)
    day = s.bed_for(
        "bastok_markets", TimeOfDay.DAY, Weather.CLEAR,
    )
    night = s.bed_for(
        "bastok_markets", TimeOfDay.NIGHT, Weather.CLEAR,
    )
    assert day.bed_id != night.bed_id


def test_default_beds_pashhow_rain_specific():
    s = AmbientSoundscapeSystem()
    populate_default_beds(s)
    b = s.bed_for(
        "pashhow_marshlands", TimeOfDay.DAY, Weather.RAIN,
    )
    assert b.bed_id == "bed_pashhow_rain"


def test_default_beds_norg_includes_waves():
    s = AmbientSoundscapeSystem()
    populate_default_beds(s)
    b = s.bed_for("norg", TimeOfDay.DAY, Weather.CLEAR)
    assert any("wave" in l.sample_uri for l in b.layers)


def test_default_beds_konschtat_chocobo_oneshot():
    s = AmbientSoundscapeSystem()
    populate_default_beds(s)
    b = s.bed_for(
        "konschtat_highlands", TimeOfDay.DAY, Weather.CLEAR,
    )
    chocos = [
        l for l in b.layers
        if l.kind == LayerKind.ONE_SHOT
        and "chocobo" in l.sample_uri
    ]
    assert len(chocos) == 1


def test_default_beds_eldieme_organ():
    s = AmbientSoundscapeSystem()
    populate_default_beds(s)
    b = s.bed_for(
        "the_eldieme_necropolis",
        TimeOfDay.DAY, Weather.CLEAR,
    )
    assert any(
        l.kind == LayerKind.SPATIAL_POINT
        and "organ" in l.sample_uri for l in b.layers
    )


def test_default_beds_qufim_seagull_oneshot():
    s = AmbientSoundscapeSystem()
    populate_default_beds(s)
    b = s.bed_for("qufim_island", TimeOfDay.DAY, Weather.CLEAR)
    assert any(
        l.kind == LayerKind.ONE_SHOT
        and "seagull" in l.sample_uri for l in b.layers
    )


def test_default_beds_tahrongi_falcon():
    s = AmbientSoundscapeSystem()
    populate_default_beds(s)
    b = s.bed_for(
        "tahrongi_canyon", TimeOfDay.DAY, Weather.CLEAR,
    )
    falcons = [
        l for l in b.layers if "falcon" in l.sample_uri
    ]
    assert len(falcons) == 1


def test_default_beds_one_shot_schedules_well_formed():
    s = AmbientSoundscapeSystem()
    populate_default_beds(s)
    sched = s.schedule_next_one_shot(
        "bastok_markets", 0.0,
        TimeOfDay.DAY, Weather.CLEAR,
    )
    assert len(sched) >= 1
    for entry in sched:
        assert entry.eta_seconds > 0.0
