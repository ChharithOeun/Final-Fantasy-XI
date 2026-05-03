"""Tests for mob aggro chain registry."""
from __future__ import annotations

import random

from server.mob_aggro_chain import (
    AggroChainEvent,
    DEFAULT_SHOUT_COOLDOWN_SECONDS,
    LinkAffinity,
    MobAggroChainRegistry,
    MobLinkProfile,
    affinity_probability,
)


def _profile(
    mob_id: str = "g1", family: str = "goblin",
    pos: tuple[int, int] = (0, 0),
    affinity: LinkAffinity = LinkAffinity.PACK,
    link_range: int = 15,
) -> MobLinkProfile:
    return MobLinkProfile(
        mob_id=mob_id, family_id=family,
        position_tile=pos,
        link_affinity=affinity,
        link_range_tiles=link_range,
    )


def test_affinity_probability_table():
    assert affinity_probability(LinkAffinity.PACK) == 1.0
    assert affinity_probability(LinkAffinity.FAMILY) == 0.7
    assert affinity_probability(LinkAffinity.OPPORTUNIST) == 0.4
    assert affinity_probability(LinkAffinity.LONE_WOLF) == 0.0


def test_register_and_get():
    reg = MobAggroChainRegistry()
    reg.register_mob(_profile())
    assert reg.get("g1") is not None
    assert reg.total_mobs() == 1


def test_unknown_instigator_returns_empty():
    reg = MobAggroChainRegistry()
    res = reg.resolve_chain(
        aggro_event=AggroChainEvent(
            instigator_mob_id="ghost",
            target_player_id="alice",
            occurred_at_seconds=0.0,
        ),
    )
    assert res.linked_mob_ids == ()
    assert "unknown" in res.notes


def test_lone_wolf_no_chain():
    reg = MobAggroChainRegistry()
    reg.register_mob(_profile(
        mob_id="bomb_1", family="bomb",
        affinity=LinkAffinity.LONE_WOLF,
    ))
    reg.register_mob(_profile(
        mob_id="bomb_2", family="bomb", pos=(2, 2),
        affinity=LinkAffinity.LONE_WOLF,
    ))
    res = reg.resolve_chain(
        aggro_event=AggroChainEvent(
            instigator_mob_id="bomb_1",
            target_player_id="alice",
            occurred_at_seconds=0.0,
        ),
        rng=random.Random(0),
    )
    assert res.linked_mob_ids == ()
    assert "lone wolf" in res.notes


def test_pack_chains_nearby_same_family():
    reg = MobAggroChainRegistry()
    reg.register_mob(_profile(mob_id="g1", pos=(0, 0)))
    reg.register_mob(_profile(mob_id="g2", pos=(5, 5)))
    reg.register_mob(_profile(mob_id="g3", pos=(8, 8)))
    res = reg.resolve_chain(
        aggro_event=AggroChainEvent(
            instigator_mob_id="g1",
            target_player_id="alice",
            occurred_at_seconds=0.0,
        ),
        rng=random.Random(0),
    )
    # PACK has 100% link prob, all in range
    assert set(res.linked_mob_ids) == {"g2", "g3"}


def test_out_of_range_skipped():
    reg = MobAggroChainRegistry()
    reg.register_mob(_profile(
        mob_id="g1", pos=(0, 0), link_range=10,
    ))
    reg.register_mob(_profile(
        mob_id="far", pos=(50, 50), link_range=10,
    ))
    res = reg.resolve_chain(
        aggro_event=AggroChainEvent(
            instigator_mob_id="g1",
            target_player_id="alice",
            occurred_at_seconds=0.0,
        ),
        rng=random.Random(0),
    )
    assert "far" in res.skipped_mob_ids
    assert "far" not in res.linked_mob_ids


def test_different_family_does_not_link():
    reg = MobAggroChainRegistry()
    reg.register_mob(_profile(mob_id="g1", family="goblin"))
    reg.register_mob(_profile(
        mob_id="o1", family="orc", pos=(2, 2),
    ))
    res = reg.resolve_chain(
        aggro_event=AggroChainEvent(
            instigator_mob_id="g1",
            target_player_id="alice",
            occurred_at_seconds=0.0,
        ),
        rng=random.Random(0),
    )
    # Orc is different family — not even considered
    assert "o1" not in res.linked_mob_ids
    assert "o1" not in res.skipped_mob_ids


def test_dead_mob_does_not_link():
    reg = MobAggroChainRegistry()
    reg.register_mob(_profile(mob_id="g1", pos=(0, 0)))
    reg.register_mob(_profile(mob_id="g2", pos=(2, 2)))
    reg.kill_mob(mob_id="g2")
    res = reg.resolve_chain(
        aggro_event=AggroChainEvent(
            instigator_mob_id="g1",
            target_player_id="alice",
            occurred_at_seconds=0.0,
        ),
        rng=random.Random(0),
    )
    assert "g2" not in res.linked_mob_ids


