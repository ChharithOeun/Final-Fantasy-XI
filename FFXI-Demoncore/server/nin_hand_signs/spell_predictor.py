"""Spell predictor — observable-prefix-matching for skilled players.

Per the doc's worked example: a NIN running through Snake -> Tiger ->
Horse -> Monkey -> Tiger is unmistakably casting Katon: San by the
fourth seal. A skilled observer reads the partial sequence and
narrows the candidate spell set seal-by-seal.

This is the basis for the visible-reading principle. Mob-NIN squads
also produce these cues — players who learn the sequences gain real
combat advantage.

API:
    candidate_spells(observed_seals)   - list of spells whose prefix
                                          matches the observed seals
    is_uniquely_identified(observed_seals) - True iff exactly one
                                              candidate remains
    SpellPredictor.observe(seal)        - stateful builder used by
                                          UI / orchestrator
"""
from __future__ import annotations

import dataclasses
import typing as t

from .seals import Seal
from .sequences import NINJUTSU_SEQUENCES


def candidate_spells(observed_seals: list[Seal]) -> list[str]:
    """Return spell ids whose seal-sequence STARTS WITH the observed
    seals. An empty observed list returns every known spell.

    Note: 'starts with' includes exact matches (a fully-completed
    sequence is still a candidate of itself)."""
    if not observed_seals:
        return sorted(NINJUTSU_SEQUENCES.keys())

    obs_tuple = tuple(observed_seals)
    out = []
    for spell, seq in NINJUTSU_SEQUENCES.items():
        if len(seq) < len(obs_tuple):
            continue
        if tuple(seq[:len(obs_tuple)]) == obs_tuple:
            out.append(spell)
    return sorted(out)


def is_uniquely_identified(observed_seals: list[Seal]) -> bool:
    """True iff exactly one spell could still produce this sequence."""
    return len(candidate_spells(observed_seals)) == 1


@dataclasses.dataclass
class SpellPredictor:
    """Stateful prefix builder. Observe seals as the NIN forms them;
    query candidates / unique identification at any time.

    Used by:
        - UI: "the NIN appears to be casting [list]"
        - Mob counter-AI: 'I see Snake -> Tiger; could be katon family;
          start preparing fire resist'
    """
    observed: list[Seal] = dataclasses.field(default_factory=list)

    def observe(self, seal: Seal) -> "SpellPredictor":
        self.observed.append(seal)
        return self

    def reset(self) -> None:
        self.observed.clear()

    def candidates(self) -> list[str]:
        return candidate_spells(self.observed)

    def is_unique(self) -> bool:
        return is_uniquely_identified(self.observed)

    def remaining_seal_count(self) -> int:
        """If uniquely identified, how many seals remain before
        spell-completion. Returns 0 if not yet unique."""
        c = self.candidates()
        if len(c) != 1:
            return 0
        full_len = len(NINJUTSU_SEQUENCES[c[0]])
        return full_len - len(self.observed)
