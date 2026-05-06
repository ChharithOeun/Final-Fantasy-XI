"""Tests for sahagin conquest phase."""
from __future__ import annotations

from server.sahagin_conquest_phase import (
    ALLIANCE_SIZE,
    AllianceSlot,
    ConquestStatus,
    PHASE_DURATION_SECONDS,
    Phase,
    SahaginConquestPhase,
    TOTAL_ALLIANCES,
)


def _make_members(prefix: str, n: int = ALLIANCE_SIZE) -> list[str]:
    return [f"{prefix}_{i}" for i in range(n)]


def _seed_full_signed(c: SahaginConquestPhase, raid_id: str = "r1"):
    c.register_raid(
        raid_id=raid_id,
        candidate_zones=["zone_a", "zone_b", "zone_c", "zone_d"],
        now_seconds=0,
    )
    c.sign_alliance(
        raid_id=raid_id, slot=AllianceSlot.ALPHA,
        member_ids=_make_members("alpha"),
    )
    c.sign_alliance(
        raid_id=raid_id, slot=AllianceSlot.BRAVO,
        member_ids=_make_members("bravo"),
    )
    c.sign_alliance(
        raid_id=raid_id, slot=AllianceSlot.CHARLIE,
        member_ids=_make_members("charlie"),
    )


def test_register_raid_happy():
    c = SahaginConquestPhase()
    assert c.register_raid(
        raid_id="r1", candidate_zones=["a", "b", "c"], now_seconds=0,
    ) is True


def test_register_raid_blank():
    c = SahaginConquestPhase()
    assert c.register_raid(
        raid_id="", candidate_zones=["a", "b", "c"], now_seconds=0,
    ) is False


def test_register_raid_too_few_zones():
    c = SahaginConquestPhase()
    assert c.register_raid(
        raid_id="r1", candidate_zones=["a", "b"], now_seconds=0,
    ) is False


def test_register_raid_duplicate_zones():
    c = SahaginConquestPhase()
    assert c.register_raid(
        raid_id="r1", candidate_zones=["a", "a", "b"], now_seconds=0,
    ) is False


def test_sign_alliance_happy():
    c = SahaginConquestPhase()
    c.register_raid(
        raid_id="r1", candidate_zones=["a", "b", "c"], now_seconds=0,
    )
    assert c.sign_alliance(
        raid_id="r1", slot=AllianceSlot.ALPHA,
        member_ids=_make_members("alpha"),
    ) is True


def test_sign_alliance_wrong_size_blocked():
    c = SahaginConquestPhase()
    c.register_raid(
        raid_id="r1", candidate_zones=["a", "b", "c"], now_seconds=0,
    )
    assert c.sign_alliance(
        raid_id="r1", slot=AllianceSlot.ALPHA,
        member_ids=_make_members("alpha", n=10),
    ) is False


def test_sign_alliance_dup_member_across_alliances():
    c = SahaginConquestPhase()
    c.register_raid(
        raid_id="r1", candidate_zones=["a", "b", "c"], now_seconds=0,
    )
    c.sign_alliance(
        raid_id="r1", slot=AllianceSlot.ALPHA,
        member_ids=_make_members("p"),
    )
    # try BRAVO with overlapping member
    overlap = _make_members("p")[:1] + _make_members("q", n=ALLIANCE_SIZE - 1)
    assert c.sign_alliance(
        raid_id="r1", slot=AllianceSlot.BRAVO, member_ids=overlap,
    ) is False


def test_status_transitions_to_signed():
    c = SahaginConquestPhase()
    _seed_full_signed(c)
    assert c.status_of(raid_id="r1") == ConquestStatus.SIGNED


def test_randomize_assigns_zones():
    c = SahaginConquestPhase()
    _seed_full_signed(c)
    c.randomize_assignments(raid_id="r1", seed=42)
    a = c.assignment_for(raid_id="r1", slot=AllianceSlot.ALPHA)
    b = c.assignment_for(raid_id="r1", slot=AllianceSlot.BRAVO)
    cc = c.assignment_for(raid_id="r1", slot=AllianceSlot.CHARLIE)
    assert a is not None and b is not None and cc is not None
    assert a.zone_id != b.zone_id
    assert b.zone_id != cc.zone_id


def test_randomize_deterministic_per_seed():
    c1 = SahaginConquestPhase()
    _seed_full_signed(c1)
    c1.randomize_assignments(raid_id="r1", seed=42)
    c2 = SahaginConquestPhase()
    _seed_full_signed(c2)
    c2.randomize_assignments(raid_id="r1", seed=42)
    a1 = c1.assignment_for(raid_id="r1", slot=AllianceSlot.ALPHA)
    a2 = c2.assignment_for(raid_id="r1", slot=AllianceSlot.ALPHA)
    assert a1.zone_id == a2.zone_id


