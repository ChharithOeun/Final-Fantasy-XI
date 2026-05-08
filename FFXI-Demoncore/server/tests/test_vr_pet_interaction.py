"""Tests for vr_pet_interaction."""
from __future__ import annotations

from server.vr_pet_interaction import (
    BodyPart, InteractionKind, VrPetInteraction,
)


def _setup_chocobo(p, pet_id="chocobo_1", x=0, y=1.0, z=0):
    p.register_pet(
        pet_id=pet_id, x=x, y=y, z=z, species="chocobo",
    )


def test_register_pet():
    p = VrPetInteraction()
    assert p.register_pet(
        pet_id="cid", x=0, y=1.0, z=0, species="chocobo",
    ) is True


def test_register_blank_blocked():
    p = VrPetInteraction()
    assert p.register_pet(
        pet_id="", x=0, y=0, z=0, species="chocobo",
    ) is False


def test_register_blank_species_blocked():
    p = VrPetInteraction()
    assert p.register_pet(
        pet_id="cid", x=0, y=0, z=0, species="",
    ) is False


def test_register_dup_blocked():
    p = VrPetInteraction()
    p.register_pet(
        pet_id="cid", x=0, y=0, z=0, species="chocobo",
    )
    assert p.register_pet(
        pet_id="cid", x=1, y=0, z=0, species="chocobo",
    ) is False


def test_pet_action():
    p = VrPetInteraction()
    _setup_chocobo(p)
    ev = p.ingest_touch(
        player_id="bob", pet_id="chocobo_1",
        hand_x=0.0, hand_y=1.4, hand_z=0.0,
        kind=InteractionKind.PET,
        duration_ms=1500, timestamp_ms=1000,
    )
    assert ev is not None
    assert ev.kind == InteractionKind.PET


def test_short_pet_blocked():
    """PET requires 1000ms minimum."""
    p = VrPetInteraction()
    _setup_chocobo(p)
    ev = p.ingest_touch(
        player_id="bob", pet_id="chocobo_1",
        hand_x=0, hand_y=1.4, hand_z=0,
        kind=InteractionKind.PET,
        duration_ms=500, timestamp_ms=1000,
    )
    assert ev is None


def test_hug_requires_2s():
    p = VrPetInteraction()
    _setup_chocobo(p)
    short = p.ingest_touch(
        player_id="bob", pet_id="chocobo_1",
        hand_x=0, hand_y=1.0, hand_z=0,
        kind=InteractionKind.HUG,
        duration_ms=1500, timestamp_ms=1000,
    )
    assert short is None
    long = p.ingest_touch(
        player_id="bob", pet_id="chocobo_1",
        hand_x=0, hand_y=1.0, hand_z=0,
        kind=InteractionKind.HUG,
        duration_ms=2500, timestamp_ms=2000,
    )
    assert long is not None


def test_out_of_reach_blocked():
    p = VrPetInteraction()
    _setup_chocobo(p, x=0, y=1.0, z=0)
    ev = p.ingest_touch(
        player_id="bob", pet_id="chocobo_1",
        hand_x=10, hand_y=1.0, hand_z=0,
        kind=InteractionKind.PET,
        duration_ms=1500, timestamp_ms=1000,
    )
    assert ev is None


def test_unknown_pet_blocked():
    p = VrPetInteraction()
    ev = p.ingest_touch(
        player_id="bob", pet_id="ghost",
        hand_x=0, hand_y=0, hand_z=0,
        kind=InteractionKind.PET,
        duration_ms=1500, timestamp_ms=1000,
    )
    assert ev is None


def test_blank_player_blocked():
    p = VrPetInteraction()
    _setup_chocobo(p)
    ev = p.ingest_touch(
        player_id="", pet_id="chocobo_1",
        hand_x=0, hand_y=1.0, hand_z=0,
        kind=InteractionKind.PET,
        duration_ms=1500, timestamp_ms=1000,
    )
    assert ev is None


def test_cooldown_blocks_dupes():
    p = VrPetInteraction()
    _setup_chocobo(p)
    p.ingest_touch(
        player_id="bob", pet_id="chocobo_1",
        hand_x=0, hand_y=1.4, hand_z=0,
        kind=InteractionKind.PET,
        duration_ms=1500, timestamp_ms=1000,
    )
    # Second pet within 1500ms cooldown
    ev = p.ingest_touch(
        player_id="bob", pet_id="chocobo_1",
        hand_x=0, hand_y=1.4, hand_z=0,
        kind=InteractionKind.PET,
        duration_ms=1500, timestamp_ms=2000,
    )
    assert ev is None


def test_cooldown_releases():
    p = VrPetInteraction()
    _setup_chocobo(p)
    p.ingest_touch(
        player_id="bob", pet_id="chocobo_1",
        hand_x=0, hand_y=1.4, hand_z=0,
        kind=InteractionKind.PET,
        duration_ms=1500, timestamp_ms=1000,
    )
    # 3000ms later, cooldown expired
    ev = p.ingest_touch(
        player_id="bob", pet_id="chocobo_1",
        hand_x=0, hand_y=1.4, hand_z=0,
        kind=InteractionKind.PET,
        duration_ms=1500, timestamp_ms=4000,
    )
    assert ev is not None


