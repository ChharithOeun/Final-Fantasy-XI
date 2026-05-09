"""Tests for entity_hobbies."""
from __future__ import annotations

from server.entity_hobbies import (
    EntityHobbiesSystem, HobbyKind, TimeSlot,
)


def _populate(s: EntityHobbiesSystem) -> None:
    s.register_entity(
        entity_id="volker",
        hobby_set=(HobbyKind.FISHING, HobbyKind.DRINKING),
    )
    s.add_schedule(
        entity_id="volker", hobby=HobbyKind.FISHING,
        day_of_week=2, time_slot=TimeSlot.MORNING,
        zone_id="bastok_docks",
    )
    s.add_schedule(
        entity_id="volker", hobby=HobbyKind.DRINKING,
        day_of_week=6, time_slot=TimeSlot.NIGHT,
        zone_id="steaming_sheep",
    )
    s.register_entity(
        entity_id="goblin_smithy",
        hobby_set=(
            HobbyKind.METALWORK, HobbyKind.GAMBLING,
        ),
    )
    s.add_schedule(
        entity_id="goblin_smithy",
        hobby=HobbyKind.METALWORK,
        day_of_week=1, time_slot=TimeSlot.AFTERNOON,
        zone_id="goblin_forge",
    )


def test_register_happy():
    s = EntityHobbiesSystem()
    assert s.register_entity(
        entity_id="x",
        hobby_set=(HobbyKind.FISHING,),
    ) is True


def test_register_duplicate_blocked():
    s = EntityHobbiesSystem()
    s.register_entity(
        entity_id="x",
        hobby_set=(HobbyKind.FISHING,),
    )
    assert s.register_entity(
        entity_id="x",
        hobby_set=(HobbyKind.READING,),
    ) is False


def test_register_too_many_hobbies():
    s = EntityHobbiesSystem()
    assert s.register_entity(
        entity_id="x",
        hobby_set=(
            HobbyKind.FISHING, HobbyKind.READING,
            HobbyKind.SINGING, HobbyKind.GAMBLING,
        ),
    ) is False


def test_register_dup_hobby_in_set():
    s = EntityHobbiesSystem()
    assert s.register_entity(
        entity_id="x",
        hobby_set=(HobbyKind.FISHING, HobbyKind.FISHING),
    ) is False


def test_register_empty_set_blocked():
    s = EntityHobbiesSystem()
    assert s.register_entity(
        entity_id="x", hobby_set=(),
    ) is False


def test_add_schedule_happy():
    s = EntityHobbiesSystem()
    s.register_entity(
        entity_id="x",
        hobby_set=(HobbyKind.FISHING,),
    )
    assert s.add_schedule(
        entity_id="x", hobby=HobbyKind.FISHING,
        day_of_week=0, time_slot=TimeSlot.MORNING,
        zone_id="z",
    ) is True


def test_schedule_hobby_not_in_set_blocked():
    s = EntityHobbiesSystem()
    s.register_entity(
        entity_id="x",
        hobby_set=(HobbyKind.FISHING,),
    )
    assert s.add_schedule(
        entity_id="x", hobby=HobbyKind.READING,
        day_of_week=0, time_slot=TimeSlot.MORNING,
        zone_id="z",
    ) is False


def test_schedule_invalid_dow():
    s = EntityHobbiesSystem()
    s.register_entity(
        entity_id="x",
        hobby_set=(HobbyKind.FISHING,),
    )
    assert s.add_schedule(
        entity_id="x", hobby=HobbyKind.FISHING,
        day_of_week=8, time_slot=TimeSlot.MORNING,
        zone_id="z",
    ) is False


