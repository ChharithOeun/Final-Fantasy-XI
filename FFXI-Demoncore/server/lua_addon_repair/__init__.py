"""Lua addon repair — diagnose and autofix broken addons.

Players load existing GearSwap files (their RDM.lua,
their friend's COR.lua, an old archive after a game
update). Common breakages:

    - referenced gear set names that don't exist
    - undefined sets (sets.OffenseMode used but never declared)
    - typo in slot names ("foot" instead of "feet")
    - deprecated API calls from prior platform versions
    - empty weapon set blocks (placeholder never filled in)
    - mismatched braces / unclosed strings

This module does STATIC analysis on lua source — it
doesn't execute the lua. It looks for known patterns
of breakage, reports them as Diagnostic items, and for
the safer fixes proposes autofix actions the caller can
apply.

The repair engine is callable in two modes:
    diagnose(source)  -> list[Diagnostic]
    autofix(source)   -> RepairResult with fixed source

The fixes intentionally err on the side of caution:
the engine will fix obvious typos and add missing-but-
referenced empty sets, but it won't invent semantically
meaningful gear lists — those need the forge.

Public surface
--------------
    Severity enum (INFO/WARN/ERROR)
    Diagnostic dataclass (frozen)
    RepairResult dataclass (frozen)
    LuaAddonRepair
        .diagnose(source) -> list[Diagnostic]
        .autofix(source) -> RepairResult
"""
from __future__ import annotations

import dataclasses
import enum
import re
import typing as t


