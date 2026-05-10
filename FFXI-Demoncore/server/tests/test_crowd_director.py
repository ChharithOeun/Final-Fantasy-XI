"""Tests for crowd_director."""
from __future__ import annotations

import pytest

from server.crowd_director import (
    Archetype,
    CrowdAgent,
    CrowdDirector,
    GreetPolicy,
    MIN_POD_DISTANCE_M,
    MIN_SOCIAL_DISTANCE_M,
    PLAYER_AWARE_RADIUS_M,
)


# ---- enum coverage ----

def test_ten_archetypes():
    assert len(list(Archetype)) == 10


def test_greet_policies_present():
    assert {p for p in GreetPolicy} == {
        GreetPolicy.WAVE,
        GreetPolicy.NOD,
        GreetPolicy.STOIC,
        GreetPolicy.SIDLE_AWAY,
    }


def test_constants_sane():
    assert MIN_SOCIAL_DISTANCE_M == 1.2
    assert MIN_POD_DISTANCE_M == 0.5
    assert PLAYER_AWARE_RADIUS_M == 4.0


# ---- registration ----

def test_register_and_get():
    d = CrowdDirector()
    a = CrowdAgent(
        agent_id="a1", npc_id="n1",
        zone_id="bastok_markets",
        archetype=Archetype.VENDOR_BUSY,
        home_pos_xyz=(0, 0, 0),
        current_pos_xyz=(0, 0, 0),
    )
    d.register_agent(a)
    assert d.get("a1") is a
    assert d.has("a1")


def test_register_empty_id_raises():
    d = CrowdDirector()
    with pytest.raises(ValueError):
        d.register_agent(CrowdAgent(
            agent_id="",
            npc_id="n",
            zone_id="z",
            archetype=Archetype.IDLER_LEAN,
            home_pos_xyz=(0, 0, 0),
            current_pos_xyz=(0, 0, 0),
        ))


def test_register_duplicate_raises():
    d = CrowdDirector()
    a = CrowdAgent(
        agent_id="a1", npc_id="n",
        zone_id="z",
        archetype=Archetype.GUARD_PATROL,
        home_pos_xyz=(0, 0, 0),
        current_pos_xyz=(0, 0, 0),
    )
    d.register_agent(a)
    with pytest.raises(ValueError):
        d.register_agent(a)


def test_get_unknown_raises():
    d = CrowdDirector()
    with pytest.raises(KeyError):
        d.get("ghost")


# ---- populate_zone ----

def test_populate_zone_spawns_to_target():
    d = CrowdDirector()
    spawned = d.populate_zone("bastok_markets", 5)
    assert len(spawned) == 5
    assert d.density_of("bastok_markets") == 5


def test_populate_zone_zero_density_dungeon():
    d = CrowdDirector()
    d.populate_zone("crawlers_nest", 0)
    assert d.density_of("crawlers_nest") == 0


def test_populate_zone_negative_raises():
    d = CrowdDirector()
    with pytest.raises(ValueError):
        d.populate_zone("z", -1)


def test_populate_zone_idempotent_at_target():
    d = CrowdDirector()
    d.populate_zone("bastok_markets", 5)
    second = d.populate_zone("bastok_markets", 5)
    assert second == ()
    assert d.density_of("bastok_markets") == 5


def test_populate_zone_despawns_when_over_target():
    d = CrowdDirector()
    d.populate_zone("z", 5)
    affected = d.populate_zone("z", 2)
    assert len(affected) == 3
    assert d.density_of("z") == 2


def test_populate_uses_zone_specific_density():
    d = CrowdDirector()
    d.populate_zone("bastok_markets", 40)
    d.populate_zone("north_gustaberg", 8)
    d.populate_zone("crawlers_nest", 0)
    assert d.density_of("bastok_markets") == 40
    assert d.density_of("north_gustaberg") == 8
    assert d.density_of("crawlers_nest") == 0


def test_agents_in_zone_filters():
    d = CrowdDirector()
    d.populate_zone("a", 3)
    d.populate_zone("b", 2)
    a_agents = d.agents_in_zone("a")
    assert len(a_agents) == 3
    assert all(x.zone_id == "a" for x in a_agents)


def test_agents_in_zone_sorted():
    d = CrowdDirector()
    d.populate_zone("z", 3)
    ids = [a.agent_id for a in d.agents_in_zone("z")]
    assert ids == sorted(ids)


# ---- despawn ----

def test_despawn_marks_agent():
    d = CrowdDirector()
    d.populate_zone("z", 1)
    aid = d.agents_in_zone("z")[0].agent_id
    d.despawn_agent(aid)
    assert d.density_of("z") == 0
    assert d.get(aid).despawned is True


# ---- conversation pods ----

def test_spawn_conversation_pod():
    d = CrowdDirector()
    pid = d.spawn_conversation_pod(
        "bastok_markets", (0, 0, 0), 3,
    )
    assert d.has_pod(pid)
    assert d.density_of("bastok_markets") == 3


