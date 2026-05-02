#!/usr/bin/env python3
"""Export the Ambuscade Repurpose recipe chart as wiki-format markdown.

Walks the slip catalog + recipe data, produces:

    docs/AMBUSCADE_RECIPE_CHART.md

Sections:
    * Header + summary stats (coverage)
    * One section per (slot, archetype) that has authored recipes
    * Each section has 2 tables: ILVL ladder, Quality ladder
    * Materials columns list bundles, components, key items

Usage:
  python -m scripts.export_recipe_chart
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

from server.recipe_data import (
    has_recipe,
    materials_for_slip,
    seeded_slot_archetype_pairs,
)
from server.recipe_slip_registry import (
    Archetype,
    Slot,
    TierAxis,
    ilvl_for_tier,
    slip_for,
)
from server.synergy_workbench import CraftRequirement


def render_materials(mats: Iterable[CraftRequirement]) -> str:
    parts: list[str] = []
    for m in mats:
        prefix = "**bundle:** " if m.is_bundle else ""
        if m.quantity == 1:
            parts.append(f"{prefix}`{m.requirement_id}`")
        else:
            parts.append(f"{prefix}`{m.requirement_id}` ×{m.quantity}")
    return "<br>".join(parts) or "_(none)_"


def render_ilvl_table(slot: Slot, archetype: Archetype) -> str:
    lines = [
        f"#### {archetype.value.title()} {slot.value.title()} — ILVL ladder",
        "",
        "| Tier | Output i-lvl | Recipe Slip | Materials |",
        "|------|---------------|-------------|-----------|",
    ]
    for tier in range(12):
        slip = slip_for(
            slot=slot, archetype=archetype,
            axis=TierAxis.ILVL, target_step=tier,
        )
        ilvl = ilvl_for_tier(tier)
        mats = materials_for_slip(slip.slip_id)
        lines.append(
            f"| T{tier} | i-lvl {ilvl} | `{slip.slip_id}` | "
            f"{render_materials(mats)} |"
        )
    return "\n".join(lines)


def render_quality_table(slot: Slot, archetype: Archetype) -> str:
    lines = [
        f"#### {archetype.value.title()} {slot.value.title()} — QUALITY ladder",
        "",
        "| Tier | Quality | Recipe Slip | Materials |",
        "|------|---------|-------------|-----------|",
    ]
    for q in range(1, 5):
        slip = slip_for(
            slot=slot, archetype=archetype,
            axis=TierAxis.QUALITY, target_step=q,
        )
        mats = materials_for_slip(slip.slip_id)
        lines.append(
            f"| Q{q} | +{q} | `{slip.slip_id}` | "
            f"{render_materials(mats)} |"
        )
    return "\n".join(lines)


def render_section(slot: Slot, archetype: Archetype) -> str:
    return (
        f"### Ambuscade {archetype.value.title()} "
        f"{slot.value.title()}\n\n"
        + render_ilvl_table(slot, archetype) + "\n\n"
        + render_quality_table(slot, archetype) + "\n"
    )


def render_chart() -> str:
    seeded = seeded_slot_archetype_pairs()
    n_authored = sum(1 for slot, arch in seeded
                      for tier in range(12)
                      if has_recipe(slip_for(
                          slot=slot, archetype=arch,
                          axis=TierAxis.ILVL, target_step=tier,
                      ).slip_id))

    header = [
        "# Ambuscade Repurpose Recipe Chart",
        "",
        "*Auto-generated from recipe_slip_registry + recipe_data.*",
        "*Run `python -m scripts.export_recipe_chart` to regenerate.*",
        "",
        "## Summary",
        "",
        f"- **Seeded coverage:** {len(seeded)} (slot, archetype) "
        "pairs",
        f"- **ILVL recipes authored:** {n_authored}",
        "- **Each piece advances on TWO axes:** i-lvl tier "
        "(T0-T11, gives 120-175) and quality (NQ, +1, +2, +3, +4)",
        "",
        "## How to read this chart",
        "",
        "Each section shows ONE (slot, archetype) combination. The "
        "ILVL ladder is the primary upgrade path: 12 tiers, each "
        "bumps i-lvl by 5. The QUALITY ladder is independent — you "
        "can advance quality at any time without re-running the "
        "ILVL ladder.",
        "",
        "**Bundle inputs** (bold) consume EVERY existing piece in "
        "that i-lvl bracket the archetype can equip — driving "
        "demand for old-content gear.",
        "",
        "**T0-T4** consume old-content gear bundles + base materials.",
        "**T5-T11** consume Shadow Genkai signature shards + "
        "shadow fragments.",
        "**Quality (+N)** consumes shadow fragments + R/EX polish "
        "drops from beastmen-stronghold NMs.",
        "",
    ]

    sections = [
        render_section(slot, arch)
        for slot, arch in seeded
    ]
    return "\n".join(header) + "\n" + "\n".join(sections)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--output", "-o",
        default="docs/AMBUSCADE_RECIPE_CHART.md",
        help="output markdown path (relative to repo root)",
    )
    ap.add_argument(
        "--stdout", action="store_true",
        help="print to stdout instead of writing a file",
    )
    args = ap.parse_args(argv)
    chart = render_chart()
    if args.stdout:
        print(chart)
        return 0
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(chart, encoding="utf-8")
    print(f"Wrote {len(chart)} chars to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
