"""Tests for ai_behavior_addon."""
from __future__ import annotations

from server.ai_behavior_addon import (
    AiBehaviorRegistry, BehaviorManifest, BehaviorScope,
)


def _manifest(
    behavior_id="maat_aggressive",
    scope=BehaviorScope.ENTITY,
    target="maat",
    reacts=("on_engaged",),
    priority=100,
):
    return BehaviorManifest(
        behavior_id=behavior_id, name="MaatAggressive",
        scope=scope, scope_target=target,
        reacts_to=reacts, priority=priority,
    )


def test_register_happy():
    r = AiBehaviorRegistry()
    assert r.register(manifest=_manifest()) is True


def test_register_blank_id_blocked():
    r = AiBehaviorRegistry()
    out = r.register(manifest=_manifest(behavior_id=""))
    assert out is False


def test_register_blank_target_blocked():
    r = AiBehaviorRegistry()
    out = r.register(manifest=_manifest(target=""))
    assert out is False


def test_register_no_reacts_blocked():
    r = AiBehaviorRegistry()
    out = r.register(manifest=_manifest(reacts=()))
    assert out is False


def test_register_duplicate_blocked():
    r = AiBehaviorRegistry()
    r.register(manifest=_manifest())
    out = r.register(manifest=_manifest())
    assert out is False


def test_install_happy():
    r = AiBehaviorRegistry()
    r.register(manifest=_manifest())
    out = r.install(
        entity_id="maat", behavior_id="maat_aggressive",
    )
    assert out is True
    assert r.behavior_for(entity_id="maat") == "maat_aggressive"


def test_install_unknown_behavior():
    r = AiBehaviorRegistry()
    out = r.install(entity_id="maat", behavior_id="ghost")
    assert out is False


def test_install_blank_entity():
    r = AiBehaviorRegistry()
    r.register(manifest=_manifest())
    out = r.install(
        entity_id="", behavior_id="maat_aggressive",
    )
    assert out is False


def test_install_replaces_prior():
    r = AiBehaviorRegistry()
    r.register(manifest=_manifest(behavior_id="a"))
    r.register(manifest=_manifest(behavior_id="b"))
    r.install(entity_id="maat", behavior_id="a")
    r.install(entity_id="maat", behavior_id="b")
    assert r.behavior_for(entity_id="maat") == "b"


def test_uninstall_happy():
    r = AiBehaviorRegistry()
    r.register(manifest=_manifest())
    r.install(entity_id="maat", behavior_id="maat_aggressive")
    out = r.uninstall(entity_id="maat")
    assert out is True
    assert r.behavior_for(entity_id="maat") is None


def test_uninstall_unknown():
    r = AiBehaviorRegistry()
    out = r.uninstall(entity_id="ghost")
    assert out is False


def test_behaviors_matching_by_entity():
    r = AiBehaviorRegistry()
    r.register(manifest=_manifest(
        behavior_id="a", scope=BehaviorScope.ENTITY, target="maat",
    ))
    out = r.behaviors_matching(entity_id="maat")
    assert len(out) == 1
    assert out[0].behavior_id == "a"


def test_behaviors_matching_by_family():
    r = AiBehaviorRegistry()
    r.register(manifest=_manifest(
        behavior_id="sahagin_pack",
        scope=BehaviorScope.FAMILY,
        target="sahagin",
    ))
    out = r.behaviors_matching(family="sahagin")
    assert len(out) == 1


def test_behaviors_matching_by_job():
    r = AiBehaviorRegistry()
    r.register(manifest=_manifest(
        behavior_id="whm_smart_curing",
        scope=BehaviorScope.JOB,
        target="WHM",
    ))
    out = r.behaviors_matching(job="WHM")
    assert len(out) == 1


def test_behaviors_matching_priority_order():
    r = AiBehaviorRegistry()
    r.register(manifest=_manifest(
        behavior_id="lo", scope=BehaviorScope.ENTITY,
        target="maat", priority=10,
    ))
    r.register(manifest=_manifest(
        behavior_id="hi", scope=BehaviorScope.ENTITY,
        target="maat", priority=100,
    ))
    out = r.behaviors_matching(entity_id="maat")
    assert out[0].behavior_id == "hi"
    assert out[1].behavior_id == "lo"


def test_behaviors_matching_no_match():
    r = AiBehaviorRegistry()
    r.register(manifest=_manifest())
    out = r.behaviors_matching(entity_id="other_entity")
    assert out == []


def test_behavior_for_unknown_entity():
    r = AiBehaviorRegistry()
    assert r.behavior_for(entity_id="ghost") is None


def test_manifest_lookup():
    r = AiBehaviorRegistry()
    r.register(manifest=_manifest())
    m = r.manifest(behavior_id="maat_aggressive")
    assert m is not None
    assert m.priority == 100


def test_manifest_unknown():
    r = AiBehaviorRegistry()
    assert r.manifest(behavior_id="ghost") is None


def test_three_behavior_scopes():
    assert len(list(BehaviorScope)) == 3


def test_total_counts():
    r = AiBehaviorRegistry()
    r.register(manifest=_manifest(behavior_id="a"))
    r.register(manifest=_manifest(behavior_id="b"))
    r.install(entity_id="m1", behavior_id="a")
    assert r.total_registered() == 2
    assert r.total_installed() == 1