def test_pod_member_count_validated():
    d = CrowdDirector()
    with pytest.raises(ValueError):
        d.spawn_conversation_pod("z", (0, 0, 0), 1)
    with pytest.raises(ValueError):
        d.spawn_conversation_pod("z", (0, 0, 0), 5)


def test_pod_members_know_partners():
    d = CrowdDirector()
    pid = d.spawn_conversation_pod("z", (0, 0, 0), 3)
    members = d.agents_in_zone("z")
    assert all(a.pod_id == pid for a in members)
    for a in members:
        assert len(a.conversation_partner_ids) == 2
        assert a.agent_id not in a.conversation_partner_ids


def test_pods_in_zone_listing():
    d = CrowdDirector()
    p1 = d.spawn_conversation_pod("z", (0, 0, 0), 2)
    p2 = d.spawn_conversation_pod("z", (3, 0, 0), 2)
    p3 = d.spawn_conversation_pod("other_z", (0, 0, 0), 2)
    in_z = d.pods_in_zone("z")
    assert p1 in in_z
    assert p2 in in_z
    assert p3 not in in_z


def test_pod_expires_after_lifetime():
    d = CrowdDirector(pod_lifetime_s=1.0)
    pid = d.spawn_conversation_pod("z", (0, 0, 0), 2)
    rep = d.tick(2.0, player_pos=(100, 0, 100))
    assert pid in rep["despawned_pods"]
    assert not d.has_pod(pid)


def test_pod_age_advances():
    d = CrowdDirector(pod_lifetime_s=10.0)
    pid = d.spawn_conversation_pod("z", (0, 0, 0), 2)
    d.tick(1.0, player_pos=(100, 0, 100))
    assert d.pod_age(pid) == pytest.approx(1.0)


def test_pod_age_unknown_raises():
    d = CrowdDirector()
    with pytest.raises(KeyError):
        d.pod_age("phantom_pod")


# ---- player awareness ----

def test_player_aware_agents_within_radius():
    d = CrowdDirector()
    d.register_agent(CrowdAgent(
        agent_id="near", npc_id="n_near",
        zone_id="z",
        archetype=Archetype.VENDOR_BUSY,
        home_pos_xyz=(1, 0, 0),
        current_pos_xyz=(1, 0, 0),
    ))
    d.register_agent(CrowdAgent(
        agent_id="far", npc_id="n_far",
        zone_id="z",
        archetype=Archetype.VENDOR_BUSY,
        home_pos_xyz=(20, 0, 0),
        current_pos_xyz=(20, 0, 0),
    ))
    aware = d.player_aware_agents((0, 0, 0))
    ids = [a.agent_id for a in aware]
    assert "near" in ids
    assert "far" not in ids


def test_player_aware_radius_override():
    d = CrowdDirector()
    d.register_agent(CrowdAgent(
        agent_id="far", npc_id="n",
        zone_id="z",
        archetype=Archetype.VENDOR_BUSY,
        home_pos_xyz=(10, 0, 0),
        current_pos_xyz=(10, 0, 0),
    ))
    aware = d.player_aware_agents(
        (0, 0, 0), radius_m=50.0,
    )
    assert len(aware) == 1


def test_tick_marks_is_player_aware():
    d = CrowdDirector()
    d.register_agent(CrowdAgent(
        agent_id="a", npc_id="n",
        zone_id="z",
        archetype=Archetype.VENDOR_BUSY,
        home_pos_xyz=(1, 0, 0),
        current_pos_xyz=(1, 0, 0),
    ))
    rep = d.tick(0.1, player_pos=(0, 0, 0))
    assert d.get("a").is_player_aware is True
    assert rep["aware_count"] >= 1


def test_tick_clears_is_player_aware_when_far():
    d = CrowdDirector()
    d.register_agent(CrowdAgent(
        agent_id="a", npc_id="n",
        zone_id="z",
        archetype=Archetype.VENDOR_BUSY,
        home_pos_xyz=(1, 0, 0),
        current_pos_xyz=(1, 0, 0),
    ))
    d.tick(0.1, player_pos=(0, 0, 0))
    d.tick(0.1, player_pos=(100, 0, 100))
    assert d.get("a").is_player_aware is False


def test_greet_policy_per_archetype():
    d = CrowdDirector()
    d.register_agent(CrowdAgent(
        agent_id="vendor", npc_id="n",
        zone_id="z",
        archetype=Archetype.VENDOR_BUSY,
        home_pos_xyz=(0, 0, 0),
        current_pos_xyz=(0, 0, 0),
    ))
    d.register_agent(CrowdAgent(
        agent_id="guard", npc_id="g",
        zone_id="z",
        archetype=Archetype.GUARD_PATROL,
        home_pos_xyz=(0, 0, 0),
        current_pos_xyz=(0, 0, 0),
    ))
    d.register_agent(CrowdAgent(
        agent_id="kid", npc_id="k",
        zone_id="z",
        archetype=Archetype.CHILD_PLAY,
        home_pos_xyz=(0, 0, 0),
        current_pos_xyz=(0, 0, 0),
    ))
    assert d.greet_policy_for("vendor") == GreetPolicy.WAVE
    assert d.greet_policy_for("guard") == GreetPolicy.STOIC
    assert d.greet_policy_for("kid") == GreetPolicy.SIDLE_AWAY


