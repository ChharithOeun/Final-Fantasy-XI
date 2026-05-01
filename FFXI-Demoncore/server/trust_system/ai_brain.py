"""TrustAIBrain — the smarter party-sync AI.

Per the user direction: 'its AI is pretty bad, so implementing a
new AI for trusts to have better party sync would be great'.

The retail FFXI trust AI was a roughly hardcoded behavior tree per
trust with weak coordination and slow reaction times. Demoncore's
AI is a single tick-based decision function with a strict priority
ladder + per-role heal thresholds + skillchain coordination + MB
awareness + intervention-MB awareness.

Priority ladder (highest first):
    1. SELF_PRESERVATION  - trust HP <= 30%, retreat or self-heal
    2. PARTY_HEAL          - any party member <= heal_threshold
    3. INTERVENTION_MB     - incoming damage on a party member; cast
                              an intervention-MB shield if available
    4. SKILLCHAIN_OPENER   - sc_priority trust who's ready to open
    5. MAGIC_BURST         - skillchain window open + nuke ready
    6. DEBUFF              - tactical debuffs (Slow / Paralyze / Bio)
    7. BUFF                - haste / regen / bards' songs (proactive)
    8. DEFAULT             - role-default action (melee / nuke /
                              shield-bash / etc.)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from .catalog import TrustRole, TrustSpec
from .party import TrustSnapshot


# Per-role default heal threshold (HP fraction at which a healer
# steps in).
DEFAULT_HEAL_THRESHOLDS: dict[TrustRole, float] = {
    TrustRole.TANK: 0.40,         # tanks heal at 40%
    TrustRole.HEALER: 0.30,       # healer self-heals at 30% (last)
    TrustRole.MELEE_DPS: 0.55,    # squishier — heal earlier
    TrustRole.RANGED_DPS: 0.55,
    TrustRole.SUPPORT: 0.50,
    TrustRole.DEBUFFER: 0.50,
    TrustRole.NUKER: 0.55,
}


class AIPriority(str, enum.Enum):
    """Priority bucket for the action selected this tick."""
    SELF_PRESERVATION = "self_preservation"
    PARTY_HEAL = "party_heal"
    INTERVENTION_MB = "intervention_mb"
    SKILLCHAIN_OPENER = "skillchain_opener"
    MAGIC_BURST = "magic_burst"
    DEBUFF = "debuff"
    BUFF = "buff"
    DEFAULT = "default"
    WAIT = "wait"


@dataclasses.dataclass
class PartyMemberState:
    """The slice of party-member info the AI cares about."""
    member_id: str
    is_player: bool
    current_hp: int
    max_hp: int
    is_alive: bool = True
    incoming_damage_predicted: int = 0   # set by aoe_telegraph layer
    is_target_of_player: bool = False     # follow-target signal


@dataclasses.dataclass
class AIDecision:
    action: str                           # "heal_iii" / "melee" / etc.
    target_id: t.Optional[str]
    spell_or_ability: t.Optional[str] = None
    priority: AIPriority = AIPriority.DEFAULT
    reason: str = ""


class TrustAIBrain:
    """Tick-based decision function. Pure: takes the trust snapshot
    + party state + an optional skillchain-window flag and returns
    an AIDecision."""

    def __init__(self,
                  *,
                  heal_thresholds: t.Optional[dict[TrustRole, float]] = None
                  ) -> None:
        self.heal_thresholds = heal_thresholds or dict(DEFAULT_HEAL_THRESHOLDS)

    def tick(self,
              *,
              trust: TrustSnapshot,
              party: list[PartyMemberState],
              now: float,
              skillchain_window_open: bool = False,
              enemy_target_id: t.Optional[str] = None,
              ) -> AIDecision:
        """Run one decision tick for `trust`. Returns the action to
        perform this tick."""
        spec = trust.spec

        # 1) Self-preservation
        if trust.current_hp / max(1, trust.max_hp) <= 0.30:
            if self._can_self_heal(spec):
                return AIDecision(
                    action="self_heal", target_id=trust.trust_id,
                    spell_or_ability=self._pick_heal_spell(spec, "self"),
                    priority=AIPriority.SELF_PRESERVATION,
                    reason="self HP critically low",
                )
            return AIDecision(
                action="retreat", target_id=None,
                priority=AIPriority.SELF_PRESERVATION,
                reason="no self-heal; retreating",
            )

        # 2) Party heal — only the healer/tank-with-heals branches enter
        if spec.role in (TrustRole.HEALER, TrustRole.TANK,
                          TrustRole.SUPPORT):
            heal_target = self._pick_heal_target(spec, party)
            if heal_target is not None:
                return AIDecision(
                    action="heal", target_id=heal_target.member_id,
                    spell_or_ability=self._pick_heal_spell(spec, "party"),
                    priority=AIPriority.PARTY_HEAL,
                    reason=(f"{heal_target.member_id} HP "
                             f"{heal_target.current_hp}/{heal_target.max_hp}"),
                )

        # 3) Intervention MB (proactive shield)
        if "intervention_mb" in spec.abilities:
            target = self._pick_incoming_damage_target(party)
            if target is not None:
                return AIDecision(
                    action="cast",
                    target_id=target.member_id,
                    spell_or_ability="intervention_mb",
                    priority=AIPriority.INTERVENTION_MB,
                    reason="incoming damage predicted on ally",
                )

        # 4) Skillchain opener (sc_priority trusts during SC window)
        if skillchain_window_open and spec.sc_priority:
            ws = self._pick_weapon_skill(spec)
            if ws is not None:
                return AIDecision(
                    action="weapon_skill",
                    target_id=enemy_target_id,
                    spell_or_ability=ws,
                    priority=AIPriority.SKILLCHAIN_OPENER,
                    reason="opening skillchain",
                )

        # 5) Magic burst (nukers during SC window)
        if skillchain_window_open and spec.role == TrustRole.NUKER:
            nuke = self._pick_nuke(spec)
            if nuke is not None:
                return AIDecision(
                    action="cast",
                    target_id=enemy_target_id,
                    spell_or_ability=nuke,
                    priority=AIPriority.MAGIC_BURST,
                    reason="MB during open SC window",
                )

        # 6) Debuff (debuffers + nukers w/ stun)
        if spec.role == TrustRole.DEBUFFER or "stun" in spec.abilities:
            return AIDecision(
                action="cast",
                target_id=enemy_target_id,
                spell_or_ability=self._pick_debuff(spec),
                priority=AIPriority.DEBUFF,
                reason="tactical debuff",
            )

        # 7) Buff (support / bard / corsair maintenance)
        if spec.role == TrustRole.SUPPORT:
            return AIDecision(
                action="cast",
                target_id=enemy_target_id,
                spell_or_ability=self._pick_buff(spec),
                priority=AIPriority.BUFF,
                reason="maintaining support buff",
            )

        # 8) Default action
        return self._default_action(trust, enemy_target_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _can_self_heal(self, spec: TrustSpec) -> bool:
        """Trust has a usable self-heal spell/ability."""
        for a in spec.abilities:
            if "cure" in a or a == "boost":
                return True
        return False

    def _pick_heal_target(self,
                           spec: TrustSpec,
                           party: list[PartyMemberState],
                           ) -> t.Optional[PartyMemberState]:
        """Pick the lowest-HP party member below their role threshold."""
        threshold = self._heal_threshold_for(spec)
        candidates = []
        for m in party:
            if not m.is_alive:
                continue
            hp_pct = m.current_hp / max(1, m.max_hp)
            if hp_pct <= threshold:
                candidates.append(m)
        if not candidates:
            return None
        return min(candidates, key=lambda m: m.current_hp / max(1, m.max_hp))

    def _heal_threshold_for(self, spec: TrustSpec) -> float:
        """Per-trust override beats role default."""
        if spec.heal_threshold_override is not None:
            return spec.heal_threshold_override
        # Healers cast at the average between their own threshold
        # and the AVG of the targets they care about (~tank threshold).
        if spec.role == TrustRole.HEALER:
            return DEFAULT_HEAL_THRESHOLDS[TrustRole.MELEE_DPS]
        return self.heal_thresholds.get(spec.role,
                                          DEFAULT_HEAL_THRESHOLDS[spec.role])

    def _pick_heal_spell(self, spec: TrustSpec, scope: str) -> str:
        """Pick the best heal spell available."""
        for a in ("cure_iv", "cure_iii", "cure_ii", "regen_iii", "regen_ii"):
            if a in spec.abilities:
                return a
        return "cure"

    def _pick_incoming_damage_target(self,
                                       party: list[PartyMemberState],
                                       ) -> t.Optional[PartyMemberState]:
        for m in party:
            if m.incoming_damage_predicted > 0 and m.is_alive:
                return m
        return None

    def _pick_weapon_skill(self, spec: TrustSpec) -> t.Optional[str]:
        """First weapon-skill-like ability in the catalog."""
        ws_keywords = ("rampage", "savage_blade", "tachi_", "guillotine",
                         "asuran_fists", "raging_rush", "torcleaver",
                         "blade_jin")
        for a in spec.abilities:
            if any(a.startswith(k) for k in ws_keywords):
                return a
        return None

    def _pick_nuke(self, spec: TrustSpec) -> t.Optional[str]:
        for a in ("comet", "burst_ii", "thundaga_iii",
                    "blizzaga_iii", "firaga_iii"):
            if a in spec.abilities:
                return a
        return None

    def _pick_debuff(self, spec: TrustSpec) -> str:
        for a in ("stun", "slow", "paralyze", "bio"):
            if a in spec.abilities:
                return a
        return "slow"   # safe default

    def _pick_buff(self, spec: TrustSpec) -> str:
        for a in ("haste", "march_iii", "ballad_ii", "minuet_iv",
                    "hunters_roll", "wizards_roll"):
            if a in spec.abilities:
                return a
        return "regen_ii"

    def _default_action(self,
                          trust: TrustSnapshot,
                          enemy_target_id: t.Optional[str]) -> AIDecision:
        spec = trust.spec
        if spec.role in (TrustRole.MELEE_DPS, TrustRole.TANK):
            return AIDecision(
                action="melee", target_id=enemy_target_id,
                priority=AIPriority.DEFAULT,
                reason="default melee swing",
            )
        if spec.role == TrustRole.RANGED_DPS:
            return AIDecision(
                action="shoot", target_id=enemy_target_id,
                priority=AIPriority.DEFAULT,
                reason="default ranged shot",
            )
        if spec.role == TrustRole.NUKER:
            nuke = self._pick_nuke(spec) or "fire"
            return AIDecision(
                action="cast", target_id=enemy_target_id,
                spell_or_ability=nuke,
                priority=AIPriority.DEFAULT,
                reason="default nuke",
            )
        # Healer / support / debuffer with no urgent task
        return AIDecision(
            action="wait", target_id=None,
            priority=AIPriority.WAIT,
            reason="nothing urgent to do",
        )
