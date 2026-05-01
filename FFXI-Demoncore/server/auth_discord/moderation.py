"""chharbot moderator behavior — the trigger -> action table.

Per AUTH_DISCORD.md the moderation table:

| Trigger                          | chharbot action                            |
|----------------------------------|--------------------------------------------|
| New member joins guild           | DM with verification button                |
| Verification timeout (24h)       | Auto-kick                                  |
| Reported message (any user can /report) | reads context, decides:
                                     dismiss / warn / mute / ban + logs rationale |
| Game-side rule violation         | LSB emits event -> chharbot ingests ->
                                     same Discord-side action                   |
| Appeal channel message           | reviews ban context, asks Qs, lifts or
                                     escalates to human ops                     |
| Patch released                   | announces in #patch-notes                  |
| Server outage detected           | announces + opens triage thread            |

'chharbot is the only moderator. Humans don't have ban buttons.'
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Trigger(str, enum.Enum):
    NEW_MEMBER_JOINED = "new_member_joined"
    VERIFICATION_TIMEOUT = "verification_timeout"
    REPORTED_MESSAGE = "reported_message"
    GAME_SIDE_RULE_VIOLATION = "game_side_rule_violation"
    APPEAL_MESSAGE = "appeal_message"
    PATCH_RELEASED = "patch_released"
    SERVER_OUTAGE_DETECTED = "server_outage_detected"


class ModAction(str, enum.Enum):
    DM_VERIFY = "dm_verify"
    AUTO_KICK = "auto_kick"
    DISMISS = "dismiss"
    WARN = "warn"
    MUTE = "mute"
    BAN = "ban"
    GAME_BAN_PROPAGATE = "game_ban_propagate"
    ASK_CLARIFY = "ask_clarify"
    LIFT_BAN = "lift_ban"
    ESCALATE_HUMAN = "escalate_human"
    ANNOUNCE = "announce"


@dataclasses.dataclass(frozen=True)
class ModerationDecision:
    """One chharbot moderation outcome."""
    trigger: Trigger
    action: ModAction
    target_discord_id: t.Optional[str]
    rationale: str
    overridable: bool = True
    related_audit_ids: tuple[str, ...] = ()


def decide(*,
              trigger: Trigger,
              target_discord_id: t.Optional[str] = None,
              context_summary: str = "",
              report_severity: str = "low",
              ) -> ModerationDecision:
    """Decision pipeline mapping triggers to actions.

    `report_severity` is the chharbot LLM's read of an incoming
    /report (low/medium/high/critical). The mapping is conservative
    — chharbot warns first, mutes for repeat low/medium, bans only
    on high/critical.
    """
    if trigger == Trigger.NEW_MEMBER_JOINED:
        return ModerationDecision(
            trigger=trigger, action=ModAction.DM_VERIFY,
            target_discord_id=target_discord_id,
            rationale="new member joined; sending verification DM",
            overridable=False,
        )
    if trigger == Trigger.VERIFICATION_TIMEOUT:
        return ModerationDecision(
            trigger=trigger, action=ModAction.AUTO_KICK,
            target_discord_id=target_discord_id,
            rationale="24h verification timeout; auto-kick per doc",
        )
    if trigger == Trigger.REPORTED_MESSAGE:
        action = {
            "low": ModAction.WARN,
            "medium": ModAction.MUTE,
            "high": ModAction.BAN,
            "critical": ModAction.BAN,
        }.get(report_severity.lower(), ModAction.DISMISS)
        return ModerationDecision(
            trigger=trigger, action=action,
            target_discord_id=target_discord_id,
            rationale=(f"reported message; severity={report_severity}; "
                          f"context={context_summary}"),
        )
    if trigger == Trigger.GAME_SIDE_RULE_VIOLATION:
        return ModerationDecision(
            trigger=trigger, action=ModAction.GAME_BAN_PROPAGATE,
            target_discord_id=target_discord_id,
            rationale=("LSB emitted rule-violation event; "
                          "propagating ban to Discord side"),
        )
    if trigger == Trigger.APPEAL_MESSAGE:
        # First-pass: ask clarifying question; the appeal loop
        # produces LIFT_BAN or ESCALATE_HUMAN downstream.
        return ModerationDecision(
            trigger=trigger, action=ModAction.ASK_CLARIFY,
            target_discord_id=target_discord_id,
            rationale="appeal received; asking clarifying question",
        )
    if trigger == Trigger.PATCH_RELEASED:
        return ModerationDecision(
            trigger=trigger, action=ModAction.ANNOUNCE,
            target_discord_id=None,
            rationale="patch released; announcing in #patch-notes",
            overridable=False,
        )
    if trigger == Trigger.SERVER_OUTAGE_DETECTED:
        return ModerationDecision(
            trigger=trigger, action=ModAction.ANNOUNCE,
            target_discord_id=None,
            rationale="outage detected; announcing + opening triage thread",
            overridable=False,
        )
    return ModerationDecision(
        trigger=trigger, action=ModAction.DISMISS,
        target_discord_id=target_discord_id,
        rationale="no rule matched",
    )


def resolve_appeal(*,
                       previous_decision: ModerationDecision,
                       appeal_strength: str,
                       ) -> ModerationDecision:
    """Second pass: chharbot has read the appeal context.

    `appeal_strength` is 'weak' / 'reasonable' / 'compelling'.
    Compelling lifts; reasonable escalates to human ops; weak
    keeps the ban.
    """
    if previous_decision.action != ModAction.BAN:
        return previous_decision
    target = previous_decision.target_discord_id
    if appeal_strength == "compelling":
        return ModerationDecision(
            trigger=Trigger.APPEAL_MESSAGE,
            action=ModAction.LIFT_BAN,
            target_discord_id=target,
            rationale="appeal compelling; lifting ban",
        )
    if appeal_strength == "reasonable":
        return ModerationDecision(
            trigger=Trigger.APPEAL_MESSAGE,
            action=ModAction.ESCALATE_HUMAN,
            target_discord_id=target,
            rationale="appeal reasonable; escalating to human ops",
        )
    return ModerationDecision(
        trigger=Trigger.APPEAL_MESSAGE,
        action=ModAction.DISMISS,
        target_discord_id=target,
        rationale="appeal weak; ban stands",
    )
