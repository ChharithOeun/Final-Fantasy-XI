"""Tests for mob sapience threshold."""
from __future__ import annotations

from server.mob_sapience_threshold import (
    BEAST_OF_NOTE_THRESHOLD,
    MobSapienceThreshold,
    NM_TIER_THRESHOLD,
    NPC_TIER_THRESHOLD,
    SapienceEvent,
    SapienceEventKind,
    SapienceTier,
)


def test_observe_mob_creates_record():
    sap = MobSapienceThreshold()
    rec = sap.observe_mob(mob_uid="orc_001", mob_kind="orc")
    assert rec is not None
    assert rec.tier == SapienceTier.UNREMARKABLE
    assert rec.sapience_score == 0


def test_double_observe_rejected():
    sap = MobSapienceThreshold()
    sap.observe_mob(mob_uid="orc_001", mob_kind="orc")
    second = sap.observe_mob(
        mob_uid="orc_001", mob_kind="orc",
    )
    assert second is None


def test_record_event_increments_score():
    sap = MobSapienceThreshold()
    sap.observe_mob(mob_uid="orc_001", mob_kind="orc")
    score = sap.record_event(
        mob_uid="orc_001",
        event=SapienceEvent(
            kind=SapienceEventKind.KILLED_PLAYER,
        ),
    )
    assert score == 5


def test_record_event_unknown_returns_none():
    sap = MobSapienceThreshold()
    assert sap.record_event(
        mob_uid="ghost",
        event=SapienceEvent(
            kind=SapienceEventKind.SURVIVED_DAY,
        ),
    ) is None


def test_promotion_to_beast_of_note():
    sap = MobSapienceThreshold()
    sap.observe_mob(mob_uid="orc_001", mob_kind="orc")
    for _ in range(2):
        sap.record_event(
            mob_uid="orc_001",
            event=SapienceEvent(
                kind=SapienceEventKind.KILLED_PLAYER,
            ),
        )
    asc = sap.check_promotion(mob_uid="orc_001")
    assert asc is not None
    assert asc.new_tier == SapienceTier.BEAST_OF_NOTE
    assert asc.earned_name != ""


def test_promotion_at_exact_threshold():
    sap = MobSapienceThreshold()
    sap.observe_mob(mob_uid="orc_001", mob_kind="orc")
    # Need at least 10 to promote
    for _ in range(BEAST_OF_NOTE_THRESHOLD):
        sap.record_event(
            mob_uid="orc_001",
            event=SapienceEvent(
                kind=SapienceEventKind.SURVIVED_DAY,
            ),
        )
    asc = sap.check_promotion(mob_uid="orc_001")
    assert asc is not None
    assert asc.new_tier == SapienceTier.BEAST_OF_NOTE


def test_no_promotion_below_threshold():
    sap = MobSapienceThreshold()
    sap.observe_mob(mob_uid="orc_001", mob_kind="orc")
    sap.record_event(
        mob_uid="orc_001",
        event=SapienceEvent(
            kind=SapienceEventKind.SURVIVED_DAY,
        ),
    )
    assert sap.check_promotion(mob_uid="orc_001") is None


def test_promotion_to_nm_tier():
    sap = MobSapienceThreshold()
    sap.observe_mob(mob_uid="t_001", mob_kind="tiger")
    # 50 score from 10 player kills
    for _ in range(10):
        sap.record_event(
            mob_uid="t_001",
            event=SapienceEvent(
                kind=SapienceEventKind.KILLED_PLAYER,
            ),
        )
    asc = sap.check_promotion(mob_uid="t_001")
    assert asc is not None
    assert asc.new_tier == SapienceTier.NM_TIER


def test_promotion_to_npc_tier():
    sap = MobSapienceThreshold()
    sap.observe_mob(mob_uid="d_001", mob_kind="wyvern")
    # 200 score
    for _ in range(40):
        sap.record_event(
            mob_uid="d_001",
            event=SapienceEvent(
                kind=SapienceEventKind.KILLED_PLAYER,
            ),
        )
    asc = sap.check_promotion(mob_uid="d_001")
    assert asc is not None
    assert asc.new_tier == SapienceTier.NPC_TIER


def test_promotion_unchanged_returns_none():
    sap = MobSapienceThreshold()
    sap.observe_mob(mob_uid="orc_001", mob_kind="orc")
    for _ in range(3):
        sap.record_event(
            mob_uid="orc_001",
            event=SapienceEvent(
                kind=SapienceEventKind.KILLED_PLAYER,
            ),
        )
    asc1 = sap.check_promotion(mob_uid="orc_001")
    assert asc1 is not None
    # Calling again with no change yields None
    asc2 = sap.check_promotion(mob_uid="orc_001")
    assert asc2 is None


def test_tier_for_lookup():
    sap = MobSapienceThreshold()
    sap.observe_mob(mob_uid="orc_001", mob_kind="orc")
    assert sap.tier_for("orc_001") == SapienceTier.UNREMARKABLE


def test_tier_for_unknown_returns_none():
    sap = MobSapienceThreshold()
    assert sap.tier_for("ghost") is None


def test_ascended_lists_only_promoted():
    sap = MobSapienceThreshold()
    sap.observe_mob(mob_uid="a", mob_kind="orc")
    sap.observe_mob(mob_uid="b", mob_kind="orc")
    sap.observe_mob(mob_uid="c", mob_kind="orc")
    # Only b crosses threshold
    for _ in range(3):
        sap.record_event(
            mob_uid="b",
            event=SapienceEvent(
                kind=SapienceEventKind.KILLED_PLAYER,
            ),
        )
    sap.check_promotion(mob_uid="b")
    asc = sap.ascended()
    assert len(asc) == 1
    assert asc[0].mob_uid == "b"


def test_earned_name_persists_after_first_promotion():
    sap = MobSapienceThreshold()
    sap.observe_mob(mob_uid="orc_001", mob_kind="orc")
    for _ in range(3):
        sap.record_event(
            mob_uid="orc_001",
            event=SapienceEvent(
                kind=SapienceEventKind.KILLED_PLAYER,
            ),
        )
    sap.check_promotion(mob_uid="orc_001")
    name1 = sap._records["orc_001"].earned_name
    # Push higher
    for _ in range(20):
        sap.record_event(
            mob_uid="orc_001",
            event=SapienceEvent(
                kind=SapienceEventKind.LED_PACK_KILL,
            ),
        )
    sap.check_promotion(mob_uid="orc_001")
    assert sap._records["orc_001"].earned_name == name1


def test_drink_from_shrine_huge_jump():
    sap = MobSapienceThreshold()
    sap.observe_mob(mob_uid="d_001", mob_kind="orc")
    sap.record_event(
        mob_uid="d_001",
        event=SapienceEvent(
            kind=SapienceEventKind.DRANK_FROM_SHRINE,
        ),
    )
    asc = sap.check_promotion(mob_uid="d_001")
    assert asc is not None
    # 20 score = BEAST_OF_NOTE
    assert asc.new_tier == SapienceTier.BEAST_OF_NOTE


def test_total_observed_count():
    sap = MobSapienceThreshold()
    sap.observe_mob(mob_uid="a", mob_kind="orc")
    sap.observe_mob(mob_uid="b", mob_kind="goblin")
    assert sap.total_observed() == 2


def test_thresholds_constants_ordering():
    assert (
        BEAST_OF_NOTE_THRESHOLD
        < NM_TIER_THRESHOLD
        < NPC_TIER_THRESHOLD
    )
