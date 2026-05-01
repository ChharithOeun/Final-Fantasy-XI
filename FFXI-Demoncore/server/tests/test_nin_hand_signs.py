"""Tests for the NIN hand-sign engine.

Run:  python -m pytest server/tests/test_nin_hand_signs.py -v
"""
import pathlib
import random
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from nin_hand_signs import (
    DAMAGE_INTERRUPT_CHANCE,
    DEFAULT_SEAL_TIME_SECONDS,
    ELEMENTAL_TINTS,
    NINJUTSU_SEQUENCES,
    NinSignManager,
    NinSignSession,
    RESUME_WINDOW_SECONDS,
    Seal,
    SEAL_SPECS,
    SignState,
    SpellPredictor,
    candidate_spells,
    chakra_brightness,
    chakra_tint,
    is_uniquely_identified,
    sequence_for,
    spell_family,
)
from nin_hand_signs.visual_chakra import BASE_CHAKRA_HEX
from nin_hand_signs.sequences import expected_total_time


# ----------------------------------------------------------------------
# Seals
# ----------------------------------------------------------------------

def test_twelve_seals_present():
    assert len(SEAL_SPECS) == 12
    for seal in Seal:
        assert seal in SEAL_SPECS


def test_seal_spec_japanese_names():
    """Spot-check a few canonical names from the doc table."""
    assert SEAL_SPECS[Seal.TIGER].japanese == "Tora"
    assert SEAL_SPECS[Seal.RABBIT].japanese == "U"
    assert SEAL_SPECS[Seal.OX].japanese == "Ushi"


def test_seal_element_bias():
    assert "fire" in SEAL_SPECS[Seal.TIGER].element_bias
    assert "thunder" in SEAL_SPECS[Seal.OX].element_bias
    assert "water" in SEAL_SPECS[Seal.DOG].element_bias


# ----------------------------------------------------------------------
# Sequences
# ----------------------------------------------------------------------

def test_thirteen_canonical_sequences():
    """The doc lists 13 sequences."""
    assert len(NINJUTSU_SEQUENCES) == 13


def test_utsusemi_progression():
    """Utsusemi Ichi is a prefix of Ni, which is a prefix of San."""
    ichi = NINJUTSU_SEQUENCES["utsusemi_ichi"]
    ni = NINJUTSU_SEQUENCES["utsusemi_ni"]
    san = NINJUTSU_SEQUENCES["utsusemi_san"]
    assert ni[: len(ichi)] == ichi
    assert san[: len(ni)] == ni


def test_katon_progression():
    """Katon family follows the same prefix-extension principle."""
    ichi = NINJUTSU_SEQUENCES["katon_ichi"]
    ni = NINJUTSU_SEQUENCES["katon_ni"]
    san = NINJUTSU_SEQUENCES["katon_san"]
    assert ni[: len(ichi)] == ichi
    assert san[: len(ni)] == ni


def test_sequence_for_unknown_returns_none():
    assert sequence_for("plasma_jutsu") is None


def test_sequence_for_case_insensitive():
    assert sequence_for("Katon_Ichi") == NINJUTSU_SEQUENCES["katon_ichi"]


def test_spell_family_lookup():
    assert spell_family("katon_san") == "katon"
    assert spell_family("hyoton_ichi") == "hyoton"
    assert spell_family("utsusemi_ni") == "utsusemi"
    assert spell_family("unknown_spell") == "unknown"


def test_expected_total_time():
    """Doc claim: Ichi-tier ~0.45s for 3-seal, San-tier 0.75s for 5-seal."""
    katon_ichi_time = expected_total_time(NINJUTSU_SEQUENCES["katon_ichi"])
    assert katon_ichi_time == pytest.approx(0.30)   # 2 seals * 0.15
    katon_san_time = expected_total_time(NINJUTSU_SEQUENCES["katon_san"])
    assert katon_san_time == pytest.approx(0.75)    # 5 seals * 0.15


# ----------------------------------------------------------------------
# Sign session lifecycle
# ----------------------------------------------------------------------

