"""Tests for face_tattoo_system."""
from __future__ import annotations

from server.face_tattoo_system import (
    FaceTattooSystem, Marking, MarkingKind, Slot,
)


def _decorative():
    return Marking(
        marking_id="rose",
        kind=MarkingKind.DECORATIVE,
        name="Rose",
        description="Small inked rose.",
        valid_slots=(Slot.LEFT_CHEEK, Slot.RIGHT_CHEEK),
    )


def _clan():
    return Marking(
        marking_id="bastok_steel",
        kind=MarkingKind.CLAN_TATTOO,
        name="Bastok Steel",
        description="Three crossed hammers.",
        valid_slots=(Slot.FOREHEAD,),
        gate_token="ls_rank_5",
    )


def test_register():
    f = FaceTattooSystem()
    assert f.register_marking(_decorative()) is True


def test_register_blank_blocked():
    f = FaceTattooSystem()
    bad = Marking(
        marking_id="", kind=MarkingKind.DECORATIVE,
        name="x", description="y",
        valid_slots=(Slot.FOREHEAD,),
    )
    assert f.register_marking(bad) is False


def test_register_no_slots_blocked():
    f = FaceTattooSystem()
    bad = Marking(
        marking_id="x", kind=MarkingKind.DECORATIVE,
        name="x", description="y", valid_slots=(),
    )
    assert f.register_marking(bad) is False


def test_register_dup_blocked():
    f = FaceTattooSystem()
    f.register_marking(_decorative())
    assert f.register_marking(_decorative()) is False


def test_apply_decorative():
    f = FaceTattooSystem()
    f.register_marking(_decorative())
    assert f.apply(
        player_id="bob", marking_id="rose",
        slot=Slot.LEFT_CHEEK, applied_day=10,
    ) is True


def test_apply_invalid_slot_blocked():
    f = FaceTattooSystem()
    f.register_marking(_decorative())  # cheeks only
    assert f.apply(
        player_id="bob", marking_id="rose",
        slot=Slot.FOREHEAD, applied_day=10,
    ) is False


def test_apply_blank_player_blocked():
    f = FaceTattooSystem()
    f.register_marking(_decorative())
    assert f.apply(
        player_id="", marking_id="rose",
        slot=Slot.LEFT_CHEEK, applied_day=10,
    ) is False


def test_apply_unknown_marking():
    f = FaceTattooSystem()
    assert f.apply(
        player_id="bob", marking_id="ghost",
        slot=Slot.LEFT_CHEEK, applied_day=10,
    ) is False


def test_apply_gated_no_gate_blocked():
    f = FaceTattooSystem()
    f.register_marking(_clan())
    assert f.apply(
        player_id="bob", marking_id="bastok_steel",
        slot=Slot.FOREHEAD, applied_day=10,
    ) is False


def test_apply_gated_with_gate_passes():
    f = FaceTattooSystem()
    f.register_marking(_clan())
    assert f.apply(
        player_id="bob", marking_id="bastok_steel",
        slot=Slot.FOREHEAD, applied_day=10,
        gates_met={"ls_rank_5"},
    ) is True


def test_apply_slot_already_taken_blocked():
    f = FaceTattooSystem()
    f.register_marking(_decorative())
    f.apply(
        player_id="bob", marking_id="rose",
        slot=Slot.LEFT_CHEEK, applied_day=10,
    )
    assert f.apply(
        player_id="bob", marking_id="rose",
        slot=Slot.LEFT_CHEEK, applied_day=11,
    ) is False


def test_remove():
    f = FaceTattooSystem()
    f.register_marking(_decorative())
    f.apply(
        player_id="bob", marking_id="rose",
        slot=Slot.LEFT_CHEEK, applied_day=10,
    )
    assert f.remove(
        player_id="bob", slot=Slot.LEFT_CHEEK,
    ) is True


def test_remove_empty_slot_blocked():
    f = FaceTattooSystem()
    assert f.remove(
        player_id="bob", slot=Slot.LEFT_CHEEK,
    ) is False


def test_re_apply_after_remove():
    f = FaceTattooSystem()
    f.register_marking(_decorative())
    f.apply(
        player_id="bob", marking_id="rose",
        slot=Slot.LEFT_CHEEK, applied_day=10,
    )
    f.remove(player_id="bob", slot=Slot.LEFT_CHEEK)
    assert f.apply(
        player_id="bob", marking_id="rose",
        slot=Slot.LEFT_CHEEK, applied_day=20,
    ) is True


def test_markings_for():
    f = FaceTattooSystem()
    f.register_marking(_decorative())
    f.register_marking(_clan())
    f.apply(
        player_id="bob", marking_id="rose",
        slot=Slot.LEFT_CHEEK, applied_day=10,
    )
    f.apply(
        player_id="bob", marking_id="bastok_steel",
        slot=Slot.FOREHEAD, applied_day=11,
        gates_met={"ls_rank_5"},
    )
    out = f.markings_for(player_id="bob")
    assert len(out) == 2


def test_marking_in_slot():
    f = FaceTattooSystem()
    f.register_marking(_decorative())
    f.apply(
        player_id="bob", marking_id="rose",
        slot=Slot.LEFT_CHEEK, applied_day=10,
    )
    am = f.marking_in_slot(
        player_id="bob", slot=Slot.LEFT_CHEEK,
    )
    assert am is not None
    assert am.marking_id == "rose"


def test_marking_in_slot_empty():
    f = FaceTattooSystem()
    assert f.marking_in_slot(
        player_id="bob", slot=Slot.NOSE,
    ) is None


def test_eight_slots():
    assert len(list(Slot)) == 8


def test_four_marking_kinds():
    assert len(list(MarkingKind)) == 4