# ---- anti-clumping ----

def test_anti_clumping_repels_close_agents():
    d = CrowdDirector()
    d.register_agent(CrowdAgent(
        agent_id="a", npc_id="na",
        zone_id="z",
        archetype=Archetype.IDLER_LEAN,
        home_pos_xyz=(0, 0, 0),
        current_pos_xyz=(0, 0, 0),
    ))
    d.register_agent(CrowdAgent(
        agent_id="b", npc_id="nb",
        zone_id="z",
        archetype=Archetype.IDLER_LEAN,
        home_pos_xyz=(0.5, 0, 0),
        current_pos_xyz=(0.5, 0, 0),
    ))
    rep = d.tick(0.1, player_pos=(100, 0, 100))
    assert ("a", "b") in rep["repelled_pairs"]
    # b moved away from a
    assert d.get("b").current_pos_xyz[0] > 0.5


def test_anti_clumping_does_not_repel_in_other_zone():
    d = CrowdDirector()
    d.register_agent(CrowdAgent(
        agent_id="a", npc_id="na",
        zone_id="z1",
        archetype=Archetype.IDLER_LEAN,
        home_pos_xyz=(0, 0, 0),
        current_pos_xyz=(0, 0, 0),
    ))
    d.register_agent(CrowdAgent(
        agent_id="b", npc_id="nb",
        zone_id="z2",
        archetype=Archetype.IDLER_LEAN,
        home_pos_xyz=(0.5, 0, 0),
        current_pos_xyz=(0.5, 0, 0),
    ))
    rep = d.tick(0.1, player_pos=(100, 0, 100))
    assert rep["repelled_pairs"] == []


def test_pod_members_have_smaller_personal_space():
    d = CrowdDirector()
    pid = d.spawn_conversation_pod(
        "z", (0, 0, 0), 3,
    )
    # Pod members are arranged on a 0.6m radius, so they're
    # ~1.04m apart — fine for pods (0.5m), would be repelled
    # if treated as general agents (1.2m).
    rep = d.tick(0.1, player_pos=(100, 0, 100))
    # No repulsion expected since within-pod threshold is
    # 0.5 m and inter-member distance > 1.0 m.
    assert rep["repelled_pairs"] == []


# ---- eye-system delegation ----

class _MockEyeSystem:
    def __init__(self) -> None:
        self.registered: list[str] = []
        self.set_targets: list[tuple[str, str]] = []
        self._known: set[str] = set()

    def has(self, npc_id: str) -> bool:
        return npc_id in self._known

    def register_eyes(self, npc_id: str) -> None:
        self.registered.append(npc_id)
        self._known.add(npc_id)

    def set_look_target(
        self, npc_id: str, target_id: str | None,
    ) -> None:
        self.set_targets.append((npc_id, target_id or ""))


def test_tick_delegates_eye_contact():
    d = CrowdDirector()
    d.register_agent(CrowdAgent(
        agent_id="a", npc_id="npc_eye_a",
        zone_id="z",
        archetype=Archetype.VENDOR_BUSY,
        home_pos_xyz=(1, 0, 0),
        current_pos_xyz=(1, 0, 0),
    ))
    eyes = _MockEyeSystem()
    d.tick(
        0.1, player_pos=(0, 0, 0),
        eye_system=eyes, player_id="player",
    )
    assert "npc_eye_a" in eyes.registered
    assert ("npc_eye_a", "player") in eyes.set_targets


# ---- diagnostics + edge ----

def test_alive_agents_excludes_despawned():
    d = CrowdDirector()
    d.populate_zone("z", 2)
    aid = d.agents_in_zone("z")[0].agent_id
    d.despawn_agent(aid)
    alive = d.alive_agents()
    assert all(not a.despawned for a in alive)
    assert len(alive) == 1


def test_all_zones_lists_active():
    d = CrowdDirector()
    d.populate_zone("a", 1)
    d.populate_zone("b", 1)
    assert set(d.all_zones()) == {"a", "b"}


def test_tick_zero_dt_raises():
    d = CrowdDirector()
    with pytest.raises(ValueError):
        d.tick(0.0, player_pos=(0, 0, 0))


def test_repeat_populate_grows_count():
    d = CrowdDirector()
    d.populate_zone("z", 3)
    d.populate_zone("z", 6)
    assert d.density_of("z") == 6


def test_pod_inflates_zone_density():
    d = CrowdDirector()
    d.populate_zone("z", 5)
    d.spawn_conversation_pod("z", (0, 0, 0), 3)
    assert d.density_of("z") == 8


def test_after_pod_expires_partners_cleared():
    d = CrowdDirector(pod_lifetime_s=1.0)
    d.spawn_conversation_pod("z", (0, 0, 0), 3)
    members = d.agents_in_zone("z")
    d.tick(2.0, player_pos=(100, 0, 100))
    for a in members:
        assert a.pod_id is None
        assert a.conversation_partner_ids == ()
