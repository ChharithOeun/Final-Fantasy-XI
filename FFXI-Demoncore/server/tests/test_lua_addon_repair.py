"""Tests for lua_addon_repair."""
from __future__ import annotations

from server.lua_addon_repair import (
    LuaAddonRepair, RepairResult, Severity,
)


def test_clean_source_no_diagnostics():
    src = (
        "sets.Idle = { head=\"Hat\" }\n"
        "function get_sets()\n"
        "  return sets.Idle\n"
        "end\n"
    )
    r = LuaAddonRepair()
    diags = r.diagnose(source=src)
    assert diags == []


def test_unbalanced_braces_error():
    src = "sets.Idle = { head=\"Hat\"\n"
    r = LuaAddonRepair()
    diags = r.diagnose(source=src)
    assert any(d.code == "UNBALANCED_BRACES" for d in diags)


def test_balanced_braces_ok():
    src = "sets.Idle = { head=\"Hat\" }\n"
    r = LuaAddonRepair()
    diags = r.diagnose(source=src)
    assert not any(d.code == "UNBALANCED_BRACES" for d in diags)


def test_slot_typo_foot_warns():
    src = "sets.Idle = { foot=\"Sollerets\" }\n"
    r = LuaAddonRepair()
    diags = r.diagnose(source=src)
    typo_diag = next(d for d in diags if d.code == "SLOT_TYPO")
    assert "feet" in typo_diag.message


def test_slot_typo_rear_warns():
    src = "sets.Idle = { rear=\"Cape\" }\n"
    r = LuaAddonRepair()
    diags = r.diagnose(source=src)
    assert any(
        d.code == "SLOT_TYPO" and "back" in d.message
        for d in diags
    )


def test_deprecated_api_warns():
    src = "windower.add_chat(8, 'msg')\n"
    r = LuaAddonRepair()
    diags = r.diagnose(source=src)
    assert any(d.code == "DEPRECATED_API" for d in diags)


def test_modern_api_ok():
    src = "windower.add_to_chat(8, 'msg')\n"
    r = LuaAddonRepair()
    diags = r.diagnose(source=src)
    assert not any(d.code == "DEPRECATED_API" for d in diags)


def test_undefined_set_error():
    src = (
        "function get_sets()\n"
        "  equip(sets.Phantom)\n"
        "end\n"
    )
    r = LuaAddonRepair()
    diags = r.diagnose(source=src)
    assert any(
        d.code == "UNDEFINED_SET" and "Phantom" in d.message
        for d in diags
    )


def test_defined_set_no_error():
    src = (
        "sets.Phantom = {}\n"
        "function get_sets()\n"
        "  equip(sets.Phantom)\n"
        "end\n"
    )
    r = LuaAddonRepair()
    diags = r.diagnose(source=src)
    assert not any(d.code == "UNDEFINED_SET" for d in diags)


def test_indexed_set_definition_recognized():
    """sets.Weapons['Death Blossom'] = ... counts as defining Weapons."""
    src = (
        "sets.Weapons['Death Blossom'] = { main=\"Murgleis\" }\n"
        "function get_sets()\n"
        "  equip(sets.Weapons['Death Blossom'])\n"
        "end\n"
    )
    r = LuaAddonRepair()
    diags = r.diagnose(source=src)
    assert not any(d.code == "UNDEFINED_SET" for d in diags)


def test_empty_set_info_only():
    src = "sets.Filler = {}\n"
    r = LuaAddonRepair()
    diags = r.diagnose(source=src)
    empty = [d for d in diags if d.code == "EMPTY_SET"]
    assert len(empty) == 1
    assert empty[0].severity == Severity.INFO


def test_autofix_applies_slot_typo():
    src = "sets.Idle = { foot=\"Sollerets\" }\n"
    r = LuaAddonRepair()
    out = r.autofix(source=src)
    assert "feet=\"Sollerets\"" in out.fixed_source
    assert "foot=\"Sollerets\"" not in out.fixed_source
    assert out.changes_applied >= 1


def test_autofix_replaces_deprecated_api():
    src = "windower.add_chat(8, 'msg')\n"
    r = LuaAddonRepair()
    out = r.autofix(source=src)
    assert "windower.add_to_chat" in out.fixed_source
    assert "windower.add_chat" not in out.fixed_source.replace(
        "windower.add_to_chat", "",
    )


def test_autofix_appends_missing_set_stubs():
    src = (
        "function get_sets()\n"
        "  equip(sets.Phantom)\n"
        "end\n"
    )
    r = LuaAddonRepair()
    out = r.autofix(source=src)
    assert "sets.Phantom = sets.Phantom or {}" in out.fixed_source


def test_autofix_no_changes_clean_source():
    src = (
        "sets.Idle = { head=\"Hat\" }\n"
        "function get_sets()\n"
        "  return sets.Idle\n"
        "end\n"
    )
    r = LuaAddonRepair()
    out = r.autofix(source=src)
    assert out.changes_applied == 0


def test_autofix_returns_diagnostics():
    src = "sets.Idle = { foot=\"x\" }\n"
    r = LuaAddonRepair()
    out = r.autofix(source=src)
    assert isinstance(out, RepairResult)
    assert len(out.diagnostics) > 0


def test_multiple_fixes_in_one_pass():
    src = (
        "sets.Idle = { foot=\"x\", rear=\"y\" }\n"
        "windower.add_chat(8, 'msg')\n"
        "function get_sets()\n"
        "  equip(sets.Phantom)\n"
        "end\n"
    )
    r = LuaAddonRepair()
    out = r.autofix(source=src)
    # 2 typos + 1 deprecated + 1 missing set = 4 fixes
    assert out.changes_applied >= 4
    assert "feet=\"x\"" in out.fixed_source
    assert "back=\"y\"" in out.fixed_source
    assert "windower.add_to_chat" in out.fixed_source
    assert "sets.Phantom" in out.fixed_source


def test_diagnostic_carries_line_number():
    src = (
        "sets.Idle = {}\n"
        "sets.Idle2 = { foot=\"x\" }\n"
    )
    r = LuaAddonRepair()
    diags = r.diagnose(source=src)
    typo = next(d for d in diags if d.code == "SLOT_TYPO")
    assert typo.line == 2


def test_unbalanced_diagnostic_line_zero():
    src = "sets.X = {\n"
    r = LuaAddonRepair()
    diags = r.diagnose(source=src)
    err = next(d for d in diags if d.code == "UNBALANCED_BRACES")
    assert err.line == 0


def test_three_severities():
    assert len(list(Severity)) == 3