def test_opportunist_link_lower_rate():
    """OPPORTUNIST=0.4 -> some skips."""
    reg = MobAggroChainRegistry()
    for i in range(10):
        reg.register_mob(_profile(
            mob_id=f"u{i}", family="undead",
            pos=(i % 5, i // 5),
            affinity=LinkAffinity.OPPORTUNIST,
        ))
    rng = random.Random(11)
    res = reg.resolve_chain(
        aggro_event=AggroChainEvent(
            instigator_mob_id="u0",
            target_player_id="alice",
            occurred_at_seconds=0.0,
        ),
        rng=rng,
    )
    # ~40% link rate * 9 candidates = expected ~3-4 linked
    assert 0 < len(res.linked_mob_ids) < 9


def test_cooldown_blocks_repeat_chain_from_instigator():
    reg = MobAggroChainRegistry()
    reg.register_mob(_profile(mob_id="g1", pos=(0, 0)))
    reg.register_mob(_profile(mob_id="g2", pos=(2, 2)))
    rng = random.Random(0)
    a = reg.resolve_chain(
        aggro_event=AggroChainEvent(
            instigator_mob_id="g1",
            target_player_id="alice",
            occurred_at_seconds=0.0,
        ),
        rng=rng,
    )
    assert "g2" in a.linked_mob_ids
    # Try again immediately
    b = reg.resolve_chain(
        aggro_event=AggroChainEvent(
            instigator_mob_id="g1",
            target_player_id="bob",
            occurred_at_seconds=10.0,
        ),
        rng=rng,
    )
    assert "cooldown" in b.notes
    assert b.linked_mob_ids == ()


def test_cooldown_clears_after_window():
    reg = MobAggroChainRegistry()
    reg.register_mob(_profile(mob_id="g1", pos=(0, 0)))
    reg.register_mob(_profile(mob_id="g2", pos=(2, 2)))
    rng = random.Random(0)
    reg.resolve_chain(
        aggro_event=AggroChainEvent(
            instigator_mob_id="g1",
            target_player_id="alice",
            occurred_at_seconds=0.0,
        ),
        rng=rng,
    )
    later = reg.resolve_chain(
        aggro_event=AggroChainEvent(
            instigator_mob_id="g1",
            target_player_id="bob",
            occurred_at_seconds=DEFAULT_SHOUT_COOLDOWN_SECONDS + 1,
        ),
        rng=rng,
    )
    # Cooldown elapsed; chain available again
    assert "cooldown" not in (later.notes or "")


def test_chain_uses_lower_affinity():
    """A FAMILY-tier mob linking with a PACK-tier instigator
    uses the lower (FAMILY=0.7) probability, not PACK=1.0."""
    reg = MobAggroChainRegistry()
    reg.register_mob(_profile(
        mob_id="pack_leader", pos=(0, 0),
        affinity=LinkAffinity.PACK,
    ))
    reg.register_mob(_profile(
        mob_id="family_member", pos=(2, 2),
        affinity=LinkAffinity.FAMILY,
    ))
    # Run many trials; expected ~70% link rate
    linked_count = 0
    for trial in range(100):
        # New registry per trial to avoid cooldown
        r = MobAggroChainRegistry()
        r.register_mob(_profile(
            mob_id="pack_leader", pos=(0, 0),
            affinity=LinkAffinity.PACK,
        ))
        r.register_mob(_profile(
            mob_id="family_member", pos=(2, 2),
            affinity=LinkAffinity.FAMILY,
        ))
        res = r.resolve_chain(
            aggro_event=AggroChainEvent(
                instigator_mob_id="pack_leader",
                target_player_id="alice",
                occurred_at_seconds=0.0,
            ),
            rng=random.Random(trial),
        )
        if "family_member" in res.linked_mob_ids:
            linked_count += 1
    # ~70% expected; allow generous variance
    assert 50 < linked_count < 90


def test_same_family_pack_links_at_100():
    reg = MobAggroChainRegistry()
    reg.register_mob(_profile(mob_id="g1", pos=(0, 0)))
    for i in range(5):
        reg.register_mob(_profile(
            mob_id=f"g{i+2}", pos=(i+1, i+1),
        ))
    res = reg.resolve_chain(
        aggro_event=AggroChainEvent(
            instigator_mob_id="g1",
            target_player_id="alice",
            occurred_at_seconds=0.0,
        ),
        rng=random.Random(0),
    )
    # All 5 should link (PACK=1.0)
    assert len(res.linked_mob_ids) == 5


def test_full_lifecycle_goblin_pack_pulls():
    """A goblin pack of 6 with one undead lurker (FAMILY tier).
    Lone bomb nearby. Different families don't link; bomb is
    LONE_WOLF and never links anyway."""
    reg = MobAggroChainRegistry()
    for i in range(6):
        reg.register_mob(_profile(
            mob_id=f"g{i}", family="goblin",
            pos=(i, 0), affinity=LinkAffinity.PACK,
        ))
    reg.register_mob(_profile(
        mob_id="undead_1", family="goblin",
        pos=(2, 2), affinity=LinkAffinity.OPPORTUNIST,
    ))
    reg.register_mob(_profile(
        mob_id="bomb_1", family="bomb",
        pos=(2, 2), affinity=LinkAffinity.LONE_WOLF,
    ))
    res = reg.resolve_chain(
        aggro_event=AggroChainEvent(
            instigator_mob_id="g0",
            target_player_id="alice",
            occurred_at_seconds=0.0,
        ),
        rng=random.Random(99),
    )
    # 5 other goblins linked; undead is lower affinity (OPPORTUNIST)
    # bomb is wrong family
    assert all(
        gid in res.linked_mob_ids for gid in ("g1", "g2", "g3", "g4", "g5")
    )
    assert "bomb_1" not in res.linked_mob_ids
    assert "bomb_1" not in res.skipped_mob_ids
