"""Builder UI state — live state of the GearSwap builder.

The top-level orchestrator. Tracks which spec is being
edited, which set is currently active in the builder
panel, what the validation status looks like right now,
and what the user has unsaved.

Hooks for the UI to subscribe to:
    on_field_change       any field modified
    on_validation_change  errors/warnings list updated
    on_active_set_change  user clicked a different set tab
    on_save_draft         user pressed Save Draft

Drives the live diff between "current spec" and "last
saved draft" — so the UI can show the unsaved-changes
asterisk on a tab.

Public surface
--------------
    BuilderMode enum (FRESH/EDITING/PREVIEW)
    DraftState dataclass (mutable)
    BuilderUIState
        .open_fresh(player_id, addon_id, job) -> bool
        .open_existing(player_id, spec) -> bool
        .set_active_set(player_id, set_name) -> bool
        .assign_slot(player_id, set_name, slot, item_id)
            -> bool
        .save_draft(player_id) -> bool
        .has_unsaved_changes(player_id) -> bool
        .current_validation(player_id) -> Optional[SpecValidationResult]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.addon_intent_spec import (
    AddonIntentSpec, GearSetEntry, SpecValidationResult,
    validate,
)
from server.gear_slot_filter import Slot


class BuilderMode(str, enum.Enum):
    FRESH = "fresh"           # blank spec, just opened
    EDITING = "editing"       # actively editing
    PREVIEW = "preview"       # rendering preview mode


@dataclasses.dataclass
class DraftState:
    player_id: str
    spec: AddonIntentSpec
    last_saved_spec: t.Optional[AddonIntentSpec]
    active_set_name: str
    mode: BuilderMode
    last_validation: t.Optional[SpecValidationResult]


def _spec_equal(
    a: t.Optional[AddonIntentSpec],
    b: t.Optional[AddonIntentSpec],
) -> bool:
    """Cheap spec equality for the unsaved-changes diff."""
    if a is None or b is None:
        return a is None and b is None
    if a.addon_id != b.addon_id or a.job != b.job:
        return False
    if a.food_item != b.food_item:
        return False
    if a.lockstyle_pallet != b.lockstyle_pallet:
        return False
    if a.macro_book != b.macro_book or a.macro_set != b.macro_set:
        return False
    if a.default_offense_mode != b.default_offense_mode:
        return False
    if set(a.weapon_sets.keys()) != set(b.weapon_sets.keys()):
        return False
    for name, ea in a.weapon_sets.items():
        eb = b.weapon_sets[name]
        if ea.slot_to_item != eb.slot_to_item:
            return False
    if (a.idle_set is None) != (b.idle_set is None):
        return False
    if (a.idle_set is not None and
            a.idle_set.slot_to_item != b.idle_set.slot_to_item):
        return False
    return True


@dataclasses.dataclass
class BuilderUIState:
    _drafts: dict[str, DraftState] = dataclasses.field(
        default_factory=dict,
    )

    def open_fresh(
        self, *, player_id: str, addon_id: str, job: str,
    ) -> bool:
        if not player_id or not addon_id or not job:
            return False
        spec = AddonIntentSpec(addon_id=addon_id, job=job)
        self._drafts[player_id] = DraftState(
            player_id=player_id, spec=spec,
            last_saved_spec=None,
            active_set_name="",
            mode=BuilderMode.FRESH,
            last_validation=validate(spec),
        )
        return True

    def open_existing(
        self, *, player_id: str, spec: AddonIntentSpec,
    ) -> bool:
        if not player_id or not spec.addon_id:
            return False
        # snapshot for the unsaved-diff baseline
        baseline = AddonIntentSpec(
            addon_id=spec.addon_id, job=spec.job,
            weapon_sets=dict(spec.weapon_sets),
            offense_modes=list(spec.offense_modes),
            idle_set=spec.idle_set,
            food_item=spec.food_item,
            lockstyle_pallet=spec.lockstyle_pallet,
            macro_book=spec.macro_book,
            macro_set=spec.macro_set,
            spell_rules=list(spec.spell_rules),
            default_offense_mode=spec.default_offense_mode,
        )
        self._drafts[player_id] = DraftState(
            player_id=player_id, spec=spec,
            last_saved_spec=baseline,
            active_set_name="",
            mode=BuilderMode.EDITING,
            last_validation=validate(spec),
        )
        return True

    def set_active_set(
        self, *, player_id: str, set_name: str,
    ) -> bool:
        d = self._drafts.get(player_id)
        if d is None:
            return False
        # The set must exist in the spec OR be a hint to
        # create a new one. Empty strings are blocked.
        if not set_name:
            return False
        d.active_set_name = set_name
        return True

    def assign_slot(
        self, *, player_id: str, set_name: str,
        slot: Slot, item_id: str,
    ) -> bool:
        d = self._drafts.get(player_id)
        if d is None or not set_name or not item_id:
            return False
        # Either find the existing set or create a new one.
        existing = d.spec.weapon_sets.get(set_name)
        if existing is None:
            new = GearSetEntry(
                set_name=set_name,
                slot_to_item={slot.value: item_id},
            )
            d.spec.weapon_sets[set_name] = new
        else:
            new_items = dict(existing.slot_to_item)
            new_items[slot.value] = item_id
            d.spec.weapon_sets[set_name] = GearSetEntry(
                set_name=set_name,
                slot_to_item=new_items,
            )
        d.mode = BuilderMode.EDITING
        d.last_validation = validate(d.spec)
        return True

    def set_default_offense_mode(
        self, *, player_id: str, mode_name: str,
    ) -> bool:
        d = self._drafts.get(player_id)
        if d is None:
            return False
        d.spec.default_offense_mode = mode_name
        d.last_validation = validate(d.spec)
        return True

    def save_draft(self, *, player_id: str) -> bool:
        d = self._drafts.get(player_id)
        if d is None:
            return False
        # snapshot baseline
        d.last_saved_spec = AddonIntentSpec(
            addon_id=d.spec.addon_id, job=d.spec.job,
            weapon_sets=dict(d.spec.weapon_sets),
            offense_modes=list(d.spec.offense_modes),
            idle_set=d.spec.idle_set,
            food_item=d.spec.food_item,
            lockstyle_pallet=d.spec.lockstyle_pallet,
            macro_book=d.spec.macro_book,
            macro_set=d.spec.macro_set,
            spell_rules=list(d.spec.spell_rules),
            default_offense_mode=d.spec.default_offense_mode,
        )
        return True

    def has_unsaved_changes(
        self, *, player_id: str,
    ) -> bool:
        d = self._drafts.get(player_id)
        if d is None:
            return False
        return not _spec_equal(d.spec, d.last_saved_spec)

    def current_validation(
        self, *, player_id: str,
    ) -> t.Optional[SpecValidationResult]:
        d = self._drafts.get(player_id)
        if d is None:
            return None
        return d.last_validation

    def current_spec(
        self, *, player_id: str,
    ) -> t.Optional[AddonIntentSpec]:
        d = self._drafts.get(player_id)
        if d is None:
            return None
        return d.spec

    def mode(
        self, *, player_id: str,
    ) -> t.Optional[BuilderMode]:
        d = self._drafts.get(player_id)
        if d is None:
            return None
        return d.mode

    def total_drafts(self) -> int:
        return len(self._drafts)


__all__ = [
    "BuilderMode", "DraftState", "BuilderUIState",
]
