"""Ambient barks — what mobs and NPCs say in passing.

The full dialogue system (npc_dialogue_system) is for sit-down
interactions. Barks are the AMBIENT layer: the muttering vendor
in the marketplace, the goblin that yells "I crush you!" as it
charges, the patrol guard who calls "halt!" as you cross his
beat, the mourning widow at dawn.

Barks are short, contextual lines selected by:
* The bark situation (greeting, idle, fighting, fleeing, etc.)
* The entity's mood (cheerful / surly / fearful / focused)
* Faction-rep band (a NEUTRAL stranger gets a different greet
  than a HERO_OF_THE_FACTION)
* Time of day (dawn prayer, evening farewell)
* Personality tags (a "schemer" mutters differently than a
  "berserker")

Author flow
-----------
A bark catalog is a list of `Bark` entries — each line tagged
with the situations / faction-rep bands / personality tags that
qualify. The selector picks one matching line; the orchestrator
emits it (UI text bubble or TTS via voice_pipeline).

Selection is deterministic with an optional rng for variety.

Public surface
--------------
    BarkSituation enum
    Bark dataclass — one tagged line
    BarkCatalog dataclass — collection of Bark + lookup helpers
    BarkSelector
        .pick(situation, ...) -> Optional[Bark]
    seed_default_catalog()  — out-of-the-box barks
"""
from __future__ import annotations

import dataclasses
import enum
import random
import typing as t

from server.faction_reputation import ReputationBand


class BarkSituation(str, enum.Enum):
    GREETING = "greeting"
    IDLE_MUTTER = "idle_mutter"
    FAREWELL = "farewell"
    AGGRO_OPEN = "aggro_open"        # mob spotting a target
    FIGHTING = "fighting"
    LOW_HP = "low_hp"
    FLEEING = "fleeing"
    KILL_CONFIRMED = "kill_confirmed"
    MOURNING = "mourning"
    DAWN_PRAYER = "dawn_prayer"
    DUSK_LAMENT = "dusk_lament"
    SHOP_HAWK = "shop_hawk"          # vendor calling out wares
    PATROL_HALT = "patrol_halt"      # guard challenging traveler
    RUMOR_SHARE = "rumor_share"      # passing on a rumor
    WARNING_BEASTMEN = "warning_beastmen"


@dataclasses.dataclass(frozen=True)
class Bark:
    bark_id: str
    line: str
    situation: BarkSituation
    # Optional filters — empty means "any value matches"
    rep_bands: frozenset[ReputationBand] = frozenset()
    personality_tags: frozenset[str] = frozenset()
    hours: frozenset[int] = frozenset()
    weight: int = 1               # higher weight -> picked more often

    def matches(
        self, *, situation: BarkSituation,
        rep_band: t.Optional[ReputationBand] = None,
        personality_tags: t.Iterable[str] = (),
        hour: t.Optional[int] = None,
    ) -> bool:
        if self.situation != situation:
            return False
        if self.rep_bands and rep_band is not None:
            if rep_band not in self.rep_bands:
                return False
        if self.personality_tags:
            tags = set(personality_tags)
            if not (tags & self.personality_tags):
                return False
        if self.hours and hour is not None:
            if hour not in self.hours:
                return False
        return True


@dataclasses.dataclass
class BarkCatalog:
    _barks: list[Bark] = dataclasses.field(default_factory=list)

    def add(self, bark: Bark) -> Bark:
        self._barks.append(bark)
        return bark

    def all_for_situation(
        self, situation: BarkSituation,
    ) -> tuple[Bark, ...]:
        return tuple(
            b for b in self._barks if b.situation == situation
        )

    def total(self) -> int:
        return len(self._barks)

    def matching(
        self, *, situation: BarkSituation,
        rep_band: t.Optional[ReputationBand] = None,
        personality_tags: t.Iterable[str] = (),
        hour: t.Optional[int] = None,
    ) -> tuple[Bark, ...]:
        tags = list(personality_tags)
        return tuple(
            b for b in self._barks
            if b.matches(
                situation=situation, rep_band=rep_band,
                personality_tags=tags, hour=hour,
            )
        )


@dataclasses.dataclass
class BarkSelector:
    catalog: BarkCatalog

    def pick(
        self, *, situation: BarkSituation,
        rep_band: t.Optional[ReputationBand] = None,
        personality_tags: t.Iterable[str] = (),
        hour: t.Optional[int] = None,
        rng: t.Optional[random.Random] = None,
    ) -> t.Optional[Bark]:
        """Pick a bark whose tags match the context, weighted by
        the bark's `weight`. Returns None when nothing matches
        (the orchestrator can fall back to silence or a default
        line)."""
        tags = list(personality_tags)
        candidates = self.catalog.matching(
            situation=situation, rep_band=rep_band,
            personality_tags=tags, hour=hour,
        )
        if not candidates:
            return None
        rng = rng or random.Random()
        # Specificity bonus — barks that filter on a tag/band/hour
        # weight more than the generic catch-all line.
        def _specificity(b: Bark) -> int:
            s = 0
            if b.rep_bands:
                s += 2
            if b.personality_tags:
                s += 2
            if b.hours:
                s += 1
            return s
        weights = [
            b.weight + _specificity(b) for b in candidates
        ]
        return rng.choices(candidates, weights=weights, k=1)[0]


