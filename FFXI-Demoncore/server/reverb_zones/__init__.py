"""Reverb zones — per-zone (and per-volume-within-zone)
acoustic profile.

Sound has a place. The slap of a hammer in Cid's smelter
is not the same hammer in the open Markets above it. The
choir in Sandy Cathedral rings for four full seconds; the
same voice in an alleyway gets back to you in one. Reverb
is what makes a space feel like a space, and getting it
wrong is one of the cheapest tells that a game world is a
game world.

This module owns the acoustic profile per zone and per
sub-volume. A zone has a default profile (Bastok Markets
== mid-air open with parallel-wall flutter); a sub-volume
inside the zone can override it (Cid's workshop within
the Markets is a small smelter, RT60 0.4s, high frequencies
damped at 3 kHz). When the listener crosses a volume
boundary the profile crossfades — couples to zone_handoff
to avoid audible pops.

The module owns *profile selection*. The actual reverb DSP
runs in the audio engine (Wwise / FMOD / UE5 MetaSounds);
this module hands them the parameters.

Public surface
--------------
    ReverbProfile dataclass (frozen)
    ReverbVolume dataclass (frozen)
    ReverbZoneSystem
    populate_default_profiles
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class ReverbProfile:
    profile_id: str
    rt60_seconds: float
    early_reflections_ms: float
    diffusion: float           # 0..1
    damping_freq_hz: float
    high_cut_freq_hz: float
    low_cut_freq_hz: float
    room_size_m3: float
    wetness: float             # 0..1


@dataclasses.dataclass(frozen=True)
class ReverbVolume:
    volume_id: str
    zone_id: str
    bounds_min: tuple[float, float, float]
    bounds_max: tuple[float, float, float]
    profile_id: str

    def contains(
        self, pos: tuple[float, float, float],
    ) -> bool:
        x, y, z = pos
        mn = self.bounds_min
        mx = self.bounds_max
        return (
            mn[0] <= x <= mx[0]
            and mn[1] <= y <= mx[1]
            and mn[2] <= z <= mx[2]
        )

    def volume_m3(self) -> float:
        dx = self.bounds_max[0] - self.bounds_min[0]
        dy = self.bounds_max[1] - self.bounds_min[1]
        dz = self.bounds_max[2] - self.bounds_min[2]
        return abs(dx * dy * dz)


def _validate_profile(p: ReverbProfile) -> None:
    if not p.profile_id:
        raise ValueError("profile_id required")
    if p.rt60_seconds < 0:
        raise ValueError("rt60_seconds must be >= 0")
    if p.early_reflections_ms < 0:
        raise ValueError(
            "early_reflections_ms must be >= 0",
        )
    if not (0.0 <= p.diffusion <= 1.0):
        raise ValueError("diffusion must be in 0..1")
    if not (0.0 <= p.wetness <= 1.0):
        raise ValueError("wetness must be in 0..1")
    if p.high_cut_freq_hz <= 0:
        raise ValueError("high_cut_freq_hz must be > 0")
    if p.low_cut_freq_hz < 0:
        raise ValueError("low_cut_freq_hz must be >= 0")
    if p.high_cut_freq_hz <= p.low_cut_freq_hz:
        raise ValueError(
            "high_cut_freq_hz must exceed low_cut_freq_hz",
        )
    if p.room_size_m3 < 0:
        raise ValueError("room_size_m3 must be >= 0")
    if p.damping_freq_hz < 0:
        raise ValueError("damping_freq_hz must be >= 0")


def _interp(a: float, b: float, t_: float) -> float:
    return a + (b - a) * t_


def interpolate_profiles(
    a: ReverbProfile, b: ReverbProfile, t_: float,
) -> ReverbProfile:
    """Smoothly blend two profiles (for zone-handoff)."""
    if t_ < 0.0 or t_ > 1.0:
        raise ValueError("t must be in 0..1")
    return ReverbProfile(
        profile_id=f"interp_{a.profile_id}_{b.profile_id}_{t_:.2f}",
        rt60_seconds=_interp(a.rt60_seconds, b.rt60_seconds, t_),
        early_reflections_ms=_interp(
            a.early_reflections_ms, b.early_reflections_ms, t_,
        ),
        diffusion=_interp(a.diffusion, b.diffusion, t_),
        damping_freq_hz=_interp(
            a.damping_freq_hz, b.damping_freq_hz, t_,
        ),
        high_cut_freq_hz=_interp(
            a.high_cut_freq_hz, b.high_cut_freq_hz, t_,
        ),
        low_cut_freq_hz=_interp(
            a.low_cut_freq_hz, b.low_cut_freq_hz, t_,
        ),
        room_size_m3=_interp(a.room_size_m3, b.room_size_m3, t_),
        wetness=_interp(a.wetness, b.wetness, t_),
    )


@dataclasses.dataclass
class ReverbZoneSystem:
    _profiles: dict[str, ReverbProfile] = dataclasses.field(
        default_factory=dict,
    )
    # zone_id -> default profile_id
    _zone_default: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )
    _volumes: dict[str, ReverbVolume] = dataclasses.field(
        default_factory=dict,
    )
    _by_zone_volumes: dict[
        str, list[str],
    ] = dataclasses.field(default_factory=dict)

    # ---------------------------------------------- profile
    def register_profile(self, profile: ReverbProfile) -> None:
        _validate_profile(profile)
        if profile.profile_id in self._profiles:
            raise ValueError(
                f"duplicate profile_id: {profile.profile_id}",
            )
        self._profiles[profile.profile_id] = profile

    def get_profile(self, profile_id: str) -> ReverbProfile:
        if profile_id not in self._profiles:
            raise KeyError(
                f"unknown profile_id: {profile_id}",
            )
        return self._profiles[profile_id]

    def profile_count(self) -> int:
        return len(self._profiles)

    def set_zone_default(
        self, zone_id: str, profile_id: str,
    ) -> None:
        if profile_id not in self._profiles:
            raise KeyError(
                f"unknown profile_id: {profile_id}",
            )
        self._zone_default[zone_id] = profile_id

    # ---------------------------------------------- volume
    def register_volume(
        self,
        volume_id: str,
        zone_id: str,
        bounds_min: tuple[float, float, float],
        bounds_max: tuple[float, float, float],
        profile_id: str,
    ) -> None:
        if not volume_id:
            raise ValueError("volume_id required")
        if not zone_id:
            raise ValueError("zone_id required")
        if profile_id not in self._profiles:
            raise KeyError(
                f"unknown profile_id: {profile_id}",
            )
        if volume_id in self._volumes:
            raise ValueError(
                f"duplicate volume_id: {volume_id}",
            )
        # bounds sanity
        for i in range(3):
            if bounds_min[i] > bounds_max[i]:
                raise ValueError(
                    "bounds_min must be <= bounds_max on all axes",
                )
        vol = ReverbVolume(
            volume_id=volume_id,
            zone_id=zone_id,
            bounds_min=bounds_min,
            bounds_max=bounds_max,
            profile_id=profile_id,
        )
        self._volumes[volume_id] = vol
        self._by_zone_volumes.setdefault(
            zone_id, [],
        ).append(volume_id)

    def get_volume(self, volume_id: str) -> ReverbVolume:
        if volume_id not in self._volumes:
            raise KeyError(
                f"unknown volume_id: {volume_id}",
            )
        return self._volumes[volume_id]

    def volume_count(self) -> int:
        return len(self._volumes)

    # ---------------------------------------------- queries
    def profile_at(
        self,
        zone_id: str,
        listener_pos: tuple[float, float, float],
    ) -> ReverbProfile:
        # Most-specific volume wins; ties broken by smallest
        # volume (the room inside the room).
        candidates: list[ReverbVolume] = []
        for vid in self._by_zone_volumes.get(zone_id, []):
            vol = self._volumes[vid]
            if vol.contains(listener_pos):
                candidates.append(vol)
        if candidates:
            candidates.sort(
                key=lambda v: (v.volume_m3(), v.volume_id),
            )
            return self._profiles[candidates[0].profile_id]
        # Fall back to zone default.
        if zone_id in self._zone_default:
            return self._profiles[self._zone_default[zone_id]]
        raise KeyError(
            f"no profile for zone={zone_id} at pos {listener_pos}",
        )

    def profiles_for_zone(
        self, zone_id: str,
    ) -> tuple[ReverbProfile, ...]:
        seen: list[str] = []
        if zone_id in self._zone_default:
            seen.append(self._zone_default[zone_id])
        for vid in self._by_zone_volumes.get(zone_id, []):
            pid = self._volumes[vid].profile_id
            if pid not in seen:
                seen.append(pid)
        return tuple(self._profiles[p] for p in seen)

    def interpolate_at_boundary(
        self, zone_a: str, zone_b: str, t_: float,
    ) -> ReverbProfile:
        if zone_a not in self._zone_default:
            raise KeyError(
                f"no default profile for zone {zone_a}",
            )
        if zone_b not in self._zone_default:
            raise KeyError(
                f"no default profile for zone {zone_b}",
            )
        pa = self._profiles[self._zone_default[zone_a]]
        pb = self._profiles[self._zone_default[zone_b]]
        return interpolate_profiles(pa, pb, t_)


# ---------------------------------------------------------
# Default catalog — 10+ canonical profiles.
# ---------------------------------------------------------

# (profile_id, rt60_s, early_ms, diffusion, damping_hz,
#  high_cut_hz, low_cut_hz, room_m3, wetness, default_zone)
_DEFAULT_PROFILES: tuple[
    tuple[
        str, float, float, float, float, float, float,
        float, float, str,
    ],
    ...,
] = (
    ("BASTOK_MINES_TUNNEL",
        2.3, 35.0, 0.85, 8000.0,
        12000.0, 60.0, 4500.0, 0.65,
        "bastok_mines"),
    ("BASTOK_MARKETS_OPEN",
        1.1, 18.0, 0.55, 12000.0,
        16000.0, 80.0, 9000.0, 0.40,
        "bastok_markets"),
    ("CIDS_WORKSHOP",
        0.4, 8.0, 0.30, 3000.0,
        14000.0, 120.0, 60.0, 0.35,
        ""),
    ("SANDY_CATHEDRAL",
        4.2, 55.0, 0.95, 6000.0,
        14000.0, 50.0, 12000.0, 0.75,
        "north_sandoria"),
    ("SANDY_ALLEYWAY",
        1.6, 22.0, 0.65, 9000.0,
        14000.0, 90.0, 800.0, 0.50,
        "south_sandoria"),
    ("WINDY_GLASS_HALL",
        0.9, 14.0, 0.70, 14000.0,
        18000.0, 120.0, 1200.0, 0.42,
        "windurst_walls"),
    ("KONSCHTAT_OPEN_PLAIN",
        0.2, 5.0, 0.10, 18000.0,
        18000.0, 40.0, 999999.0, 0.10,
        "konschtat_highlands"),
    ("CAVE_SUBTERRANEAN",
        3.5, 45.0, 0.90, 4500.0,
        12000.0, 50.0, 8000.0, 0.70,
        "dangruf_wadi"),
    ("DUNGEON_GARLAIGE",
        2.7, 38.0, 0.80, 5500.0,
        12000.0, 55.0, 6500.0, 0.62,
        ""),
    ("FOREST_DENSE",
        0.3, 6.0, 0.20, 6500.0,
        14000.0, 60.0, 3500.0, 0.18,
        "jugner_forest"),
    ("WINDY_WOODS_PAVILION",
        1.0, 16.0, 0.55, 12000.0,
        16000.0, 70.0, 2200.0, 0.40,
        "windurst_woods"),
    ("NORG_PIRATE_HALL",
        1.4, 20.0, 0.60, 9000.0,
        14000.0, 80.0, 1800.0, 0.45,
        "norg"),
)


def populate_default_profiles(sys: ReverbZoneSystem) -> int:
    n = 0
    for row in _DEFAULT_PROFILES:
        (pid, rt, er, diff, damp, hc, lc, room,
         wet, zone) = row
        sys.register_profile(ReverbProfile(
            profile_id=pid,
            rt60_seconds=rt,
            early_reflections_ms=er,
            diffusion=diff,
            damping_freq_hz=damp,
            high_cut_freq_hz=hc,
            low_cut_freq_hz=lc,
            room_size_m3=room,
            wetness=wet,
        ))
        n += 1
        if zone:
            sys.set_zone_default(zone, pid)
    # Also register a CIDS_WORKSHOP volume inside Bastok
    # Markets so the canonical example works out of the box.
    sys.register_volume(
        volume_id="cids_workshop_inner",
        zone_id="bastok_markets",
        bounds_min=(140.0, 0.0, -10.0),
        bounds_max=(150.0, 4.0, 0.0),
        profile_id="CIDS_WORKSHOP",
    )
    return n


__all__ = [
    "ReverbProfile",
    "ReverbVolume",
    "ReverbZoneSystem",
    "interpolate_profiles",
    "populate_default_profiles",
]
