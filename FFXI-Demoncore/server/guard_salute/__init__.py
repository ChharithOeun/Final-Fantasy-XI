"""Guard salute — town/nation guards recognize and salute legends.

A reverence-tier player walking past nation guards should
get a different reception than the rest. The guard_salute
module coordinates that:

   - At REVERED+ recognition, guards salute (visible animation
     + audible callout).
   - At MYTHICAL recognition, guards open restricted gates
     and waive the toll.
   - Outlaw-flagged players get HOSTILE response regardless
     of titles — wanted is wanted.
   - Cooldown per guard prevents spam saluting.

Public surface
--------------
    GuardResponse enum
    GuardOutcome dataclass (frozen)
    GuardSaluteRegistry
        .register_post(post_id, zone_id, allows_gate_pass)
        .request_passage(post_id, player_id, recognition,
                         is_outlaw, now_seconds)
            -> GuardOutcome
        .seconds_until_ready(post_id, player_id, now_seconds)
            -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.npc_legend_awareness import RecognitionResult, RecognitionTier


class GuardResponse(str, enum.Enum):
    IGNORE = "ignore"
    NOD = "nod"
    SALUTE = "salute"
    OPEN_GATE = "open_gate"
    HOSTILE = "hostile"


SALUTE_COOLDOWN = 30  # seconds — don't spam


@dataclasses.dataclass(frozen=True)
class GuardOutcome:
    response: GuardResponse
    callout: str
    granted_passage: bool
    waived_toll: bool


@dataclasses.dataclass
class _Post:
    post_id: str
    zone_id: str
    allows_gate_pass: bool
    # last salute time per (post_id, player_id) pair
    last_salute_for: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class GuardSaluteRegistry:
    _posts: dict[str, _Post] = dataclasses.field(
        default_factory=dict,
    )

    def register_post(
        self, *, post_id: str, zone_id: str,
        allows_gate_pass: bool = False,
    ) -> bool:
        if not post_id or not zone_id:
            return False
        if post_id in self._posts:
            return False
        self._posts[post_id] = _Post(
            post_id=post_id, zone_id=zone_id,
            allows_gate_pass=allows_gate_pass,
        )
        return True

    def request_passage(
        self, *, post_id: str, player_id: str,
        recognition: RecognitionResult,
        is_outlaw: bool,
        now_seconds: int,
    ) -> GuardOutcome:
        post = self._posts.get(post_id)
        if post is None or not player_id:
            return GuardOutcome(
                response=GuardResponse.IGNORE,
                callout="",
                granted_passage=False,
                waived_toll=False,
            )

        # outlaws override everything
        if is_outlaw:
            return GuardOutcome(
                response=GuardResponse.HOSTILE,
                callout=f"Halt, outlaw! In the king's name!",
                granted_passage=False,
                waived_toll=False,
            )

        last_salute = post.last_salute_for.get(player_id, -1_000_000)
        on_cooldown = (now_seconds - last_salute) < SALUTE_COOLDOWN

        tier = recognition.tier
        if tier == RecognitionTier.MYTHICAL:
            response = GuardResponse.OPEN_GATE
            callout = (
                "ATTEN-SHUN! The gate is open! "
                "Pass freely, Demoncore!"
            )
            granted = post.allows_gate_pass
            waived = True
        elif tier == RecognitionTier.REVERED:
            response = GuardResponse.SALUTE
            callout = "Hail and well met, hero!"
            granted = False
            waived = False
        elif tier == RecognitionTier.HONORED:
            response = GuardResponse.SALUTE
            callout = "An honor, champion."
            granted = False
            waived = False
        elif tier == RecognitionTier.NOTED:
            response = GuardResponse.NOD
            callout = "Move along."
            granted = False
            waived = False
        else:
            response = GuardResponse.IGNORE
            callout = ""
            granted = False
            waived = False

        # apply cooldown — if on cooldown, demote dramatic responses
        if on_cooldown and response in (
            GuardResponse.SALUTE, GuardResponse.OPEN_GATE,
        ):
            response = GuardResponse.NOD
            callout = ""
        else:
            if response in (GuardResponse.SALUTE,
                            GuardResponse.OPEN_GATE):
                post.last_salute_for[player_id] = now_seconds

        return GuardOutcome(
            response=response, callout=callout,
            granted_passage=granted, waived_toll=waived,
        )

    def seconds_until_ready(
        self, *, post_id: str, player_id: str,
        now_seconds: int,
    ) -> int:
        post = self._posts.get(post_id)
        if post is None:
            return 0
        last = post.last_salute_for.get(player_id, -1_000_000)
        elapsed = now_seconds - last
        if elapsed >= SALUTE_COOLDOWN:
            return 0
        return SALUTE_COOLDOWN - elapsed


__all__ = [
    "GuardResponse", "GuardOutcome", "SALUTE_COOLDOWN",
    "GuardSaluteRegistry",
]
