"""Gear augment picker — curated augment selection helper.

Tart's RDM.lua reference uses augments heavily — every
high-tier item has lines like:

    main={ name="Crocea Mors", augments={'Path: C',}}
    back={ name="Sucellos's Cape", augments={
        'INT+10','MND+20','"Mag. Atk. Bns."+10',
        'Mag. Acc+20 /Mag. Dmg.+20','Phys. dmg. taken-10%'
    }}

These augment strings are the OTHER spelling-error
nightmare. The picker fixes it the same way: per-item
curated lists of legal augments, presented as a multi-
select. The player checks the boxes; the picker emits
the canonical strings. No typos possible.

Augment paths (Path: A/B/C/D) are mutually exclusive —
selecting one auto-deselects the others. Free augments
(INT+10, MND+20) can stack up to the item's max_augment_count.

Public surface
--------------
    AugmentTier enum (PATH/STAT/ELEMENT/SPECIAL)
    AugmentChoice dataclass (frozen)
    AugmentSchema dataclass (frozen) — per-item legal options
    AugmentSelection dataclass (mutable) — current picks
    GearAugmentPicker
        .define_schema(item_id, schema) -> bool
        .start_selection(item_id) -> Optional[AugmentSelection]
        .toggle(selection, choice_id) -> bool
        .render(selection) -> tuple[str, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class AugmentTier(str, enum.Enum):
    PATH = "path"           # Path: A/B/C/D — mutually exclusive
    STAT = "stat"           # INT+10, MND+20, etc. — additive
    ELEMENT = "element"     # +Fire dmg, +Water res — additive
    SPECIAL = "special"     # Phys. dmg. taken-10%, etc.


@dataclasses.dataclass(frozen=True)
class AugmentChoice:
    choice_id: str
    tier: AugmentTier
    canonical_string: str   # what gets emitted into the lua


@dataclasses.dataclass(frozen=True)
class AugmentSchema:
    item_id: str
    legal_choices: tuple[AugmentChoice, ...]
    max_augment_count: int  # cap on total selections (0 = unlimited)


@dataclasses.dataclass
class AugmentSelection:
    item_id: str
    selected: list[str]      # choice_ids in selection order


@dataclasses.dataclass
class GearAugmentPicker:
    _schemas: dict[str, AugmentSchema] = dataclasses.field(
        default_factory=dict,
    )

    def define_schema(
        self, *, schema: AugmentSchema,
    ) -> bool:
        if not schema.item_id:
            return False
        if schema.item_id in self._schemas:
            return False
        if not schema.legal_choices:
            return False
        # All choice_ids must be unique within the schema.
        ids = [c.choice_id for c in schema.legal_choices]
        if len(ids) != len(set(ids)):
            return False
        self._schemas[schema.item_id] = schema
        return True

    def start_selection(
        self, *, item_id: str,
    ) -> t.Optional[AugmentSelection]:
        if item_id not in self._schemas:
            return None
        return AugmentSelection(item_id=item_id, selected=[])

    def toggle(
        self, *, selection: AugmentSelection,
        choice_id: str,
    ) -> bool:
        schema = self._schemas.get(selection.item_id)
        if schema is None:
            return False
        choice = next(
            (c for c in schema.legal_choices
             if c.choice_id == choice_id),
            None,
        )
        if choice is None:
            return False
        # Toggle off: just remove.
        if choice_id in selection.selected:
            selection.selected.remove(choice_id)
            return True
        # PATH choices are mutually exclusive — pick one,
        # the others auto-deselect.
        if choice.tier == AugmentTier.PATH:
            new_sel = [
                cid for cid in selection.selected
                if not self._is_path_choice(schema, cid)
            ]
            new_sel.append(choice_id)
            selection.selected = new_sel
            return True
        # Otherwise check the cap.
        if (schema.max_augment_count > 0 and
                len(selection.selected) >= schema.max_augment_count):
            return False
        selection.selected.append(choice_id)
        return True

    def _is_path_choice(
        self, schema: AugmentSchema, choice_id: str,
    ) -> bool:
        for c in schema.legal_choices:
            if c.choice_id == choice_id:
                return c.tier == AugmentTier.PATH
        return False

    def render(
        self, *, selection: AugmentSelection,
    ) -> tuple[str, ...]:
        """Emit the canonical strings for the lua augments list."""
        schema = self._schemas.get(selection.item_id)
        if schema is None:
            return ()
        out: list[str] = []
        # Maintain selection order — players see what they
        # picked, not what some sort would prefer.
        for cid in selection.selected:
            for c in schema.legal_choices:
                if c.choice_id == cid:
                    out.append(c.canonical_string)
                    break
        return tuple(out)

    def schema_for(
        self, *, item_id: str,
    ) -> t.Optional[AugmentSchema]:
        return self._schemas.get(item_id)

    def total_schemas(self) -> int:
        return len(self._schemas)


__all__ = [
    "AugmentTier", "AugmentChoice", "AugmentSchema",
    "AugmentSelection", "GearAugmentPicker",
]
