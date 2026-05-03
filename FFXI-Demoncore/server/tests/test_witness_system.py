"""Tests for the witness system."""
from __future__ import annotations

from server.witness_system import (
    Crime,
    CrimeKind,
    IdentificationLevel,
    SensoryChannel,
    WitnessCandidate,
    WitnessStatus,
    WitnessSystem,
)


def _murder(at: tuple[int, int], perp: str = "alice") -> Crime:
    return Crime(
        crime_id="c1", kind=CrimeKind.MURDER, perp_id=perp,
        victim_id="merchant_1", position_tile=at,
        occurred_at_seconds=0.0,
    )


def test_register_and_total_witness():
    sys = WitnessSystem()
    sys.register_witness(WitnessCandidate(
        entity_id="bystander_1", position_tile=(0, 0),
    ))
    assert sys.total_witnesses() == 1


def test_deregister_witness():
    sys = WitnessSystem()
    sys.register_witness(WitnessCandidate(
        entity_id="b1", position_tile=(0, 0),
    ))
    assert sys.deregister_witness(entity_id="b1")
    assert not sys.deregister_witness(entity_id="b1")


def test_no_witnesses_means_no_reports():
    sys = WitnessSystem()
    reports = sys.observe_crime(crime=_murder((10, 10)))
    assert reports == ()


def test_witness_in_sight_full_id():
    sys = WitnessSystem()
    sys.register_witness(WitnessCandidate(
        entity_id="b1", position_tile=(2, 2),
    ))
    reports = sys.observe_crime(crime=_murder((0, 0)))
    assert len(reports) == 1
    r = reports[0]
    assert r.identification_level == IdentificationLevel.FULL
    assert r.status == WitnessStatus.SAW_AND_REPORTED
    assert r.primary_channel == SensoryChannel.SIGHT


def test_distant_witness_did_not_see():
    sys = WitnessSystem()
    sys.register_witness(WitnessCandidate(
        entity_id="far_away", position_tile=(200, 200),
    ))
    reports = sys.observe_crime(crime=_murder((0, 0)))
    r = reports[0]
    assert r.status == WitnessStatus.DID_NOT_SEE
    assert r.identification_level == IdentificationLevel.NONE


def test_obstructed_sight_drops_to_partial():
    """Wall blocks sight but earshot still picks up murder
    (which has high hearing visibility too)."""
    sys = WitnessSystem()
    sys.register_witness(WitnessCandidate(
        entity_id="b1", position_tile=(2, 2),
        obstructed=True,
    ))
    reports = sys.observe_crime(crime=_murder((0, 0)))
    r = reports[0]
    # Obstructed sight = sight conf * 0.3, but hearing still works
    # The strongest channel should be hearing
    assert r.primary_channel == SensoryChannel.HEARING
    assert r.identification_level in (
        IdentificationLevel.FULL, IdentificationLevel.PARTIAL,
    )


def test_perp_disguised_caps_at_partial():
    sys = WitnessSystem()
    sys.register_witness(WitnessCandidate(
        entity_id="b1", position_tile=(2, 2),
    ))
    crime = Crime(
        crime_id="c2", kind=CrimeKind.MURDER, perp_id="alice",
        victim_id="merchant_1", position_tile=(0, 0),
        occurred_at_seconds=0.0, perp_disguised=True,
    )
    reports = sys.observe_crime(crime=crime)
    r = reports[0]
    assert r.identification_level == IdentificationLevel.PARTIAL


def test_pickpocket_quiet_only_close_witnesses():
    """Pickpocket has low SIGHT visibility (0.4) and zero
    hearing/magic. Only nearby observers detect it."""
    sys = WitnessSystem()
    sys.register_witness(WitnessCandidate(
        entity_id="close", position_tile=(2, 2),
    ))
    sys.register_witness(WitnessCandidate(
        entity_id="far", position_tile=(15, 15),
    ))
    crime = Crime(
        crime_id="c3", kind=CrimeKind.PICKPOCKET, perp_id="alice",
        victim_id="merchant_1", position_tile=(0, 0),
        occurred_at_seconds=0.0,
    )
    reports_by_id = {
        r.witness_id: r for r in sys.observe_crime(crime=crime)
    }
    assert reports_by_id["close"].status == (
        WitnessStatus.SAW_AND_REPORTED
    )
    assert reports_by_id["far"].status == (
        WitnessStatus.DID_NOT_SEE
    )


def test_hostile_magic_detected_via_magic_sense():
    """A magic-sensitive witness picks up the cast even from
    long distance."""
    sys = WitnessSystem()
    sys.register_witness(WitnessCandidate(
        entity_id="mage_witness", position_tile=(40, 40),
        magic_sense_range=60,
    ))
    crime = Crime(
        crime_id="c4", kind=CrimeKind.HOSTILE_MAGIC,
        perp_id="alice", victim_id=None,
        position_tile=(0, 0), occurred_at_seconds=0.0,
    )
    reports = sys.observe_crime(crime=crime)
    r = reports[0]
    assert r.primary_channel == SensoryChannel.MAGIC


