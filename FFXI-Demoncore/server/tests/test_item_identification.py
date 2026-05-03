"""Tests for item identification."""
from __future__ import annotations

import random

from server.item_identification import (
    IdentifyMethod,
    IdentifyOutcome,
    ItemIdentificationRegistry,
    UnknownItem,
    UnknownTier,
)


def _unknown(
    unknown_id: str = "u1",
    tier: UnknownTier = UnknownTier.COMMON,
    real_id: str = "iron_sword",
    cursed: bool = False,
) -> UnknownItem:
    return UnknownItem(
        unknown_id=unknown_id,
        placeholder_descriptor="rusty blade",
        real_item_id=real_id, tier=tier,
        is_cursed=cursed,
    )


def test_register_unknown():
    reg = ItemIdentificationRegistry()
    assert reg.register_unknown(
        player_id="alice", unknown=_unknown(),
    )
    assert reg.total_pending("alice") == 1


def test_duplicate_register_rejected():
    reg = ItemIdentificationRegistry()
    reg.register_unknown(
        player_id="alice", unknown=_unknown(),
    )
    res = reg.register_unknown(
        player_id="alice", unknown=_unknown(),
    )
    assert not res


def test_npc_appraise_unknown_item_rejected():
    reg = ItemIdentificationRegistry()
    res = reg.appraise_via_npc(
        player_id="alice", unknown_id="ghost",
        gil_offered=10000,
    )
    assert res.outcome == IdentifyOutcome.FAILED


def test_npc_appraise_insufficient_gil_rejected():
    reg = ItemIdentificationRegistry()
    reg.register_unknown(
        player_id="alice",
        unknown=_unknown(tier=UnknownTier.RARE),
    )
    res = reg.appraise_via_npc(
        player_id="alice", unknown_id="u1",
        gil_offered=100,
    )
    assert res.outcome == IdentifyOutcome.FAILED
    assert "1500 gil" in res.reason


def test_npc_appraise_success_charges_fee():
    reg = ItemIdentificationRegistry()
    reg.register_unknown(
        player_id="alice",
        unknown=_unknown(tier=UnknownTier.COMMON),
    )
    res = reg.appraise_via_npc(
        player_id="alice", unknown_id="u1",
        gil_offered=500,
    )
    assert res.outcome == IdentifyOutcome.IDENTIFIED
    assert res.fee_paid == 200
    assert res.real_item_id == "iron_sword"
    # Pending consumed; known set
    assert reg.total_pending("alice") == 0
    assert "iron_sword" in reg.known_for("alice")


def test_npc_appraise_does_not_trigger_curse():
    """NPC appraisal is safe even on cursed items."""
    reg = ItemIdentificationRegistry()
    reg.register_unknown(
        player_id="alice",
        unknown=_unknown(cursed=True),
    )
    res = reg.appraise_via_npc(
        player_id="alice", unknown_id="u1",
        gil_offered=500,
    )
    assert res.outcome == IdentifyOutcome.IDENTIFIED


def test_self_appraise_low_skill_fails():
    reg = ItemIdentificationRegistry()
    reg.register_unknown(
        player_id="alice",
        unknown=_unknown(tier=UnknownTier.RARE),
    )
    res = reg.self_appraise(
        player_id="alice", unknown_id="u1",
        appraisal_skill=10,
        rng=random.Random(0),
    )
    assert res.outcome == IdentifyOutcome.FAILED


def test_self_appraise_meeting_dc_can_succeed():
    reg = ItemIdentificationRegistry()
    reg.register_unknown(
        player_id="alice",
        unknown=_unknown(tier=UnknownTier.COMMON),
    )
    res = reg.self_appraise(
        player_id="alice", unknown_id="u1",
        appraisal_skill=200,
        rng=random.Random(0),
    )
    # DC 30 vs skill 200 -> high success chance
    assert res.outcome == IdentifyOutcome.IDENTIFIED


