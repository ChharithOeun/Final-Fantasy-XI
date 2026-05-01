"""Tests for server.auth_discord — Discord OAuth + chharbot moderation."""
from __future__ import annotations

import json

import pytest

from server.auth_discord import (
    DISCORD_ACCESS_TOKEN_LIFETIME_S,
    DISCORD_REFRESH_TOKEN_LIFETIME_S,
    LSB_ACCOUNT_TOKEN_LIFETIME_S,
    SESSION_TOKEN_LIFETIME_S,
    VERIFICATION_TIMEOUT_SECONDS,
    VERIFIED_ROLE,
    AccountRegistry,
    AuditLog,
    GateState,
    ModAction,
    ModerationDecision,
    PhoneBanRegistry,
    PhoneBanResult,
    Token,
    TokenKind,
    TokenReplayCheck,
    Trigger,
    VerificationStatus,
    check_hardware_fingerprint,
    complete_verification,
    decide,
    lifetime_for,
    maybe_timeout,
    mint_token,
    open_verification_request,
    resolve_appeal,
    revoke,
    revoke_verification,
    slide_lsb_token,
)


class TestTokens:

    def test_lifetimes(self):
        # Doc table
        assert DISCORD_ACCESS_TOKEN_LIFETIME_S == 7 * 86400
        assert LSB_ACCOUNT_TOKEN_LIFETIME_S == 30 * 86400
        assert SESSION_TOKEN_LIFETIME_S == 12 * 3600
        assert DISCORD_REFRESH_TOKEN_LIFETIME_S is None

    def test_lifetime_for(self):
        assert lifetime_for(TokenKind.DISCORD_ACCESS) == 7 * 86400
        assert lifetime_for(TokenKind.DISCORD_REFRESH) is None

    def test_mint_access_token(self):
        t = mint_token(kind=TokenKind.DISCORD_ACCESS,
                          discord_id="alice", now=100.0)
        assert t.discord_id == "alice"
        assert t.expires_at == 100.0 + 7 * 86400
        assert t.is_active(now=100.0)
        assert not t.is_active(now=t.expires_at + 1)

    def test_mint_refresh_indefinite(self):
        t = mint_token(kind=TokenKind.DISCORD_REFRESH,
                          discord_id="alice", now=0.0)
        assert t.expires_at is None
        assert t.is_active(now=10**12)

    def test_slide_lsb_token(self):
        t = mint_token(kind=TokenKind.LSB_ACCOUNT,
                          discord_id="alice", now=0.0)
        original_expiry = t.expires_at
        slide_lsb_token(t, now=86400.0)        # one day later
        assert t.expires_at == 86400.0 + 30 * 86400
        assert t.last_refreshed_at == 86400.0
        assert t.expires_at > original_expiry

    def test_slide_only_lsb(self):
        t = mint_token(kind=TokenKind.SESSION,
                          discord_id="alice", now=0.0)
        with pytest.raises(ValueError):
            slide_lsb_token(t, now=10.0)

    def test_revoke(self):
        t = mint_token(kind=TokenKind.SESSION,
                          discord_id="alice", now=0.0)
        revoke(t)
        assert not t.is_active(now=0.0)


class TestOauthFlow:

    def test_open_verification(self):
        req = open_verification_request(discord_id="bob", now=10.0)
        assert req.status == VerificationStatus.PENDING
        assert req.expires_at == 10.0 + VERIFICATION_TIMEOUT_SECONDS

    def test_24h_timeout(self):
        # Doc: 'Verification timeout (24h, no click) -> Auto-kick'
        assert VERIFICATION_TIMEOUT_SECONDS == 24 * 3600

    def test_maybe_timeout_pending(self):
        req = open_verification_request(discord_id="bob", now=0.0)
        # Inside the window
        assert maybe_timeout(req, now=3600.0) is False
        # Past the window
        assert maybe_timeout(req, now=24 * 3600 + 1) is True
        assert req.status == VerificationStatus.TIMED_OUT

    def test_complete_verification_grants_role_and_tokens(self):
        req = open_verification_request(discord_id="bob", now=0.0)
        outcome = complete_verification(
            req, now=10.0,
            launcher_download_url="https://demoncore.gg/launcher",
        )
        assert outcome.granted_role == VERIFIED_ROLE
        assert outcome.discord_access_token is not None
        assert outcome.discord_refresh_token is not None
        assert outcome.lsb_account_token is not None
        assert outcome.launcher_download_link.endswith("/launcher")
        assert req.status == VerificationStatus.VERIFIED

    def test_complete_verification_after_timeout_blocked(self):
        req = open_verification_request(discord_id="bob", now=0.0)
        maybe_timeout(req, now=99 * 3600)
        outcome = complete_verification(
            req, now=99 * 3600,
            launcher_download_url="https://x")
        assert outcome.lsb_account_token is None
        assert "timed out" in outcome.reason

    def test_revoke_verification(self):
        req = open_verification_request(discord_id="bob", now=0.0)
        revoke_verification(req)
        assert req.status == VerificationStatus.REVOKED
        outcome = complete_verification(
            req, now=10.0, launcher_download_url="x")
        assert outcome.lsb_account_token is None


