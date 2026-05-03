"""Tests for pet bonding."""
from __future__ import annotations

from server.pet_bonding import (
    BondEvent,
    BondEventKind,
    BondTier,
    MAX_BOND,
    MIN_BOND,
    PetBondingRegistry,
    PetKind,
    modifier_for_tier,
)


def test_register_pet_creates_distant_bond():
    reg = PetBondingRegistry()
    bond = reg.register_pet(
        master_id="alice", pet_id="shantotto_trust",
        pet_kind=PetKind.TRUST_SPIRIT,
        nickname="The Doctor",
    )
    assert bond is not None
    assert bond.bond_score == 0
    assert reg.bond_tier(
        master_id="alice", pet_id="shantotto_trust",
    ) == BondTier.DISTANT


def test_double_register_same_pet_rejected():
    reg = PetBondingRegistry()
    reg.register_pet(
        master_id="alice", pet_id="ifrit",
        pet_kind=PetKind.SUMMON_AVATAR,
    )
    second = reg.register_pet(
        master_id="alice", pet_id="ifrit",
        pet_kind=PetKind.SUMMON_AVATAR,
    )
    assert second is None


def test_shared_victory_bumps_bond():
    reg = PetBondingRegistry()
    reg.register_pet(
        master_id="alice", pet_id="ifrit",
        pet_kind=PetKind.SUMMON_AVATAR,
    )
    new_score = reg.record_event(
        master_id="alice", pet_id="ifrit",
        event=BondEvent(kind=BondEventKind.SHARED_VICTORY),
    )
    assert new_score == 5
    bond = reg.bond_for(
        master_id="alice", pet_id="ifrit",
    )
    assert bond.fights_shared == 1


def test_revived_event_logs_times_revived():
    reg = PetBondingRegistry()
    reg.register_pet(
        master_id="alice", pet_id="ifrit",
        pet_kind=PetKind.SUMMON_AVATAR,
    )
    reg.record_event(
        master_id="alice", pet_id="ifrit",
        event=BondEvent(
            kind=BondEventKind.REVIVED_AFTER_DEATH,
        ),
    )
    bond = reg.bond_for(
        master_id="alice", pet_id="ifrit",
    )
    assert bond.times_revived == 1
    assert bond.bond_score == 20


def test_negative_event_lowers_bond():
    reg = PetBondingRegistry()
    reg.register_pet(
        master_id="alice", pet_id="ifrit",
        pet_kind=PetKind.SUMMON_AVATAR,
    )
    reg.record_event(
        master_id="alice", pet_id="ifrit",
        event=BondEvent(
            kind=BondEventKind.ABANDONED_TO_DIE,
        ),
    )
    bond = reg.bond_for(
        master_id="alice", pet_id="ifrit",
    )
    assert bond.bond_score == -25


def test_bond_clamped_to_min():
    reg = PetBondingRegistry()
    reg.register_pet(
        master_id="alice", pet_id="x",
        pet_kind=PetKind.BST_JUG,
    )
    for _ in range(20):
        reg.record_event(
            master_id="alice", pet_id="x",
            event=BondEvent(
                kind=BondEventKind.ABANDONED_TO_DIE,
            ),
        )
    bond = reg.bond_for(
        master_id="alice", pet_id="x",
    )
    assert bond.bond_score == MIN_BOND


def test_bond_clamped_to_max():
    reg = PetBondingRegistry()
    reg.register_pet(
        master_id="alice", pet_id="x",
        pet_kind=PetKind.BST_JUG,
    )
    for _ in range(200):
        reg.record_event(
            master_id="alice", pet_id="x",
            event=BondEvent(
                kind=BondEventKind.SHARED_PERIL,
                weight_multiplier=2.0,
            ),
        )
    bond = reg.bond_for(
        master_id="alice", pet_id="x",
    )
    assert bond.bond_score == MAX_BOND


