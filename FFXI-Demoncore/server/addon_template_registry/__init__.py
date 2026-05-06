"""Addon template registry — catalog of shapes the forge renders.

The lua_addon_forge can produce many flavors of addon, not
just GearSwap. Each shape declares:
    - which AddonIntentSpec fields it requires
    - which client API surface(s) it targets (Windower /
      Ashita / Both)
    - the renderer function that turns spec → lua code

This registry is the catalog. The forge UI consults it to
know "what kinds of addon can I make today?" and to
validate that the player's intent is actually expressible
in the chosen template.

Catalog of addon shapes worth AI-forging (per Tart's
ask "what other addons could we do that with"):

    GEARSWAP        — equip the right set on event
    BUFFMONITOR     — track party-buff timers + alerts
    DPSMETER        — rolling damage meter per player
    AUTOEXEC        — list of commands at startup
    CANCEL          — drop named buffs on demand
    HEALBOT         — cure-priority logic
    RECAST          — JA/spell timer display
    DISTANCE        — range-to-target display
    TH_TRACKER      — Treasure Hunter proc state
    EXTRADATA       — per-mob stat dump
    SPELLCAST       — cast-time/target predicate router
    AUTO_TRANSLATE  — phrase shortcut expander

Public surface
--------------
    AddonShape enum
    ApiTarget enum (WINDOWER/ASHITA/BOTH)
    TemplateManifest dataclass (frozen)
    AddonTemplateRegistry
        .register(manifest) -> bool
        .lookup(shape) -> Optional[TemplateManifest]
        .shapes_for_target(target) -> list[AddonShape]
        .required_fields(shape) -> tuple[str, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class AddonShape(str, enum.Enum):
    GEARSWAP = "gearswap"
    BUFFMONITOR = "buffmonitor"
    DPSMETER = "dpsmeter"
    AUTOEXEC = "autoexec"
    CANCEL = "cancel"
    HEALBOT = "healbot"
    RECAST = "recast"
    DISTANCE = "distance"
    TH_TRACKER = "th_tracker"
    EXTRADATA = "extradata"
    SPELLCAST = "spellcast"
    AUTO_TRANSLATE = "auto_translate"


class ApiTarget(str, enum.Enum):
    WINDOWER = "windower"
    ASHITA = "ashita"
    BOTH = "both"      # rendered against the compat layer


@dataclasses.dataclass(frozen=True)
class TemplateManifest:
    shape: AddonShape
    name: str
    api_target: ApiTarget
    # Names of AddonIntentSpec fields the renderer needs.
    # The forge validates that all are populated before
    # invoking the renderer.
    required_fields: tuple[str, ...]
    # Optional spec fields that enrich output but aren't
    # required.
    optional_fields: tuple[str, ...]
    # Short human description shown in the UI.
    description: str


@dataclasses.dataclass
class AddonTemplateRegistry:
    _manifests: dict[AddonShape, TemplateManifest] = \
        dataclasses.field(default_factory=dict)

    def register(
        self, *, manifest: TemplateManifest,
    ) -> bool:
        if not manifest.name:
            return False
        if manifest.shape in self._manifests:
            return False
        if not manifest.required_fields:
            # Every template needs at least one required
            # field to be meaningful. AUTOEXEC needs a
            # command list; GEARSWAP needs a job; etc.
            return False
        self._manifests[manifest.shape] = manifest
        return True

    def lookup(
        self, *, shape: AddonShape,
    ) -> t.Optional[TemplateManifest]:
        return self._manifests.get(shape)

    def shapes_for_target(
        self, *, target: ApiTarget,
    ) -> list[AddonShape]:
        out: list[AddonShape] = []
        for shape, m in self._manifests.items():
            if target == ApiTarget.BOTH:
                out.append(shape)
            elif m.api_target == target:
                out.append(shape)
            elif m.api_target == ApiTarget.BOTH:
                # BOTH-targeted templates work for either
                out.append(shape)
        return out

    def required_fields(
        self, *, shape: AddonShape,
    ) -> tuple[str, ...]:
        m = self._manifests.get(shape)
        if m is None:
            return ()
        return m.required_fields

    def total_registered(self) -> int:
        return len(self._manifests)


def default_registry() -> AddonTemplateRegistry:
    """Bootstrap a registry with the canonical addon shapes."""
    r = AddonTemplateRegistry()
    r.register(manifest=TemplateManifest(
        shape=AddonShape.GEARSWAP, name="GearSwap",
        api_target=ApiTarget.BOTH,
        required_fields=("job", "weapon_sets"),
        optional_fields=(
            "idle_set", "offense_modes", "food_item",
            "lockstyle_pallet", "macro_book", "macro_set",
            "default_offense_mode",
        ),
        description="Equip the right set on combat events.",
    ))
    r.register(manifest=TemplateManifest(
        shape=AddonShape.BUFFMONITOR, name="BuffMonitor",
        api_target=ApiTarget.BOTH,
        required_fields=("addon_id",),
        optional_fields=("spell_rules",),
        description="Track party buff timers and alert on expiry.",
    ))
    r.register(manifest=TemplateManifest(
        shape=AddonShape.DPSMETER, name="DPSMeter",
        api_target=ApiTarget.BOTH,
        required_fields=("addon_id",),
        optional_fields=(),
        description="Rolling DPS / DTPS / HPS per party member.",
    ))
    r.register(manifest=TemplateManifest(
        shape=AddonShape.AUTOEXEC, name="AutoExec",
        api_target=ApiTarget.BOTH,
        required_fields=("addon_id",),
        optional_fields=(),
        description="Run a list of commands on addon load.",
    ))
    r.register(manifest=TemplateManifest(
        shape=AddonShape.HEALBOT, name="Healbot",
        api_target=ApiTarget.BOTH,
        required_fields=("addon_id", "spell_rules"),
        optional_fields=(),
        description="Auto-cure based on party HP thresholds.",
    ))
    r.register(manifest=TemplateManifest(
        shape=AddonShape.CANCEL, name="Cancel",
        api_target=ApiTarget.BOTH,
        required_fields=("addon_id",),
        optional_fields=(),
        description="Drop named buffs on /cancel command.",
    ))
    r.register(manifest=TemplateManifest(
        shape=AddonShape.RECAST, name="Recast",
        api_target=ApiTarget.BOTH,
        required_fields=("addon_id",),
        optional_fields=(),
        description="JA / spell recast timer display.",
    ))
    r.register(manifest=TemplateManifest(
        shape=AddonShape.DISTANCE, name="Distance",
        api_target=ApiTarget.BOTH,
        required_fields=("addon_id",),
        optional_fields=(),
        description="Live range-to-target indicator.",
    ))
    r.register(manifest=TemplateManifest(
        shape=AddonShape.TH_TRACKER, name="THTracker",
        api_target=ApiTarget.BOTH,
        required_fields=("addon_id",),
        optional_fields=(),
        description="Treasure Hunter proc state tracker.",
    ))
    r.register(manifest=TemplateManifest(
        shape=AddonShape.EXTRADATA, name="ExtraData",
        api_target=ApiTarget.BOTH,
        required_fields=("addon_id",),
        optional_fields=(),
        description="Per-mob hidden-stat dump.",
    ))
    r.register(manifest=TemplateManifest(
        shape=AddonShape.SPELLCAST, name="SpellCast",
        api_target=ApiTarget.WINDOWER,
        required_fields=("job", "spell_rules"),
        optional_fields=(),
        description="Pre-GearSwap-style spell event router.",
    ))
    r.register(manifest=TemplateManifest(
        shape=AddonShape.AUTO_TRANSLATE, name="AutoTranslate",
        api_target=ApiTarget.BOTH,
        required_fields=("addon_id",),
        optional_fields=(),
        description="Expand chat shortcuts to {auto-translate} tokens.",
    ))
    return r


__all__ = [
    "AddonShape", "ApiTarget", "TemplateManifest",
    "AddonTemplateRegistry", "default_registry",
]
