"""Neutral WHM Rogue Automatons — 1 per large continent.

Per the user direction: a special class of rogue automaton that
behaves NEUTRAL by default. They patrol their continent and randomly
heal/revive nearby players. Attacking one triggers an alarm that
spawns a hostile automaton party which attacks the aggressor
relentlessly.

This is a distinct entity from the standard rogue automaton NMs in
rogue_automatons.py — those are KOS apex enemies; these are
ambient guardians.

Continents (per FFXI canon):
    Quon       - Sandy / Bastok lands (west)
    Mindartia  - Windurst lands (east)
    Aradjiah   - Aht Urhgan lands (south)
    Ulbuka     - Adoulin lands (Demoncore extension; far west)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class NeutralRogueState(str, enum.Enum):
    NEUTRAL = "neutral"          # default; randomly heals nearby players
    ALARMED = "alarmed"          # attacked; alarm party inbound + hostile


@dataclasses.dataclass(frozen=True)
class NeutralWhmRogueSpec:
    """Static definition of one neutral WHM rogue."""
    nm_id: str
    name: str
    continent: str
    home_zone: str
    patrol_zones: tuple[str, ...]
    level: int
    hp_pool: int
    base_heal_amount: int
    raise_capability: bool
    # The hostile alarm-party that spawns when attacked
    alarm_party: tuple[str, ...]
    notes: str = ""


# 4 continental neutral WHM rogues
NEUTRAL_WHM_ROGUES: dict[str, NeutralWhmRogueSpec] = {
    "the_quon_handmaid": NeutralWhmRogueSpec(
        nm_id="the_quon_handmaid", name="The Quon Handmaid",
        continent="quon",
        home_zone="ronfaure_east",
        patrol_zones=("ronfaure_east", "ronfaure_west",
                        "gustaberg_north", "gustaberg_south",
                        "konschtat_highlands", "la_theine_plateau"),
        level=85,
        hp_pool=60000,
        base_heal_amount=800,
        raise_capability=True,
        alarm_party=("automaton_valoredge", "automaton_valoredge",
                       "automaton_sharpshot", "automaton_spiritreaver"),
        notes="legendary western continent guardian; cures + raises in a pulse",
    ),
    "the_mindartian_oracle": NeutralWhmRogueSpec(
        nm_id="the_mindartian_oracle", name="The Mindartian Oracle",
        continent="mindartia",
        home_zone="sarutabaruta_east",
        patrol_zones=("sarutabaruta_east", "sarutabaruta_west",
                        "tahrongi_canyon", "buburimu_peninsula",
                        "meriphataud_mountains", "rolanberry_fields"),
        level=85,
        hp_pool=60000,
        base_heal_amount=800,
        raise_capability=True,
        alarm_party=("automaton_valoredge", "automaton_spiritreaver",
                       "automaton_spiritreaver", "automaton_stormwaker"),
        notes="oracle-tier; haste-buffs allies near Windurst",
    ),
    "the_aradjiah_caretaker": NeutralWhmRogueSpec(
        nm_id="the_aradjiah_caretaker", name="The Aradjiah Caretaker",
        continent="aradjiah",
        home_zone="bhaflau_thickets",
        patrol_zones=("bhaflau_thickets", "wajaom_woodlands",
                        "mamook", "halvung",
                        "arrapago_reef", "caedarva_mire"),
        level=88,
        hp_pool=70000,
        base_heal_amount=900,
        raise_capability=True,
        alarm_party=("automaton_valoredge", "automaton_sharpshot",
                       "automaton_sharpshot", "automaton_stormwaker"),
        notes="tropical continent guardian; tough against Aht Urhgan beasts",
    ),
    "the_ulbukan_hermit": NeutralWhmRogueSpec(
        nm_id="the_ulbukan_hermit", name="The Ulbukan Hermit",
        continent="ulbuka",
        home_zone="cirdas_caverns",
        patrol_zones=("cirdas_caverns", "rala_waterways",
                        "yorcia_weald", "morimar_basalt_fields",
                        "ceizak_battlegrounds"),
        level=90,
        hp_pool=80000,
        base_heal_amount=1000,
        raise_capability=True,
        alarm_party=("automaton_valoredge", "automaton_sharpshot",
                       "automaton_spiritreaver", "automaton_spiritreaver",
                       "automaton_stormwaker"),
        notes="Adoulin frontier; alarm party is the largest of the four",
    ),
}


@dataclasses.dataclass
class NeutralWhmRogueRuntime:
    """Live state of one neutral WHM rogue."""
    spec: NeutralWhmRogueSpec
    state: NeutralRogueState = NeutralRogueState.NEUTRAL
    current_zone: str = ""
    # None until the first pulse fires; subsequent pulses use the
    # cooldown gate against this stored timestamp.
    last_heal_pulse_at: t.Optional[float] = None
    alarm_started_at: t.Optional[float] = None

    def __post_init__(self) -> None:
        if not self.current_zone:
            self.current_zone = self.spec.home_zone


# How often the neutral rogue pulses a heal (random heal/raise of
# nearby downed/injured players in the zone).
HEAL_PULSE_INTERVAL_SECONDS = 90.0
HEAL_PULSE_RADIUS_CM = 5000.0    # 50m


class NeutralWhmRogueManager:
    """Tracks the 4 continental rogues + their state. The combat
    pipeline calls notify_attacked() when a player aggros one;
    the heal-pulse cron calls maybe_heal_pulse() on each tick."""

    def __init__(self) -> None:
        self._runtimes: dict[str, NeutralWhmRogueRuntime] = {
            nm_id: NeutralWhmRogueRuntime(spec=spec)
            for nm_id, spec in NEUTRAL_WHM_ROGUES.items()
        }

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def get(self, nm_id: str) -> t.Optional[NeutralWhmRogueRuntime]:
        return self._runtimes.get(nm_id)

    def all_neutral(self) -> list[NeutralWhmRogueRuntime]:
        return [r for r in self._runtimes.values()
                  if r.state == NeutralRogueState.NEUTRAL]

    def is_neutral(self, nm_id: str) -> bool:
        rt = self._runtimes.get(nm_id)
        return rt is not None and rt.state == NeutralRogueState.NEUTRAL

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def notify_attacked(self,
                          nm_id: str,
                          *,
                          attacker_id: str,
                          now: float) -> t.Optional[tuple[str, ...]]:
        """A player attacked the rogue. Trip the alarm, return the
        alarm-party automaton ids to spawn (or None if no-op)."""
        rt = self._runtimes.get(nm_id)
        if rt is None:
            return None
        if rt.state == NeutralRogueState.ALARMED:
            return None   # already alarmed; party already exists
        rt.state = NeutralRogueState.ALARMED
        rt.alarm_started_at = now
        return rt.spec.alarm_party

    def maybe_heal_pulse(self,
                           nm_id: str,
                           *,
                           now: float,
                           nearby_player_ids: list[str],
                           nearby_downed_player_ids: list[str],
                           ) -> t.Optional[dict]:
        """Run a heal-pulse cycle. Returns a dict describing the heal
        event (so the orchestrator can apply HP / raise) or None if
        the cycle didn't fire (cooldown / alarmed / no nearby targets).
        """
        rt = self._runtimes.get(nm_id)
        if rt is None or rt.state != NeutralRogueState.NEUTRAL:
            return None
        if (rt.last_heal_pulse_at is not None
                and (now - rt.last_heal_pulse_at) < HEAL_PULSE_INTERVAL_SECONDS):
            return None
        if not nearby_player_ids and not nearby_downed_player_ids:
            return None

        rt.last_heal_pulse_at = now
        return {
            "nm_id": nm_id,
            "heal_amount": rt.spec.base_heal_amount,
            "healed": list(nearby_player_ids),
            "raised": (list(nearby_downed_player_ids)
                         if rt.spec.raise_capability else []),
            "radius_cm": HEAL_PULSE_RADIUS_CM,
        }

    def reset_to_neutral(self, nm_id: str) -> bool:
        """GM / cleanup helper. Returns the rogue to NEUTRAL state."""
        rt = self._runtimes.get(nm_id)
        if rt is None:
            return False
        rt.state = NeutralRogueState.NEUTRAL
        rt.alarm_started_at = None
        return True
