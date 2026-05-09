"""Tests for player_advocate_registry."""
from __future__ import annotations

from server.player_advocate_registry import (
    PlayerAdvocateRegistrySystem, RetainerState,
)


def _register(
    s: PlayerAdvocateRegistrySystem, fee: int = 1000,
) -> None:
    s.register_advocate(
        advocate_id="naji", name="Naji of Bastok",
        specialty="theft", retainer_fee_gil=fee,
    )


def test_register_happy():
    s = PlayerAdvocateRegistrySystem()
    assert s.register_advocate(
        advocate_id="naji", name="N",
        specialty="theft", retainer_fee_gil=1000,
    ) is True


def test_register_dup_blocked():
    s = PlayerAdvocateRegistrySystem()
    _register(s)
    assert s.register_advocate(
        advocate_id="naji", name="X",
        specialty="fraud", retainer_fee_gil=2000,
    ) is False


def test_register_zero_fee_blocked():
    s = PlayerAdvocateRegistrySystem()
    assert s.register_advocate(
        advocate_id="naji", name="N",
        specialty="theft", retainer_fee_gil=0,
    ) is False


def test_register_empty_specialty_blocked():
    s = PlayerAdvocateRegistrySystem()
    assert s.register_advocate(
        advocate_id="naji", name="N",
        specialty="", retainer_fee_gil=1000,
    ) is False


def test_hire_happy():
    s = PlayerAdvocateRegistrySystem()
    _register(s)
    assert s.hire(
        advocate_id="naji", client_id="alice",
    ) is not None


def test_hire_self_blocked():
    s = PlayerAdvocateRegistrySystem()
    _register(s)
    assert s.hire(
        advocate_id="naji", client_id="naji",
    ) is None


def test_hire_dup_blocked():
    s = PlayerAdvocateRegistrySystem()
    _register(s)
    s.hire(advocate_id="naji", client_id="alice")
    assert s.hire(
        advocate_id="naji", client_id="alice",
    ) is None


def test_hire_unknown_advocate_blocked():
    s = PlayerAdvocateRegistrySystem()
    assert s.hire(
        advocate_id="ghost", client_id="alice",
    ) is None


def test_hire_increments_cases_taken():
    s = PlayerAdvocateRegistrySystem()
    _register(s)
    s.hire(advocate_id="naji", client_id="alice")
    s.hire(advocate_id="naji", client_id="bob")
    assert s.advocate(
        advocate_id="naji",
    ).cases_taken == 2


def test_drop_client_happy():
    s = PlayerAdvocateRegistrySystem()
    _register(s, fee=1000)
    s.hire(advocate_id="naji", client_id="alice")
    refund = s.drop_client(
        advocate_id="naji", client_id="alice",
    )
    assert refund == 500


def test_drop_client_no_active_blocked():
    s = PlayerAdvocateRegistrySystem()
    _register(s)
    assert s.drop_client(
        advocate_id="naji", client_id="alice",
    ) is None


def test_re_hire_after_drop():
    s = PlayerAdvocateRegistrySystem()
    _register(s)
    s.hire(advocate_id="naji", client_id="alice")
    s.drop_client(
        advocate_id="naji", client_id="alice",
    )
    assert s.hire(
        advocate_id="naji", client_id="alice",
    ) is not None


def test_discharge_happy():
    s = PlayerAdvocateRegistrySystem()
    _register(s)
    s.hire(advocate_id="naji", client_id="alice")
    assert s.discharge(
        advocate_id="naji", client_id="alice",
    ) is True


def test_discharge_no_active_blocked():
    s = PlayerAdvocateRegistrySystem()
    _register(s)
    assert s.discharge(
        advocate_id="naji", client_id="alice",
    ) is False


def test_complete_case_won():
    s = PlayerAdvocateRegistrySystem()
    _register(s)
    s.hire(advocate_id="naji", client_id="alice")
    assert s.complete_case(
        advocate_id="naji", client_id="alice",
        won=True,
    ) is True
    assert s.advocate(
        advocate_id="naji",
    ).cases_won == 1


def test_complete_case_lost():
    s = PlayerAdvocateRegistrySystem()
    _register(s)
    s.hire(advocate_id="naji", client_id="alice")
    s.complete_case(
        advocate_id="naji", client_id="alice",
        won=False,
    )
    assert s.advocate(
        advocate_id="naji",
    ).cases_won == 0


def test_complete_case_no_active_blocked():
    s = PlayerAdvocateRegistrySystem()
    _register(s)
    assert s.complete_case(
        advocate_id="naji", client_id="alice",
        won=True,
    ) is False


def test_win_rate_computed():
    s = PlayerAdvocateRegistrySystem()
    _register(s)
    s.hire(advocate_id="naji", client_id="a")
    s.complete_case(
        advocate_id="naji", client_id="a", won=True,
    )
    s.hire(advocate_id="naji", client_id="b")
    s.complete_case(
        advocate_id="naji", client_id="b", won=False,
    )
    assert s.win_rate(advocate_id="naji") == 0.5


def test_win_rate_no_cases_none():
    s = PlayerAdvocateRegistrySystem()
    _register(s)
    assert s.win_rate(advocate_id="naji") is None


def test_find_by_specialty():
    s = PlayerAdvocateRegistrySystem()
    _register(s)
    s.register_advocate(
        advocate_id="bob", name="B",
        specialty="theft", retainer_fee_gil=500,
    )
    s.register_advocate(
        advocate_id="cara", name="C",
        specialty="fraud", retainer_fee_gil=500,
    )
    assert len(s.find_by_specialty(
        specialty="theft",
    )) == 2


def test_unknown_advocate():
    s = PlayerAdvocateRegistrySystem()
    assert s.advocate(
        advocate_id="ghost",
    ) is None


def test_state_count():
    assert len(list(RetainerState)) == 4
