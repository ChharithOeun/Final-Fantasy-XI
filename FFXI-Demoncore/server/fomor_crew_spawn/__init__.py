"""Fomor crew spawn — turns abducted/drowned crew into world mobs.

The missing_ship_registry plots a CREW_FATE per ship at file
time ("abducted" / "drowned_to_fomor" / "drowned" / "missing").
This module converts those fate strings into actual SPAWN
INTENTS that the world spawner can realize as fomor-variant
entities scattered through underwater zones.

Mapping:
  abducted          -> spawns a captive in the abductor's
                       primary_zone_id (typically a wreckage
                       graveyard or abyss trench, depending on
                       which fleet did the abduction). Captive
                       can be RESCUED — see abduction_recovery_quest.
  drowned_to_fomor  -> spawns a FOMOR_<original_race> mob at
                       the wreck's zone. They're hostile and
                       NM-patterned (named, +tier-2 stats).
  drowned           -> no spawn (they're just dead).
  missing           -> no spawn (lore-only).

Each crew_fate token gets a deterministic spawn_id derived
from (ship_id, fate_index). That keeps reruns idempotent —
re-emitting the same crew won't double-spawn.

Public surface
--------------
    SpawnKind enum    CAPTIVE / FOMOR_MOB / NONE
    CrewSpawnIntent dataclass
    FomorCrewSpawn
        .emit_intents(ship_id, crew_fate, wreck_zone_id,
                      pirate_zone_id, original_race)
        .intents_for_ship(ship_id)
        .mark_resolved(spawn_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SpawnKind(str, enum.Enum):
    NONE = "none"
    CAPTIVE = "captive"
    FOMOR_MOB = "fomor_mob"


@dataclasses.dataclass
class CrewSpawnIntent:
    spawn_id: str
    ship_id: str
    fate_index: int
    kind: SpawnKind
    zone_id: str
    fomor_race: t.Optional[str] = None    # "fomor_hume", "fomor_galka", ...
    resolved: bool = False


# fates that produce a spawn intent
_FATES_THAT_SPAWN = ("abducted", "drowned_to_fomor")


@dataclasses.dataclass
class FomorCrewSpawn:
    _intents: dict[str, CrewSpawnIntent] = dataclasses.field(
        default_factory=dict,
    )
    _by_ship: dict[str, list[str]] = dataclasses.field(
        default_factory=dict,
    )

    @staticmethod
    def _spawn_id(ship_id: str, fate_index: int) -> str:
        return f"{ship_id}#crew{fate_index:03d}"

    def emit_intents(
        self, *, ship_id: str,
        crew_fate: tuple[str, ...],
        wreck_zone_id: str,
        pirate_zone_id: str,
        original_race: str,
    ) -> tuple[CrewSpawnIntent, ...]:
        if not ship_id or not original_race:
            return ()
        emitted: list[CrewSpawnIntent] = []
        for idx, fate in enumerate(crew_fate):
            if fate not in _FATES_THAT_SPAWN:
                continue
            sid = self._spawn_id(ship_id, idx)
            if sid in self._intents:
                # idempotent — already emitted
                continue
            if fate == "abducted":
                intent = CrewSpawnIntent(
                    spawn_id=sid,
                    ship_id=ship_id,
                    fate_index=idx,
                    kind=SpawnKind.CAPTIVE,
                    zone_id=pirate_zone_id,
                )
            else:  # drowned_to_fomor
                intent = CrewSpawnIntent(
                    spawn_id=sid,
                    ship_id=ship_id,
                    fate_index=idx,
                    kind=SpawnKind.FOMOR_MOB,
                    zone_id=wreck_zone_id,
                    fomor_race=f"fomor_{original_race}",
                )
            self._intents[sid] = intent
            self._by_ship.setdefault(ship_id, []).append(sid)
            emitted.append(intent)
        return tuple(emitted)

    def intents_for_ship(
        self, *, ship_id: str,
    ) -> tuple[CrewSpawnIntent, ...]:
        ids = self._by_ship.get(ship_id, [])
        return tuple(self._intents[i] for i in ids)

    def mark_resolved(self, *, spawn_id: str) -> bool:
        intent = self._intents.get(spawn_id)
        if intent is None:
            return False
        intent.resolved = True
        return True

    def open_intents(
        self, *, kind: t.Optional[SpawnKind] = None,
    ) -> tuple[CrewSpawnIntent, ...]:
        return tuple(
            i for i in self._intents.values()
            if not i.resolved
            and (kind is None or i.kind == kind)
        )

    def total_intents(self) -> int:
        return len(self._intents)


__all__ = [
    "SpawnKind", "CrewSpawnIntent", "FomorCrewSpawn",
]
