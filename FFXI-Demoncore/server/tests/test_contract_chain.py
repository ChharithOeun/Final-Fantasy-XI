"""Tests for contract_chain."""
from __future__ import annotations

from server.contract_chain import (
    ContractChainSystem, ChainState, StepState,
)


def _build_three_step(
    s: ContractChainSystem,
) -> str:
    cid = s.create_chain(
        poster_id="naji",
        description="Ore -> ingot -> sword -> deliver",
    )
    s.add_step(chain_id=cid, job_id="job_1")
    s.add_step(chain_id=cid, job_id="job_2")
    s.add_step(chain_id=cid, job_id="job_3")
    return cid


def test_create_chain_happy():
    s = ContractChainSystem()
    cid = s.create_chain(
        poster_id="naji", description="d",
    )
    assert cid is not None


def test_create_empty_poster_blocked():
    s = ContractChainSystem()
    assert s.create_chain(
        poster_id="", description="d",
    ) is None


def test_create_empty_description_blocked():
    s = ContractChainSystem()
    assert s.create_chain(
        poster_id="naji", description="",
    ) is None


def test_add_step_happy():
    s = ContractChainSystem()
    cid = s.create_chain(
        poster_id="naji", description="d",
    )
    sid = s.add_step(chain_id=cid, job_id="job_1")
    assert sid is not None


def test_add_step_increments_index():
    s = ContractChainSystem()
    cid = _build_three_step(s)
    steps = s.steps(chain_id=cid)
    indices = [step.step_index for step in steps]
    assert indices == [0, 1, 2]


def test_add_step_after_begin_blocked():
    s = ContractChainSystem()
    cid = _build_three_step(s)
    s.begin_chain(chain_id=cid)
    assert s.add_step(
        chain_id=cid, job_id="job_4",
    ) is None


def test_begin_chain_happy():
    s = ContractChainSystem()
    cid = _build_three_step(s)
    assert s.begin_chain(chain_id=cid) is True


def test_begin_no_steps_blocked():
    s = ContractChainSystem()
    cid = s.create_chain(
        poster_id="naji", description="d",
    )
    assert s.begin_chain(chain_id=cid) is False


def test_begin_double_blocked():
    s = ContractChainSystem()
    cid = _build_three_step(s)
    s.begin_chain(chain_id=cid)
    assert s.begin_chain(chain_id=cid) is False


def test_first_step_active_after_begin():
    s = ContractChainSystem()
    cid = _build_three_step(s)
    s.begin_chain(chain_id=cid)
    steps = s.steps(chain_id=cid)
    assert steps[0].state == StepState.ACTIVE
    assert steps[1].state == StepState.LOCKED
    assert steps[2].state == StepState.LOCKED


def test_complete_active_advances():
    s = ContractChainSystem()
    cid = _build_three_step(s)
    s.begin_chain(chain_id=cid)
    next_idx = s.complete_active_step(chain_id=cid)
    assert next_idx == 1
    steps = s.steps(chain_id=cid)
    assert steps[0].state == StepState.COMPLETED
    assert steps[1].state == StepState.ACTIVE
    assert steps[2].state == StepState.LOCKED


def test_complete_all_finishes_chain():
    s = ContractChainSystem()
    cid = _build_three_step(s)
    s.begin_chain(chain_id=cid)
    s.complete_active_step(chain_id=cid)
    s.complete_active_step(chain_id=cid)
    final = s.complete_active_step(chain_id=cid)
    assert final == -1
    assert s.chain(
        chain_id=cid,
    ).state == ChainState.COMPLETED


def test_complete_before_begin_blocked():
    s = ContractChainSystem()
    cid = _build_three_step(s)
    assert s.complete_active_step(
        chain_id=cid,
    ) is None


def test_break_chain_mid_run():
    s = ContractChainSystem()
    cid = _build_three_step(s)
    s.begin_chain(chain_id=cid)
    s.complete_active_step(chain_id=cid)
    # Step 1 is active, fail it
    assert s.break_chain(
        chain_id=cid, reason_step_index=1,
    ) is True
    chain = s.chain(chain_id=cid)
    assert chain.state == ChainState.CHAIN_BROKEN


def test_break_cancels_remaining_steps():
    s = ContractChainSystem()
    cid = _build_three_step(s)
    s.begin_chain(chain_id=cid)
    s.complete_active_step(chain_id=cid)
    s.break_chain(
        chain_id=cid, reason_step_index=1,
    )
    steps = s.steps(chain_id=cid)
    assert steps[0].state == StepState.COMPLETED
    assert steps[1].state == StepState.CANCELED
    assert steps[2].state == StepState.CANCELED


def test_break_invalid_index_blocked():
    s = ContractChainSystem()
    cid = _build_three_step(s)
    s.begin_chain(chain_id=cid)
    assert s.break_chain(
        chain_id=cid, reason_step_index=10,
    ) is False
    assert s.break_chain(
        chain_id=cid, reason_step_index=-1,
    ) is False


def test_break_after_completion_blocked():
    s = ContractChainSystem()
    cid = _build_three_step(s)
    s.begin_chain(chain_id=cid)
    s.complete_active_step(chain_id=cid)
    s.complete_active_step(chain_id=cid)
    s.complete_active_step(chain_id=cid)
    # Chain is COMPLETED, can't break it
    assert s.break_chain(
        chain_id=cid, reason_step_index=2,
    ) is False


def test_active_step_query():
    s = ContractChainSystem()
    cid = _build_three_step(s)
    s.begin_chain(chain_id=cid)
    s.complete_active_step(chain_id=cid)
    active = s.active_step(chain_id=cid)
    assert active is not None
    assert active.step_index == 1


def test_active_step_none_when_pending():
    s = ContractChainSystem()
    cid = _build_three_step(s)
    assert s.active_step(chain_id=cid) is None


def test_active_step_none_after_complete():
    s = ContractChainSystem()
    cid = _build_three_step(s)
    s.begin_chain(chain_id=cid)
    s.complete_active_step(chain_id=cid)
    s.complete_active_step(chain_id=cid)
    s.complete_active_step(chain_id=cid)
    assert s.active_step(chain_id=cid) is None


def test_unknown_chain():
    s = ContractChainSystem()
    assert s.chain(chain_id="ghost") is None
    assert s.steps(chain_id="ghost") == []


def test_enum_counts():
    assert len(list(ChainState)) == 4
    assert len(list(StepState)) == 4