def test_randomize_blocked_before_signed():
    c = SahaginConquestPhase()
    c.register_raid(
        raid_id="r1", candidate_zones=["a", "b", "c"], now_seconds=0,
    )
    assert c.randomize_assignments(raid_id="r1", seed=1) is False


def test_start_phase_1_after_assigned():
    c = SahaginConquestPhase()
    _seed_full_signed(c)
    c.randomize_assignments(raid_id="r1", seed=42)
    assert c.start_phase(
        raid_id="r1", slot=AllianceSlot.ALPHA,
        phase=Phase.PHASE_1, now_seconds=10,
    ) is True


def test_start_phase_2_blocked_before_phase_1_complete():
    c = SahaginConquestPhase()
    _seed_full_signed(c)
    c.randomize_assignments(raid_id="r1", seed=42)
    assert c.start_phase(
        raid_id="r1", slot=AllianceSlot.ALPHA,
        phase=Phase.PHASE_2, now_seconds=10,
    ) is False


def test_complete_phase_1_then_phase_2():
    c = SahaginConquestPhase()
    _seed_full_signed(c)
    c.randomize_assignments(raid_id="r1", seed=42)
    c.start_phase(
        raid_id="r1", slot=AllianceSlot.ALPHA,
        phase=Phase.PHASE_1, now_seconds=10,
    )
    assert c.complete_phase(
        raid_id="r1", slot=AllianceSlot.ALPHA,
        phase=Phase.PHASE_1, now_seconds=100,
    ) is True
    assert c.start_phase(
        raid_id="r1", slot=AllianceSlot.ALPHA,
        phase=Phase.PHASE_2, now_seconds=120,
    ) is True


def test_phase_timer_expiry_fails_alliance():
    c = SahaginConquestPhase()
    _seed_full_signed(c)
    c.randomize_assignments(raid_id="r1", seed=42)
    c.start_phase(
        raid_id="r1", slot=AllianceSlot.ALPHA,
        phase=Phase.PHASE_1, now_seconds=10,
    )
    # try to complete past the timer
    c.complete_phase(
        raid_id="r1", slot=AllianceSlot.ALPHA,
        phase=Phase.PHASE_1,
        now_seconds=10 + PHASE_DURATION_SECONDS + 100,
    )
    assert c.status_of(raid_id="r1") == ConquestStatus.FAILED


def test_one_alliance_failure_kills_whole_raid():
    c = SahaginConquestPhase()
    _seed_full_signed(c)
    c.randomize_assignments(raid_id="r1", seed=42)
    # alpha + bravo crush phase 1
    for slot in [AllianceSlot.ALPHA, AllianceSlot.BRAVO]:
        c.start_phase(
            raid_id="r1", slot=slot,
            phase=Phase.PHASE_1, now_seconds=10,
        )
        c.complete_phase(
            raid_id="r1", slot=slot,
            phase=Phase.PHASE_1, now_seconds=100,
        )
    # charlie fails outright
    c.fail_phase(
        raid_id="r1", slot=AllianceSlot.CHARLIE,
        reason="wiped on second NM", now_seconds=200,
    )
    assert c.status_of(raid_id="r1") == ConquestStatus.FAILED
    assert c.all_phases_complete(raid_id="r1") is False


def test_all_phases_complete_only_when_all_done():
    c = SahaginConquestPhase()
    _seed_full_signed(c)
    c.randomize_assignments(raid_id="r1", seed=42)
    for slot in AllianceSlot:
        c.start_phase(
            raid_id="r1", slot=slot,
            phase=Phase.PHASE_1, now_seconds=10,
        )
        c.complete_phase(
            raid_id="r1", slot=slot,
            phase=Phase.PHASE_1, now_seconds=100,
        )
        c.start_phase(
            raid_id="r1", slot=slot,
            phase=Phase.PHASE_2, now_seconds=200,
        )
        c.complete_phase(
            raid_id="r1", slot=slot,
            phase=Phase.PHASE_2, now_seconds=400,
        )
    assert c.all_phases_complete(raid_id="r1") is True
    assert c.status_of(raid_id="r1") == ConquestStatus.COMPLETE


def test_assignment_for_unknown_returns_none():
    c = SahaginConquestPhase()
    assert c.assignment_for(
        raid_id="ghost", slot=AllianceSlot.ALPHA,
    ) is None


def test_total_alliances_canonical():
    assert TOTAL_ALLIANCES == 3
    assert ALLIANCE_SIZE == 18
