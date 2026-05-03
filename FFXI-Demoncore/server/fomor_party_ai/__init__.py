"""Fomor party AI — group movement, skillchain coordination,
magic burst attempts.

In Demoncore, Fomors don't roam as isolated mobs — they travel
in PARTIES (canonical 4-6 members) using the same alliance
discipline that player parties do. The AI driving them tries to:

* maintain a FORMATION (leader anchor + members hold positions)
* lock onto the same kill target as the leader
* call out SKILLCHAIN INTENT — leader announces "I'm casting WS X
  with element Y in N seconds" so the party can chain
* attempt MAGIC BURSTS on each other's chains — casters watch
  the open window in magic_burst_window and burst-cast the
  matching element

This module is a state-modeling layer; the actual decision-making
runs in agent_orchestrator (the AI agents). What this module
provides:

* PARTY STATE — leader, members, formation slots, focus target
* CHAIN INTENT broadcasts — what the leader is about to do
* BURST INTENT broadcasts — what casters intend to do in the
  follow-up window
* helpers the AI uses to reason about ideal next actions

Public surface
--------------
    FomorRole enum (leader / melee / caster / healer)
    FomorMember dataclass
    FomorParty
        .add_member(...) / .set_leader(...)
        .set_focus_target(target_id)
        .broadcast_chain_intent(...) / .broadcast_burst_intent(...)
        .casters_watching_for_burst() / .melees_ready_to_chain()
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.magic_burst_window import SkillchainElement


MAX_FOMOR_PARTY_SIZE = 6
DEFAULT_CHAIN_LEAD_SECONDS = 6   # how long the leader telegraphs


class FomorRole(str, enum.Enum):
    LEADER = "leader"
    MELEE = "melee"
    CASTER = "caster"
    HEALER = "healer"
    SUPPORT = "support"


class FormationSlot(str, enum.Enum):
    """Standard formation slots — AI moves members to fill them."""
    POINT = "point"          # leader's position
    LEFT = "left_flank"
    RIGHT = "right_flank"
    REAR = "rear"
    PROTECT_HEALER = "protect_healer"
    SCOUT = "scout"


@dataclasses.dataclass
class FomorMember:
    mob_id: str
    role: FomorRole
    slot: FormationSlot = FormationSlot.POINT
    last_action_at_seconds: float = 0.0


@dataclasses.dataclass(frozen=True)
class ChainIntent:
    """Leader broadcasts: 'I'm doing WS X with element Y at time Z.'
    The AI agents subscribe to these."""
    leader_id: str
    skillchain_element: SkillchainElement
    intended_at_seconds: float
    weapon_skill_id: str


@dataclasses.dataclass(frozen=True)
class BurstIntent:
    """Caster broadcasts: 'I will burst element X on the leader's
    chain at time T.'"""
    caster_id: str
    burst_element: SkillchainElement
    intended_at_seconds: float
    spell_id: str


@dataclasses.dataclass(frozen=True)
class AddMemberResult:
    accepted: bool
    member: t.Optional[FomorMember] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class FomorParty:
    party_id: str
    members: list[FomorMember] = dataclasses.field(default_factory=list)
    leader_id: t.Optional[str] = None
    focus_target_id: t.Optional[str] = None
    chain_intents: list[ChainIntent] = dataclasses.field(
        default_factory=list,
    )
    burst_intents: list[BurstIntent] = dataclasses.field(
        default_factory=list,
    )

    @property
    def member_ids(self) -> tuple[str, ...]:
        return tuple(m.mob_id for m in self.members)

    @property
    def is_full(self) -> bool:
        return len(self.members) >= MAX_FOMOR_PARTY_SIZE

    def add_member(
        self, *, mob_id: str, role: FomorRole,
        slot: FormationSlot = FormationSlot.POINT,
    ) -> AddMemberResult:
        if mob_id in self.member_ids:
            return AddMemberResult(False, reason="duplicate")
        if self.is_full:
            return AddMemberResult(False, reason="party full")
        m = FomorMember(mob_id=mob_id, role=role, slot=slot)
        self.members.append(m)
        if role == FomorRole.LEADER and self.leader_id is None:
            self.leader_id = mob_id
        return AddMemberResult(True, member=m)

    def set_leader(self, *, mob_id: str) -> bool:
        if mob_id not in self.member_ids:
            return False
        for m in self.members:
            if m.role == FomorRole.LEADER and m.mob_id != mob_id:
                m.role = FomorRole.MELEE   # demote prior leader
            if m.mob_id == mob_id:
                m.role = FomorRole.LEADER
        self.leader_id = mob_id
        return True

    def set_focus_target(self, *, target_id: str) -> bool:
        if not target_id:
            return False
        self.focus_target_id = target_id
        return True

    def members_in_role(
        self, role: FomorRole,
    ) -> tuple[FomorMember, ...]:
        return tuple(m for m in self.members if m.role == role)

    # ----- Chain / burst broadcasts ----------------------------------
    def broadcast_chain_intent(
        self, *, leader_id: str,
        skillchain_element: SkillchainElement,
        weapon_skill_id: str, now_seconds: float,
        lead_seconds: float = DEFAULT_CHAIN_LEAD_SECONDS,
    ) -> ChainIntent:
        intent = ChainIntent(
            leader_id=leader_id,
            skillchain_element=skillchain_element,
            intended_at_seconds=now_seconds + lead_seconds,
            weapon_skill_id=weapon_skill_id,
        )
        self.chain_intents.append(intent)
        return intent

    def broadcast_burst_intent(
        self, *, caster_id: str,
        burst_element: SkillchainElement,
        spell_id: str,
        intended_at_seconds: float,
    ) -> BurstIntent:
        intent = BurstIntent(
            caster_id=caster_id, burst_element=burst_element,
            spell_id=spell_id,
            intended_at_seconds=intended_at_seconds,
        )
        self.burst_intents.append(intent)
        return intent

    def latest_chain_intent(self) -> t.Optional[ChainIntent]:
        return self.chain_intents[-1] if self.chain_intents else None

    def casters_watching_for_burst(
        self, *, now_seconds: float, watch_window: float = 12.0,
    ) -> tuple[FomorMember, ...]:
        """Casters that should be primed to burst on the latest
        chain intent (within the magic-burst window)."""
        latest = self.latest_chain_intent()
        if latest is None:
            return ()
        if abs(latest.intended_at_seconds - now_seconds) > watch_window:
            return ()
        return self.members_in_role(FomorRole.CASTER)

    def melees_ready_to_chain(
        self, *, now_seconds: float,
    ) -> tuple[FomorMember, ...]:
        """Melee members who have not acted recently and could
        contribute to a chain."""
        candidates: list[FomorMember] = []
        for m in self.members:
            if m.role not in (FomorRole.MELEE, FomorRole.LEADER):
                continue
            # Last action older than 5s -> ready
            if now_seconds - m.last_action_at_seconds >= 5.0:
                candidates.append(m)
        return tuple(candidates)

    def record_action(self, *, mob_id: str, now_seconds: float) -> bool:
        for m in self.members:
            if m.mob_id == mob_id:
                m.last_action_at_seconds = now_seconds
                return True
        return False


__all__ = [
    "MAX_FOMOR_PARTY_SIZE", "DEFAULT_CHAIN_LEAD_SECONDS",
    "FomorRole", "FormationSlot",
    "FomorMember", "ChainIntent", "BurstIntent",
    "AddMemberResult", "FomorParty",
]
