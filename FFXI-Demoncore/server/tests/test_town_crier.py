"""Tests for town crier broadcast registry."""
from __future__ import annotations

from server.town_crier import (
    AnnouncementKind,
    AnnouncementPriority,
    CrierAnnouncement,
    CrierProfile,
    DEFAULT_EXPIRY_SECONDS,
    TownCrierRegistry,
)


def _crier(
    crier_id: str = "bastok_crier",
    schedule_hours: tuple[int, ...] = (9, 10, 11, 14, 15, 16),
) -> CrierProfile:
    return CrierProfile(
        crier_id=crier_id, venue_id="bastok_plaza",
        schedule_hours=schedule_hours,
        audience_radius_tiles=30,
    )


def _ann(
    announcement_id: str = "a1",
    kind: AnnouncementKind = AnnouncementKind.EVENT_OPENING,
    priority: AnnouncementPriority = AnnouncementPriority.NORMAL,
    times: int = 3,
    text: str = "An event opens",
) -> CrierAnnouncement:
    return CrierAnnouncement(
        announcement_id=announcement_id,
        kind=kind, text=text, priority=priority,
        times_to_repeat=times,
    )


def test_register_crier():
    reg = TownCrierRegistry()
    reg.register_crier(_crier())
    assert reg.crier("bastok_crier") is not None
    assert reg.total_criers() == 1


def test_queue_announcement_sets_expiry():
    reg = TownCrierRegistry()
    a = reg.queue_announcement(
        announcement=_ann(), now_seconds=100.0,
    )
    assert a.expires_at_seconds == 100.0 + DEFAULT_EXPIRY_SECONDS
    assert a.queued_at_seconds == 100.0


def test_active_queue_filters_expired():
    reg = TownCrierRegistry()
    reg.queue_announcement(
        announcement=_ann("old"), now_seconds=0.0,
    )
    reg.queue_announcement(
        announcement=_ann("fresh"), now_seconds=1000.0,
    )
    # Way past expiry of "old"
    actives = reg.active_queue(
        now_seconds=DEFAULT_EXPIRY_SECONDS + 100,
    )
    ids = {a.announcement_id for a in actives}
    assert "fresh" in ids
    assert "old" not in ids


def test_active_queue_sorts_by_priority():
    reg = TownCrierRegistry()
    reg.queue_announcement(
        announcement=_ann(
            "low", priority=AnnouncementPriority.LOW,
        ),
        now_seconds=0.0,
    )
    reg.queue_announcement(
        announcement=_ann(
            "urgent", priority=AnnouncementPriority.URGENT,
        ),
        now_seconds=0.0,
    )
    reg.queue_announcement(
        announcement=_ann(
            "normal", priority=AnnouncementPriority.NORMAL,
        ),
        now_seconds=0.0,
    )
    queue = reg.active_queue(now_seconds=10.0)
    ids_in_order = [a.announcement_id for a in queue]
    assert ids_in_order == ["urgent", "normal", "low"]


def test_proclaim_unknown_crier_rejected():
    reg = TownCrierRegistry()
    res = reg.proclaim(
        crier_id="ghost", now_seconds=0.0, hour=10,
    )
    assert not res.accepted


def test_proclaim_off_shift_rejected():
    reg = TownCrierRegistry()
    reg.register_crier(_crier())
    res = reg.proclaim(
        crier_id="bastok_crier", now_seconds=0.0, hour=3,
    )
    assert not res.accepted
    assert "off-shift" in res.reason


def test_proclaim_nothing_queued_returns_empty():
    reg = TownCrierRegistry()
    reg.register_crier(_crier())
    res = reg.proclaim(
        crier_id="bastok_crier", now_seconds=0.0, hour=10,
    )
    assert res.accepted
    assert res.proclaimed == ()


def test_proclaim_top_priority_first():
    reg = TownCrierRegistry()
    reg.register_crier(_crier())
    reg.queue_announcement(
        announcement=_ann(
            "low", priority=AnnouncementPriority.LOW,
        ),
        now_seconds=0.0,
    )
    reg.queue_announcement(
        announcement=_ann(
            "urgent", priority=AnnouncementPriority.URGENT,
        ),
        now_seconds=0.0,
    )
    res = reg.proclaim(
        crier_id="bastok_crier", now_seconds=10.0, hour=10,
    )
    assert "urgent" in res.proclaimed


def test_announcement_repeats_count_decrements():
    reg = TownCrierRegistry()
    reg.register_crier(_crier())
    a = reg.queue_announcement(
        announcement=_ann("a1", times=3),
        now_seconds=0.0,
    )
    for _ in range(3):
        reg.proclaim(
            crier_id="bastok_crier", now_seconds=10.0, hour=10,
        )
    assert a.proclaim_count == 3


def test_done_announcement_drops_from_queue():
    reg = TownCrierRegistry()
    reg.register_crier(_crier())
    reg.queue_announcement(
        announcement=_ann("once", times=1),
        now_seconds=0.0,
    )
    reg.proclaim(
        crier_id="bastok_crier", now_seconds=10.0, hour=10,
    )
    queue_after = reg.active_queue(now_seconds=20.0)
    assert "once" not in [a.announcement_id for a in queue_after]


def test_max_per_call_caps_proclamations():
    reg = TownCrierRegistry()
    reg.register_crier(_crier())
    for i in range(5):
        reg.queue_announcement(
            announcement=_ann(f"a{i}"), now_seconds=0.0,
        )
    res = reg.proclaim(
        crier_id="bastok_crier", now_seconds=10.0, hour=10,
        max_per_call=2,
    )
    assert len(res.proclaimed) == 2


def test_expire_old_sweeps_stale():
    reg = TownCrierRegistry()
    reg.queue_announcement(
        announcement=_ann("ancient"), now_seconds=0.0,
    )
    reg.queue_announcement(
        announcement=_ann("fresh"),
        now_seconds=DEFAULT_EXPIRY_SECONDS + 1000,
    )
    dropped = reg.expire_old(
        now_seconds=DEFAULT_EXPIRY_SECONDS + 2000,
    )
    assert dropped == 1


def test_full_lifecycle_festival_announcement():
    """Republic Day announcement: queued the day before, gets
    proclaimed three times by the crier on his 9-11am shift."""
    reg = TownCrierRegistry()
    reg.register_crier(_crier(schedule_hours=(9, 10, 11)))
    reg.queue_announcement(
        announcement=_ann(
            "republic_day",
            kind=AnnouncementKind.EVENT_OPENING,
            priority=AnnouncementPriority.HIGH,
            text="Republic Day opens at dawn!",
            times=3,
        ),
        now_seconds=100.0,
    )
    # Proclaim three times on his shift
    out: list[str] = []
    for hour in (9, 10, 11):
        res = reg.proclaim(
            crier_id="bastok_crier", now_seconds=200.0,
            hour=hour,
        )
        out.extend(res.proclaimed)
    assert out.count("republic_day") == 3
    # Now done — no more proclamations
    fourth = reg.proclaim(
        crier_id="bastok_crier", now_seconds=300.0, hour=10,
    )
    assert "republic_day" not in fourth.proclaimed
