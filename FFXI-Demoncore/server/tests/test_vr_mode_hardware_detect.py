"""Tests for vr_mode_hardware_detect."""
from __future__ import annotations

from server.vr_mode_hardware_detect import (
    HmdProfile, VrModeHardwareDetect, VrSettings,
)


def _profile(pid="bob"):
    return HmdProfile(
        player_id=pid, runtime="openxr",
        model="Quest 3", has_inside_out=True,
        has_hand_tracking=True,
    )


def _settings(pid="bob"):
    return VrSettings(
        player_id=pid, snap_turning_deg=45,
        vignette_on_motion=True, seated_recenter=False,
        ipd_mm=63.0,
    )


def test_register_hmd_happy():
    v = VrModeHardwareDetect()
    assert v.register_hmd(
        player_id="bob", profile=_profile(),
    ) is True


def test_register_hmd_blank_player():
    v = VrModeHardwareDetect()
    assert v.register_hmd(
        player_id="", profile=_profile(""),
    ) is False


def test_register_hmd_player_mismatch():
    v = VrModeHardwareDetect()
    out = v.register_hmd(
        player_id="bob", profile=_profile("cara"),
    )
    assert out is False


def test_register_hmd_blank_runtime():
    v = VrModeHardwareDetect()
    bad = HmdProfile(
        player_id="bob", runtime="",
        model="Quest 3", has_inside_out=True,
        has_hand_tracking=True,
    )
    assert v.register_hmd(
        player_id="bob", profile=bad,
    ) is False


def test_unregister_hmd():
    v = VrModeHardwareDetect()
    v.register_hmd(
        player_id="bob", profile=_profile(),
    )
    assert v.unregister_hmd(player_id="bob") is True
    assert v.has_hmd(player_id="bob") is False


def test_unregister_unknown():
    v = VrModeHardwareDetect()
    assert v.unregister_hmd(player_id="ghost") is False


def test_unregister_disables_vr():
    v = VrModeHardwareDetect()
    v.register_hmd(
        player_id="bob", profile=_profile(),
    )
    v.enable_vr(player_id="bob", settings=_settings())
    v.unregister_hmd(player_id="bob")
    assert v.is_vr_enabled(player_id="bob") is False


def test_enable_vr_requires_hmd():
    v = VrModeHardwareDetect()
    out = v.enable_vr(
        player_id="bob", settings=_settings(),
    )
    assert out is False


def test_enable_vr_happy():
    v = VrModeHardwareDetect()
    v.register_hmd(
        player_id="bob", profile=_profile(),
    )
    out = v.enable_vr(
        player_id="bob", settings=_settings(),
    )
    assert out is True


def test_enable_vr_player_mismatch():
    v = VrModeHardwareDetect()
    v.register_hmd(
        player_id="bob", profile=_profile(),
    )
    out = v.enable_vr(
        player_id="bob", settings=_settings("cara"),
    )
    assert out is False


def test_enable_vr_invalid_snap_deg():
    v = VrModeHardwareDetect()
    v.register_hmd(
        player_id="bob", profile=_profile(),
    )
    bad = VrSettings(
        player_id="bob", snap_turning_deg=33,
        vignette_on_motion=True, seated_recenter=False,
        ipd_mm=63.0,
    )
    assert v.enable_vr(
        player_id="bob", settings=bad,
    ) is False


def test_enable_vr_smooth_turning_allowed():
    v = VrModeHardwareDetect()
    v.register_hmd(
        player_id="bob", profile=_profile(),
    )
    smooth = VrSettings(
        player_id="bob", snap_turning_deg=0,
        vignette_on_motion=True, seated_recenter=False,
        ipd_mm=63.0,
    )
    assert v.enable_vr(
        player_id="bob", settings=smooth,
    ) is True


def test_enable_vr_ipd_below_min_blocked():
    v = VrModeHardwareDetect()
    v.register_hmd(
        player_id="bob", profile=_profile(),
    )
    bad = VrSettings(
        player_id="bob", snap_turning_deg=45,
        vignette_on_motion=True, seated_recenter=False,
        ipd_mm=50.0,
    )
    assert v.enable_vr(
        player_id="bob", settings=bad,
    ) is False


def test_enable_vr_ipd_above_max_blocked():
    v = VrModeHardwareDetect()
    v.register_hmd(
        player_id="bob", profile=_profile(),
    )
    bad = VrSettings(
        player_id="bob", snap_turning_deg=45,
        vignette_on_motion=True, seated_recenter=False,
        ipd_mm=80.0,
    )
    assert v.enable_vr(
        player_id="bob", settings=bad,
    ) is False


def test_disable_vr_happy():
    v = VrModeHardwareDetect()
    v.register_hmd(
        player_id="bob", profile=_profile(),
    )
    v.enable_vr(player_id="bob", settings=_settings())
    assert v.disable_vr(player_id="bob") is True


def test_disable_vr_unknown():
    v = VrModeHardwareDetect()
    assert v.disable_vr(player_id="bob") is False


def test_settings_for_returns_record():
    v = VrModeHardwareDetect()
    v.register_hmd(
        player_id="bob", profile=_profile(),
    )
    v.enable_vr(player_id="bob", settings=_settings())
    s = v.settings_for(player_id="bob")
    assert s is not None
    assert s.snap_turning_deg == 45


def test_settings_for_unknown_none():
    v = VrModeHardwareDetect()
    assert v.settings_for(player_id="ghost") is None


def test_total_counts():
    v = VrModeHardwareDetect()
    v.register_hmd(
        player_id="bob", profile=_profile("bob"),
    )
    v.register_hmd(
        player_id="cara", profile=_profile("cara"),
    )
    v.enable_vr(player_id="bob", settings=_settings("bob"))
    assert v.total_hmds() == 2
    assert v.total_vr_enabled() == 1