def test_begin_signing_starts_active():
    mgr = NinSignManager()
    s = mgr.begin_signing(spell="katon_ichi", caster_id="alice", now=0)
    assert s.state == SignState.ACTIVE
    assert s.seal_index == 0
    assert s.sequence == NINJUTSU_SEQUENCES["katon_ichi"]


def test_begin_signing_unknown_spell_raises():
    mgr = NinSignManager()
    with pytest.raises(KeyError):
        mgr.begin_signing(spell="plasma_jutsu", caster_id="alice", now=0)


def test_tick_advances_seal_index():
    mgr = NinSignManager()
    s = mgr.begin_signing(spell="katon_san", caster_id="alice", now=0)
    # 5 seals × 0.15s = 0.75s total
    tick = mgr.tick(s.session_id, now=0)
    assert tick.seal_index == 0
    tick = mgr.tick(s.session_id, now=0.15)
    assert tick.seal_index == 1
    tick = mgr.tick(s.session_id, now=0.45)
    assert tick.seal_index == 3
    tick = mgr.tick(s.session_id, now=0.75)
    assert tick.seal_index == 5
    assert tick.state == SignState.COMPLETE


def test_tick_clamps_at_completion():
    mgr = NinSignManager()
    s = mgr.begin_signing(spell="katon_ichi", caster_id="alice", now=0)
    tick = mgr.tick(s.session_id, now=10.0)   # way past completion
    assert tick.seal_index == 2     # full sequence
    assert tick.state == SignState.COMPLETE


def test_visible_seals_reflect_progress():
    mgr = NinSignManager()
    s = mgr.begin_signing(spell="katon_san", caster_id="alice", now=0)
    mgr.tick(s.session_id, now=0.30)   # 2 seals done
    seen = mgr.visible_seals(s.session_id)
    assert seen == [Seal.SNAKE, Seal.TIGER]


def test_progress_pct_grows():
    mgr = NinSignManager()
    s = mgr.begin_signing(spell="katon_san", caster_id="alice", now=0)
    mgr.tick(s.session_id, now=0.30)   # 2/5
    assert mgr.progress_pct(s.session_id) == pytest.approx(0.4)
    mgr.tick(s.session_id, now=0.75)
    assert mgr.progress_pct(s.session_id) == 1.0


# ----------------------------------------------------------------------
# Damage interrupt + resume
# ----------------------------------------------------------------------

def _force_interrupt_rng() -> random.Random:
    """RNG that always rolls 0.0 — interrupt fires every time."""
    rng = random.Random()
    rng.random = lambda: 0.0   # type: ignore[assignment]
    return rng


def _force_no_interrupt_rng() -> random.Random:
    rng = random.Random()
    rng.random = lambda: 0.99   # type: ignore[assignment]
    return rng


def test_damage_might_pause_on_unlucky_roll():
    mgr = NinSignManager()
    s = mgr.begin_signing(spell="katon_san", caster_id="alice", now=0)
    interrupted = mgr.notify_damage_taken(
        s.session_id, now=0.20, rng=_force_interrupt_rng(),
    )
    assert interrupted is True
    assert s.state == SignState.PAUSED
    assert s.paused_at == 0.20


def test_damage_usually_doesnt_pause():
    """RNG that never rolls below 0.10 → never interrupted."""
    mgr = NinSignManager()
    s = mgr.begin_signing(spell="katon_san", caster_id="alice", now=0)
    interrupted = mgr.notify_damage_taken(
        s.session_id, now=0.20, rng=_force_no_interrupt_rng(),
    )
    assert interrupted is False
    assert s.state == SignState.ACTIVE


def test_resume_within_window_succeeds():
    mgr = NinSignManager()
    s = mgr.begin_signing(spell="katon_san", caster_id="alice", now=0)
    mgr.tick(s.session_id, now=0.30)   # 2 seals done
    mgr.notify_damage_taken(
        s.session_id, now=0.30, rng=_force_interrupt_rng(),
    )
    assert s.state == SignState.PAUSED
    # Resume 1.0s later (within 1.5s window)
    ok = mgr.attempt_resume(s.session_id, now=1.30)
    assert ok is True
    assert s.state == SignState.ACTIVE
    # Seal index preserved
    assert s.seal_index == 2


