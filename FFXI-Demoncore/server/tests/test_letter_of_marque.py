"""Tests for letter of marque."""
from __future__ import annotations

from server.letter_of_marque import (
    LetterOfMarque,
    LicenseScope,
    Nation,
    TargetKind,
)


def test_issue_happy():
    L = LetterOfMarque()
    r = L.issue(
        player_id="p", nation=Nation.BASTOK,
        scope=LicenseScope.TARGETS_PIRATE_ONLY,
        issued_at_seconds=0,
        duration_seconds=86_400,
    )
    assert r.accepted is True
    assert r.expires_at == 86_400


def test_issue_blank_player():
    L = LetterOfMarque()
    r = L.issue(
        player_id="", nation=Nation.BASTOK,
        scope=LicenseScope.TARGETS_PIRATE_ONLY,
        issued_at_seconds=0, duration_seconds=86_400,
    )
    assert r.accepted is False


def test_issue_zero_duration_rejected():
    L = LetterOfMarque()
    r = L.issue(
        player_id="p", nation=Nation.BASTOK,
        scope=LicenseScope.TARGETS_PIRATE_ONLY,
        issued_at_seconds=0, duration_seconds=0,
    )
    assert r.accepted is False


def test_double_issue_blocked():
    L = LetterOfMarque()
    L.issue(
        player_id="p", nation=Nation.BASTOK,
        scope=LicenseScope.TARGETS_PIRATE_ONLY,
        issued_at_seconds=0, duration_seconds=86_400,
    )
    r = L.issue(
        player_id="p", nation=Nation.SAN_DORIA,
        scope=LicenseScope.TARGETS_ENEMY_NAVY,
        issued_at_seconds=10, duration_seconds=86_400,
    )
    assert r.accepted is False


def test_reissue_after_expiry_ok():
    L = LetterOfMarque()
    L.issue(
        player_id="p", nation=Nation.BASTOK,
        scope=LicenseScope.TARGETS_PIRATE_ONLY,
        issued_at_seconds=0, duration_seconds=10,
    )
    # past expiry - reissue
    r = L.issue(
        player_id="p", nation=Nation.SAN_DORIA,
        scope=LicenseScope.TARGETS_ENEMY_NAVY,
        issued_at_seconds=100, duration_seconds=86_400,
    )
    assert r.accepted is True


def test_holder_status_active():
    L = LetterOfMarque()
    L.issue(
        player_id="p", nation=Nation.BASTOK,
        scope=LicenseScope.TARGETS_PIRATE_ONLY,
        issued_at_seconds=0, duration_seconds=86_400,
    )
    s = L.holder_status(player_id="p", now_seconds=10)
    assert s is not None
    assert s.nation == Nation.BASTOK


def test_holder_status_expired_returns_none():
    L = LetterOfMarque()
    L.issue(
        player_id="p", nation=Nation.BASTOK,
        scope=LicenseScope.TARGETS_PIRATE_ONLY,
        issued_at_seconds=0, duration_seconds=10,
    )
    s = L.holder_status(player_id="p", now_seconds=100)
    assert s is None


def test_revoke():
    L = LetterOfMarque()
    L.issue(
        player_id="p", nation=Nation.BASTOK,
        scope=LicenseScope.TARGETS_PIRATE_ONLY,
        issued_at_seconds=0, duration_seconds=86_400,
    )
    ok = L.revoke(player_id="p", reason="treaty broken")
    assert ok is True
    assert L.holder_status(player_id="p", now_seconds=10) is None


def test_revoke_unknown():
    L = LetterOfMarque()
    assert L.revoke(player_id="p", reason="x") is False


def test_pirate_only_lawful_against_pirate():
    L = LetterOfMarque()
    L.issue(
        player_id="p", nation=Nation.BASTOK,
        scope=LicenseScope.TARGETS_PIRATE_ONLY,
        issued_at_seconds=0, duration_seconds=86_400,
    )
    assert L.is_target_lawful(
        player_id="p",
        target_kind=TargetKind.PIRATE_FLEET,
        attacker_nation_at_war=False,
        now_seconds=10,
    ) is True


def test_pirate_only_unlawful_against_enemy_nation():
    L = LetterOfMarque()
    L.issue(
        player_id="p", nation=Nation.BASTOK,
        scope=LicenseScope.TARGETS_PIRATE_ONLY,
        issued_at_seconds=0, duration_seconds=86_400,
    )
    assert L.is_target_lawful(
        player_id="p",
        target_kind=TargetKind.ENEMY_NATION_SHIP,
        attacker_nation_at_war=True,
        now_seconds=10,
    ) is False


def test_enemy_navy_only_lawful_when_at_war():
    L = LetterOfMarque()
    L.issue(
        player_id="p", nation=Nation.BASTOK,
        scope=LicenseScope.TARGETS_ENEMY_NAVY,
        issued_at_seconds=0, duration_seconds=86_400,
    )
    # at war -> lawful
    assert L.is_target_lawful(
        player_id="p",
        target_kind=TargetKind.ENEMY_NATION_SHIP,
        attacker_nation_at_war=True,
        now_seconds=10,
    ) is True
    # peacetime -> unlawful
    assert L.is_target_lawful(
        player_id="p",
        target_kind=TargetKind.ENEMY_NATION_SHIP,
        attacker_nation_at_war=False,
        now_seconds=10,
    ) is False


def test_any_vessel_lawful_except_own_nation():
    L = LetterOfMarque()
    L.issue(
        player_id="p", nation=Nation.BASTOK,
        scope=LicenseScope.ANY_VESSEL_AT_SEA,
        issued_at_seconds=0, duration_seconds=86_400,
    )
    assert L.is_target_lawful(
        player_id="p",
        target_kind=TargetKind.NEUTRAL_NATION_SHIP,
        attacker_nation_at_war=False, now_seconds=10,
    ) is True
    # never lawful: own-nation
    assert L.is_target_lawful(
        player_id="p",
        target_kind=TargetKind.OWN_NATION_SHIP,
        attacker_nation_at_war=True, now_seconds=10,
    ) is False


def test_no_letter_no_lawful_targets():
    L = LetterOfMarque()
    assert L.is_target_lawful(
        player_id="p",
        target_kind=TargetKind.PIRATE_FLEET,
        attacker_nation_at_war=False,
        now_seconds=10,
    ) is False