class TestAccountRegistry:

    def test_link_idempotent(self):
        reg = AccountRegistry()
        a1 = reg.link(account_id="acc1", discord_id="bob",
                         now=0.0)
        a2 = reg.link(account_id="acc1", discord_id="bob",
                         now=10.0)
        assert a1 is a2
        assert a2.linked_at == 10.0

    def test_link_collision_raises(self):
        reg = AccountRegistry()
        reg.link(account_id="acc1", discord_id="bob", now=0.0)
        with pytest.raises(ValueError):
            reg.link(account_id="acc2", discord_id="bob", now=0.0)

    def test_lookups(self):
        reg = AccountRegistry()
        reg.link(account_id="acc1", discord_id="bob", now=0.0)
        assert reg.by_discord("bob").account_id == "acc1"
        assert reg.by_account("acc1").discord_id == "bob"
        assert reg.by_discord("not_a_user") is None

    def test_apply_ban_propagates(self):
        reg = AccountRegistry()
        reg.link(account_id="acc1", discord_id="bob", now=0.0)
        ok = reg.apply_ban(discord_id="bob",
                              reason="rmt", origin="game_side")
        assert ok is True
        a = reg.by_discord("bob")
        assert a.is_banned is True
        assert a.ban_origin == "game_side"

    def test_apply_ban_unknown_user(self):
        reg = AccountRegistry()
        ok = reg.apply_ban(discord_id="ghost",
                              reason="x", origin="discord")
        assert ok is False

    def test_lift_ban(self):
        reg = AccountRegistry()
        reg.link(account_id="acc1", discord_id="bob", now=0.0)
        reg.apply_ban(discord_id="bob", reason="x", origin="discord")
        assert reg.lift_ban("bob") is True
        a = reg.by_discord("bob")
        assert a.is_banned is False