def test_resume_after_window_fails_and_expires():
    mgr = NinSignManager()
    s = mgr.begin_signing(spell="katon_san", caster_id="alice", now=0)
    mgr.notify_damage_taken(
        s.session_id, now=0.30, rng=_force_interrupt_rng(),
    )
    # Try to resume 2.0s later — past the 1.5s window
    ok = mgr.attempt_resume(s.session_id, now=2.30)
    assert ok is False
    assert s.state == SignState.EXPIRED


def test_resume_pause_doesnt_auto_advance_seals():
    """A 1-second pause + resume shouldn't advance the seal index by
    its full elapsed-time math."""
    mgr = NinSignManager()
    s = mgr.begin_signing(spell="katon_san", caster_id="alice", now=0)
    mgr.tick(s.session_id, now=0.30)   # 2 seals done
    mgr.notify_damage_taken(
        s.session_id, now=0.30, rng=_force_interrupt_rng(),
    )
    mgr.attempt_resume(s.session_id, now=1.30)   # paused 1 second
    # Tick at 1.45s elapsed total; only 0.45s of "active" time
    tick = mgr.tick(s.session_id, now=1.45)
    assert tick.seal_index == 3   # 0.45s / 0.15s = 3 seals


def test_expire_if_window_passed():
    mgr = NinSignManager()
    s = mgr.begin_signing(spell="katon_ichi", caster_id="alice", now=0)
    mgr.notify_damage_taken(
        s.session_id, now=0.10, rng=_force_interrupt_rng(),
    )
    expired = mgr.expire_if_window_passed(s.session_id, now=0.50)
    assert expired is False
    expired = mgr.expire_if_window_passed(s.session_id, now=2.0)
    assert expired is True
    assert s.state == SignState.EXPIRED


def test_cancel_session():
    mgr = NinSignManager()
    s = mgr.begin_signing(spell="katon_ichi", caster_id="alice", now=0)
    assert mgr.cancel(s.session_id) is True
    assert s.state == SignState.CANCELED


# ----------------------------------------------------------------------
# Spell predictor
# ----------------------------------------------------------------------

def test_empty_observation_returns_all_spells():
    cands = candidate_spells([])
    assert len(cands) == 13


def test_first_seal_narrows_candidates():
    cands = candidate_spells([Seal.SNAKE])
    # Snake-starting spells: katon (3 tiers) + aisha = 4
    assert "katon_ichi" in cands
    assert "katon_ni" in cands
    assert "katon_san" in cands
    assert "aisha" in cands
    # NOT utsusemi (starts with Tiger)
    assert "utsusemi_ichi" not in cands


def test_doc_example_katon_san_progressive_narrowing():
    """The doc's worked example: skilled player narrows to Katon: San
    by the fourth seal."""
    pred = SpellPredictor()
    # Snake
    pred.observe(Seal.SNAKE)
    cands1 = pred.candidates()
    assert len(cands1) >= 3   # could be katon + aisha
    # Tiger -> narrows to fire-school + aisha (Snake-Boar-Tiger)
    pred.observe(Seal.TIGER)
    cands2 = pred.candidates()
    assert "katon_ichi" in cands2
    assert "katon_ni" in cands2
    assert "katon_san" in cands2
    # Aisha was Snake-Boar-Tiger, so it's NOT in (we hit Tiger after Snake)
    assert "aisha" not in cands2
    # Horse -> confirmed Katon family (rules out Katon: Ichi which only has Snake-Tiger)
    pred.observe(Seal.HORSE)
    cands3 = pred.candidates()
    # Katon Ichi (2 seals) is fully formed at Snake-Tiger; Horse extends past it
    assert "katon_ichi" not in cands3
    assert "katon_ni" in cands3
    assert "katon_san" in cands3
    # Monkey -> only Katon: San
    pred.observe(Seal.MONKEY)
    assert pred.candidates() == ["katon_san"]
    assert pred.is_unique() is True
    # Tiger -> Katon: San complete
    pred.observe(Seal.TIGER)
    assert pred.candidates() == ["katon_san"]


