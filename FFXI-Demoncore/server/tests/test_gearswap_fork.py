"""Tests for gearswap_fork."""
from __future__ import annotations

from server.gearswap_adopt import AdoptMode, GearswapAdopt
from server.gearswap_fork import GearswapFork
from server.gearswap_publisher import GearswapPublisher


def _seed():
    p = GearswapPublisher()
    for aid, name in [
        ("chharith", "Chharith"),
        ("bob", "Bob"),
        ("cara", "Cara"),
    ]:
        p.set_mentor_status(
            author_id=aid, is_mentor=True, display_name=name,
        )
    pid_root = p.publish(
        author_id="chharith", job="RDM",
        addon_id="rdm_chharith", lua_source="-- root",
        reputation_snapshot=80, hours_played_on_job=500,
        published_at=1000,
    )
    a = GearswapAdopt(_publisher=p)
    f = GearswapFork(_publisher=p)
    return p, a, f, pid_root


def test_fork_happy():
    _, _, f, pid_root = _seed()
    new_pid = f.fork(
        forker_id="bob", source_publish_id=pid_root,
        job="RDM", addon_id="rdm_bob_tuned",
        lua_source="-- bob's tweaks",
        hours_played_on_job=300, reputation_snapshot=10,
        published_at=2000,
    )
    assert new_pid is not None
    assert f.fork_of(publish_id=new_pid) == pid_root


def test_fork_unknown_source_blocked():
    _, _, f, _ = _seed()
    out = f.fork(
        forker_id="bob", source_publish_id="ghost",
        job="RDM", addon_id="rdm_bob",
        lua_source="-- x", hours_played_on_job=300,
        reputation_snapshot=10, published_at=2000,
    )
    assert out is None


def test_fork_revoked_source_blocked():
    p, _, f, pid_root = _seed()
    p.revoke(publish_id=pid_root, reason="exploit")
    out = f.fork(
        forker_id="bob", source_publish_id=pid_root,
        job="RDM", addon_id="rdm_bob",
        lua_source="-- x", hours_played_on_job=300,
        reputation_snapshot=10, published_at=2000,
    )
    assert out is None


def test_fork_unlisted_source_still_allowed():
    """The author parking their own listing shouldn't
    stop people who already saw it from publishing
    derivative work — UNLISTED forks-of are OK."""
    p, _, f, pid_root = _seed()
    p.unlist(author_id="chharith", publish_id=pid_root)
    out = f.fork(
        forker_id="bob", source_publish_id=pid_root,
        job="RDM", addon_id="rdm_bob",
        lua_source="-- x", hours_played_on_job=300,
        reputation_snapshot=10, published_at=2000,
    )
    assert out is not None


def test_fork_blocked_when_forker_not_eligible():
    """Forking still goes through publisher gates."""
    _, _, f, pid_root = _seed()
    out = f.fork(
        forker_id="bob", source_publish_id=pid_root,
        job="RDM", addon_id="rdm_bob",
        lua_source="-- x",
        hours_played_on_job=10,   # below the 200 gate
        reputation_snapshot=10, published_at=2000,
    )
    assert out is None


def test_fork_self_allowed():
    """Refactoring your own build into a new lineage
    is fine."""
    _, _, f, pid_root = _seed()
    out = f.fork(
        forker_id="chharith", source_publish_id=pid_root,
        job="RDM", addon_id="rdm_chharith_v2",
        lua_source="-- self-fork", hours_played_on_job=500,
        reputation_snapshot=80, published_at=2000,
    )
    assert out is not None


def test_fork_chain_two_levels():
    _, _, f, pid_root = _seed()
    pid_bob = f.fork(
        forker_id="bob", source_publish_id=pid_root,
        job="RDM", addon_id="rdm_bob",
        lua_source="-- bob", hours_played_on_job=300,
        reputation_snapshot=10, published_at=2000,
    )
    pid_cara = f.fork(
        forker_id="cara", source_publish_id=pid_bob,
        job="RDM", addon_id="rdm_cara",
        lua_source="-- cara", hours_played_on_job=300,
        reputation_snapshot=10, published_at=3000,
    )
    chain = f.fork_chain(publish_id=pid_cara)
    assert chain == [pid_cara, pid_bob, pid_root]