# --------------------------------------------------------------------
# Default catalog — out-of-the-box ambient lines
# --------------------------------------------------------------------
def _build_default_catalog() -> tuple[Bark, ...]:
    return (
        # GREETING
        Bark(
            bark_id="greet_neutral_generic",
            line="Hail, traveler.",
            situation=BarkSituation.GREETING,
        ),
        Bark(
            bark_id="greet_friendly",
            line="Good to see you again, friend.",
            situation=BarkSituation.GREETING,
            rep_bands=frozenset({
                ReputationBand.FRIENDLY,
                ReputationBand.ALLIED,
            }),
        ),
        Bark(
            bark_id="greet_hero",
            line="By the gods, it's an honor.",
            situation=BarkSituation.GREETING,
            rep_bands=frozenset({
                ReputationBand.HERO_OF_THE_FACTION,
            }),
        ),
        Bark(
            bark_id="greet_unfriendly",
            line="What do you want?",
            situation=BarkSituation.GREETING,
            rep_bands=frozenset({ReputationBand.UNFRIENDLY}),
        ),
        Bark(
            bark_id="greet_dawn",
            line="A bright morning. Altana be praised.",
            situation=BarkSituation.GREETING,
            hours=frozenset({6, 7, 8}),
        ),
        # AGGRO_OPEN
        Bark(
            bark_id="aggro_berserker",
            line="I'll crush you to dust!",
            situation=BarkSituation.AGGRO_OPEN,
            personality_tags=frozenset({"berserker", "brawler"}),
        ),
        Bark(
            bark_id="aggro_schemer",
            line="You shouldn't have come here.",
            situation=BarkSituation.AGGRO_OPEN,
            personality_tags=frozenset({"schemer", "scout"}),
        ),
        Bark(
            bark_id="aggro_generic",
            line="An intruder!",
            situation=BarkSituation.AGGRO_OPEN,
        ),
        # LOW_HP
        Bark(
            bark_id="low_hp_coward",
            line="Mercy! Please, mercy!",
            situation=BarkSituation.LOW_HP,
            personality_tags=frozenset({"coward"}),
        ),
        Bark(
            bark_id="low_hp_zealot",
            line="My faith does not waver!",
            situation=BarkSituation.LOW_HP,
            personality_tags=frozenset({"zealot"}),
        ),
        Bark(
            bark_id="low_hp_generic",
            line="It's not over...",
            situation=BarkSituation.LOW_HP,
        ),
        # FLEEING
        Bark(
            bark_id="flee_generic",
            line="I'll be back!",
            situation=BarkSituation.FLEEING,
        ),
        Bark(
            bark_id="flee_traitor",
            line="To the seven hells with this.",
            situation=BarkSituation.FLEEING,
            personality_tags=frozenset({"traitor"}),
        ),
        # SHOP_HAWK
        Bark(
            bark_id="hawk_morning",
            line="Fresh bread, hot from the oven!",
            situation=BarkSituation.SHOP_HAWK,
            hours=frozenset({8, 9, 10, 11}),
        ),
        Bark(
            bark_id="hawk_afternoon",
            line="Last chance for the day's catch!",
            situation=BarkSituation.SHOP_HAWK,
            hours=frozenset({16, 17, 18}),
        ),
        # PATROL_HALT
        Bark(
            bark_id="halt_neutral",
            line="Halt — state your business.",
            situation=BarkSituation.PATROL_HALT,
        ),
        Bark(
            bark_id="halt_outlaw",
            line="You — drop your weapon!",
            situation=BarkSituation.PATROL_HALT,
            rep_bands=frozenset({
                ReputationBand.HOSTILE,
                ReputationBand.KILL_ON_SIGHT,
            }),
        ),
        # MOURNING / DAWN / DUSK
        Bark(
            bark_id="mourn",
            line="Why did Altana take them so soon...",
            situation=BarkSituation.MOURNING,
        ),
        Bark(
            bark_id="dawn_prayer",
            line="Goddess, watch over us this day.",
            situation=BarkSituation.DAWN_PRAYER,
            hours=frozenset({5, 6}),
        ),
        Bark(
            bark_id="dusk_lament",
            line="Another day done. The night is long.",
            situation=BarkSituation.DUSK_LAMENT,
            hours=frozenset({18, 19, 20}),
        ),
        # WARNING_BEASTMEN
        Bark(
            bark_id="warn_orcs",
            line="Orcs on the road — don't take it alone.",
            situation=BarkSituation.WARNING_BEASTMEN,
        ),
        # IDLE_MUTTER
        Bark(
            bark_id="idle_general",
            line="...",
            situation=BarkSituation.IDLE_MUTTER,
        ),
        Bark(
            bark_id="idle_schemer",
            line="They won't see it coming.",
            situation=BarkSituation.IDLE_MUTTER,
            personality_tags=frozenset({"schemer", "traitor"}),
        ),
        # KILL_CONFIRMED
        Bark(
            bark_id="kill_berserker",
            line="One more for the pile!",
            situation=BarkSituation.KILL_CONFIRMED,
            personality_tags=frozenset({"berserker"}),
        ),
        Bark(
            bark_id="kill_generic",
            line="Down they go.",
            situation=BarkSituation.KILL_CONFIRMED,
        ),
    )


def seed_default_catalog(catalog: BarkCatalog) -> BarkCatalog:
    for b in _build_default_catalog():
        catalog.add(b)
    return catalog


__all__ = [
    "BarkSituation", "Bark", "BarkCatalog", "BarkSelector",
    "seed_default_catalog",
]
