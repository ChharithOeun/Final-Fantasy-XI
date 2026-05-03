"""Colonization Reives — WoTG-era zone liberation waves.

A separate reive layer from wildskeeper_reives. These are
multi-stage colonization waves that liberate WoTG outdoor zones
from beastman occupation. Each zone has 3-4 wave nodes; players
clear waves to install BIVOUAC NPCs (mobile camps that provide
buffs, vendors, and spawn-back points).

Once all wave nodes in a zone are cleared, the zone is in
"colonized" state — it stays beastman-free until reset, NPC
shops unlock, faster mob respawn for non-beastman fauna.

Public surface
--------------
    WotgZone enum (5 sample WotG outdoor zones)
    ReiveWaveStatus enum
    BivouacNpc dataclass
    ColonizationZoneState
        .complete_wave(wave_index, contributors)
        .progress -> tuple[(wave_index, status), ...]
        .colonized -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


WAVES_PER_ZONE = 3


class WotgZone(str, enum.Enum):
    EAST_RONFAURE_S = "east_ronfaure_s"
    JUGNER_FOREST_S = "jugner_forest_s"
    BATALLIA_DOWNS_S = "batallia_downs_s"
    SAUROMUGUE_S = "sauromugue_champaign_s"
    GRAUBERG = "grauberg_s"


class ReiveWaveStatus(str, enum.Enum):
    DORMANT = "dormant"
    ACTIVE = "active"
    CLEARED = "cleared"


@dataclasses.dataclass(frozen=True)
class BivouacNpc:
    npc_id: str
    label: str
    services: tuple[str, ...]      # vendor / repair / homepoint / etc.


# Each zone has a fixed Bivouac NPC roster. Each successive wave
# clear unlocks the next NPC's services.
_BIVOUAC_BY_ZONE: dict[WotgZone, tuple[BivouacNpc, ...]] = {
    WotgZone.EAST_RONFAURE_S: (
        BivouacNpc("ronfaure_supply_quartermaster",
                    "Supply Quartermaster",
                    services=("vendor_supplies",)),
        BivouacNpc("ronfaure_armorer",
                    "Bivouac Armorer",
                    services=("repair_equipment",)),
        BivouacNpc("ronfaure_homepoint",
                    "Mobile Home Point",
                    services=("home_point",)),
    ),
    WotgZone.JUGNER_FOREST_S: (
        BivouacNpc("jugner_field_medic",
                    "Field Medic",
                    services=("vendor_potions",)),
        BivouacNpc("jugner_quartermaster",
                    "Field Quartermaster",
                    services=("vendor_supplies",)),
        BivouacNpc("jugner_homepoint",
                    "Mobile Home Point",
                    services=("home_point",)),
    ),
    WotgZone.BATALLIA_DOWNS_S: (
        BivouacNpc("batallia_scout",
                    "Bivouac Scout",
                    services=("zone_intel",)),
        BivouacNpc("batallia_quartermaster",
                    "Field Quartermaster",
                    services=("vendor_supplies",)),
        BivouacNpc("batallia_homepoint",
                    "Mobile Home Point",
                    services=("home_point",)),
    ),
    WotgZone.SAUROMUGUE_S: (
        BivouacNpc("sauromugue_field_medic",
                    "Field Medic",
                    services=("vendor_potions",)),
        BivouacNpc("sauromugue_armorer",
                    "Bivouac Armorer",
                    services=("repair_equipment",)),
        BivouacNpc("sauromugue_homepoint",
                    "Mobile Home Point",
                    services=("home_point",)),
    ),
    WotgZone.GRAUBERG: (
        BivouacNpc("grauberg_quartermaster",
                    "Field Quartermaster",
                    services=("vendor_supplies",)),
        BivouacNpc("grauberg_field_medic",
                    "Field Medic",
                    services=("vendor_potions",)),
        BivouacNpc("grauberg_homepoint",
                    "Mobile Home Point",
                    services=("home_point",)),
    ),
}


def bivouac_roster(zone: WotgZone) -> tuple[BivouacNpc, ...]:
    return _BIVOUAC_BY_ZONE.get(zone, ())


@dataclasses.dataclass(frozen=True)
class WaveResult:
    accepted: bool
    wave_index: int = 0
    contributors: tuple[str, ...] = ()
    bivouac_unlocked: t.Optional[BivouacNpc] = None
    zone_now_colonized: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class ColonizationZoneState:
    zone: WotgZone
    wave_status: list[ReiveWaveStatus] = dataclasses.field(
        default_factory=lambda: [ReiveWaveStatus.DORMANT] * WAVES_PER_ZONE,
    )
    contributors_per_wave: list[list[str]] = dataclasses.field(
        default_factory=lambda: [[] for _ in range(WAVES_PER_ZONE)],
    )
    unlocked_bivouacs: list[BivouacNpc] = dataclasses.field(
        default_factory=list,
    )

    def begin_wave(self, *, wave_index: int) -> bool:
        if not (0 <= wave_index < WAVES_PER_ZONE):
            return False
        if self.wave_status[wave_index] != ReiveWaveStatus.DORMANT:
            return False
        # Sequential — must clear earlier waves first
        for i in range(wave_index):
            if self.wave_status[i] != ReiveWaveStatus.CLEARED:
                return False
        self.wave_status[wave_index] = ReiveWaveStatus.ACTIVE
        return True

    def complete_wave(
        self, *, wave_index: int, contributors: t.Iterable[str],
    ) -> WaveResult:
        if not (0 <= wave_index < WAVES_PER_ZONE):
            return WaveResult(False, reason="wave OOR")
        if self.wave_status[wave_index] != ReiveWaveStatus.ACTIVE:
            return WaveResult(False, reason="wave not active")
        contribs = tuple(contributors)
        self.contributors_per_wave[wave_index].extend(contribs)
        self.wave_status[wave_index] = ReiveWaveStatus.CLEARED
        # Unlock corresponding Bivouac NPC
        roster = bivouac_roster(self.zone)
        unlocked: t.Optional[BivouacNpc] = None
        if wave_index < len(roster):
            unlocked = roster[wave_index]
            self.unlocked_bivouacs.append(unlocked)
        return WaveResult(
            accepted=True, wave_index=wave_index,
            contributors=contribs,
            bivouac_unlocked=unlocked,
            zone_now_colonized=self.colonized,
        )

    @property
    def colonized(self) -> bool:
        return all(
            s == ReiveWaveStatus.CLEARED for s in self.wave_status
        )

    @property
    def progress(self) -> tuple[tuple[int, ReiveWaveStatus], ...]:
        return tuple(enumerate(self.wave_status))


__all__ = [
    "WAVES_PER_ZONE",
    "WotgZone", "ReiveWaveStatus", "BivouacNpc",
    "WaveResult", "ColonizationZoneState",
    "bivouac_roster",
]
