"""Tests for boss negotiation."""
from __future__ import annotations

from server.boss_negotiation import (
    BossDisposition,
    BossNegotiationPolicy,
    NegotiationContext,
    NegotiationOutcome,
    NegotiationRegistry,
    Offer,
    OfferKind,
    seed_default_policies,
)


def _ctx(**overrides) -> NegotiationContext:
    base = dict(party_id="alpha", party_size=3, honor=100,
                reputation=50, outlaw_flag=False, bosses_killed=5,
                party_avg_level=75)
    base.update(overrides)
    return NegotiationContext(**base)


def _registry_with_defaults() -> NegotiationRegistry:
    return seed_default_policies(NegotiationRegistry())


def test_unknown_boss_attacks():
    reg = NegotiationRegistry()
    res = reg.evaluate_offer(
        boss_id="ghost",
        offer=Offer(kind=OfferKind.OATH),
        context=_ctx(),
    )
    assert res.outcome == NegotiationOutcome.ATTACK


def test_outlaw_blocked_attacks():
    reg = _registry_with_defaults()
    res = reg.evaluate_offer(
        boss_id="maat",
        offer=Offer(kind=OfferKind.OATH),
        context=_ctx(outlaw_flag=True),
    )
    assert res.outcome == NegotiationOutcome.ATTACK


def test_maat_accepts_oath_with_honor():
    reg = _registry_with_defaults()
    res = reg.evaluate_offer(
        boss_id="maat",
        offer=Offer(kind=OfferKind.OATH, payload_id="oath_humility"),
        context=_ctx(honor=100),
    )
    assert res.outcome == NegotiationOutcome.ACCEPT


def test_maat_low_honor_returns_conditional():
    reg = _registry_with_defaults()
    res = reg.evaluate_offer(
        boss_id="maat",
        offer=Offer(kind=OfferKind.OATH),
        context=_ctx(honor=10),
    )
    assert res.outcome == NegotiationOutcome.CONDITIONAL
    assert "honor" in res.counter_condition.lower()


def test_maat_threat_attacks():
    """Threatening Maat is a fast way to die."""
    reg = _registry_with_defaults()
    res = reg.evaluate_offer(
        boss_id="maat",
        offer=Offer(kind=OfferKind.THREAT),
        context=_ctx(),
    )
    assert res.outcome == NegotiationOutcome.ATTACK


def test_maat_refuses_gil_tribute():
    reg = _registry_with_defaults()
    res = reg.evaluate_offer(
        boss_id="maat",
        offer=Offer(kind=OfferKind.TRIBUTE_GIL, value=999_999),
        context=_ctx(),
    )
    assert res.outcome == NegotiationOutcome.REFUSE


def test_goblin_chief_accepts_big_tribute():
    reg = _registry_with_defaults()
    res = reg.evaluate_offer(
        boss_id="goblin_brigand_chief",
        offer=Offer(kind=OfferKind.TRIBUTE_GIL, value=100_000),
        context=_ctx(),
    )
    assert res.outcome == NegotiationOutcome.ACCEPT


def test_goblin_chief_rejects_lowball():
    reg = _registry_with_defaults()
    res = reg.evaluate_offer(
        boss_id="goblin_brigand_chief",
        offer=Offer(kind=OfferKind.TRIBUTE_GIL, value=1000),
        context=_ctx(),
    )
    assert res.outcome == NegotiationOutcome.REFUSE
    assert "minimum" in res.rationale


def test_goblin_chief_rejects_oath():
    reg = _registry_with_defaults()
    res = reg.evaluate_offer(
        boss_id="goblin_brigand_chief",
        offer=Offer(kind=OfferKind.OATH),
        context=_ctx(),
    )
    assert res.outcome == NegotiationOutcome.REFUSE


def test_bloodthirsty_warlord_attacks_truce():
    reg = _registry_with_defaults()
    res = reg.evaluate_offer(
        boss_id="fomor_warlord_khaavex",
        offer=Offer(kind=OfferKind.TRUCE_REQUEST),
        context=_ctx(),
    )
    assert res.outcome == NegotiationOutcome.ATTACK


def test_bloodthirsty_refuses_oath():
    reg = _registry_with_defaults()
    res = reg.evaluate_offer(
        boss_id="fomor_warlord_khaavex",
        offer=Offer(kind=OfferKind.OATH),
        context=_ctx(),
    )
    assert res.outcome == NegotiationOutcome.REFUSE


def test_pious_boss_accepts_patron():
    reg = _registry_with_defaults()
    res = reg.evaluate_offer(
        boss_id="bishop_zhayolm",
        offer=Offer(kind=OfferKind.PATRON_INVOCATION,
                     payload_id="altana"),
        context=_ctx(honor=50),
    )
    assert res.outcome == NegotiationOutcome.ACCEPT


def test_lonely_dragon_accepts_truce():
    reg = _registry_with_defaults()
    res = reg.evaluate_offer(
        boss_id="ancient_dragon_solitary",
        offer=Offer(kind=OfferKind.TRUCE_REQUEST),
        context=_ctx(),
    )
    assert res.outcome == NegotiationOutcome.ACCEPT


def test_unhandled_offer_refused():
    """Offer kind not in any of the boss's lists -> REFUSE."""
    reg = NegotiationRegistry()
    reg.register_boss(BossNegotiationPolicy(
        boss_id="silent_one",
        disposition=BossDisposition.TIRED,
        accept_kinds=frozenset({OfferKind.TRUCE_REQUEST}),
    ))
    res = reg.evaluate_offer(
        boss_id="silent_one",
        offer=Offer(kind=OfferKind.OATH),
        context=_ctx(),
    )
    assert res.outcome == NegotiationOutcome.REFUSE


def test_register_boss_returns_policy():
    reg = NegotiationRegistry()
    p = BossNegotiationPolicy(
        boss_id="test_boss",
        disposition=BossDisposition.PROUD,
    )
    out = reg.register_boss(p)
    assert out is p
    assert reg.policy_for("test_boss") is p


def test_full_lifecycle_party_climbs_to_acceptance():
    """Party first offers low-honor oath -> CONDITIONAL. Goes
    away, raises honor, returns -> ACCEPT."""
    reg = _registry_with_defaults()
    weak = reg.evaluate_offer(
        boss_id="maat",
        offer=Offer(kind=OfferKind.OATH),
        context=_ctx(honor=5),
    )
    assert weak.outcome == NegotiationOutcome.CONDITIONAL
    # Returns later with high honor
    strong = reg.evaluate_offer(
        boss_id="maat",
        offer=Offer(kind=OfferKind.OATH, payload_id="oath_humility"),
        context=_ctx(honor=200),
    )
    assert strong.outcome == NegotiationOutcome.ACCEPT
