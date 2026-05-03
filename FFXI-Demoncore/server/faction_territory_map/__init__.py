"""Faction territory map — region control + capture.

The world is divided into REGIONS (zone subdivisions). Each
region has a controlling FACTION and a control STRENGTH. Capture
rises when the controlling faction's forces hold ground; falls
when enemy presence builds. Below a flip-threshold the region
goes CONTESTED, and a successful CONTEST_WIN flips control.

Wires into:
* siege_system — large-scale capture campaigns
* conquest_tally — nation conquest points feed regional control
* npc_economy — controlled-faction prices in town markets
* mob_migration — hostile factions push mobs out of newly held land

Public surface
--------------
    RegionStatus enum
    RegionControl dataclass
    CaptureAttemptResult dataclass
    FactionTerritoryMap
        .register_region(region_id, zone_id, controlling_faction)
        .build_strength(region_id, faction, amount)
        .erode_strength(region_id, faction, amount)
        .capture_attempt(region_id, by_faction) -> Result
        .controlled_by(faction_id) -> regions
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Defaults.
INITIAL_CONTROL_STRENGTH = 100
CONTEST_THRESHOLD = 30           # below this = CONTESTED
CAPTURE_THRESHOLD = 50           # challenger needs this strength
                                 # AND defender must be CONTESTED
MAX_STRENGTH = 200


class RegionStatus(str, enum.Enum):
    HELD = "held"
    CONTESTED = "contested"
    NEUTRAL = "neutral"      # no controlling faction
    OCCUPIED = "occupied"    # captured but garrison thin


@dataclasses.dataclass
class RegionControl:
    region_id: str
    zone_id: str
    controlling_faction: t.Optional[str]
    control_strength: int = INITIAL_CONTROL_STRENGTH
    challenger_strength: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )
    status: RegionStatus = RegionStatus.HELD
    last_change_at_seconds: float = 0.0
    capture_count: int = 0


@dataclasses.dataclass(frozen=True)
class CaptureAttemptResult:
    accepted: bool
    region_id: str
    new_controller: t.Optional[str] = None
    old_controller: t.Optional[str] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class FactionTerritoryMap:
    contest_threshold: int = CONTEST_THRESHOLD
    capture_threshold: int = CAPTURE_THRESHOLD
    max_strength: int = MAX_STRENGTH
    _regions: dict[str, RegionControl] = dataclasses.field(
        default_factory=dict,
    )

    def register_region(
        self, *, region_id: str, zone_id: str,
        controlling_faction: t.Optional[str] = None,
        initial_strength: t.Optional[int] = None,
    ) -> t.Optional[RegionControl]:
        if region_id in self._regions:
            return None
        rc = RegionControl(
            region_id=region_id, zone_id=zone_id,
            controlling_faction=controlling_faction,
            control_strength=(
                initial_strength
                if initial_strength is not None
                else INITIAL_CONTROL_STRENGTH
            ),
            status=(
                RegionStatus.HELD
                if controlling_faction is not None
                else RegionStatus.NEUTRAL
            ),
        )
        self._regions[region_id] = rc
        return rc

    def region(
        self, region_id: str,
    ) -> t.Optional[RegionControl]:
        return self._regions.get(region_id)

    def _refresh_status(self, rc: RegionControl) -> None:
        if rc.controlling_faction is None:
            rc.status = RegionStatus.NEUTRAL
            return
        if rc.control_strength < self.contest_threshold:
            rc.status = RegionStatus.CONTESTED
            return
        if rc.control_strength < INITIAL_CONTROL_STRENGTH * 0.6:
            rc.status = RegionStatus.OCCUPIED
            return
        rc.status = RegionStatus.HELD

    def build_strength(
        self, *, region_id: str, faction: str,
        amount: int, now_seconds: float = 0.0,
    ) -> bool:
        rc = self._regions.get(region_id)
        if rc is None or amount <= 0:
            return False
        if faction == rc.controlling_faction:
            rc.control_strength = min(
                self.max_strength,
                rc.control_strength + amount,
            )
        else:
            rc.challenger_strength[faction] = min(
                self.max_strength,
                rc.challenger_strength.get(faction, 0)
                + amount,
            )
        rc.last_change_at_seconds = now_seconds
        self._refresh_status(rc)
        return True

    def erode_strength(
        self, *, region_id: str, faction: str,
        amount: int, now_seconds: float = 0.0,
    ) -> bool:
        rc = self._regions.get(region_id)
        if rc is None or amount <= 0:
            return False
        if faction == rc.controlling_faction:
            rc.control_strength = max(
                0, rc.control_strength - amount,
            )
        else:
            current = rc.challenger_strength.get(faction, 0)
            new_val = max(0, current - amount)
            if new_val == 0 and current > 0:
                del rc.challenger_strength[faction]
            else:
                rc.challenger_strength[faction] = new_val
        rc.last_change_at_seconds = now_seconds
        self._refresh_status(rc)
        return True

    def capture_attempt(
        self, *, region_id: str, by_faction: str,
        now_seconds: float = 0.0,
    ) -> CaptureAttemptResult:
        rc = self._regions.get(region_id)
        if rc is None:
            return CaptureAttemptResult(
                False, region_id=region_id,
                reason="no such region",
            )
        if by_faction == rc.controlling_faction:
            return CaptureAttemptResult(
                False, region_id=region_id,
                reason="already controlling",
            )
        challenger = rc.challenger_strength.get(by_faction, 0)
        if challenger < self.capture_threshold:
            return CaptureAttemptResult(
                False, region_id=region_id,
                reason="insufficient challenger strength",
            )
        # Defender must be contested OR neutral
        if (
            rc.controlling_faction is not None
            and rc.status not in (
                RegionStatus.CONTESTED,
                RegionStatus.NEUTRAL,
            )
        ):
            return CaptureAttemptResult(
                False, region_id=region_id,
                reason="defender too strong",
            )
        old = rc.controlling_faction
        rc.controlling_faction = by_faction
        rc.control_strength = challenger
        rc.challenger_strength.pop(by_faction, None)
        rc.capture_count += 1
        rc.last_change_at_seconds = now_seconds
        self._refresh_status(rc)
        return CaptureAttemptResult(
            accepted=True, region_id=region_id,
            new_controller=by_faction,
            old_controller=old,
        )

    def controlled_by(
        self, faction_id: str,
    ) -> tuple[RegionControl, ...]:
        return tuple(
            rc for rc in self._regions.values()
            if rc.controlling_faction == faction_id
        )

    def total_regions(self) -> int:
        return len(self._regions)


__all__ = [
    "INITIAL_CONTROL_STRENGTH",
    "CONTEST_THRESHOLD", "CAPTURE_THRESHOLD",
    "MAX_STRENGTH",
    "RegionStatus", "RegionControl",
    "CaptureAttemptResult",
    "FactionTerritoryMap",
]