def test_bond_tier_progression():
    reg = PetBondingRegistry()
    reg.register_pet(
        master_id="alice", pet_id="x",
        pet_kind=PetKind.PUP_AUTOMATON,
    )
    # 0 = DISTANT
    assert reg.bond_tier(
        master_id="alice", pet_id="x",
    ) == BondTier.DISTANT
    # FAMILIAR (51..200)
    for _ in range(20):
        reg.record_event(
            master_id="alice", pet_id="x",
            event=BondEvent(
                kind=BondEventKind.SHARED_VICTORY,
            ),
        )
    assert reg.bond_tier(
        master_id="alice", pet_id="x",
    ) == BondTier.FAMILIAR
    # LOYAL (201..500)
    for _ in range(20):
        reg.record_event(
            master_id="alice", pet_id="x",
            event=BondEvent(
                kind=BondEventKind.SHARED_PERIL,
            ),
        )
    assert reg.bond_tier(
        master_id="alice", pet_id="x",
    ) == BondTier.LOYAL


def test_break_bond_drops_to_min():
    reg = PetBondingRegistry()
    reg.register_pet(
        master_id="alice", pet_id="ifrit",
        pet_kind=PetKind.SUMMON_AVATAR,
    )
    reg.record_event(
        master_id="alice", pet_id="ifrit",
        event=BondEvent(
            kind=BondEventKind.SHARED_VICTORY,
        ),
    )
    assert reg.break_bond(
        master_id="alice", pet_id="ifrit",
    )
    bond = reg.bond_for(
        master_id="alice", pet_id="ifrit",
    )
    assert bond.bond_score == MIN_BOND
    assert reg.bond_tier(
        master_id="alice", pet_id="ifrit",
    ) == BondTier.BROKEN


def test_break_bond_unknown_returns_false():
    reg = PetBondingRegistry()
    assert not reg.break_bond(
        master_id="ghost", pet_id="x",
    )


def test_modifier_for_broken_refuses():
    mod = modifier_for_tier(BondTier.BROKEN)
    assert mod.refuses_to_follow
    assert mod.damage_mult < 1.0


def test_modifier_for_soulbound_buffs():
    mod = modifier_for_tier(BondTier.SOULBOUND)
    assert not mod.refuses_to_follow
    assert mod.damage_mult > 1.3


def test_pets_for_master_lookup():
    reg = PetBondingRegistry()
    reg.register_pet(
        master_id="alice", pet_id="ifrit",
        pet_kind=PetKind.SUMMON_AVATAR,
    )
    reg.register_pet(
        master_id="alice", pet_id="garuda",
        pet_kind=PetKind.SUMMON_AVATAR,
    )
    pets = reg.pets_for("alice")
    assert "ifrit" in pets and "garuda" in pets


def test_record_event_unknown_returns_none():
    reg = PetBondingRegistry()
    assert reg.record_event(
        master_id="ghost", pet_id="x",
        event=BondEvent(
            kind=BondEventKind.SHARED_VICTORY,
        ),
    ) is None


def test_weight_multiplier_amplifies_delta():
    reg = PetBondingRegistry()
    reg.register_pet(
        master_id="alice", pet_id="ifrit",
        pet_kind=PetKind.SUMMON_AVATAR,
    )
    reg.record_event(
        master_id="alice", pet_id="ifrit",
        event=BondEvent(
            kind=BondEventKind.SHARED_VICTORY,
            weight_multiplier=3.0,
        ),
    )
    bond = reg.bond_for(
        master_id="alice", pet_id="ifrit",
    )
    # base 5 * 3 = 15
    assert bond.bond_score == 15


def test_total_bonds_count():
    reg = PetBondingRegistry()
    reg.register_pet(
        master_id="alice", pet_id="x",
        pet_kind=PetKind.GEO_LUOPAN,
    )
    reg.register_pet(
        master_id="bob", pet_id="y",
        pet_kind=PetKind.GEO_LUOPAN,
    )
    assert reg.total_bonds() == 2