def test_is_uniquely_identified():
    """A unique sequence after enough seals."""
    # Doton starts with Boar -> Dragon, but Dragon also doesn't start
    # any other sequence
    assert is_uniquely_identified([Seal.BOAR, Seal.DRAGON]) is True
    # Just Boar — at least two spells start with it (none in the doc),
    # actually only doton; but utsusemi starts with Tiger, etc.
    # Check what spells start with Boar
    boar_starters = [s for s in NINJUTSU_SEQUENCES.values() if s[0] == Seal.BOAR]
    if len(boar_starters) == 1:
        assert is_uniquely_identified([Seal.BOAR]) is True
    else:
        assert is_uniquely_identified([Seal.BOAR]) is False


def test_predictor_remaining_seal_count():
    pred = SpellPredictor()
    pred.observe(Seal.SNAKE).observe(Seal.TIGER).observe(Seal.HORSE).observe(Seal.MONKEY)
    # Now uniquely Katon: San (5 seals total); 4 seen
    assert pred.is_unique()
    assert pred.remaining_seal_count() == 1


def test_predictor_reset():
    pred = SpellPredictor()
    pred.observe(Seal.TIGER)
    pred.reset()
    assert pred.observed == []


# ----------------------------------------------------------------------
# Visual chakra
# ----------------------------------------------------------------------

def test_chakra_brightness_starts_faint():
    """At seal_index 0, brightness is 0.20 — faint glow on hands."""
    assert chakra_brightness(0, 5) == pytest.approx(0.20)


def test_chakra_brightness_peaks_at_completion():
    assert chakra_brightness(5, 5) == pytest.approx(1.0)


def test_chakra_brightness_mid_sequence():
    """Halfway: 0.20 + 0.80 * 0.5 = 0.60."""
    assert chakra_brightness(2, 4) == pytest.approx(0.60)


def test_chakra_tint_pre_threshold_is_base():
    """Below the 70% mark, tint stays on the base blue."""
    assert chakra_tint("katon_san", seal_index=0, total_seals=5) == BASE_CHAKRA_HEX
    assert chakra_tint("katon_san", seal_index=2, total_seals=5) == BASE_CHAKRA_HEX


def test_chakra_tint_after_threshold_uses_family_color():
    """At 80% (4/5), tint shifts to the family color."""
    katon_tint = chakra_tint("katon_san", seal_index=4, total_seals=5)
    assert katon_tint == ELEMENTAL_TINTS["katon"]
    # Hyoton: cyan
    hyoton_tint = chakra_tint("hyoton_ichi", seal_index=5, total_seals=6)
    assert hyoton_tint == ELEMENTAL_TINTS["hyoton"]


def test_chakra_tint_unknown_family_falls_back():
    assert chakra_tint("plasma_jutsu", seal_index=10, total_seals=10) == BASE_CHAKRA_HEX


def test_elemental_tints_table_completeness():
    for family in ("katon", "hyoton", "raiton", "suiton", "doton",
                     "huton", "tonko", "utsusemi"):
        assert family in ELEMENTAL_TINTS


# ----------------------------------------------------------------------
# Integration scenario: full Katon: San cast end-to-end
# ----------------------------------------------------------------------

def test_full_katon_san_signed_and_observed():
    """End-to-end: NIN signs Katon: San; observer reads progressive
    seals; predictor identifies uniquely at seal 4 of 5; chakra tint
    activates around that mark."""
    mgr = NinSignManager()
    s = mgr.begin_signing(spell="katon_san", caster_id="alice", now=0)
    pred = SpellPredictor()

    # Tick at each seal completion, observer reads
    for i in range(1, 6):
        tick = mgr.tick(s.session_id, now=i * 0.15)
        if tick.seal_index > len(pred.observed):
            for seal in tick.visible_seals[len(pred.observed):]:
                pred.observe(seal)
        # By seal 4 the spell should be uniquely identified
        if tick.seal_index >= 4:
            assert pred.is_unique() is True

    assert s.state == SignState.COMPLETE
    assert pred.candidates() == ["katon_san"]


def test_damage_interrupt_doc_chance_value():
    """Verify the magic number from the doc matches the constant."""
    assert DAMAGE_INTERRUPT_CHANCE == 0.10
    assert RESUME_WINDOW_SECONDS == 1.5
    assert DEFAULT_SEAL_TIME_SECONDS == 0.15
