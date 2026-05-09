"""Contract chain — multi-step sequential dependencies.

Some commissions only make sense as ordered sequences. A
collector wants a rare ore (delivery) → smelted into ingots
(craft) → forged into a weapon (craft) → delivered to him in
Norg (delivery + escort). Posting all four as separate jobs
means the wrong contractor might pick them up in the wrong
order or the chain breaks halfway.

A contract_chain bundles the steps. Each step references an
adventurers_guild job_id. Step N+1 only becomes ACTIVE when
step N is COMPLETED. If any step EXPIRES or is CANCELED, the
whole chain enters CHAIN_BROKEN — remaining steps are
canceled, escrows refunded by upstream rules.

Lifecycle (per chain)
    PENDING       all steps created, none active yet
    ACTIVE        a step is currently active
    COMPLETED     all steps completed in order
    CHAIN_BROKEN  a step failed, remaining canceled

Public surface
--------------
    ChainState enum
    StepState enum
    ChainStep dataclass (frozen)
    Chain dataclass (frozen)
    ContractChainSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ChainState(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CHAIN_BROKEN = "chain_broken"


class StepState(str, enum.Enum):
    LOCKED = "locked"     # waiting for predecessor
    ACTIVE = "active"     # currently the open step
    COMPLETED = "completed"
    CANCELED = "canceled"


@dataclasses.dataclass(frozen=True)
class ChainStep:
    step_id: str
    chain_id: str
    step_index: int
    job_id: str
    state: StepState


@dataclasses.dataclass(frozen=True)
class Chain:
    chain_id: str
    poster_id: str
    description: str
    state: ChainState
    current_step_index: int


@dataclasses.dataclass
class _CState:
    spec: Chain
    steps: list[ChainStep] = dataclasses.field(
        default_factory=list,
    )


@dataclasses.dataclass
class ContractChainSystem:
    _chains: dict[str, _CState] = dataclasses.field(
        default_factory=dict,
    )
    _next_chain: int = 1
    _next_step: int = 1

    def create_chain(
        self, *, poster_id: str, description: str,
    ) -> t.Optional[str]:
        if not poster_id or not description:
            return None
        cid = f"chain_{self._next_chain}"
        self._next_chain += 1
        self._chains[cid] = _CState(
            spec=Chain(
                chain_id=cid, poster_id=poster_id,
                description=description,
                state=ChainState.PENDING,
                current_step_index=0,
            ),
        )
        return cid

    def add_step(
        self, *, chain_id: str, job_id: str,
    ) -> t.Optional[str]:
        if chain_id not in self._chains:
            return None
        st = self._chains[chain_id]
        if st.spec.state != ChainState.PENDING:
            return None
        if not job_id:
            return None
        sid = f"step_{self._next_step}"
        self._next_step += 1
        idx = len(st.steps)
        st.steps.append(
            ChainStep(
                step_id=sid, chain_id=chain_id,
                step_index=idx, job_id=job_id,
                state=StepState.LOCKED,
            ),
        )
        return sid

    def begin_chain(
        self, *, chain_id: str,
    ) -> bool:
        if chain_id not in self._chains:
            return False
        st = self._chains[chain_id]
        if st.spec.state != ChainState.PENDING:
            return False
        if not st.steps:
            return False
        # Activate the first step
        first = st.steps[0]
        st.steps[0] = dataclasses.replace(
            first, state=StepState.ACTIVE,
        )
        st.spec = dataclasses.replace(
            st.spec, state=ChainState.ACTIVE,
            current_step_index=0,
        )
        return True

    def complete_active_step(
        self, *, chain_id: str,
    ) -> t.Optional[int]:
        """Mark current ACTIVE step COMPLETED and
        activate the next. Returns next step_index
        or -1 if chain finished.
        """
        if chain_id not in self._chains:
            return None
        st = self._chains[chain_id]
        if st.spec.state != ChainState.ACTIVE:
            return None
        idx = st.spec.current_step_index
        if idx >= len(st.steps):
            return None
        cur = st.steps[idx]
        if cur.state != StepState.ACTIVE:
            return None
        st.steps[idx] = dataclasses.replace(
            cur, state=StepState.COMPLETED,
        )
        next_idx = idx + 1
        if next_idx >= len(st.steps):
            st.spec = dataclasses.replace(
                st.spec, state=ChainState.COMPLETED,
                current_step_index=next_idx,
            )
            return -1
        nxt = st.steps[next_idx]
        st.steps[next_idx] = dataclasses.replace(
            nxt, state=StepState.ACTIVE,
        )
        st.spec = dataclasses.replace(
            st.spec, current_step_index=next_idx,
        )
        return next_idx

    def break_chain(
        self, *, chain_id: str, reason_step_index: int,
    ) -> bool:
        """A step failed (expired/canceled). All
        remaining steps become CANCELED. Chain
        enters CHAIN_BROKEN.
        """
        if chain_id not in self._chains:
            return False
        st = self._chains[chain_id]
        if st.spec.state != ChainState.ACTIVE:
            return False
        if reason_step_index < 0:
            return False
        if reason_step_index >= len(st.steps):
            return False
        # Cancel the failing step + all later locked
        for i in range(reason_step_index, len(st.steps)):
            step = st.steps[i]
            if step.state in (
                StepState.LOCKED, StepState.ACTIVE,
            ):
                st.steps[i] = dataclasses.replace(
                    step, state=StepState.CANCELED,
                )
        st.spec = dataclasses.replace(
            st.spec, state=ChainState.CHAIN_BROKEN,
        )
        return True

    def chain(
        self, *, chain_id: str,
    ) -> t.Optional[Chain]:
        st = self._chains.get(chain_id)
        return st.spec if st else None

    def steps(
        self, *, chain_id: str,
    ) -> list[ChainStep]:
        st = self._chains.get(chain_id)
        if st is None:
            return []
        return list(st.steps)

    def active_step(
        self, *, chain_id: str,
    ) -> t.Optional[ChainStep]:
        st = self._chains.get(chain_id)
        if st is None:
            return None
        if st.spec.state != ChainState.ACTIVE:
            return None
        idx = st.spec.current_step_index
        if 0 <= idx < len(st.steps):
            return st.steps[idx]
        return None


__all__ = [
    "ChainState", "StepState", "ChainStep", "Chain",
    "ContractChainSystem",
]