class Severity(str, enum.Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


@dataclasses.dataclass(frozen=True)
class Diagnostic:
    severity: Severity
    code: str            # short stable identifier
    line: int            # 1-based line number; 0 if unknown
    message: str
    suggested_fix: str   # short human description, "" if no fix


@dataclasses.dataclass(frozen=True)
class RepairResult:
    diagnostics: tuple[Diagnostic, ...]
    fixed_source: str
    changes_applied: int


# Slots that addons commonly typo. Map of typo → correct.
_SLOT_TYPOS: dict[str, str] = {
    "foot": "feet",
    "rear": "back",
    "earring1": "ear1",
    "earring2": "ear2",
    "lring": "ring1",
    "rring": "ring2",
}

# Deprecated API calls and their modern equivalents.
_DEPRECATED_CALLS: dict[str, str] = {
    "windower.add_chat": "windower.add_to_chat",
    "windower.equip": "windower.ffxi.set_equip",
    "AshitaCore.GetChatManager.add_msg":
        "AshitaCore.GetChatManager.AddChatMessage",
}


def _find_set_definitions(source: str) -> set[str]:
    """Find every sets.X (and sets.X.Y) definition site."""
    out: set[str] = set()
    # sets.Idle = ...   or sets.Weapons['Death Blossom'] = ...
    pattern_simple = re.compile(
        r"sets\.([A-Za-z_][A-Za-z0-9_]*)\s*=",
    )
    pattern_indexed = re.compile(
        r"sets\.([A-Za-z_][A-Za-z0-9_]*)\["
    )
    for m in pattern_simple.finditer(source):
        out.add(m.group(1))
    for m in pattern_indexed.finditer(source):
        out.add(m.group(1))
    return out


def _find_set_references(source: str) -> list[tuple[str, int]]:
    """Find every (set_name, line) where sets.X is referenced."""
    out: list[tuple[str, int]] = []
    pattern = re.compile(
        r"sets\.([A-Za-z_][A-Za-z0-9_]*)",
    )
    for line_num, line in enumerate(source.splitlines(), start=1):
        for m in pattern.finditer(line):
            out.append((m.group(1), line_num))
    return out


@dataclasses.dataclass
class LuaAddonRepair:

    def diagnose(self, *, source: str) -> list[Diagnostic]:
        out: list[Diagnostic] = []

        # 1. Brace balance check.
        opens = source.count("{")
        closes = source.count("}")
        if opens != closes:
            out.append(Diagnostic(
                severity=Severity.ERROR,
                code="UNBALANCED_BRACES",
                line=0,
                message=(
                    f"Unbalanced braces: {opens} open, "
                    f"{closes} close"
                ),
                suggested_fix="add missing brace",
            ))

        # 2. Slot-name typos.
        for typo, correct in _SLOT_TYPOS.items():
            for line_num, line in enumerate(
                source.splitlines(), start=1,
            ):
                # match "<typo>=" with optional whitespace
                if re.search(
                    rf"\b{re.escape(typo)}\s*=", line,
                ):
                    out.append(Diagnostic(
                        severity=Severity.WARN,
                        code="SLOT_TYPO",
                        line=line_num,
                        message=(
                            f"slot '{typo}' is not a valid slot; "
                            f"likely '{correct}'"
                        ),
                        suggested_fix=f"rename to {correct}",
                    ))

        # 3. Deprecated API calls.
        for old, new in _DEPRECATED_CALLS.items():
            for line_num, line in enumerate(
                source.splitlines(), start=1,
            ):
                if old in line:
                    out.append(Diagnostic(
                        severity=Severity.WARN,
                        code="DEPRECATED_API",
                        line=line_num,
                        message=(
                            f"deprecated API '{old}'; use '{new}'"
                        ),
                        suggested_fix=f"replace with {new}",
                    ))

        # 4. Referenced-but-undefined sets.
        defs = _find_set_definitions(source)
        for ref, line_num in _find_set_references(source):
            if ref not in defs:
                out.append(Diagnostic(
                    severity=Severity.ERROR,
                    code="UNDEFINED_SET",
                    line=line_num,
                    message=(
                        f"sets.{ref} referenced but never defined"
                    ),
                    suggested_fix=f"add empty sets.{ref} = {{}}",
                ))

        # 5. Empty weapon set blocks (sets.X = {} placeholder).
        for line_num, line in enumerate(source.splitlines(), start=1):
            stripped = line.strip()
            m = re.match(
                r"sets\.([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{\s*\}",
                stripped,
            )
            if m:
                out.append(Diagnostic(
                    severity=Severity.INFO,
                    code="EMPTY_SET",
                    line=line_num,
                    message=(
                        f"sets.{m.group(1)} is empty — "
                        f"placeholder?"
                    ),
                    suggested_fix="",
                ))

        return out

    def autofix(self, *, source: str) -> RepairResult:
        diags = self.diagnose(source=source)
        fixed = source
        changes = 0

        # Apply slot-name typo fixes.
        for typo, correct in _SLOT_TYPOS.items():
            pattern = re.compile(
                rf"\b{re.escape(typo)}(\s*=)",
            )
            new_fixed, n = pattern.subn(
                rf"{correct}\1", fixed,
            )
            if n > 0:
                fixed = new_fixed
                changes += n

        # Apply deprecated-API replacements.
        for old, new in _DEPRECATED_CALLS.items():
            count = fixed.count(old)
            if count > 0:
                fixed = fixed.replace(old, new)
                changes += count

        # Add empty set declarations for undefined-but-referenced.
        # We rerun the analysis on the fixed source after typo
        # repairs because typos could have been on set names too.
        defs = _find_set_definitions(fixed)
        missing: set[str] = set()
        for ref, _ in _find_set_references(fixed):
            if ref not in defs:
                missing.add(ref)
        if missing:
            stub_lines = ["", "-- Auto-added by lua_addon_repair:"]
            for name in sorted(missing):
                stub_lines.append(f"sets.{name} = sets.{name} or {{}}")
            fixed = fixed + "\n" + "\n".join(stub_lines) + "\n"
            changes += len(missing)

        return RepairResult(
            diagnostics=tuple(diags),
            fixed_source=fixed,
            changes_applied=changes,
        )


__all__ = [
    "Severity", "Diagnostic", "RepairResult",
    "LuaAddonRepair",
]