def test_fork_chain_root_only_self():
    _, _, f, pid_root = _seed()
    chain = f.fork_chain(publish_id=pid_root)
    assert chain == [pid_root]


def test_fork_of_unknown_none():
    _, _, f, _ = _seed()
    assert f.fork_of(publish_id="ghost") is None


def test_descendants_one_level():
    _, _, f, pid_root = _seed()
    pid_bob = f.fork(
        forker_id="bob", source_publish_id=pid_root,
        job="RDM", addon_id="rdm_bob",
        lua_source="-- b", hours_played_on_job=300,
        reputation_snapshot=10, published_at=2000,
    )
    out = f.descendants(publish_id=pid_root)
    assert out == [pid_bob]


def test_descendants_two_levels():
    _, _, f, pid_root = _seed()
    pid_bob = f.fork(
        forker_id="bob", source_publish_id=pid_root,
        job="RDM", addon_id="rdm_bob",
        lua_source="-- b", hours_played_on_job=300,
        reputation_snapshot=10, published_at=2000,
    )
    pid_cara = f.fork(
        forker_id="cara", source_publish_id=pid_bob,
        job="RDM", addon_id="rdm_cara",
        lua_source="-- c", hours_played_on_job=300,
        reputation_snapshot=10, published_at=3000,
    )
    out = f.descendants(publish_id=pid_root)
    assert sorted(out) == sorted([pid_bob, pid_cara])


def test_descendants_empty_when_no_forks():
    _, _, f, pid_root = _seed()
    assert f.descendants(publish_id=pid_root) == []


def test_influence_count_aggregates_descendants():
    _, a, f, pid_root = _seed()
    pid_bob = f.fork(
        forker_id="bob", source_publish_id=pid_root,
        job="RDM", addon_id="rdm_bob",
        lua_source="-- b", hours_played_on_job=300,
        reputation_snapshot=10, published_at=2000,
    )
    # 3 people adopt Bob's fork
    for player in ["x", "y", "z"]:
        a.adopt(
            player_id=player, publish_id=pid_bob,
            mode=AdoptMode.USE_AS_IS, adopted_at=3000,
        )
    n = f.influence_count(author_id="chharith", _adopt=a)
    assert n == 3


def test_influence_count_two_level_chain():
    _, a, f, pid_root = _seed()
    pid_bob = f.fork(
        forker_id="bob", source_publish_id=pid_root,
        job="RDM", addon_id="rdm_bob",
        lua_source="-- b", hours_played_on_job=300,
        reputation_snapshot=10, published_at=2000,
    )
    pid_cara = f.fork(
        forker_id="cara", source_publish_id=pid_bob,
        job="RDM", addon_id="rdm_cara",
        lua_source="-- c", hours_played_on_job=300,
        reputation_snapshot=10, published_at=3000,
    )
    a.adopt(
        player_id="p1", publish_id=pid_bob,
        mode=AdoptMode.USE_AS_IS, adopted_at=4000,
    )
    a.adopt(
        player_id="p2", publish_id=pid_cara,
        mode=AdoptMode.USE_AS_IS, adopted_at=4000,
    )
    # Chharith's influence reaches both grandchild and child
    n = f.influence_count(author_id="chharith", _adopt=a)
    assert n == 2


def test_influence_count_excludes_direct_adopts():
    _, a, f, pid_root = _seed()
    a.adopt(
        player_id="p1", publish_id=pid_root,
        mode=AdoptMode.USE_AS_IS, adopted_at=2000,
    )
    # Direct adopters don't count as influence
    n = f.influence_count(author_id="chharith", _adopt=a)
    assert n == 0


def test_influence_count_unknown_author_zero():
    _, a, f, _ = _seed()
    assert f.influence_count(
        author_id="ghost", _adopt=a,
    ) == 0


def test_total_forks():
    _, _, f, pid_root = _seed()
    f.fork(
        forker_id="bob", source_publish_id=pid_root,
        job="RDM", addon_id="rdm_bob",
        lua_source="-- b", hours_played_on_job=300,
        reputation_snapshot=10, published_at=2000,
    )
    assert f.total_forks() == 1
