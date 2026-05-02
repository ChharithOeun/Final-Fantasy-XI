#!/usr/bin/env python3
"""Validate that every Recipe Slip has authored recipe data.

Walks the slip catalog, cross-references the recipe table, and
reports:

  GREEN   — slip has a non-empty recipe
  ORANGE  — slip is in a (slot, archetype) we haven't seeded yet
            (expected; these will be added as content batches roll)
  RED     — slip is in a seeded (slot, archetype) but has NO recipe
            (a real bug in the data — author missed an entry)

Exit codes:
  0  no RED issues
  1  one or more RED issues — recipe data is incomplete

Usage:
  python -m scripts.validate_recipe_coverage [--verbose]
"""
from __future__ import annotations

import argparse
import sys
from typing import Iterable

from server.recipe_data import has_recipe, seeded_slot_archetype_pairs
from server.recipe_slip_registry import (
    RECIPE_SLIP_CATALOG,
    Archetype,
    RecipeSlip,
    Slot,
)


GREEN = "[GREEN]"
ORANGE = "[ORANGE]"
RED = "[RED]"


def categorize(
    slips: Iterable[RecipeSlip],
    seeded: set[tuple[Slot, Archetype]],
) -> dict[str, list[RecipeSlip]]:
    # Always pre-populate the three buckets so callers can reason
    # about all categories without KeyError.
    out: dict[str, list[RecipeSlip]] = {
        "green": [], "orange": [], "red": [],
    }
    for s in slips:
        if has_recipe(s.slip_id):
            out["green"].append(s)
        elif (s.slot, s.archetype) in seeded:
            out["red"].append(s)
        else:
            out["orange"].append(s)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--verbose", "-v", action="store_true",
        help="list every slip in each category",
    )
    args = ap.parse_args(argv)

    seeded = set(seeded_slot_archetype_pairs())
    buckets = categorize(RECIPE_SLIP_CATALOG, seeded)

    total = len(RECIPE_SLIP_CATALOG)
    n_green = len(buckets["green"])
    n_orange = len(buckets["orange"])
    n_red = len(buckets["red"])

    print(f"Recipe coverage: {n_green}/{total} slips authored")
    print(f"  {GREEN} {n_green:5d} authored")
    print(f"  {ORANGE} {n_orange:5d} unseeded (expected, content batch pending)")
    print(f"  {RED} {n_red:5d} MISSING in seeded coverage")
    print()
    print("Seeded (slot, archetype) pairs:")
    for slot, arch in sorted(seeded, key=lambda p: (p[0].value, p[1].value)):
        print(f"  - {slot.value} / {arch.value}")

    if args.verbose:
        for tag, name in (
            ("green", GREEN), ("orange", ORANGE), ("red", RED),
        ):
            entries = sorted(buckets[tag], key=lambda s: s.slip_id)
            if not entries:
                continue
            print()
            print(f"== {name} ({len(entries)}) ==")
            for s in entries[:50]:
                print(f"  {s.slip_id} ({s.slot.value} / "
                      f"{s.archetype.value} / {s.axis.value}"
                      f" T{s.target_step})")
            if len(entries) > 50:
                print(f"  ... and {len(entries) - 50} more")

    if n_red > 0:
        print()
        print(f"FAILED: {n_red} slip(s) in seeded (slot,arch) pairs "
              "have no recipe.")
        return 1
    print()
    print("PASS: no missing recipes in seeded coverage.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
