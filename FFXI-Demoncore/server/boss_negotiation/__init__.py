"""Boss negotiation — AI bosses can be talked to.

Bosses in Demoncore aren't HP sponges with scripted dialogue
trees. They're real AI agents holding territory. A clever
adventuring party can sometimes AVOID the fight by negotiating —
offer tribute, invoke an ally faction, swear an oath, or
threaten with a credible third-party patron. The boss's AI
weighs the offer against its goals (faction loyalty, the player's
reputation, the player's known kill record, the offered value)
and decides:

    ACCEPT          — boss yields, lets the party pass / hands
                      over the key item peacefully (smaller reward
                      pile but no fight, no risk).
    CONDITIONAL     — boss demands a counter-condition (kill a
                      rival, ferry a message, return in 7 days).
    REFUSE          — boss declines but does NOT attack (yet).
                      Player can re-offer.
    ATTACK          — boss is offended; combat begins immediately.

This module is the input/output surface. The actual AI weighing
happens in agent_orchestrator with the boss's persona profile;
this module exposes:

* What inputs the boss AI sees (Offer payload + reputation /
  honor / faction snapshot of the player party)
* What outcomes the system supports (NegotiationOutcome)
* A registry of boss-specific NEGOTIATION POLICIES — flat data
  the AI prompt is grounded with so it stays IN CHARACTER
  (e.g. Maat will always ACCEPT a worthy challenge but will
  ATTACK if you ask him to skip the fight).

Public surface
--------------
    OfferKind enum (TRIBUTE_GIL / TRIBUTE_ITEM / OATH /
                    PATRON_INVOCATION / THREAT / TRUCE_REQUEST)
    Offer dataclass
    NegotiationOutcome enum
    BossDisposition enum (BLOODTHIRSTY / PROUD / GREEDY /
                          PIOUS / LONELY / TIRED)
    BossNegotiationPolicy dataclass — what flips a given boss
    NegotiationContext dataclass — player party snapshot
    NegotiationRegistry
        .register_boss(policy)
        .evaluate_offer(...)  -> NegotiationDecision
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class OfferKind(str, enum.Enum):
    TRIBUTE_GIL = "tribute_gil"
    TRIBUTE_ITEM = "tribute_item"
    OATH = "oath"                   # swear allegiance
    PATRON_INVOCATION = "patron_invocation"  # "in name of X"
    THREAT = "threat"               # show of force, ultimatum
    TRUCE_REQUEST = "truce_request"  # ask for pause


class NegotiationOutcome(str, enum.Enum):
    ACCEPT = "accept"
    CONDITIONAL = "conditional"
    REFUSE = "refuse"
    ATTACK = "attack"


class BossDisposition(str, enum.Enum):
    """Personality flag for the boss. The AI prompt frames the
    boss with this tag; the policy below names the offer kinds
    that move them."""
    BLOODTHIRSTY = "bloodthirsty"   # rarely accepts; THREAT often -> ATTACK
    PROUD = "proud"                 # accepts OATH or worthy combat
    GREEDY = "greedy"               # accepts TRIBUTE_GIL / TRIBUTE_ITEM
    PIOUS = "pious"                 # PATRON_INVOCATION matters
    LONELY = "lonely"               # accepts TRUCE_REQUEST easily
    TIRED = "tired"                 # accepts TRUCE_REQUEST, refuses combat


@dataclasses.dataclass(frozen=True)
class Offer:
    kind: OfferKind
    payload_id: str = ""        # e.g. item id, oath text id, patron id
    value: int = 0              # gil offered, etc.
    description: str = ""


@dataclasses.dataclass(frozen=True)
class NegotiationContext:
    """Snapshot of the player party at the moment of the offer.
    Sourced from honor_reputation, outlaw_system, achievements."""
    party_id: str
    party_size: int = 1
    honor: int = 0              # +
    reputation: int = 0
    outlaw_flag: bool = False
    bosses_killed: int = 0
    party_avg_level: int = 1


@dataclasses.dataclass(frozen=True)
class BossNegotiationPolicy:
    """Per-boss flat data that anchors the AI's decision.

    accept_kinds   — offer kinds the boss is OPEN TO (ACCEPT-eligible).
    refuse_kinds   — offers the boss flatly REFUSES.
    attack_kinds   — offers that ANGER the boss (ATTACK).
    min_tribute    — for greedy bosses, the gil floor below which
                     a tribute offer is treated as an INSULT.
    min_honor      — the player party must have at least this
                     much honor for ACCEPT to be possible.
    outlaw_blocked — if True, outlaw parties can never negotiate.
    """
    boss_id: str
    disposition: BossDisposition
    accept_kinds: frozenset[OfferKind] = frozenset()
    refuse_kinds: frozenset[OfferKind] = frozenset()
    attack_kinds: frozenset[OfferKind] = frozenset()
    min_tribute: int = 0
    min_honor: int = 0
    outlaw_blocked: bool = True


@dataclasses.dataclass(frozen=True)
class NegotiationDecision:
    outcome: NegotiationOutcome
    rationale: str
    counter_condition: str = ""    # only meaningful for CONDITIONAL


@dataclasses.dataclass
class NegotiationRegistry:
    _policies: dict[str, BossNegotiationPolicy] = dataclasses.field(
        default_factory=dict,
    )

    def register_boss(
        self, policy: BossNegotiationPolicy,
    ) -> BossNegotiationPolicy:
        self._policies[policy.boss_id] = policy
        return policy

    def policy_for(
        self, boss_id: str,
    ) -> t.Optional[BossNegotiationPolicy]:
        return self._policies.get(boss_id)

    def evaluate_offer(
        self, *, boss_id: str, offer: Offer,
        context: NegotiationContext,
    ) -> NegotiationDecision:
        """Apply the boss's policy to the offer + context. This
        is the BASELINE judgment — the actual AI may further
        season it with persona flavor in the orchestrator, but
        the registry's outcome is the floor."""
        policy = self._policies.get(boss_id)
        if policy is None:
            return NegotiationDecision(
                outcome=NegotiationOutcome.ATTACK,
                rationale="no negotiation policy registered",
            )

        # 1) Outlaws can't talk to law-and-order bosses.
        if context.outlaw_flag and policy.outlaw_blocked:
            return NegotiationDecision(
                outcome=NegotiationOutcome.ATTACK,
                rationale="outlaw flag — boss attacks on sight",
            )

        # 2) Offers that anger the boss override everything.
        if offer.kind in policy.attack_kinds:
            return NegotiationDecision(
                outcome=NegotiationOutcome.ATTACK,
                rationale=f"{offer.kind.value} offends this boss",
            )

        # 3) Flat refusals.
        if offer.kind in policy.refuse_kinds:
            return NegotiationDecision(
                outcome=NegotiationOutcome.REFUSE,
                rationale=f"{offer.kind.value} not welcome",
            )

        # 4) If the offer kind is acceptable in principle, check
        #    the gates.
        if offer.kind in policy.accept_kinds:
            # Honor floor
            if context.honor < policy.min_honor:
                return NegotiationDecision(
                    outcome=NegotiationOutcome.CONDITIONAL,
                    rationale="party honor too low to accept directly",
                    counter_condition=(
                        "earn honor and return"
                    ),
                )
            # Tribute floor
            if (
                offer.kind in (
                    OfferKind.TRIBUTE_GIL, OfferKind.TRIBUTE_ITEM,
                )
                and offer.value < policy.min_tribute
            ):
                return NegotiationDecision(
                    outcome=NegotiationOutcome.REFUSE,
                    rationale="tribute below minimum",
                )
            return NegotiationDecision(
                outcome=NegotiationOutcome.ACCEPT,
                rationale=f"{offer.kind.value} accepted",
            )

        # 5) Unknown / unhandled offer kind for this boss
        return NegotiationDecision(
            outcome=NegotiationOutcome.REFUSE,
            rationale="boss does not engage with this offer kind",
        )


