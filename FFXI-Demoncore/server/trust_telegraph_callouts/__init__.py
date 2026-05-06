"""Trust telegraph callouts — NPCs shout when they spot a tell.

Some Trust NPCs are sharp-eyed. SCH/BLU/SMN trusts have
the perception to notice tells the player might miss.
When their boss target triggers a tell, the trust shouts
a callout that:
    - prints to chat / plays voice line
    - briefly grants the player a half-second SECONDARY
      hint (NOT full visibility, just an audio + text
      ping)

This is NOT a free GEO bubble — it doesn't draw the AOE
overlay. It just speeds up the player's gesture-reading
by giving them an extra audible cue. A casual player
without GEO/BRD support gets a meaningful boost from
having an attentive Trust in their party.

Trust perception levels
-----------------------
    DULL          0% callout chance
    WATCHFUL     50% chance to call known tells
    SHARP        80% chance, calls 1 second sooner
    ORACLE      100% chance, calls 1.5 seconds sooner
                 AND grants 2-second BARD-style visibility

Per-trust profile (defaults — designers can override):
    trust_id          perception
    Apururu_UC        SHARP    (WHM, has it from rank)
    Koru_Moru         WATCHFUL (BLM, paranoid)
    Joachim           SHARP    (BRD, song-conductor)
    Ulmia             ORACLE   (BRD, lore-keeper, rare)
    Kupipi            DULL     (1st-tier moogle)
    Star_Sibyl        ORACLE   (Windy seer, story trust)

Public surface
--------------
    Perception enum
    TrustCallout dataclass (frozen)
    CalloutEvent dataclass (frozen)
    TrustTelegraphCallouts
        .register_trust_perception(trust_id, perception)
        .on_tell_detected(party_trust_ids, boss_id,
                          ability_id, tell_kind, now_seconds,
                          rng_roll_pct, gate, listener_player_ids)
            -> tuple[CalloutEvent, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.boss_ability_tells import TellKind
from server.telegraph_visibility_gate import (
    TelegraphVisibilityGate, VisibilitySource,
)


class Perception(str, enum.Enum):
    DULL = "dull"
    WATCHFUL = "watchful"
    SHARP = "sharp"
    ORACLE = "oracle"


# Profile per perception tier
@dataclasses.dataclass(frozen=True)
class _PerceptionProfile:
    callout_chance_pct: int
    earlier_warning_seconds: float
    grants_visibility_seconds: int


_PROFILES: dict[Perception, _PerceptionProfile] = {
    Perception.DULL: _PerceptionProfile(0, 0.0, 0),
    Perception.WATCHFUL: _PerceptionProfile(50, 0.0, 0),
    Perception.SHARP: _PerceptionProfile(80, 1.0, 0),
    Perception.ORACLE: _PerceptionProfile(100, 1.5, 2),
}


@dataclasses.dataclass(frozen=True)
class TrustCallout:
    trust_id: str
    perception: Perception


@dataclasses.dataclass(frozen=True)
class CalloutEvent:
    trust_id: str
    perception: Perception
    boss_id: str
    ability_id: str
    tell: TellKind
    voice_line: str
    earlier_warning_seconds: float
    visibility_seconds_granted: int
    fired_at: int


# Default voice-line table — short, BRD-flavored
_VOICE_LINES: dict[TellKind, str] = {
    TellKind.WEAPON_GLOW: "It charges its weapon — brace!",
    TellKind.HAND_GESTURE: "It raises its arm — watch the cone!",
    TellKind.DUST_FALLING: "Above! The ceiling's about to fall!",
    TellKind.WATER_RIPPLE: "The water stirs — wave incoming!",
    TellKind.SHADOW_LENGTHENS: "A shadow lengthens — curse rising!",
    TellKind.GUSTING_WIND: "Wind's gathering — lightning coming!",
    TellKind.EARTH_CRACK: "The ground splits — quake!",
    TellKind.AIR_DISTORTS: "The air shimmers — fire AOE!",
}


@dataclasses.dataclass
class TrustTelegraphCallouts:
    _trust_perception: dict[str, Perception] = dataclasses.field(
        default_factory=dict,
    )

    def register_trust_perception(
        self, *, trust_id: str, perception: Perception,
    ) -> bool:
        if not trust_id:
            return False
        self._trust_perception[trust_id] = perception
        return True

    def perception_for(self, *, trust_id: str) -> Perception:
        return self._trust_perception.get(trust_id, Perception.DULL)

    def on_tell_detected(
        self, *, party_trust_ids: t.Iterable[str],
        boss_id: str, ability_id: str, tell: TellKind,
        now_seconds: int, rng_roll_pct: int,
        gate: TelegraphVisibilityGate,
        listener_player_ids: t.Iterable[str] = (),
    ) -> tuple[CalloutEvent, ...]:
        if not (1 <= rng_roll_pct <= 100):
            return ()
        out: list[CalloutEvent] = []
        listeners = [p for p in listener_player_ids if p]
        for trust_id in party_trust_ids:
            if not trust_id:
                continue
            perception = self.perception_for(trust_id=trust_id)
            prof = _PROFILES[perception]
            if rng_roll_pct > prof.callout_chance_pct:
                continue
            line = _VOICE_LINES.get(tell, "Watch the boss!")
            voice_line = f"{trust_id}: {line}"
            granted_secs = 0
            if prof.grants_visibility_seconds > 0:
                for p in listeners:
                    gate.grant_visibility(
                        player_id=p,
                        source=VisibilitySource.OTHER,
                        granted_at=now_seconds,
                        expires_at=(
                            now_seconds + prof.grants_visibility_seconds
                        ),
                        granted_by=trust_id,
                    )
                granted_secs = prof.grants_visibility_seconds
            out.append(CalloutEvent(
                trust_id=trust_id,
                perception=perception,
                boss_id=boss_id,
                ability_id=ability_id,
                tell=tell,
                voice_line=voice_line,
                earlier_warning_seconds=prof.earlier_warning_seconds,
                visibility_seconds_granted=granted_secs,
                fired_at=now_seconds,
            ))
        return tuple(out)


__all__ = [
    "Perception", "TrustCallout", "CalloutEvent",
    "TrustTelegraphCallouts",
]
