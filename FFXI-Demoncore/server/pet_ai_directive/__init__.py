"""Pet command vocabulary — per-job canonical commands.

Demoncore's AI is fully autonomous. Pets are NOT
state-machine-driven scripts — they're real AI agents (driven
by the agent_orchestrator and the broader AI stack). This
module defines:

* the CANONICAL command VOCABULARY each pet job can receive
  (these are the JAs/abilities the OWNER can request)
* a DIRECTIVE INTENT model — the most recent command the
  player issued, with a freshness timestamp
* a STATUS SNAPSHOT helper — facts the AI consumes to make its
  decisions (HP%, target, cooldowns)

The AI may FOLLOW the directive or COUNTERMAND it (e.g. ignore a
SIC if the pet would die mid-engagement). Decision-making lives
in the AI agent, NOT in this module — we just model the inputs.

Public surface
--------------
    PetJob enum (PUP / BST / SMN / GEO)
    PUP_COMMANDS / BST_COMMANDS / SMN_COMMANDS / GEO_COMMANDS
    Directive dataclass — single owner intent
    PetStatusSnapshot — facts the AI consumes
    PetCommandQueue — directive history for the AI to read
        .issue(command_id, target_id, now)
        .latest() / .recent_within(seconds) / .clear()
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


DIRECTIVE_FRESH_SECONDS = 30      # > 30s old, AI may de-prioritize
MAX_QUEUED_DIRECTIVES = 4         # short queue; older entries drop


class PetJob(str, enum.Enum):
    PUPPETMASTER = "puppetmaster"
    BEASTMASTER = "beastmaster"
    SUMMONER = "summoner"
    GEOMANCER = "geomancer"


# ---------------------------------------------------------------------
# Per-job canonical command catalogs
# ---------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class PetCommandDef:
    command_id: str
    label: str
    description: str
    cooldown_seconds: int = 0
    target_required: bool = False


# PUP — Puppetmaster commands. Maneuvers are tracked in
# automaton_synergy; this module covers the JA layer.
PUP_COMMANDS: dict[str, PetCommandDef] = {
    "activate": PetCommandDef(
        "activate", "Activate",
        "Summon the automaton to your side.",
        cooldown_seconds=20 * 60,
    ),
    "deactivate": PetCommandDef(
        "deactivate", "Deactivate",
        "Recall the automaton.",
        cooldown_seconds=0,
    ),
    "deus_ex_automata": PetCommandDef(
        "deus_ex_automata", "Deus Ex Automata",
        "Re-summon a downed automaton at full HP.",
        cooldown_seconds=20 * 60,
    ),
    "repair": PetCommandDef(
        "repair", "Repair",
        "Restore automaton HP at the cost of an automaton oil.",
        cooldown_seconds=60,
    ),
    "ready": PetCommandDef(
        "ready", "Ready",
        "Queue an automaton special ability the AI will fire "
        "when the situation matches.",
        cooldown_seconds=30, target_required=True,
    ),
    "overdrive": PetCommandDef(
        "overdrive", "Overdrive",
        "5x SP boost on next maneuver-stacked synergy.",
        cooldown_seconds=60 * 60,
    ),
    "tactical_switch": PetCommandDef(
        "tactical_switch", "Tactical Switch",
        "Swap automaton head/frame mid-fight (if multiple sets are equipped).",
        cooldown_seconds=10 * 60,
    ),
    "cooldown": PetCommandDef(
        "cooldown", "Cooldown",
        "Vent automaton heat — required before using maneuvers when "
        "the heat gauge is full.",
        cooldown_seconds=20,
    ),
}


# BST — Beastmaster commands.
BST_COMMANDS: dict[str, PetCommandDef] = {
    "charm": PetCommandDef(
        "charm", "Charm",
        "Charm a wild beast to fight for you (skill-gated).",
        cooldown_seconds=60, target_required=True,
    ),
    "tame": PetCommandDef(
        "tame", "Tame",
        "Pacify a wild beast briefly without claiming it.",
        cooldown_seconds=30, target_required=True,
    ),
    "sic": PetCommandDef(
        "sic", "Sic",
        "Order pet to use its strongest known mob ability.",
        cooldown_seconds=60, target_required=True,
    ),
    "snarl": PetCommandDef(
        "snarl", "Snarl",
        "Pet transfers all hate to a different target.",
        cooldown_seconds=60, target_required=True,
    ),
    "reward": PetCommandDef(
        "reward", "Reward",
        "Heal the pet by feeding it a piece of pet food.",
        cooldown_seconds=10,
    ),
    "heel": PetCommandDef(
        "heel", "Heel",
        "Pet returns to your side and stops engaging.",
        cooldown_seconds=0,
    ),
    "spur": PetCommandDef(
        "spur", "Spur",
        "Pet movement speed buff.",
        cooldown_seconds=5 * 60,
    ),
    "run_wild": PetCommandDef(
        "run_wild", "Run Wild",
        "Pet's enmity is wiped — used to drop hate after a heavy fight.",
        cooldown_seconds=10 * 60,
    ),
    "killer_instinct": PetCommandDef(
        "killer_instinct", "Killer Instinct",
        "Pet gains intimidation aura.",
        cooldown_seconds=10 * 60,
    ),
    "release": PetCommandDef(
        "release", "Release",
        "Dismiss the pet.",
        cooldown_seconds=0,
    ),
}


# SMN — Summoner commands. Per-avatar BPs are catalog-driven
# elsewhere (avatar_pacts); this module covers the JA layer.
SMN_COMMANDS: dict[str, PetCommandDef] = {
    "summon_avatar": PetCommandDef(
        "summon_avatar", "Summon Avatar",
        "Call the chosen avatar (target is the avatar id).",
        cooldown_seconds=20, target_required=True,
    ),
    "release_avatar": PetCommandDef(
        "release_avatar", "Release",
        "Dismiss the avatar.",
        cooldown_seconds=0,
    ),
    "astral_flow": PetCommandDef(
        "astral_flow", "Astral Flow",
        "Unlocks all 4 elemental Astral BPs for 1 minute.",
        cooldown_seconds=60 * 60 * 60,   # 60-min cooldown
    ),
    "astral_conduit": PetCommandDef(
        "astral_conduit", "Astral Conduit",
        "Avatar's BPs cost 0 MP and 0 timer for 30 seconds.",
        cooldown_seconds=15 * 60,
    ),
    "apogee": PetCommandDef(
        "apogee", "Apogee",
        "Next avatar BP-rage is double potency.",
        cooldown_seconds=10 * 60,
    ),
    "avatars_favor": PetCommandDef(
        "avatars_favor", "Avatar's Favor",
        "Activate the avatar's passive aura buff.",
        cooldown_seconds=10 * 60,
    ),
    "elemental_siphon": PetCommandDef(
        "elemental_siphon", "Elemental Siphon",
        "Drain MP from spirit element matching weather/day.",
        cooldown_seconds=60,
    ),
    "mana_cede": PetCommandDef(
        "mana_cede", "Mana Cede",
        "Force-share avatar MP with master.",
        cooldown_seconds=2 * 60,
    ),
    "blood_pact_rage": PetCommandDef(
        "blood_pact_rage", "Blood Pact: Rage",
        "Offensive avatar BP (target id required).",
        cooldown_seconds=60, target_required=True,
    ),
    "blood_pact_ward": PetCommandDef(
        "blood_pact_ward", "Blood Pact: Ward",
        "Defensive/buff avatar BP.",
        cooldown_seconds=60,
    ),
}


# GEO — Geomancer commands. Geo/indi-spells live in
# geomancy_luopans; this layer covers JAs around the luopan.
GEO_COMMANDS: dict[str, PetCommandDef] = {
    "summon_luopan": PetCommandDef(
        "summon_luopan", "Cast Geo-spell",
        "Summon a luopan with the chosen geo-spell anchor.",
        cooldown_seconds=10, target_required=True,
    ),
    "recall_luopan": PetCommandDef(
        "recall_luopan", "Full Circle",
        "Recall the active luopan (refunds some MP).",
        cooldown_seconds=20,
    ),
    "bolster": PetCommandDef(
        "bolster", "Bolster",
        "Doubles indi/geo bubble potency for 30 seconds.",
        cooldown_seconds=10 * 60,
    ),
    "ecliptic_attrition": PetCommandDef(
        "ecliptic_attrition", "Ecliptic Attrition",
        "Increase active bubble potency by 25%.",
        cooldown_seconds=60,
    ),
    "life_cycle": PetCommandDef(
        "life_cycle", "Life Cycle",
        "Sacrifice GEO HP to restore luopan HP.",
        cooldown_seconds=2 * 60,
    ),
    "blaze_of_glory": PetCommandDef(
        "blaze_of_glory", "Blaze of Glory",
        "Next geo-spell creates a luopan with 3x potency at the cost of HP.",
        cooldown_seconds=10 * 60,
    ),
    "dematerialize": PetCommandDef(
        "dematerialize", "Dematerialize",
        "Make the luopan invulnerable for 30 seconds.",
        cooldown_seconds=10 * 60,
    ),
    "concentric_pulse": PetCommandDef(
        "concentric_pulse", "Concentric Pulse",
        "AoE damage centered on the luopan.",
        cooldown_seconds=2 * 60, target_required=True,
    ),
    "mending_halation": PetCommandDef(
        "mending_halation", "Mending Halation",
        "AoE heal centered on the luopan.",
        cooldown_seconds=2 * 60,
    ),
    "radial_arcana": PetCommandDef(
        "radial_arcana", "Radial Arcana",
        "AoE buff for allies near the luopan.",
        cooldown_seconds=2 * 60,
    ),
    "curative_recantation": PetCommandDef(
        "curative_recantation", "Curative Recantation",
        "Erase one debuff per ally near the luopan.",
        cooldown_seconds=5 * 60,
    ),
    "theurgic_focus": PetCommandDef(
        "theurgic_focus", "Theurgic Focus",
        "Reduce magic-burst recast on the next nuke.",
        cooldown_seconds=10 * 60,
    ),
}


COMMANDS_BY_JOB: dict[PetJob, dict[str, PetCommandDef]] = {
    PetJob.PUPPETMASTER: PUP_COMMANDS,
    PetJob.BEASTMASTER: BST_COMMANDS,
    PetJob.SUMMONER: SMN_COMMANDS,
    PetJob.GEOMANCER: GEO_COMMANDS,
}


def commands_for(job: PetJob) -> dict[str, PetCommandDef]:
    return COMMANDS_BY_JOB[job]


def is_valid_command(*, job: PetJob, command_id: str) -> bool:
    return command_id in COMMANDS_BY_JOB[job]


# ---------------------------------------------------------------------
# Directive intent model — owner expresses intent, AI decides
# ---------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class Directive:
    command_id: str
    target_id: t.Optional[str]
    issued_at_seconds: float

    def age_seconds(self, *, now_seconds: float) -> float:
        return max(0.0, now_seconds - self.issued_at_seconds)

    def is_fresh(self, *, now_seconds: float,
                  fresh_window: float = DIRECTIVE_FRESH_SECONDS,
                  ) -> bool:
        return self.age_seconds(now_seconds=now_seconds) <= fresh_window


@dataclasses.dataclass(frozen=True)
class IssueResult:
    accepted: bool
    directive: t.Optional[Directive] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PetCommandQueue:
    """Short queue of recent directives. The AI agent reads this,
    weights by freshness, and decides moment-to-moment behavior."""
    owner_id: str
    pet_job: PetJob
    _queue: list[Directive] = dataclasses.field(default_factory=list)

    def issue(
        self, *, command_id: str,
        target_id: t.Optional[str], now_seconds: float,
    ) -> IssueResult:
        cmd = COMMANDS_BY_JOB[self.pet_job].get(command_id)
        if cmd is None:
            return IssueResult(False, reason="unknown command for job")
        if cmd.target_required and not target_id:
            return IssueResult(False, reason="target required")
        d = Directive(
            command_id=command_id, target_id=target_id,
            issued_at_seconds=now_seconds,
        )
        self._queue.append(d)
        if len(self._queue) > MAX_QUEUED_DIRECTIVES:
            self._queue = self._queue[-MAX_QUEUED_DIRECTIVES:]
        return IssueResult(True, directive=d)

    def latest(self) -> t.Optional[Directive]:
        return self._queue[-1] if self._queue else None

    def recent_within(
        self, *, seconds: float, now_seconds: float,
    ) -> tuple[Directive, ...]:
        cutoff = now_seconds - seconds
        return tuple(
            d for d in self._queue
            if d.issued_at_seconds >= cutoff
        )

    def clear(self) -> None:
        self._queue.clear()


# ---------------------------------------------------------------------
# Status snapshot — facts the AI consumes
# ---------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class PetStatusSnapshot:
    """A read-only snapshot of pet state the AI agent uses to
    plan its next action. The AI is in agent_orchestrator; this
    module just defines the shape of what it reads."""
    pet_id: str
    pet_job: PetJob
    owner_id: str
    hp_pct: int
    mp_pct: int
    in_combat: bool
    target_id: t.Optional[str]
    distance_to_owner: float
    cooldowns_active: tuple[str, ...]    # command_ids on cooldown


__all__ = [
    "DIRECTIVE_FRESH_SECONDS", "MAX_QUEUED_DIRECTIVES",
    "PetJob",
    "PetCommandDef", "PUP_COMMANDS", "BST_COMMANDS",
    "SMN_COMMANDS", "GEO_COMMANDS", "COMMANDS_BY_JOB",
    "commands_for", "is_valid_command",
    "Directive", "IssueResult",
    "PetCommandQueue", "PetStatusSnapshot",
]