def test_self_appraise_mythic_blocked():
    reg = ItemIdentificationRegistry()
    reg.register_unknown(
        player_id="alice",
        unknown=_unknown(tier=UnknownTier.MYTHIC),
    )
    res = reg.self_appraise(
        player_id="alice", unknown_id="u1",
        appraisal_skill=200,
        rng=random.Random(0),
    )
    assert res.outcome == IdentifyOutcome.FAILED


def test_scroll_identify_always_works():
    reg = ItemIdentificationRegistry()
    reg.register_unknown(
        player_id="alice",
        unknown=_unknown(tier=UnknownTier.MYTHIC),
    )
    res = reg.scroll_identify(
        player_id="alice", unknown_id="u1",
    )
    assert res.outcome == IdentifyOutcome.IDENTIFIED
    assert res.method == IdentifyMethod.SCROLL_OF_IDENTIFY


def test_item_use_identifies_normal_item():
    reg = ItemIdentificationRegistry()
    reg.register_unknown(
        player_id="alice", unknown=_unknown(cursed=False),
    )
    res = reg.item_use_identify(
        player_id="alice", unknown_id="u1",
    )
    assert res.outcome == IdentifyOutcome.IDENTIFIED


def test_item_use_triggers_curse():
    reg = ItemIdentificationRegistry()
    reg.register_unknown(
        player_id="alice", unknown=_unknown(cursed=True),
    )
    res = reg.item_use_identify(
        player_id="alice", unknown_id="u1",
    )
    assert res.outcome == IdentifyOutcome.CURSED_TRIGGERED
    # Item still gets identified though
    assert res.real_item_id == "iron_sword"
    assert "curse" in res.cursed_penalty


def test_pending_for_lists():
    reg = ItemIdentificationRegistry()
    reg.register_unknown(
        player_id="alice",
        unknown=_unknown(unknown_id="u1"),
    )
    reg.register_unknown(
        player_id="alice",
        unknown=_unknown(unknown_id="u2", real_id="other"),
    )
    pending = reg.pending_for("alice")
    ids = {u.unknown_id for u in pending}
    assert ids == {"u1", "u2"}


def test_known_for_grows():
    reg = ItemIdentificationRegistry()
    reg.register_unknown(
        player_id="alice", unknown=_unknown(),
    )
    reg.scroll_identify(
        player_id="alice", unknown_id="u1",
    )
    assert "iron_sword" in reg.known_for("alice")


def test_relic_appraisal_requires_high_fee():
    reg = ItemIdentificationRegistry()
    reg.register_unknown(
        player_id="alice",
        unknown=_unknown(
            unknown_id="u1", tier=UnknownTier.RELIC,
        ),
    )
    cheap = reg.appraise_via_npc(
        player_id="alice", unknown_id="u1",
        gil_offered=1000,
    )
    assert cheap.outcome == IdentifyOutcome.FAILED
    enough = reg.appraise_via_npc(
        player_id="alice", unknown_id="u1",
        gil_offered=25000,
    )
    assert enough.outcome == IdentifyOutcome.IDENTIFIED
    assert enough.fee_paid == 25000


def test_full_lifecycle_relic_identified_via_scroll():
    reg = ItemIdentificationRegistry()
    reg.register_unknown(
        player_id="alice",
        unknown=_unknown(
            unknown_id="relic_1", tier=UnknownTier.RELIC,
            real_id="excalibur",
        ),
    )
    # Self-appraise with low skill fails
    fail = reg.self_appraise(
        player_id="alice", unknown_id="relic_1",
        appraisal_skill=50,
    )
    assert fail.outcome == IdentifyOutcome.FAILED
    # Use scroll
    res = reg.scroll_identify(
        player_id="alice", unknown_id="relic_1",
    )
    assert res.outcome == IdentifyOutcome.IDENTIFIED
    assert res.real_item_id == "excalibur"
