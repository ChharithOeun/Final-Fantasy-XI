"""Siren song apprentice — BRD with mermaid council standing
learns limited siren songs.

Once a player has TIDE_KEEPERS plurality on the
mermaid_diplomacy_council AND is leveled BRD, they can
apprentice with a Sirenhall master and learn LIMITED siren
songs they can cast on enemy mobs (PvE only — siren songs
against players are forbidden by the council).

Apprentice spells:
  WHISPER_BIND   - 30s lure on a single PvE mob
  CHORD_DRIFT    - small AoE confusion in PvE
  HYMN_LULL      - sleep effect on PvE mobs

These are STRICTLY weaker than NPC siren cast — half the
strength, half the duration, no SHIPWRECK or BECALM kinds.
The council pulls the spells if the player loses the rep
threshold or if the council shifts away from TIDE_KEEPERS
(re-checked at cast time).

Public surface
--------------
    Apprentice spell enum
    LearnResult / CastResult dataclasses
    SirenSongApprentice
        .learn(player_id, spell, job, faction_holding_court,
               mermaid_rep)
        .cast(player_id, spell, target_kind, faction_holding_court,
              mermaid_rep, now_seconds)
        .knows(player_id, spell)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ApprenticeSpell(str, enum.Enum):
    WHISPER_BIND = "whisper_bind"
    CHORD_DRIFT = "chord_drift"
    HYMN_LULL = "hymn_lull"


REQUIRED_REP = 100
REQUIRED_FACTION = "tide_keepers"
REQUIRED_JOB = "BRD"

_SPELL_DURATION_SECONDS: dict[ApprenticeSpell, int] = {
    ApprenticeSpell.WHISPER_BIND: 30,
    ApprenticeSpell.CHORD_DRIFT: 20,
    ApprenticeSpell.HYMN_LULL: 60,
}


@dataclasses.dataclass(frozen=True)
class LearnResult:
    accepted: bool
    spell: t.Optional[ApprenticeSpell] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class CastResult:
    accepted: bool
    spell: t.Optional[ApprenticeSpell] = None
    duration_seconds: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class SirenSongApprentice:
    _known: dict[str, set[ApprenticeSpell]] = dataclasses.field(
        default_factory=dict,
    )

    def _gates_pass(
        self, *, job: str,
        faction_holding_court: str,
        mermaid_rep: int,
    ) -> t.Optional[str]:
        if job != REQUIRED_JOB:
            return "BRD required"
        if faction_holding_court != REQUIRED_FACTION:
            return "council not TIDE_KEEPERS"
        if mermaid_rep < REQUIRED_REP:
            return "mermaid rep too low"
        return None

    def learn(
        self, *, player_id: str,
        spell: ApprenticeSpell,
        job: str,
        faction_holding_court: str,
        mermaid_rep: int,
    ) -> LearnResult:
        if not player_id:
            return LearnResult(False, reason="bad player")
        if spell not in _SPELL_DURATION_SECONDS:
            return LearnResult(False, reason="unknown spell")
        gate_fail = self._gates_pass(
            job=job,
            faction_holding_court=faction_holding_court,
            mermaid_rep=mermaid_rep,
        )
        if gate_fail is not None:
            return LearnResult(False, reason=gate_fail)
        known = self._known.setdefault(player_id, set())
        if spell in known:
            return LearnResult(
                False, spell=spell, reason="already known",
            )
        known.add(spell)
        return LearnResult(True, spell=spell)

    def cast(
        self, *, player_id: str,
        spell: ApprenticeSpell,
        target_kind: str,    # "pve" or "pvp"
        faction_holding_court: str,
        mermaid_rep: int,
        now_seconds: int,
    ) -> CastResult:
        known = self._known.get(player_id, set())
        if spell not in known:
            return CastResult(False, reason="not learned")
        if target_kind != "pve":
            return CastResult(
                False, spell=spell, reason="pvp use forbidden",
            )
        # gates re-checked at cast — council can revoke at any time
        if faction_holding_court != REQUIRED_FACTION:
            return CastResult(
                False, spell=spell, reason="council revoked",
            )
        if mermaid_rep < REQUIRED_REP:
            return CastResult(
                False, spell=spell, reason="rep below threshold",
            )
        return CastResult(
            accepted=True,
            spell=spell,
            duration_seconds=_SPELL_DURATION_SECONDS[spell],
        )

    def knows(
        self, *, player_id: str, spell: ApprenticeSpell,
    ) -> bool:
        return spell in self._known.get(player_id, set())


__all__ = [
    "ApprenticeSpell", "LearnResult", "CastResult",
    "SirenSongApprentice",
    "REQUIRED_REP", "REQUIRED_FACTION", "REQUIRED_JOB",
]
