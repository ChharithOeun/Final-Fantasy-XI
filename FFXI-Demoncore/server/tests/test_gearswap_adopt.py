"""Tests for gearswap_adopt."""
from __future__ import annotations

from server.gearswap_adopt import AdoptMode, GearswapAdopt
from server.gearswap_publisher import GearswapPublisher


def _seed():
    p = GearswapPublisher()
    p.set_mentor_status(
        author_id="chharith", is_mentor=True,
        display_name="Chharith",
    )
    pid = p.publish(
        author_id="chharith", job="RDM",
        addon_id="rdm_chharith",
        lua_source="-- v1 lua source",
        reputation_snapshot=80,
        hours_played_on_job=500, published_at=1000,
    )
    a = GearswapAdopt(_publisher=p)
    return p, a, pid


def test_adopt_happy():
    _, a, pid = _seed()
    out = a.adopt(
        player_id="bob", publish_id=pid,
        mode=AdoptMode.USE_AS_IS, adopted_at=2000,
    )
    assert out is not None
    assert out.player_id == "bob"
    assert out.mode == AdoptMode.USE_AS_IS


def test_adopt_clone_to_draft():
    _, a, pid = _seed()
    out = a.adopt(
        player_id="bob", publish_id=pid,
        mode=AdoptMode.CLONE_TO_DRAFT, adopted_at=2000,
    )
    assert out.mode == AdoptMode.CLONE_TO_DRAFT


def test_adopt_blank_player_blocked():
    _, a, pid = _seed()
    out = a.adopt(
        player_id="", publish_id=pid,
        mode=AdoptMode.USE_AS_IS, adopted_at=2000,
    )
    assert out is None


def test_adopt_unknown_publish_blocked():
    _, a, _ = _seed()
    out = a.adopt(
        player_id="bob", publish_id="ghost",
        mode=AdoptMode.USE_AS_IS, adopted_at=2000,
    )
    assert out is None


def test_adopt_revoked_blocked():
    p, a, pid = _seed()
    p.revoke(publish_id=pid, reason="exploit")
    out = a.adopt(
        player_id="bob", publish_id=pid,
        mode=AdoptMode.USE_AS_IS, adopted_at=2000,
    )
    assert out is None


def test_adopt_unlisted_blocked():
    p, a, pid = _seed()
    p.unlist(author_id="chharith", publish_id=pid)
    out = a.adopt(
        player_id="bob", publish_id=pid,
        mode=AdoptMode.USE_AS_IS, adopted_at=2000,
    )
    assert out is None


def test_double_adopt_blocked():
    _, a, pid = _seed()
    a.adopt(
        player_id="bob", publish_id=pid,
        mode=AdoptMode.USE_AS_IS, adopted_at=2000,
    )
    out = a.adopt(
        player_id="bob", publish_id=pid,
        mode=AdoptMode.USE_AS_IS, adopted_at=2100,
    )
    assert out is None


def test_un_adopt():
    _, a, pid = _seed()
    a.adopt(
        player_id="bob", publish_id=pid,
        mode=AdoptMode.USE_AS_IS, adopted_at=2000,
    )
    assert a.un_adopt(player_id="bob", publish_id=pid) is True
    assert a.has_adopted(
        player_id="bob", publish_id=pid,
    ) is False


def test_un_adopt_unknown():
    _, a, pid = _seed()
    out = a.un_adopt(player_id="bob", publish_id=pid)
    assert out is False


def test_un_adopt_then_re_adopt():
    _, a, pid = _seed()
    a.adopt(
        player_id="bob", publish_id=pid,
        mode=AdoptMode.USE_AS_IS, adopted_at=2000,
    )
    a.un_adopt(player_id="bob", publish_id=pid)
    out = a.adopt(
        player_id="bob", publish_id=pid,
        mode=AdoptMode.USE_AS_IS, adopted_at=3000,
    )
    assert out is not None


def test_has_adopted_true():
    _, a, pid = _seed()
    a.adopt(
        player_id="bob", publish_id=pid,
        mode=AdoptMode.USE_AS_IS, adopted_at=2000,
    )
    assert a.has_adopted(
        player_id="bob", publish_id=pid,
    ) is True


def test_has_adopted_false():
    _, a, pid = _seed()
    assert a.has_adopted(
        player_id="bob", publish_id=pid,
    ) is False


def test_adoptions_for_player():
    p, a, pid = _seed()
    pid2 = p.publish(
        author_id="chharith", job="BLM",
        addon_id="blm_chharith",
        lua_source="-- blm v1", reputation_snapshot=80,
        hours_played_on_job=300, published_at=1500,
    )
    a.adopt(
        player_id="bob", publish_id=pid,
        mode=AdoptMode.USE_AS_IS, adopted_at=2000,
    )
    a.adopt(
        player_id="bob", publish_id=pid2,
        mode=AdoptMode.CLONE_TO_DRAFT, adopted_at=2500,
    )
    out = a.adoptions_for(player_id="bob")
    assert len(out) == 2


def test_adoptions_for_unknown_empty():
    _, a, _ = _seed()
    assert a.adoptions_for(player_id="ghost") == []


def test_adopters_count():
    _, a, pid = _seed()
    a.adopt(
        player_id="bob", publish_id=pid,
        mode=AdoptMode.USE_AS_IS, adopted_at=2000,
    )
    a.adopt(
        player_id="cara", publish_id=pid,
        mode=AdoptMode.USE_AS_IS, adopted_at=2100,
    )
    assert a.adopters_count(publish_id=pid) == 2


def test_adopters_count_zero():
    _, a, pid = _seed()
    assert a.adopters_count(publish_id=pid) == 0


def test_adoption_records_content_hash():
    _, a, pid = _seed()
    record = a.adopt(
        player_id="bob", publish_id=pid,
        mode=AdoptMode.USE_AS_IS, adopted_at=2000,
    )
    assert len(record.content_hash_at_adopt) == 64


def test_outdated_version_false_when_unchanged():
    _, a, pid = _seed()
    a.adopt(
        player_id="bob", publish_id=pid,
        mode=AdoptMode.USE_AS_IS, adopted_at=2000,
    )
    assert a.has_outdated_version(
        player_id="bob", publish_id=pid,
    ) is False


def test_outdated_version_unknown_adoption():
    _, a, pid = _seed()
    assert a.has_outdated_version(
        player_id="ghost", publish_id=pid,
    ) is False


def test_total_adoptions():
    _, a, pid = _seed()
    a.adopt(
        player_id="bob", publish_id=pid,
        mode=AdoptMode.USE_AS_IS, adopted_at=2000,
    )
    a.adopt(
        player_id="cara", publish_id=pid,
        mode=AdoptMode.USE_AS_IS, adopted_at=2100,
    )
    assert a.total_adoptions() == 2


def test_two_adopt_modes():
    assert len(list(AdoptMode)) == 2
