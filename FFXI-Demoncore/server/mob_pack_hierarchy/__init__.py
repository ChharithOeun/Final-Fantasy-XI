"""Mob pack hierarchy — alpha/beta/omega pack roles.

Within a pack (mob_breeding pack_id), individuals occupy roles:
ALPHA buffs the pack, BETAs are seasoned mid-rankers, OMEGAs flee
first when morale breaks. Killing the alpha triggers SUCCESSION:
the strongest beta promotes to alpha, an omega may promote up,
and pack-wide morale takes a temporary hit.

Wires into mob_fear (rout cascades faster after alpha death) and
combat_tactics (alpha-led packs choose more aggressive openers).

Public surface
--------------
    PackRole enum
    PackMember dataclass
    PackHierarchy dataclass
    SuccessionResult dataclass
    MobPackHierarchyRegistry
        .form_pack(pack_id, alpha_uid)
        .add_member(pack_id, member_uid, role, strength)
        .alpha_buffs(pack_id) -> bonuses
        .kill_member(pack_id, member_uid) -> Optional[SuccessionResult]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Pack-wide morale penalty when alpha dies (out of 100).
ALPHA_DEATH_MORALE_PENALTY = 25
ALPHA_DAMAGE_BUFF_PCT = 15
ALPHA_DEFENSE_BUFF_PCT = 10
ALPHA_AGGRO_RANGE_BONUS = 5


class PackRole(str, enum.Enum):
    ALPHA = "alpha"
    BETA = "beta"
    OMEGA = "omega"
    PUP = "pup"            # juvenile, can't lead


@dataclasses.dataclass
class PackMember:
    member_uid: str
    role: PackRole
    strength: int = 50      # 0..100; promotion order
    alive: bool = True


@dataclasses.dataclass
class PackHierarchy:
    pack_id: str
    alpha_uid: t.Optional[str] = None
    members: dict[str, PackMember] = dataclasses.field(
        default_factory=dict,
    )
    morale: int = 100      # 0..100; current
    succession_count: int = 0


@dataclasses.dataclass(frozen=True)
class AlphaBuffs:
    damage_pct: int
    defense_pct: int
    aggro_range_bonus: int


@dataclasses.dataclass(frozen=True)
class SuccessionResult:
    pack_id: str
    fallen_alpha: str
    new_alpha: t.Optional[str]
    morale_after: int
    note: str = ""


@dataclasses.dataclass
class MobPackHierarchyRegistry:
    alpha_death_morale_penalty: int = ALPHA_DEATH_MORALE_PENALTY
    _packs: dict[str, PackHierarchy] = dataclasses.field(
        default_factory=dict,
    )

    def form_pack(
        self, *, pack_id: str, alpha_uid: str,
        alpha_strength: int = 80,
    ) -> t.Optional[PackHierarchy]:
        if pack_id in self._packs:
            return None
        pack = PackHierarchy(
            pack_id=pack_id, alpha_uid=alpha_uid,
        )
        pack.members[alpha_uid] = PackMember(
            member_uid=alpha_uid, role=PackRole.ALPHA,
            strength=alpha_strength,
        )
        self._packs[pack_id] = pack
        return pack

    def pack(
        self, pack_id: str,
    ) -> t.Optional[PackHierarchy]:
        return self._packs.get(pack_id)

    def add_member(
        self, *, pack_id: str, member_uid: str,
        role: PackRole, strength: int = 50,
    ) -> bool:
        pack = self._packs.get(pack_id)
        if pack is None:
            return False
        if member_uid in pack.members:
            return False
        if role == PackRole.ALPHA and pack.alpha_uid:
            return False        # only one alpha per pack
        pack.members[member_uid] = PackMember(
            member_uid=member_uid, role=role,
            strength=max(0, min(100, strength)),
        )
        if role == PackRole.ALPHA:
            pack.alpha_uid = member_uid
        return True

    def alpha_buffs(
        self, pack_id: str,
    ) -> t.Optional[AlphaBuffs]:
        pack = self._packs.get(pack_id)
        if pack is None or pack.alpha_uid is None:
            return None
        alpha = pack.members.get(pack.alpha_uid)
        if alpha is None or not alpha.alive:
            return None
        return AlphaBuffs(
            damage_pct=ALPHA_DAMAGE_BUFF_PCT,
            defense_pct=ALPHA_DEFENSE_BUFF_PCT,
            aggro_range_bonus=ALPHA_AGGRO_RANGE_BONUS,
        )

    def kill_member(
        self, *, pack_id: str, member_uid: str,
    ) -> t.Optional[SuccessionResult]:
        pack = self._packs.get(pack_id)
        if pack is None:
            return None
        member = pack.members.get(member_uid)
        if member is None or not member.alive:
            return None
        member.alive = False
        # If alpha fell, run succession
        if pack.alpha_uid == member_uid:
            old_alpha = member_uid
            pack.alpha_uid = None
            pack.morale = max(
                0,
                pack.morale - self.alpha_death_morale_penalty,
            )
            # Promote strongest living beta
            betas = [
                m for m in pack.members.values()
                if m.alive and m.role == PackRole.BETA
            ]
            if not betas:
                return SuccessionResult(
                    pack_id=pack_id,
                    fallen_alpha=old_alpha,
                    new_alpha=None,
                    morale_after=pack.morale,
                    note="no beta available",
                )
            new_alpha = max(betas, key=lambda m: m.strength)
            new_alpha.role = PackRole.ALPHA
            pack.alpha_uid = new_alpha.member_uid
            pack.succession_count += 1
            # Promote one omega up to beta if any exist
            omegas = [
                m for m in pack.members.values()
                if m.alive and m.role == PackRole.OMEGA
            ]
            if omegas:
                strongest_omega = max(
                    omegas, key=lambda m: m.strength,
                )
                strongest_omega.role = PackRole.BETA
            return SuccessionResult(
                pack_id=pack_id,
                fallen_alpha=old_alpha,
                new_alpha=new_alpha.member_uid,
                morale_after=pack.morale,
            )
        return None

    def members_by_role(
        self, *, pack_id: str, role: PackRole,
    ) -> tuple[PackMember, ...]:
        pack = self._packs.get(pack_id)
        if pack is None:
            return ()
        return tuple(
            m for m in pack.members.values()
            if m.role == role and m.alive
        )

    def total_packs(self) -> int:
        return len(self._packs)


__all__ = [
    "ALPHA_DEATH_MORALE_PENALTY",
    "ALPHA_DAMAGE_BUFF_PCT",
    "ALPHA_DEFENSE_BUFF_PCT",
    "ALPHA_AGGRO_RANGE_BONUS",
    "PackRole", "PackMember", "PackHierarchy",
    "AlphaBuffs", "SuccessionResult",
    "MobPackHierarchyRegistry",
]
