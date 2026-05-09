"""Tests for npc_relocation_trigger."""
from __future__ import annotations

from server.npc_relocation_trigger import (
    NPCRelocationTriggerSystem, RelocationKind,
)


def test_emit_happy():
    s = NPCRelocationTriggerSystem()
    eid = s.emit(
        npc_id="off_volker",
        kind=RelocationKind.DEFECTED,
        from_faction="bastok",
        to_faction="windy", occurred_day=400,
        note="loyalty drift",
    )
    assert eid is not None


def test_emit_blank_npc():
    s = NPCRelocationTriggerSystem()
    eid = s.emit(
        npc_id="", kind=RelocationKind.DEFECTED,
        from_faction="bastok",
        to_faction="windy", occurred_day=400,
    )
    assert eid is None


def test_emit_blank_from():
    s = NPCRelocationTriggerSystem()
    eid = s.emit(
        npc_id="o", kind=RelocationKind.DEFECTED,
        from_faction="", to_faction="windy",
        occurred_day=400,
    )
    assert eid is None


def test_emit_deceased_no_to_required():
    s = NPCRelocationTriggerSystem()
    eid = s.emit(
        npc_id="o", kind=RelocationKind.DECEASED,
        from_faction="bastok", to_faction="",
        occurred_day=400,
    )
    assert eid is not None


def test_emit_defected_requires_to():
    s = NPCRelocationTriggerSystem()
    eid = s.emit(
        npc_id="o", kind=RelocationKind.DEFECTED,
        from_faction="bastok", to_faction="",
        occurred_day=400,
    )
    assert eid is None


def test_register_hook():
    s = NPCRelocationTriggerSystem()
    assert s.register_hook(
        name="dialogue_hook", fn=lambda e: True,
    ) is True


def test_register_hook_blank():
    s = NPCRelocationTriggerSystem()
    assert s.register_hook(
        name="", fn=lambda e: True,
    ) is False


def test_register_dup_hook_blocked():
    s = NPCRelocationTriggerSystem()
    s.register_hook(name="h", fn=lambda e: True)
    assert s.register_hook(
        name="h", fn=lambda e: True,
    ) is False


def test_emit_fires_hooks_in_order():
    s = NPCRelocationTriggerSystem()
    fired: list[str] = []
    s.register_hook(
        name="first",
        fn=lambda e: fired.append("first") or True,
    )
    s.register_hook(
        name="second",
        fn=lambda e: fired.append("second") or True,
    )
    eid = s.emit(
        npc_id="o", kind=RelocationKind.DEFECTED,
        from_faction="bastok", to_faction="windy",
        occurred_day=400,
    )
    assert fired == ["first", "second"]
    res = s.hook_results(event_id=eid)
    assert all(r.succeeded for r in res)


def test_failing_hook_recorded():
    s = NPCRelocationTriggerSystem()
    s.register_hook(
        name="ok", fn=lambda e: True,
    )
    s.register_hook(
        name="bad", fn=lambda e: False,
    )
    eid = s.emit(
        npc_id="o", kind=RelocationKind.DEFECTED,
        from_faction="bastok", to_faction="windy",
        occurred_day=400,
    )
    failed = s.failed_hooks_for(event_id=eid)
    assert len(failed) == 1
    assert failed[0].hook_name == "bad"


def test_exception_hook_captured():
    s = NPCRelocationTriggerSystem()

    def boom(_e):
        raise RuntimeError("kaboom")

    s.register_hook(name="bad", fn=boom)
    s.register_hook(
        name="ok", fn=lambda e: True,
    )
    eid = s.emit(
        npc_id="o", kind=RelocationKind.DEFECTED,
        from_faction="bastok", to_faction="windy",
        occurred_day=400,
    )
    failed = s.failed_hooks_for(event_id=eid)
    assert len(failed) == 1
    assert "kaboom" in failed[0].details
    # And the OK hook still fired
    all_res = s.hook_results(event_id=eid)
    assert any(
        r.hook_name == "ok" and r.succeeded
        for r in all_res
    )


def test_event_lookup():
    s = NPCRelocationTriggerSystem()
    eid = s.emit(
        npc_id="o", kind=RelocationKind.DEFECTED,
        from_faction="bastok", to_faction="windy",
        occurred_day=400,
    )
    e = s.event(event_id=eid)
    assert e.npc_id == "o"
    assert e.kind == RelocationKind.DEFECTED


def test_event_unknown():
    s = NPCRelocationTriggerSystem()
    assert s.event(event_id="ghost") is None


def test_all_events_for_npc_sorted():
    s = NPCRelocationTriggerSystem()
    s.emit(
        npc_id="o", kind=RelocationKind.DEFECTED,
        from_faction="bastok", to_faction="windy",
        occurred_day=400,
    )
    s.emit(
        npc_id="o",
        kind=RelocationKind.APPOINTED_HOME,
        from_faction="windy", to_faction="bastok",
        occurred_day=200,
    )
    s.emit(
        npc_id="o", kind=RelocationKind.EXILED,
        from_faction="bastok",
        to_faction="wilderness", occurred_day=500,
    )
    out = s.all_events_for(npc_id="o")
    days = [e.occurred_day for e in out]
    assert days == [200, 400, 500]


def test_hook_count():
    s = NPCRelocationTriggerSystem()
    s.register_hook(name="a", fn=lambda e: True)
    s.register_hook(name="b", fn=lambda e: True)
    assert s.hook_count() == 2


def test_emit_negative_day_blocked():
    s = NPCRelocationTriggerSystem()
    eid = s.emit(
        npc_id="o", kind=RelocationKind.DEFECTED,
        from_faction="bastok", to_faction="windy",
        occurred_day=-1,
    )
    assert eid is None


def test_full_ripple_scenario():
    """End-to-end: 1 defection event triggers 3
    downstream hooks (dialogue/cutscene/quest)."""
    s = NPCRelocationTriggerSystem()
    dialogue_called: list[str] = []
    cutscene_called: list[str] = []
    quest_called: list[str] = []
    s.register_hook(
        name="dialogue",
        fn=lambda e: (
            dialogue_called.append(e.npc_id) or True
        ),
    )
    s.register_hook(
        name="cutscene",
        fn=lambda e: (
            cutscene_called.append(e.npc_id) or True
        ),
    )
    s.register_hook(
        name="quest",
        fn=lambda e: (
            quest_called.append(e.npc_id) or True
        ),
    )
    eid = s.emit(
        npc_id="off_volker",
        kind=RelocationKind.DEFECTED,
        from_faction="bastok",
        to_faction="windy", occurred_day=400,
    )
    # All three hooks fired
    assert dialogue_called == ["off_volker"]
    assert cutscene_called == ["off_volker"]
    assert quest_called == ["off_volker"]
    # And recorded
    assert len(s.hook_results(event_id=eid)) == 3


def test_enum_count():
    assert len(list(RelocationKind)) == 5