def test_different_kind_no_cooldown():
    """PET cooldown doesn't block SCRATCH."""
    p = VrPetInteraction()
    _setup_chocobo(p)
    p.ingest_touch(
        player_id="bob", pet_id="chocobo_1",
        hand_x=0, hand_y=1.4, hand_z=0,
        kind=InteractionKind.PET,
        duration_ms=1500, timestamp_ms=1000,
    )
    ev = p.ingest_touch(
        player_id="bob", pet_id="chocobo_1",
        hand_x=0, hand_y=1.4, hand_z=0,
        kind=InteractionKind.SCRATCH,
        duration_ms=600, timestamp_ms=1500,
    )
    assert ev is not None


def test_body_part_classification_neck():
    p = VrPetInteraction()
    _setup_chocobo(p, x=0, y=1.0, z=0)
    ev = p.ingest_touch(
        player_id="bob", pet_id="chocobo_1",
        hand_x=0, hand_y=1.5, hand_z=0,  # +0.5 above
        kind=InteractionKind.PET,
        duration_ms=1500, timestamp_ms=1000,
    )
    assert ev.body_part == BodyPart.NECK


def test_body_part_classification_tail():
    p = VrPetInteraction()
    _setup_chocobo(p, x=0, y=1.0, z=0)
    ev = p.ingest_touch(
        player_id="bob", pet_id="chocobo_1",
        hand_x=0, hand_y=1.0, hand_z=-0.7,  # behind
        kind=InteractionKind.PET,
        duration_ms=1500, timestamp_ms=1000,
    )
    assert ev.body_part == BodyPart.TAIL


def test_body_part_muzzle_for_feed():
    p = VrPetInteraction()
    _setup_chocobo(p, x=0, y=1.0, z=0)
    ev = p.ingest_touch(
        player_id="bob", pet_id="chocobo_1",
        hand_x=0, hand_y=1.7, hand_z=0.7,  # front + up
        kind=InteractionKind.FEED,
        duration_ms=300, timestamp_ms=1000,
    )
    assert ev is not None
    assert ev.body_part == BodyPart.MUZZLE


def test_events_for_returns_player_only():
    p = VrPetInteraction()
    _setup_chocobo(p)
    p.ingest_touch(
        player_id="bob", pet_id="chocobo_1",
        hand_x=0, hand_y=1.0, hand_z=0,
        kind=InteractionKind.PET,
        duration_ms=1500, timestamp_ms=1000,
    )
    p.ingest_touch(
        player_id="cara", pet_id="chocobo_1",
        hand_x=0, hand_y=1.0, hand_z=0,
        kind=InteractionKind.PET,
        duration_ms=1500, timestamp_ms=2000,
    )
    bob_events = p.events_for(player_id="bob")
    assert len(bob_events) == 1
    assert bob_events[0].player_id == "bob"


def test_events_for_pet():
    p = VrPetInteraction()
    _setup_chocobo(p, "cid_a")
    p.register_pet(
        pet_id="cid_b", x=10, y=1.0, z=0,
        species="automaton",
    )
    p.ingest_touch(
        player_id="bob", pet_id="cid_a",
        hand_x=0, hand_y=1.0, hand_z=0,
        kind=InteractionKind.PET,
        duration_ms=1500, timestamp_ms=1000,
    )
    p.ingest_touch(
        player_id="bob", pet_id="cid_b",
        hand_x=10, hand_y=1.0, hand_z=0,
        kind=InteractionKind.PET,
        duration_ms=1500, timestamp_ms=2000,
    )
    a_events = p.events_for_pet(pet_id="cid_a")
    assert len(a_events) == 1
    assert a_events[0].pet_id == "cid_a"


def test_move_pet():
    p = VrPetInteraction()
    _setup_chocobo(p, x=0, y=1.0, z=0)
    p.move_pet(pet_id="chocobo_1", x=5, y=1.0, z=5)
    # New position; old hand pos out of reach
    ev = p.ingest_touch(
        player_id="bob", pet_id="chocobo_1",
        hand_x=0, hand_y=1.0, hand_z=0,
        kind=InteractionKind.PET,
        duration_ms=1500, timestamp_ms=1000,
    )
    assert ev is None


def test_clear_pet():
    p = VrPetInteraction()
    _setup_chocobo(p)
    p.ingest_touch(
        player_id="bob", pet_id="chocobo_1",
        hand_x=0, hand_y=1.0, hand_z=0,
        kind=InteractionKind.PET,
        duration_ms=1500, timestamp_ms=1000,
    )
    assert p.clear_pet(pet_id="chocobo_1") is True
    assert p.events_for_pet(pet_id="chocobo_1") == []


def test_clear_unknown_pet():
    p = VrPetInteraction()
    assert p.clear_pet(pet_id="ghost") is False


def test_five_interaction_kinds():
    assert len(list(InteractionKind)) == 5


def test_seven_body_parts():
    assert len(list(BodyPart)) == 7
