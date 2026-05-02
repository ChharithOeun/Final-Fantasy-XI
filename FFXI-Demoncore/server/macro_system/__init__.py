"""Macro system — in-game macro books / pages / lines.

Canonical FFXI keyboard layout: 20 macro books, each with 10
pages, each with 10 macro slots, each macro a 6-line action
queue executed sequentially with optional sleep delays.

Each line is one of a small allowed-command set:
    /equipset N           -- equip a saved gear set
    /ja "Ability"         -- job ability
    /ws "Weapon Skill"    -- weapon skill
    /ma "Spell" <target>  -- magic / spell
    /item "Item" <target> -- consumable
    /sleep N              -- delay N seconds
    /target <name>        -- targeting
    /macro book/page/line N -- chain to another macro
    /echo TEXT            -- print to chat (debug)

Public surface
--------------
    MAX_BOOKS, MAX_PAGES_PER_BOOK, MAX_LINES_PER_MACRO
    LINE_LIMIT (6 per macro), MACRO_SLOTS_PER_PAGE (10)
    MacroLineKind enum
    MacroLine / Macro / MacroPage / MacroBook
    PlayerMacros
        .set_line(book, page, slot, idx, line) -> bool
        .get_macro(book, page, slot) -> Optional[Macro]
        .validate_line(line) -> ValidationResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


MAX_BOOKS = 20
MAX_PAGES_PER_BOOK = 10
MACRO_SLOTS_PER_PAGE = 10
LINE_LIMIT = 6


class MacroLineKind(str, enum.Enum):
    EQUIPSET = "equipset"
    JOB_ABILITY = "ja"
    WEAPON_SKILL = "ws"
    MAGIC = "ma"
    ITEM = "item"
    SLEEP = "sleep"
    TARGET = "target"
    CHAIN = "chain"
    ECHO = "echo"


# Reasonable per-line limits to keep macros from being abused.
_MAX_TARGET_NAME = 32
_MAX_ECHO_LEN = 80
_MAX_SLEEP_SECONDS = 60


@dataclasses.dataclass(frozen=True)
class MacroLine:
    kind: MacroLineKind
    payload: str = ""           # spell name, item name, sleep #, etc.
    target: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ValidationResult:
    accepted: bool
    reason: t.Optional[str] = None


def validate_line(line: MacroLine) -> ValidationResult:
    p = line.payload.strip()
    t_name = (line.target or "").strip()
    if line.kind == MacroLineKind.EQUIPSET:
        if not p.isdigit():
            return ValidationResult(False, reason="equipset N must be int")
        n = int(p)
        if not (1 <= n <= 200):
            return ValidationResult(
                False, reason="equipset N must be 1-200",
            )
    elif line.kind == MacroLineKind.SLEEP:
        try:
            n = int(p)
        except ValueError:
            return ValidationResult(
                False, reason="sleep N must be int",
            )
        if not (1 <= n <= _MAX_SLEEP_SECONDS):
            return ValidationResult(
                False, reason=f"sleep 1-{_MAX_SLEEP_SECONDS}",
            )
    elif line.kind in (MacroLineKind.JOB_ABILITY,
                       MacroLineKind.WEAPON_SKILL,
                       MacroLineKind.MAGIC,
                       MacroLineKind.ITEM):
        if not p:
            return ValidationResult(
                False, reason=f"{line.kind.value} needs a name",
            )
        if line.kind in (MacroLineKind.MAGIC, MacroLineKind.ITEM):
            if t_name and len(t_name) > _MAX_TARGET_NAME:
                return ValidationResult(False, reason="target too long")
    elif line.kind == MacroLineKind.TARGET:
        if not t_name:
            return ValidationResult(False, reason="target name required")
        if len(t_name) > _MAX_TARGET_NAME:
            return ValidationResult(False, reason="target too long")
    elif line.kind == MacroLineKind.CHAIN:
        # payload format: "book/page/slot"
        parts = p.split("/")
        if len(parts) != 3 or not all(x.isdigit() for x in parts):
            return ValidationResult(
                False, reason="chain payload must be book/page/slot",
            )
        b, pg, sl = (int(x) for x in parts)
        if not (1 <= b <= MAX_BOOKS):
            return ValidationResult(False, reason="chain book OOR")
        if not (1 <= pg <= MAX_PAGES_PER_BOOK):
            return ValidationResult(False, reason="chain page OOR")
        if not (1 <= sl <= MACRO_SLOTS_PER_PAGE):
            return ValidationResult(False, reason="chain slot OOR")
    elif line.kind == MacroLineKind.ECHO:
        if len(p) > _MAX_ECHO_LEN:
            return ValidationResult(False, reason="echo too long")
    return ValidationResult(True)


@dataclasses.dataclass
class Macro:
    label: str = ""
    lines: list[MacroLine] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class PlayerMacros:
    player_id: str
    _books: dict[int, dict[int, dict[int, Macro]]] = dataclasses.field(
        default_factory=dict,
    )

    def _ensure(self, book: int, page: int, slot: int) -> Macro:
        b = self._books.setdefault(book, {})
        p = b.setdefault(page, {})
        m = p.get(slot)
        if m is None:
            m = Macro()
            p[slot] = m
            m.lines = [
                MacroLine(kind=MacroLineKind.ECHO, payload="")
                for _ in range(LINE_LIMIT)
            ]
        return m

    def get_macro(self, *, book: int, page: int, slot: int
                   ) -> t.Optional[Macro]:
        return (
            self._books.get(book, {}).get(page, {}).get(slot)
        )

    def set_label(self, *, book: int, page: int, slot: int,
                    label: str) -> bool:
        if not (1 <= book <= MAX_BOOKS):
            return False
        if not (1 <= page <= MAX_PAGES_PER_BOOK):
            return False
        if not (1 <= slot <= MACRO_SLOTS_PER_PAGE):
            return False
        self._ensure(book, page, slot).label = label
        return True

    def set_line(self, *, book: int, page: int, slot: int,
                  index: int, line: MacroLine) -> ValidationResult:
        if not (1 <= book <= MAX_BOOKS):
            return ValidationResult(False, reason="book OOR")
        if not (1 <= page <= MAX_PAGES_PER_BOOK):
            return ValidationResult(False, reason="page OOR")
        if not (1 <= slot <= MACRO_SLOTS_PER_PAGE):
            return ValidationResult(False, reason="slot OOR")
        if not (0 <= index < LINE_LIMIT):
            return ValidationResult(
                False, reason=f"line index 0-{LINE_LIMIT - 1}",
            )
        v = validate_line(line)
        if not v.accepted:
            return v
        m = self._ensure(book, page, slot)
        m.lines[index] = line
        return ValidationResult(True)


__all__ = [
    "MAX_BOOKS", "MAX_PAGES_PER_BOOK",
    "MACRO_SLOTS_PER_PAGE", "LINE_LIMIT",
    "MacroLineKind", "MacroLine", "Macro",
    "ValidationResult", "validate_line",
    "PlayerMacros",
]