def test_schedule_slot_collision_blocked():
    s = EntityHobbiesSystem()
    s.register_entity(
        entity_id="x",
        hobby_set=(HobbyKind.FISHING, HobbyKind.READING),
    )
    s.add_schedule(
        entity_id="x", hobby=HobbyKind.FISHING,
        day_of_week=0, time_slot=TimeSlot.MORNING,
        zone_id="z",
    )
    # Same DOW + slot — collision
    assert s.add_schedule(
        entity_id="x", hobby=HobbyKind.READING,
        day_of_week=0, time_slot=TimeSlot.MORNING,
        zone_id="z",
    ) is False


def test_current_activity_happy():
    s = EntityHobbiesSystem()
    _populate(s)
    # Day 9 → dow 9 % 7 = 2; volker fishes Tuesday
    # mornings.
    sched = s.current_activity(
        entity_id="volker", day=9,
        time_slot=TimeSlot.MORNING,
    )
    assert sched is not None
    assert sched.hobby == HobbyKind.FISHING
    assert sched.zone_id == "bastok_docks"


def test_current_activity_wrong_dow():
    s = EntityHobbiesSystem()
    _populate(s)
    # Day 8 → dow 1, no morning fishing slot
    sched = s.current_activity(
        entity_id="volker", day=8,
        time_slot=TimeSlot.MORNING,
    )
    assert sched is None


def test_current_activity_in_combat_suppressed():
    s = EntityHobbiesSystem()
    _populate(s)
    s.set_combat_state(
        entity_id="volker", in_combat=True,
    )
    sched = s.current_activity(
        entity_id="volker", day=9,
        time_slot=TimeSlot.MORNING,
    )
    assert sched is None


def test_combat_clears_returns_activity():
    s = EntityHobbiesSystem()
    _populate(s)
    s.set_combat_state(
        entity_id="volker", in_combat=True,
    )
    s.set_combat_state(
        entity_id="volker", in_combat=False,
    )
    sched = s.current_activity(
        entity_id="volker", day=9,
        time_slot=TimeSlot.MORNING,
    )
    assert sched is not None


def test_current_activity_unknown_entity():
    s = EntityHobbiesSystem()
    sched = s.current_activity(
        entity_id="ghost", day=0,
        time_slot=TimeSlot.MORNING,
    )
    assert sched is None


def test_entities_practicing_lookup():
    s = EntityHobbiesSystem()
    _populate(s)
    fishing = s.entities_practicing(
        hobby=HobbyKind.FISHING, day=9,
        time_slot=TimeSlot.MORNING,
    )
    assert "volker" in fishing
    assert "goblin_smithy" not in fishing


def test_entities_practicing_filters_combat():
    s = EntityHobbiesSystem()
    _populate(s)
    s.set_combat_state(
        entity_id="volker", in_combat=True,
    )
    fishing = s.entities_practicing(
        hobby=HobbyKind.FISHING, day=9,
        time_slot=TimeSlot.MORNING,
    )
    assert "volker" not in fishing


def test_rare_for_class_flag():
    s = EntityHobbiesSystem()
    s.register_entity(
        entity_id="taru_war",
        hobby_set=(HobbyKind.WEIGHTLIFTING,),
        rare_for_class=True,
    )
    assert s.is_rare_pairing(
        entity_id="taru_war",
    ) is True


def test_normal_pairing_not_rare():
    s = EntityHobbiesSystem()
    s.register_entity(
        entity_id="x",
        hobby_set=(HobbyKind.READING,),
    )
    assert s.is_rare_pairing(entity_id="x") is False


def test_is_rare_unknown_entity():
    s = EntityHobbiesSystem()
    assert s.is_rare_pairing(
        entity_id="ghost",
    ) is False


def test_hobby_lookup():
    s = EntityHobbiesSystem()
    _populate(s)
    h = s.hobby(entity_id="volker")
    assert HobbyKind.FISHING in h.hobby_set
    assert len(h.schedules) == 2


def test_hobby_unknown():
    s = EntityHobbiesSystem()
    assert s.hobby(entity_id="ghost") is None


def test_enum_counts():
    assert len(list(HobbyKind)) == 12
    assert len(list(TimeSlot)) == 4
