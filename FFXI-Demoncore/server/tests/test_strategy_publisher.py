"""Tests for strategy_publisher."""
from __future__ import annotations

from server.strategy_publisher import (
    ClearProof, EncounterKind, EncounterRef, GuideStatus,
    StrategyPublisher,
)


def _enc():
    return EncounterRef(
        kind=EncounterKind.HTBC, encounter_id="maat",
        display_name="Maat",
    )


def _setup():
    p = StrategyPublisher()
    p.set_mentor_status(
        author_id="chharith", is_mentor=True,
        display_name="Chharith",
    )
    return p


def _publish(p, **overrides):
    kwargs = dict(
        author_id="chharith", encounter=_enc(),
        title="Maat as BST", body="Use Carby tank, ...",
        clear_proof=ClearProof(clears_count=5, wins_count=4),
        published_at=1000,
    )
    kwargs.update(overrides)
    return p.publish(**kwargs)


def test_eligibility_happy():
    p = _setup()
    elig = p.check_eligibility(
        author_id="chharith", encounter=_enc(),
        clear_proof=ClearProof(clears_count=5, wins_count=4),
    )
    assert elig.eligible is True


def test_non_mentor_rejected():
    p = StrategyPublisher()
    elig = p.check_eligibility(
        author_id="someone", encounter=_enc(),
        clear_proof=ClearProof(clears_count=5, wins_count=4),
    )
    assert elig.failure_reason == "not_mentor"


def test_insufficient_clears_rejected():
    p = _setup()
    elig = p.check_eligibility(
        author_id="chharith", encounter=_enc(),
        clear_proof=ClearProof(clears_count=2, wins_count=2),
    )
    assert elig.failure_reason == "insufficient_clears"


def test_low_win_rate_rejected():
    p = _setup()
    elig = p.check_eligibility(
        author_id="chharith", encounter=_enc(),
        clear_proof=ClearProof(clears_count=10, wins_count=3),
    )
    assert elig.failure_reason == "win_rate_too_low"


def test_blank_author_rejected():
    p = _setup()
    elig = p.check_eligibility(
        author_id="", encounter=_enc(),
        clear_proof=ClearProof(clears_count=5, wins_count=4),
    )
    assert elig.failure_reason == "author_id_required"


def test_blank_encounter_rejected():
    p = _setup()
    elig = p.check_eligibility(
        author_id="chharith",
        encounter=EncounterRef(
            kind=EncounterKind.NM, encounter_id="",
            display_name="",
        ),
        clear_proof=ClearProof(clears_count=5, wins_count=4),
    )
    assert elig.failure_reason == "encounter_required"


def test_publish_happy():
    p = _setup()
    gid = _publish(p)
    assert gid is not None
    assert gid.startswith("sg_")


def test_publish_blank_title_blocked():
    p = _setup()
    assert _publish(p, title="   ") is None


def test_publish_blank_body_blocked():
    p = _setup()
    assert _publish(p, body="   ") is None


def test_publish_returns_none_when_ineligible():
    p = StrategyPublisher()
    assert _publish(p, author_id="not_mentor") is None


def test_lookup_returns_published():
    p = _setup()
    gid = _publish(p)
    g = p.lookup(guide_id=gid)
    assert g is not None
    assert g.author_display_name == "Chharith"
    assert g.encounter.encounter_id == "maat"


def test_lookup_unknown_none():
    p = _setup()
    assert p.lookup(guide_id="ghost") is None


def test_content_hash_stable():
    p = _setup()
    gid = _publish(p)
    g = p.lookup(guide_id=gid)
    assert len(g.content_hash) == 64


def test_clears_and_winrate_recorded():
    p = _setup()
    gid = _publish(
        p, clear_proof=ClearProof(
            clears_count=10, wins_count=8,
        ),
    )
    g = p.lookup(guide_id=gid)
    assert g.clears_at_publish == 10
    assert g.win_rate_at_publish == 0.8


def test_unique_guide_ids():
    p = _setup()
    gid1 = _publish(p)
    gid2 = _publish(p, title="Maat v2")
    assert gid1 != gid2


def test_by_author_lists_all():
    p = _setup()
    _publish(p)
    _publish(p, title="Maat speed run")
    out = p.by_author(author_id="chharith")
    assert len(out) == 2


def test_by_author_unknown_empty():
    p = _setup()
    assert p.by_author(author_id="nobody") == []


def test_by_encounter_filters():
    p = _setup()
    gid = _publish(p)
    other_enc = EncounterRef(
        kind=EncounterKind.NM, encounter_id="aerial_manta",
        display_name="Aerial Manta",
    )
    _publish(p, encounter=other_enc, title="Manta tips")
    out = p.by_encounter(encounter=_enc())
    assert len(out) == 1
    assert out[0].guide_id == gid


def test_by_encounter_excludes_unlisted():
    p = _setup()
    gid = _publish(p)
    p.unlist(author_id="chharith", guide_id=gid)
    assert p.by_encounter(encounter=_enc()) == []


def test_unlist_owner():
    p = _setup()
    gid = _publish(p)
    assert p.unlist(
        author_id="chharith", guide_id=gid,
    ) is True
    assert p.lookup(
        guide_id=gid,
    ).status == GuideStatus.UNLISTED


def test_unlist_non_owner_blocked():
    p = _setup()
    gid = _publish(p)
    assert p.unlist(
        author_id="impostor", guide_id=gid,
    ) is False


def test_relist_after_unlist():
    p = _setup()
    gid = _publish(p)
    p.unlist(author_id="chharith", guide_id=gid)
    assert p.relist(
        author_id="chharith", guide_id=gid,
    ) is True
    assert p.lookup(
        guide_id=gid,
    ).status == GuideStatus.PUBLISHED


def test_relist_when_not_unlisted_blocked():
    p = _setup()
    gid = _publish(p)
    assert p.relist(
        author_id="chharith", guide_id=gid,
    ) is False


def test_revoke_terminal():
    p = _setup()
    gid = _publish(p)
    assert p.revoke(
        guide_id=gid, reason="encourages_exploit",
    ) is True
    assert p.lookup(
        guide_id=gid,
    ).status == GuideStatus.REVOKED


def test_revoke_blank_reason_blocked():
    p = _setup()
    gid = _publish(p)
    assert p.revoke(guide_id=gid, reason="") is False


def test_revoked_cannot_be_unlisted():
    p = _setup()
    gid = _publish(p)
    p.revoke(guide_id=gid, reason="bad")
    assert p.unlist(
        author_id="chharith", guide_id=gid,
    ) is False


def test_total_published_excludes_unlisted():
    p = _setup()
    gid1 = _publish(p)
    _publish(p, title="another")
    p.unlist(author_id="chharith", guide_id=gid1)
    assert p.total_published() == 1


def test_total_entries_includes_all():
    p = _setup()
    _publish(p)
    _publish(p, title="another")
    assert p.total_entries() == 2


def test_clear_proof_zero_clears_winrate_zero():
    cp = ClearProof(clears_count=0, wins_count=0)
    assert cp.win_rate == 0.0


def test_five_encounter_kinds():
    assert len(list(EncounterKind)) == 5


def test_four_guide_statuses():
    assert len(list(GuideStatus)) == 4