# --------------------------------------------------------------------
# Sample policies — exemplars showing how each disposition reads
# --------------------------------------------------------------------
def _build_default_policies() -> tuple[BossNegotiationPolicy, ...]:
    return (
        # Maat: Proud master, only respects worthy challenges
        BossNegotiationPolicy(
            boss_id="maat",
            disposition=BossDisposition.PROUD,
            accept_kinds=frozenset({OfferKind.OATH}),
            refuse_kinds=frozenset({
                OfferKind.TRIBUTE_GIL, OfferKind.TRIBUTE_ITEM,
                OfferKind.TRUCE_REQUEST,
            }),
            attack_kinds=frozenset({OfferKind.THREAT}),
            min_honor=50,
        ),
        # Greedy goblin chief: gil-driven
        BossNegotiationPolicy(
            boss_id="goblin_brigand_chief",
            disposition=BossDisposition.GREEDY,
            accept_kinds=frozenset({
                OfferKind.TRIBUTE_GIL, OfferKind.TRIBUTE_ITEM,
            }),
            refuse_kinds=frozenset({OfferKind.OATH}),
            attack_kinds=frozenset({OfferKind.THREAT}),
            min_tribute=50_000,
        ),
        # Bloodthirsty fomor warlord: almost nothing works
        BossNegotiationPolicy(
            boss_id="fomor_warlord_khaavex",
            disposition=BossDisposition.BLOODTHIRSTY,
            accept_kinds=frozenset(),
            refuse_kinds=frozenset({
                OfferKind.OATH, OfferKind.TRIBUTE_GIL,
                OfferKind.TRIBUTE_ITEM, OfferKind.PATRON_INVOCATION,
            }),
            attack_kinds=frozenset({
                OfferKind.THREAT, OfferKind.TRUCE_REQUEST,
            }),
        ),
        # Pious cleric-boss: invoke a deity to sway him
        BossNegotiationPolicy(
            boss_id="bishop_zhayolm",
            disposition=BossDisposition.PIOUS,
            accept_kinds=frozenset({
                OfferKind.PATRON_INVOCATION, OfferKind.OATH,
            }),
            refuse_kinds=frozenset({
                OfferKind.TRIBUTE_GIL, OfferKind.THREAT,
            }),
            min_honor=20,
        ),
        # Lonely capstone: weary world boss happy to chat
        BossNegotiationPolicy(
            boss_id="ancient_dragon_solitary",
            disposition=BossDisposition.LONELY,
            accept_kinds=frozenset({
                OfferKind.TRUCE_REQUEST, OfferKind.OATH,
                OfferKind.PATRON_INVOCATION,
            }),
            refuse_kinds=frozenset({OfferKind.TRIBUTE_GIL}),
            attack_kinds=frozenset({OfferKind.THREAT}),
        ),
    )


def seed_default_policies(
    registry: NegotiationRegistry,
) -> NegotiationRegistry:
    for p in _build_default_policies():
        registry.register_boss(p)
    return registry


__all__ = [
    "OfferKind", "Offer", "NegotiationOutcome",
    "BossDisposition",
    "BossNegotiationPolicy", "NegotiationContext",
    "NegotiationDecision", "NegotiationRegistry",
    "seed_default_policies",
]
