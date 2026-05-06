"""AI behavior addon — installable boss/mob playbooks.

A boss's combat AI usually lives in code, hidden inside
the engine. This module turns it into an addon: a named
playbook that any entity can install. The same Lua
ecosystem that lets a player ship gearswap can let a
modder ship "Maat_Aggressive_v2" or "Sahagin_Tactical".

A behavior addon is a manifest declaring:
    - which entity classes it applies to (mob_family,
      job_id, or specific entity_id)
    - which game events it reacts to
    - a priority for resolving conflicts when multiple
      behaviors match the same entity

Installing a behavior on a mob marks that mob as "AI
controlled by addon X" — the engine consults the addon
for action selection rather than the default boss_critic.

This is the bridge between the lua_addon_loader (which
catalogs addons) and the runtime AI loop. The addon
itself lives in the Lua VM; this module is the binding.

Public surface
--------------
    BehaviorScope enum (FAMILY/JOB/ENTITY)
    BehaviorManifest dataclass (frozen)
    AiBehaviorRegistry
        .register(manifest) -> bool
        .install(entity_id, behavior_id) -> bool
        .uninstall(entity_id) -> bool
        .behavior_for(entity_id) -> Optional[str]
        .behaviors_matching(family, job, entity_id)
            -> list[BehaviorManifest]   (priority-ordered)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class BehaviorScope(str, enum.Enum):
    FAMILY = "family"     # all mobs in mob_family
    JOB = "job"           # all entities of a particular job
    ENTITY = "entity"     # this specific entity_id


@dataclasses.dataclass(frozen=True)
class BehaviorManifest:
    behavior_id: str
    name: str
    scope: BehaviorScope
    scope_target: str       # family name, job_id, or entity_id
    reacts_to: tuple[str, ...]   # event hook names
    priority: int           # higher wins on conflict


@dataclasses.dataclass
class AiBehaviorRegistry:
    _manifests: dict[str, BehaviorManifest] = dataclasses.field(
        default_factory=dict,
    )
    # entity_id → installed behavior_id
    _installed: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )

    def register(
        self, *, manifest: BehaviorManifest,
    ) -> bool:
        if not manifest.behavior_id or not manifest.name:
            return False
        if not manifest.scope_target:
            return False
        if not manifest.reacts_to:
            return False
        if manifest.behavior_id in self._manifests:
            return False
        self._manifests[manifest.behavior_id] = manifest
        return True

    def install(
        self, *, entity_id: str, behavior_id: str,
    ) -> bool:
        if not entity_id:
            return False
        if behavior_id not in self._manifests:
            return False
        self._installed[entity_id] = behavior_id
        return True

    def uninstall(self, *, entity_id: str) -> bool:
        if entity_id not in self._installed:
            return False
        del self._installed[entity_id]
        return True

    def behavior_for(
        self, *, entity_id: str,
    ) -> t.Optional[str]:
        return self._installed.get(entity_id)

    def behaviors_matching(
        self, *, family: str = "", job: str = "",
        entity_id: str = "",
    ) -> list[BehaviorManifest]:
        out: list[BehaviorManifest] = []
        for m in self._manifests.values():
            if m.scope == BehaviorScope.FAMILY and m.scope_target == family:
                out.append(m)
            elif m.scope == BehaviorScope.JOB and m.scope_target == job:
                out.append(m)
            elif m.scope == BehaviorScope.ENTITY and m.scope_target == entity_id:
                out.append(m)
        # sort by priority descending — highest wins
        out.sort(key=lambda m: m.priority, reverse=True)
        return out

    def manifest(
        self, *, behavior_id: str,
    ) -> t.Optional[BehaviorManifest]:
        return self._manifests.get(behavior_id)

    def total_registered(self) -> int:
        return len(self._manifests)

    def total_installed(self) -> int:
        return len(self._installed)


__all__ = [
    "BehaviorScope", "BehaviorManifest", "AiBehaviorRegistry",
]