class TestModeration:

    def test_new_member_dm_verify(self):
        d = decide(trigger=Trigger.NEW_MEMBER_JOINED,
                     target_discord_id="bob")
        assert d.action == ModAction.DM_VERIFY
        assert d.overridable is False     # this is a system action

    def test_verification_timeout_auto_kick(self):
        d = decide(trigger=Trigger.VERIFICATION_TIMEOUT,
                     target_discord_id="bob")
        assert d.action == ModAction.AUTO_KICK

    def test_report_low_warns(self):
        d = decide(trigger=Trigger.REPORTED_MESSAGE,
                     target_discord_id="bob",
                     report_severity="low")
        assert d.action == ModAction.WARN

    def test_report_medium_mutes(self):
        d = decide(trigger=Trigger.REPORTED_MESSAGE,
                     target_discord_id="bob",
                     report_severity="medium")
        assert d.action == ModAction.MUTE

    def test_report_high_bans(self):
        d = decide(trigger=Trigger.REPORTED_MESSAGE,
                     target_discord_id="bob",
                     report_severity="high")
        assert d.action == ModAction.BAN

    def test_report_critical_bans(self):
        d = decide(trigger=Trigger.REPORTED_MESSAGE,
                     target_discord_id="bob",
                     report_severity="critical")
        assert d.action == ModAction.BAN

    def test_game_side_propagates(self):
        d = decide(trigger=Trigger.GAME_SIDE_RULE_VIOLATION,
                     target_discord_id="bob")
        assert d.action == ModAction.GAME_BAN_PROPAGATE

    def test_appeal_first_pass_asks_clarify(self):
        d = decide(trigger=Trigger.APPEAL_MESSAGE,
                     target_discord_id="bob")
        assert d.action == ModAction.ASK_CLARIFY

    def test_patch_announce(self):
        d = decide(trigger=Trigger.PATCH_RELEASED)
        assert d.action == ModAction.ANNOUNCE
        assert d.overridable is False

    def test_outage_announce(self):
        d = decide(trigger=Trigger.SERVER_OUTAGE_DETECTED)
        assert d.action == ModAction.ANNOUNCE

    def test_appeal_compelling_lifts(self):
        prev = ModerationDecision(
            trigger=Trigger.REPORTED_MESSAGE,
            action=ModAction.BAN,
            target_discord_id="bob",
            rationale="banned for x",
        )
        out = resolve_appeal(previous_decision=prev,
                                appeal_strength="compelling")
        assert out.action == ModAction.LIFT_BAN

    def test_appeal_reasonable_escalates(self):
        prev = ModerationDecision(
            trigger=Trigger.REPORTED_MESSAGE,
            action=ModAction.BAN,
            target_discord_id="bob",
            rationale="banned for x",
        )
        out = resolve_appeal(previous_decision=prev,
                                appeal_strength="reasonable")
        assert out.action == ModAction.ESCALATE_HUMAN

    def test_appeal_weak_dismisses(self):
        prev = ModerationDecision(
            trigger=Trigger.REPORTED_MESSAGE,
            action=ModAction.BAN,
            target_discord_id="bob",
            rationale="banned",
        )
        out = resolve_appeal(previous_decision=prev,
                                appeal_strength="weak")
        assert out.action == ModAction.DISMISS

    def test_appeal_on_non_ban_passthrough(self):
        prev = ModerationDecision(
            trigger=Trigger.REPORTED_MESSAGE,
            action=ModAction.WARN, target_discord_id="bob",
            rationale="warned",
        )
        out = resolve_appeal(previous_decision=prev,
                                appeal_strength="compelling")
        # No ban to lift; same decision returned
        assert out.action == ModAction.WARN


class TestAuditLog:

    def test_record(self):
        log = AuditLog()
        d = decide(trigger=Trigger.REPORTED_MESSAGE,
                     target_discord_id="bob",
                     report_severity="medium")
        entry = log.record(decision=d, at_time=100.0)
        assert entry.action == ModAction.MUTE
        assert entry.audit_id.startswith("audit_")
        assert len(log) == 1

    def test_jsonl_roundtrip(self):
        log = AuditLog()
        log.record(decision=decide(trigger=Trigger.REPORTED_MESSAGE,
                                            target_discord_id="bob",
                                            report_severity="high"),
                      at_time=100.0)
        line = log.to_jsonl()
        parsed = json.loads(line)
        assert parsed["target"] == "bob"
        assert parsed["action"] == "ban"

    def test_history_for(self):
        # /why <user> command
        log = AuditLog()
        log.record(decision=decide(trigger=Trigger.REPORTED_MESSAGE,
                                            target_discord_id="bob",
                                            report_severity="low"),
                      at_time=100.0)
        log.record(decision=decide(trigger=Trigger.REPORTED_MESSAGE,
                                            target_discord_id="alice",
                                            report_severity="low"),
                      at_time=200.0)
        log.record(decision=decide(trigger=Trigger.REPORTED_MESSAGE,
                                            target_discord_id="bob",
                                            report_severity="high"),
                      at_time=300.0)
        bob = log.history_for("bob")
        assert len(bob) == 2

    def test_mark_overridden(self):
        log = AuditLog()
        e = log.record(decision=decide(trigger=Trigger.REPORTED_MESSAGE,
                                              target_discord_id="bob",
                                              report_severity="high"),
                          at_time=0.0)
        ok = log.mark_overridden(
            e.audit_id, override_by_discord_id="owner_id")
        assert ok is True
        # Re-fetch from history
        bob_entries = log.history_for("bob")
        assert bob_entries[0].overridden is True
        assert bob_entries[0].override_by == "owner_id"


