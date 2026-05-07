"""Tests for strategy_credit_chain."""
from __future__ import annotations

from server.strategy_credit_chain import StrategyCreditChain
from server.strategy_publisher import (
    ClearProof, EncounterKind, EncounterRef,
    StrategyPublisher,
)


def _enc(eid="maat"):
    return EncounterRef(
        kind=EncounterKind.HTBC, encounter_id=eid,
        display_name=eid.title(),
    )


def _seed():
    p = StrategyPublisher()
    for aid, name in [
        ("chharith", "Chharith"),
        ("bob", "Bob"),
        ("cara", "Cara"),
    ]:
        p.set_mentor_status(
            author_id=aid, is_mentor=True, display_name=name,
        )
    g_root = p.publish(
        author_id="chharith", encounter=_enc(),
        title="Maat BST", body="root strat",
        clear_proof=ClearProof(clears_count=5, wins_count=4),
        published_at=1000,
    )
    g_bob = p.publish(
        author_id="bob", encounter=_enc(),
        title="Maat RDM (based on Chharith)", body="rdm twist",
        clear_proof=ClearProof(clears_count=4, wins_count=3),
        published_at=2000,
    )
    g_cara = p.publish(
        author_id="cara", encounter=_enc(),
        title="Maat WHM solo", body="cara strat",
        clear_proof=ClearProof(clears_count=4, wins_count=4),
        published_at=3000,
    )
    cc = StrategyCreditChain(_publisher=p)
    return p, cc, g_root, g_bob, g_cara


def test_cite_happy():
    _, cc, g_root, g_bob, _ = _seed()
    out = cc.cite(
        citing_guide_id=g_bob,
        cited_guide_ids=[g_root], cited_at=2500,
    )
    assert out is True


def test_cite_blank_citing_blocked():
    _, cc, g_root, _, _ = _seed()
    assert cc.cite(
        citing_guide_id="",
        cited_guide_ids=[g_root], cited_at=2500,
    ) is False


def test_cite_empty_cited_list_blocked():
    _, cc, _, g_bob, _ = _seed()
    assert cc.cite(
        citing_guide_id=g_bob,
        cited_guide_ids=[], cited_at=2500,
    ) is False


def test_cite_too_many_blocked():
    _, cc, _, g_bob, _ = _seed()
    assert cc.cite(
        citing_guide_id=g_bob,
        cited_guide_ids=[
            "g1", "g2", "g3", "g4", "g5", "g6",
        ],
        cited_at=2500,
    ) is False


def test_cite_unknown_citing_blocked():
    _, cc, g_root, _, _ = _seed()
    assert cc.cite(
        citing_guide_id="ghost",
        cited_guide_ids=[g_root], cited_at=2500,
    ) is False


def test_cite_unknown_cited_blocked():
    _, cc, _, g_bob, _ = _seed()
    assert cc.cite(
        citing_guide_id=g_bob,
        cited_guide_ids=["ghost"], cited_at=2500,
    ) is False


def test_cite_revoked_cited_blocked():
    p, cc, g_root, g_bob, _ = _seed()
    p.revoke(guide_id=g_root, reason="bad")
    assert cc.cite(
        citing_guide_id=g_bob,
        cited_guide_ids=[g_root], cited_at=2500,
    ) is False


def test_cite_unlisted_cited_allowed():
    """Author of cited guide unlisted theirs after Bob
    cited it; Bob's citation still records (UI can
    show the name even if the link is parked)."""
    p, cc, g_root, g_bob, _ = _seed()
    p.unlist(author_id="chharith", guide_id=g_root)
    assert cc.cite(
        citing_guide_id=g_bob,
        cited_guide_ids=[g_root], cited_at=2500,
    ) is True


def test_cite_dup_in_one_call_blocked():
    _, cc, g_root, g_bob, _ = _seed()
    assert cc.cite(
        citing_guide_id=g_bob,
        cited_guide_ids=[g_root, g_root], cited_at=2500,
    ) is False


def test_cite_set_once_immutable():
    _, cc, g_root, g_bob, g_cara = _seed()
    cc.cite(
        citing_guide_id=g_bob,
        cited_guide_ids=[g_root], cited_at=2500,
    )
    out = cc.cite(
        citing_guide_id=g_bob,
        cited_guide_ids=[g_cara], cited_at=2700,
    )
    assert out is False


def test_cite_self_allowed():
    _, cc, _, g_bob, _ = _seed()
    out = cc.cite(
        citing_guide_id=g_bob,
        cited_guide_ids=[g_bob], cited_at=2500,
    )
    assert out is True


def test_citations_of():
    _, cc, g_root, g_bob, _ = _seed()
    cc.cite(
        citing_guide_id=g_bob,
        cited_guide_ids=[g_root], cited_at=2500,
    )
    out = cc.citations_of(citing_guide_id=g_bob)
    assert out == [g_root]


def test_citations_of_unknown_empty():
    _, cc, _, _, _ = _seed()
    assert cc.citations_of(citing_guide_id="ghost") == []


def test_citations_to():
    _, cc, g_root, g_bob, g_cara = _seed()
    cc.cite(
        citing_guide_id=g_bob,
        cited_guide_ids=[g_root], cited_at=2500,
    )
    cc.cite(
        citing_guide_id=g_cara,
        cited_guide_ids=[g_root], cited_at=2700,
    )
    out = cc.citations_to(cited_guide_id=g_root)
    assert sorted(out) == sorted([g_bob, g_cara])


def test_cited_count_distinct_citers():
    _, cc, g_root, g_bob, g_cara = _seed()
    cc.cite(
        citing_guide_id=g_bob,
        cited_guide_ids=[g_root], cited_at=2500,
    )
    cc.cite(
        citing_guide_id=g_cara,
        cited_guide_ids=[g_root], cited_at=2700,
    )
    n = cc.cited_count(author_id="chharith")
    assert n == 2


def test_cited_count_unknown_zero():
    _, cc, _, _, _ = _seed()
    assert cc.cited_count(author_id="ghost") == 0


def test_resolve_lineage_chain():
    _, cc, g_root, g_bob, g_cara = _seed()
    cc.cite(
        citing_guide_id=g_bob,
        cited_guide_ids=[g_root], cited_at=2500,
    )
    cc.cite(
        citing_guide_id=g_cara,
        cited_guide_ids=[g_bob], cited_at=2700,
    )
    out = cc.resolve_lineage(guide_id=g_cara)
    assert out == [g_cara, g_bob, g_root]


def test_resolve_lineage_handles_cycle():
    _, cc, _, g_bob, g_cara = _seed()
    cc.cite(
        citing_guide_id=g_bob,
        cited_guide_ids=[g_cara], cited_at=2500,
    )
    cc.cite(
        citing_guide_id=g_cara,
        cited_guide_ids=[g_bob], cited_at=2700,
    )
    out = cc.resolve_lineage(guide_id=g_bob)
    # Both visited once; no infinite loop
    assert sorted(out) == sorted([g_bob, g_cara])


def test_total_citations():
    _, cc, g_root, g_bob, g_cara = _seed()
    cc.cite(
        citing_guide_id=g_bob,
        cited_guide_ids=[g_root, g_cara], cited_at=2500,
    )
    assert cc.total_citations() == 2
