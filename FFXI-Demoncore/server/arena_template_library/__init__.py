"""Arena template library — pre-built fight rooms in a box.

Designers shouldn't have to manually wire ten arena
features + five cascade rules + three habitat links + two
cannon emplacements every time they want a new boss
fight. This module is a CATALOG of arena templates,
each a complete declarative recipe you can instantiate
into a live arena_id with one call.

A template bundles:
    features         - list[ArenaFeature]
    cascade_rules    - list[CascadeRule]
    habitat_links    - list[(feature_id, habitat_id, threshold)]
    cannon_emplacements - list[(cannon_id, size, band)]
    suggested_prep_minutes - int (default fortification window)

Templates shipped here:
    KELP_CHAMBER     - underwater tunnel with kelp walls
                       and a frozen ceiling
    SHIP_DECK        - rolling ship with hull, masts,
                       and 4 cannons
    ICE_CAVERN       - ice sheet floor over a deep pool
    DAM_BASIN        - holding chamber with a fragile
                       dam and a deep flood basin
    ROYAL_PALACE     - throne room with pillars, ceiling
                       chandelier, and ornamental cannons

Public surface
--------------
    TemplateId enum
    ArenaTemplate dataclass (frozen)
    ArenaTemplateLibrary
        .register_template(template) -> bool
        .get(template_id) -> Optional[ArenaTemplate]
        .all_templates() -> tuple[ArenaTemplate, ...]
        .instantiate(template_id, arena_id, environment,
                     habitat_disturbance, cascade,
                     siege_cannons) -> InstantiateResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.arena_environment import (
    ArenaEnvironment, ArenaFeature, FeatureKind,
)
from server.environment_cascade import (
    CascadeRule, CascadeTrigger, EnvironmentCascade,
)
from server.habitat_disturbance import HabitatDisturbance
from server.siege_cannons import CannonSize, SiegeCannons


class TemplateId(str, enum.Enum):
    KELP_CHAMBER = "kelp_chamber"
    SHIP_DECK = "ship_deck"
    ICE_CAVERN = "ice_cavern"
    DAM_BASIN = "dam_basin"
    ROYAL_PALACE = "royal_palace"


@dataclasses.dataclass(frozen=True)
class HabitatLink:
    feature_id: str
    habitat_id: str
    threshold: int


@dataclasses.dataclass(frozen=True)
class CannonEmplacement:
    cannon_id: str
    size: CannonSize
    band: int = 1


@dataclasses.dataclass(frozen=True)
class ArenaTemplate:
    template_id: TemplateId
    label: str
    features: tuple[ArenaFeature, ...]
    cascade_rules: tuple[CascadeRule, ...] = ()
    habitat_links: tuple[HabitatLink, ...] = ()
    cannon_emplacements: tuple[CannonEmplacement, ...] = ()
    suggested_prep_minutes: int = 30


@dataclasses.dataclass(frozen=True)
class InstantiateResult:
    accepted: bool
    arena_id: str = ""
    features_registered: int = 0
    cascade_rules_registered: int = 0
    habitat_links_registered: int = 0
    cannons_registered: int = 0
    reason: t.Optional[str] = None


def _build_canonical_templates() -> dict[TemplateId, ArenaTemplate]:
    """Hand-authored canonical templates."""
    out: dict[TemplateId, ArenaTemplate] = {}

    # KELP_CHAMBER
    kelp = ArenaTemplate(
        template_id=TemplateId.KELP_CHAMBER,
        label="Kelp Chamber",
        features=(
            ArenaFeature(
                feature_id="kelp_north_wall", kind=FeatureKind.WALL,
                hp_max=8000, band=2,
                element_mults={"fire": 2.0},
            ),
            ArenaFeature(
                feature_id="ice_ceiling", kind=FeatureKind.CEILING,
                hp_max=6000, band=3,
                element_mults={"fire": 2.5, "ice": 0.0},
            ),
            ArenaFeature(
                feature_id="kelp_floor", kind=FeatureKind.FLOOR,
                hp_max=12000, band=1,
            ),
        ),
        cascade_rules=(
            CascadeRule(
                rule_id="kc_ceiling_to_floor",
                trigger=CascadeTrigger.ON_BREAK,
                source_feature_id="ice_ceiling",
                target_feature_id="kelp_floor",
                followup_damage=2000,
                target_element="ice",
            ),
        ),
        habitat_links=(
            HabitatLink(
                feature_id="kelp_north_wall",
                habitat_id="kelp_predators",
                threshold=8000,
            ),
        ),
    )
    out[TemplateId.KELP_CHAMBER] = kelp

    # SHIP_DECK
    ship = ArenaTemplate(
        template_id=TemplateId.SHIP_DECK,
        label="Ship Deck",
        features=(
            ArenaFeature(
                feature_id="port_hull", kind=FeatureKind.SHIP_HULL,
                hp_max=15000, band=1,
            ),
            ArenaFeature(
                feature_id="starboard_hull", kind=FeatureKind.SHIP_HULL,
                hp_max=15000, band=1,
            ),
            ArenaFeature(
                feature_id="main_mast", kind=FeatureKind.PILLAR,
                hp_max=8000, band=3,
            ),
            ArenaFeature(
                feature_id="deck_floor", kind=FeatureKind.FLOOR,
                hp_max=20000, band=2,
            ),
        ),
        cannon_emplacements=(
            CannonEmplacement(
                cannon_id="port_fwd_cannon",
                size=CannonSize.MEDIUM, band=2,
            ),
            CannonEmplacement(
                cannon_id="port_aft_cannon",
                size=CannonSize.MEDIUM, band=2,
            ),
            CannonEmplacement(
                cannon_id="bow_cannon",
                size=CannonSize.HEAVY, band=2,
            ),
            CannonEmplacement(
                cannon_id="stern_cannon",
                size=CannonSize.LIGHT, band=2,
            ),
        ),
        cascade_rules=(
            CascadeRule(
                rule_id="ship_mast_to_deck",
                trigger=CascadeTrigger.ON_BREAK,
                source_feature_id="main_mast",
                target_feature_id="deck_floor",
                followup_damage=3000,
            ),
        ),
        habitat_links=(
            HabitatLink(
                feature_id="port_hull",
                habitat_id="shipwreck_haunts",
                threshold=10000,
            ),
        ),
    )
    out[TemplateId.SHIP_DECK] = ship

    # ICE_CAVERN
    ice = ArenaTemplate(
        template_id=TemplateId.ICE_CAVERN,
        label="Ice Cavern",
        features=(
            ArenaFeature(
                feature_id="lake_ice", kind=FeatureKind.ICE_SHEET,
                hp_max=5000, band=1,
                element_mults={"fire": 3.0, "ice": 0.0},
            ),
            ArenaFeature(
                feature_id="cavern_ceiling", kind=FeatureKind.CEILING,
                hp_max=10000, band=3,
            ),
            ArenaFeature(
                feature_id="ice_pillar_e", kind=FeatureKind.PILLAR,
                hp_max=4500, band=2,
            ),
            ArenaFeature(
                feature_id="ice_pillar_w", kind=FeatureKind.PILLAR,
                hp_max=4500, band=2,
            ),
        ),
        cascade_rules=(
            CascadeRule(
                rule_id="ice_pillar_e_to_ceiling",
                trigger=CascadeTrigger.ON_BREAK,
                source_feature_id="ice_pillar_e",
                target_feature_id="cavern_ceiling",
                followup_damage=2500,
            ),
            CascadeRule(
                rule_id="ice_pillar_w_to_ceiling",
                trigger=CascadeTrigger.ON_BREAK,
                source_feature_id="ice_pillar_w",
                target_feature_id="cavern_ceiling",
                followup_damage=2500,
            ),
        ),
        habitat_links=(
            HabitatLink(
                feature_id="lake_ice",
                habitat_id="frozen_deep_things",
                threshold=4000,
            ),
        ),
    )
    out[TemplateId.ICE_CAVERN] = ice

    # DAM_BASIN
    dam = ArenaTemplate(
        template_id=TemplateId.DAM_BASIN,
        label="Dam Basin",
        features=(
            ArenaFeature(
                feature_id="great_dam", kind=FeatureKind.DAM,
                hp_max=18000, band=0,
            ),
            ArenaFeature(
                feature_id="basin_floor", kind=FeatureKind.FLOOR,
                hp_max=15000, band=1,
            ),
            ArenaFeature(
                feature_id="basin_north_wall", kind=FeatureKind.WALL,
                hp_max=12000, band=2,
            ),
        ),
        cascade_rules=(
            CascadeRule(
                rule_id="dam_to_floor_flood",
                trigger=CascadeTrigger.ON_BREAK,
                source_feature_id="great_dam",
                target_feature_id="basin_floor",
                followup_damage=1500,
                delay_seconds=10,
            ),
        ),
    )
    out[TemplateId.DAM_BASIN] = dam

    # ROYAL_PALACE
    palace = ArenaTemplate(
        template_id=TemplateId.ROYAL_PALACE,
        label="Royal Palace",
        features=(
            ArenaFeature(
                feature_id="throne_floor", kind=FeatureKind.FLOOR,
                hp_max=25000, band=1,
            ),
            ArenaFeature(
                feature_id="chandelier_ceiling", kind=FeatureKind.CEILING,
                hp_max=12000, band=4,
            ),
            ArenaFeature(
                feature_id="palace_pillar_n", kind=FeatureKind.PILLAR,
                hp_max=9000, band=2,
            ),
            ArenaFeature(
                feature_id="palace_pillar_s", kind=FeatureKind.PILLAR,
                hp_max=9000, band=2,
            ),
            ArenaFeature(
                feature_id="palace_pillar_e", kind=FeatureKind.PILLAR,
                hp_max=9000, band=2,
            ),
            ArenaFeature(
                feature_id="palace_pillar_w", kind=FeatureKind.PILLAR,
                hp_max=9000, band=2,
            ),
        ),
        cannon_emplacements=(
            CannonEmplacement(
                cannon_id="palace_ornamental_a",
                size=CannonSize.LIGHT, band=2,
            ),
            CannonEmplacement(
                cannon_id="palace_ornamental_b",
                size=CannonSize.LIGHT, band=2,
            ),
        ),
        cascade_rules=tuple(
            CascadeRule(
                rule_id=f"pp_{d}_to_ceiling",
                trigger=CascadeTrigger.ON_BREAK,
                source_feature_id=f"palace_pillar_{d}",
                target_feature_id="chandelier_ceiling",
                followup_damage=2000,
            )
            for d in ("n", "s", "e", "w")
        ),
        suggested_prep_minutes=45,
    )
    out[TemplateId.ROYAL_PALACE] = palace

    return out


@dataclasses.dataclass
class ArenaTemplateLibrary:
    _templates: dict[TemplateId, ArenaTemplate] = dataclasses.field(
        default_factory=_build_canonical_templates,
    )

    def register_template(self, template: ArenaTemplate) -> bool:
        if template.template_id in self._templates:
            return False
        if not template.features:
            return False
        self._templates[template.template_id] = template
        return True

    def get(
        self, *, template_id: TemplateId,
    ) -> t.Optional[ArenaTemplate]:
        return self._templates.get(template_id)

    def all_templates(self) -> tuple[ArenaTemplate, ...]:
        return tuple(self._templates.values())

    def instantiate(
        self, *, template_id: TemplateId, arena_id: str,
        environment: ArenaEnvironment,
        habitat_disturbance: t.Optional[HabitatDisturbance] = None,
        cascade: t.Optional[EnvironmentCascade] = None,
        siege_cannons: t.Optional[SiegeCannons] = None,
    ) -> InstantiateResult:
        tpl = self._templates.get(template_id)
        if tpl is None:
            return InstantiateResult(False, reason="unknown template")
        if not arena_id:
            return InstantiateResult(False, reason="blank arena_id")
        if not environment.register_arena(
            arena_id=arena_id, features=tpl.features,
        ):
            return InstantiateResult(False, reason="arena already exists")
        feats_n = len(tpl.features)
        cascade_n = 0
        habitat_n = 0
        cannon_n = 0
        if cascade is not None:
            for r in tpl.cascade_rules:
                if cascade.register_rule(r):
                    cascade_n += 1
        if habitat_disturbance is not None:
            for hl in tpl.habitat_links:
                if habitat_disturbance.link_habitat_to_feature(
                    arena_id=arena_id,
                    feature_id=hl.feature_id,
                    habitat_id=hl.habitat_id,
                    threshold=hl.threshold,
                ):
                    habitat_n += 1
        if siege_cannons is not None:
            for ce in tpl.cannon_emplacements:
                if siege_cannons.register_cannon(
                    cannon_id=ce.cannon_id, size=ce.size,
                    arena_id=arena_id, band=ce.band,
                ):
                    cannon_n += 1
        return InstantiateResult(
            accepted=True, arena_id=arena_id,
            features_registered=feats_n,
            cascade_rules_registered=cascade_n,
            habitat_links_registered=habitat_n,
            cannons_registered=cannon_n,
        )


__all__ = [
    "TemplateId", "HabitatLink", "CannonEmplacement",
    "ArenaTemplate", "InstantiateResult",
    "ArenaTemplateLibrary",
]