class TestThreatModel:

    def test_first_link_pins_fingerprint(self):
        d = check_hardware_fingerprint(expected=None,
                                              reported="abc123")
        assert d.outcome == TokenReplayCheck.OK

    def test_fingerprint_match(self):
        d = check_hardware_fingerprint(expected="abc123",
                                              reported="abc123")
        assert d.outcome == TokenReplayCheck.OK

    def test_fingerprint_mismatch_revokes(self):
        d = check_hardware_fingerprint(expected="abc123",
                                              reported="xyz999")
        assert d.outcome == TokenReplayCheck.REVOKE
        assert "mismatch" in d.reason

    def test_empty_fingerprint_revokes(self):
        d = check_hardware_fingerprint(expected=None, reported="")
        assert d.outcome == TokenReplayCheck.REVOKE

    def test_phone_ban_registry(self):
        reg = PhoneBanRegistry()
        reg.record_banned_phone("+15551234")
        # New verification with banned phone -> blocked
        assert reg.check_new_verification(phone_number="+15551234") == PhoneBanResult.BLOCKED_BY_PHONE
        # Different phone -> allowed
        assert reg.check_new_verification(phone_number="+15559999") == PhoneBanResult.OK
        # No phone (declined scope) -> allowed
        assert reg.check_new_verification(phone_number=None) == PhoneBanResult.OK

    def test_gate_closed_when_chharbot_offline(self):
        # Doc: 'if chharbot is offline, the gate stays closed'
        gate = GateState()
        assert gate.can_accept_new_verifications() is True
        gate.mark_offline()
        assert gate.can_accept_new_verifications() is False
        gate.heartbeat(now=100.0)
        assert gate.can_accept_new_verifications() is True


# ----------------------------------------------------------------------
# Composition: end-to-end flow
# ----------------------------------------------------------------------

class TestComposition:

    def test_new_player_full_flow(self):
        """Doc flow: new player joins -> DM -> click verify -> tokens
        minted -> account linked -> ready to play."""
        # 1) new member joins guild -> chharbot decides DM_VERIFY
        decision = decide(trigger=Trigger.NEW_MEMBER_JOINED,
                              target_discord_id="newbie_001")
        assert decision.action == ModAction.DM_VERIFY

        # 2) chharbot opens verification request
        req = open_verification_request(discord_id="newbie_001",
                                              now=0.0)
        assert req.status == VerificationStatus.PENDING

        # 3) player clicks button at T+30s -> OAuth completes
        outcome = complete_verification(
            req, now=30.0,
            launcher_download_url="https://demoncore.gg/launcher",
        )
        assert outcome.granted_role == VERIFIED_ROLE

        # 4) chharbot links account
        reg = AccountRegistry()
        account = reg.link(
            account_id="acc_newbie_001",
            discord_id="newbie_001",
            now=30.0,
            lsb_token=outcome.lsb_account_token,
            hardware_fingerprint="hw_aaa",
        )
        assert account.lsb_token is not None

        # 5) launcher logs in 5 days later -> sliding window refreshes
        slide_lsb_token(account.lsb_token, now=5 * 86400.0)
        assert account.lsb_token.expires_at == 5 * 86400.0 + 30 * 86400

    def test_game_ban_propagates_to_discord(self):
        reg = AccountRegistry()
        log = AuditLog()
        reg.link(account_id="acc1", discord_id="cheater", now=0.0)
        # LSB emits a rule-violation event
        decision = decide(trigger=Trigger.GAME_SIDE_RULE_VIOLATION,
                              target_discord_id="cheater")
        assert decision.action == ModAction.GAME_BAN_PROPAGATE
        # chharbot applies the ban + audits
        reg.apply_ban(discord_id="cheater",
                         reason="rmt detected by LSB",
                         origin="game_side")
        log.record(decision=decision, at_time=100.0)
        a = reg.by_discord("cheater")
        assert a.is_banned and a.ban_origin == "game_side"
        assert len(log.history_for("cheater")) == 1

    def test_token_replay_revokes(self):
        reg = AccountRegistry()
        token = mint_token(kind=TokenKind.LSB_ACCOUNT,
                              discord_id="bob", now=0.0)
        reg.link(account_id="acc1", discord_id="bob", now=0.0,
                    lsb_token=token, hardware_fingerprint="hw_aaa")
        # Attacker tries with stolen token from a different machine
        decision = check_hardware_fingerprint(
            expected="hw_aaa", reported="hw_evil",
        )
        assert decision.outcome == TokenReplayCheck.REVOKE
        # chharbot revokes the token
        revoke(token)
        assert not token.is_active(now=10.0)
