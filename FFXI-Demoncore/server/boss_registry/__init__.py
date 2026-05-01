"""Boss registry — the composition site for deployable bosses.

Combines mob_class_library (catalog body), boss_grammar (5-layer
recipe), cinematic_grammar (entrance + defeat) into deployable
bosses the orchestrator can spawn.

Module layout:
    instance.py - DeployableBoss + cross-system validate
    builder.py  - BossBuildPlan + build() fluent composer
    registry.py - BossRegistry + global singleton
"""
from .builder import (
    BossBuildPlan,
    build,
    family_for_plan,
)
from .instance import DeployableBoss, validate_deployable
from .registry import (
    BossRegistry,
    global_registry,
    reset_global_registry,
)

__all__ = [
    "DeployableBoss", "validate_deployable",
    "BossBuildPlan", "build", "family_for_plan",
    "BossRegistry", "global_registry", "reset_global_registry",
]