def test_schemer_silent_on_petty_theft():
    sys = WitnessSystem()
    sys.register_witness(WitnessCandidate(
        entity_id="schemer", position_tile=(2, 2),
        is_schemer=True,
    ))
    crime = Crime(
        crime_id="c5", kind=CrimeKind.THEFT, perp_id="alice",
        victim_id="merchant_1", position_tile=(0, 0),
        occurred_at_seconds=0.0,
    )
    r = sys.observe_crime(crime=crime)[0]
    assert r.status == WitnessStatus.SAW_BUT_SILENT


def test_coward_silent_on_murder():
    sys = WitnessSystem()
    sys.register_witness(WitnessCandidate(
        entity_id="coward", position_tile=(2, 2),
        is_coward=True,
    ))
    r = sys.observe_crime(crime=_murder((0, 0)))[0]
    assert r.status == WitnessStatus.SAW_BUT_SILENT


def test_zealot_reports_even_low_stakes():
    """Zealot personality doesn't suppress reporting."""
    sys = WitnessSystem()
    sys.register_witness(WitnessCandidate(
        entity_id="zealot", position_tile=(2, 2),
        is_zealot=True,
    ))
    crime = Crime(
        crime_id="c6", kind=CrimeKind.THEFT, perp_id="alice",
        victim_id="merchant_1", position_tile=(0, 0),
        occurred_at_seconds=0.0,
    )
    r = sys.observe_crime(crime=crime)[0]
    assert r.status == WitnessStatus.SAW_AND_REPORTED


def test_reports_indexed_by_crime():
    sys = WitnessSystem()
    sys.register_witness(WitnessCandidate(
        entity_id="b1", position_tile=(2, 2),
    ))
    sys.observe_crime(crime=_murder((0, 0)))
    reports = sys.reports_for("c1")
    assert len(reports) == 1


def test_identifications_of_perp_aggregate():
    sys = WitnessSystem()
    sys.register_witness(WitnessCandidate(
        entity_id="b1", position_tile=(2, 2),
    ))
    sys.register_witness(WitnessCandidate(
        entity_id="b2", position_tile=(3, 3),
    ))
    sys.observe_crime(crime=_murder((0, 0)))
    sys.observe_crime(crime=Crime(
        crime_id="c2", kind=CrimeKind.THEFT, perp_id="alice",
        victim_id="merchant_2", position_tile=(0, 0),
        occurred_at_seconds=10.0,
    ))
    ids = sys.identifications_of(perp_id="alice")
    assert len(ids) >= 2


def test_credible_witnesses_only_full_id_reported():
    sys = WitnessSystem()
    # Close witness - full ID, reports
    sys.register_witness(WitnessCandidate(
        entity_id="close_zealot", position_tile=(2, 2),
        is_zealot=True,
    ))
    # Coward - sees but stays silent
    sys.register_witness(WitnessCandidate(
        entity_id="coward", position_tile=(3, 3),
        is_coward=True,
    ))
    # Distant - doesn't see
    sys.register_witness(WitnessCandidate(
        entity_id="far", position_tile=(200, 200),
    ))
    sys.observe_crime(crime=_murder((0, 0)))
    credible = sys.credible_witnesses(crime_id="c1")
    ids = {r.witness_id for r in credible}
    assert "close_zealot" in ids
    assert "coward" not in ids
    assert "far" not in ids


def test_full_lifecycle_plaza_murder():
    """Plaza scene: 5 NPCs at varying distances + traits.
    Verify the right ones identify the killer."""
    sys = WitnessSystem()
    sys.register_witness(WitnessCandidate(
        entity_id="vendor_a", position_tile=(3, 3),
    ))
    sys.register_witness(WitnessCandidate(
        entity_id="guard_b", position_tile=(5, 5),
    ))
    sys.register_witness(WitnessCandidate(
        entity_id="schemer_c", position_tile=(2, 2),
        is_schemer=True,
    ))
    sys.register_witness(WitnessCandidate(
        entity_id="far_d", position_tile=(150, 150),
    ))
    sys.register_witness(WitnessCandidate(
        entity_id="behind_wall_e", position_tile=(4, 4),
        obstructed=True,
    ))
    sys.observe_crime(crime=_murder((0, 0), perp="alice"))
    credible = sys.credible_witnesses(crime_id="c1")
    cred_ids = {r.witness_id for r in credible}
    assert "vendor_a" in cred_ids
    assert "guard_b" in cred_ids
    assert "far_d" not in cred_ids
    # Schemer for petty crime -> silent. Murder is heavy: schemer
    # still reports (only suppresses on petty theft).
    assert "schemer_c" in cred_ids
