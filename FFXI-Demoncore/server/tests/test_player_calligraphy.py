"""Tests for player_calligraphy."""
from __future__ import annotations

from server.player_calligraphy import (
    PlayerCalligraphySystem, DocumentKind,
    InkQuality,
)


def _craft(s, **overrides):
    args = dict(
        scribe_id="bob",
        scribe_signature="Bob the Scribe",
        kind=DocumentKind.NOTE,
        title="Hello", body="Hello there friend.",
        ink_quality=InkQuality.STANDARD,
        effort_minutes=30, scribe_skill=70,
        crafted_day=10,
    )
    args.update(overrides)
    return s.craft(**args)


def test_craft_happy():
    s = PlayerCalligraphySystem()
    assert _craft(s) is not None


def test_craft_blank_scribe():
    s = PlayerCalligraphySystem()
    assert _craft(s, scribe_id="") is None


def test_craft_blank_title():
    s = PlayerCalligraphySystem()
    assert _craft(s, title="") is None


def test_craft_zero_effort():
    s = PlayerCalligraphySystem()
    assert _craft(s, effort_minutes=0) is None


def test_craft_invalid_skill():
    s = PlayerCalligraphySystem()
    assert _craft(s, scribe_skill=120) is None


def test_grade_combines_skill_ink_effort():
    s = PlayerCalligraphySystem()
    did = _craft(
        s, scribe_skill=70,
        ink_quality=InkQuality.MASTER,
        effort_minutes=100,
    )
    d = s.document(document_id=did)
    # 70 + 25 + min(15, 10) = 105 -> clamped 100
    assert d.craftsmanship_grade == 100


def test_grade_poor_ink_penalty():
    s = PlayerCalligraphySystem()
    did = _craft(
        s, scribe_skill=50,
        ink_quality=InkQuality.POOR,
        effort_minutes=10,
    )
    d = s.document(document_id=did)
    # 50 + (-10) + 1 = 41
    assert d.craftsmanship_grade == 41


def test_grade_clamps_at_zero():
    s = PlayerCalligraphySystem()
    did = _craft(
        s, scribe_skill=0,
        ink_quality=InkQuality.POOR,
        effort_minutes=1,
    )
    d = s.document(document_id=did)
    assert d.craftsmanship_grade == 0


def test_genuine_document_signed_authentic():
    s = PlayerCalligraphySystem()
    did = _craft(s)
    d = s.document(document_id=did)
    assert d.is_signed_authentic is True


def test_forge_creates_unauthentic():
    s = PlayerCalligraphySystem()
    did = s.forge(
        forger_id="cara",
        claimed_signature="Bob the Scribe",
        kind=DocumentKind.SCROLL_POEM,
        title="Forged Poem",
        body="Pretending to be Bob.",
        ink_quality=InkQuality.STANDARD,
        effort_minutes=30, forger_skill=80,
        crafted_day=15,
    )
    d = s.document(document_id=did)
    assert d.is_signed_authentic is False
    assert d.scribe_id == "cara"
    assert d.scribe_signature == "Bob the Scribe"


def test_authenticate_genuine_returns_false():
    s = PlayerCalligraphySystem()
    did = _craft(s)
    # Genuine doc -> always confirmed (False = not
    # forgery)
    assert s.authenticate(
        document_id=did, appraiser_skill=80,
    ) is False


def test_authenticate_skilled_appraiser_detects():
    s = PlayerCalligraphySystem()
    did = s.forge(
        forger_id="cara",
        claimed_signature="Bob",
        kind=DocumentKind.NOTE, title="x",
        body="x", ink_quality=InkQuality.STANDARD,
        effort_minutes=10, forger_skill=50,
        crafted_day=10,
    )
    # Forger grade = 50 + 0 + 1 = 51
    # Appraiser skill 80 > 51 -> detect
    assert s.authenticate(
        document_id=did, appraiser_skill=80,
    ) is True


def test_authenticate_low_skill_misses():
    s = PlayerCalligraphySystem()
    did = s.forge(
        forger_id="cara",
        claimed_signature="Bob",
        kind=DocumentKind.NOTE, title="x",
        body="x", ink_quality=InkQuality.MASTER,
        effort_minutes=120, forger_skill=80,
        crafted_day=10,
    )
    # Forger grade = 80+25+12=117 -> clamp 100
    # Appraiser 70 not > 100 -> miss
    assert s.authenticate(
        document_id=did, appraiser_skill=70,
    ) is False


def test_authenticate_invalid_skill():
    s = PlayerCalligraphySystem()
    did = _craft(s)
    assert s.authenticate(
        document_id=did, appraiser_skill=120,
    ) is None


def test_authenticate_unknown():
    s = PlayerCalligraphySystem()
    assert s.authenticate(
        document_id="ghost", appraiser_skill=80,
    ) is None


def test_documents_by_scribe():
    s = PlayerCalligraphySystem()
    _craft(s, scribe_id="bob", title="A")
    _craft(s, scribe_id="bob", title="B")
    _craft(s, scribe_id="other", title="C")
    out = s.documents_by_scribe(scribe_id="bob")
    assert len(out) == 2


def test_documents_signed_includes_forgeries():
    s = PlayerCalligraphySystem()
    _craft(
        s, scribe_id="bob",
        scribe_signature="Bob the Scribe",
    )
    s.forge(
        forger_id="cara",
        claimed_signature="Bob the Scribe",
        kind=DocumentKind.NOTE, title="forged",
        body="x", ink_quality=InkQuality.STANDARD,
        effort_minutes=10, forger_skill=40,
        crafted_day=10,
    )
    out = s.documents_signed(
        signature="Bob the Scribe",
    )
    assert len(out) == 2


def test_famous_works():
    s = PlayerCalligraphySystem()
    _craft(s, scribe_skill=90,
           ink_quality=InkQuality.MASTER,
           effort_minutes=60, title="Master Work")
    _craft(s, scribe_skill=30,
           ink_quality=InkQuality.POOR,
           effort_minutes=5, title="Crude Note")
    s.forge(
        forger_id="cara",
        claimed_signature="Bob",
        kind=DocumentKind.NOTE, title="Forged",
        body="x", ink_quality=InkQuality.MASTER,
        effort_minutes=120, forger_skill=90,
        crafted_day=10,
    )
    out = s.famous_works(min_grade=80)
    titles = [d.title for d in out]
    # Forgery excluded
    assert "Master Work" in titles
    assert "Forged" not in titles


def test_famous_works_invalid_min():
    s = PlayerCalligraphySystem()
    assert s.famous_works(min_grade=150) == []


def test_famous_works_sorted_descending():
    s = PlayerCalligraphySystem()
    _craft(s, scribe_skill=85, title="middling")
    _craft(s, scribe_skill=95, title="top")
    out = s.famous_works(min_grade=80)
    assert out[0].title == "top"


def test_document_unknown():
    s = PlayerCalligraphySystem()
    assert s.document(
        document_id="ghost",
    ) is None


def test_enum_counts():
    assert len(list(DocumentKind)) == 6
    assert len(list(InkQuality)) == 4
