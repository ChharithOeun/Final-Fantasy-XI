"""Player lawsuit — formal civil/criminal complaint.

A plaintiff files a lawsuit against a defendant for a
specific kind of grievance. Both parties submit evidence;
the defendant answers the complaint; finally a justice
rules in favor of plaintiff, defendant, or dismisses.
The case is then closed for the historical record.

Lifecycle
    FILED        plaintiff submitted; awaiting defendant
    ANSWERED     defendant has formally responded
    JUDGED       a justice has ruled
    DISMISSED    case withdrawn or thrown out

Verdicts (when JUDGED)
    PLAINTIFF    plaintiff prevailed
    DEFENDANT    defendant prevailed

Public surface
--------------
    LawsuitState enum
    Verdict enum
    Lawsuit dataclass (frozen)
    PlayerLawsuitSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class LawsuitState(str, enum.Enum):
    FILED = "filed"
    ANSWERED = "answered"
    JUDGED = "judged"
    DISMISSED = "dismissed"


class Verdict(str, enum.Enum):
    PLAINTIFF = "plaintiff"
    DEFENDANT = "defendant"


@dataclasses.dataclass(frozen=True)
class Lawsuit:
    lawsuit_id: str
    court_id: str
    plaintiff_id: str
    defendant_id: str
    kind: str
    claim: str
    state: LawsuitState
    verdict: t.Optional[Verdict]
    presiding_justice_id: str
    filed_day: int


@dataclasses.dataclass
class _LState:
    spec: Lawsuit
    plaintiff_evidence: list[str] = dataclasses.field(
        default_factory=list,
    )
    defendant_evidence: list[str] = dataclasses.field(
        default_factory=list,
    )


@dataclasses.dataclass
class PlayerLawsuitSystem:
    _suits: dict[str, _LState] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def file_lawsuit(
        self, *, court_id: str, plaintiff_id: str,
        defendant_id: str, kind: str, claim: str,
        filed_day: int,
    ) -> t.Optional[str]:
        if not court_id or not plaintiff_id:
            return None
        if not defendant_id:
            return None
        if plaintiff_id == defendant_id:
            return None
        if not kind or not claim:
            return None
        if filed_day < 0:
            return None
        lid = f"suit_{self._next}"
        self._next += 1
        self._suits[lid] = _LState(
            spec=Lawsuit(
                lawsuit_id=lid, court_id=court_id,
                plaintiff_id=plaintiff_id,
                defendant_id=defendant_id,
                kind=kind, claim=claim,
                state=LawsuitState.FILED,
                verdict=None, presiding_justice_id="",
                filed_day=filed_day,
            ),
        )
        return lid

    def submit_evidence(
        self, *, lawsuit_id: str, party_id: str,
        item: str,
    ) -> bool:
        if lawsuit_id not in self._suits:
            return False
        st = self._suits[lawsuit_id]
        if st.spec.state in (
            LawsuitState.JUDGED,
            LawsuitState.DISMISSED,
        ):
            return False
        if not item:
            return False
        if party_id == st.spec.plaintiff_id:
            st.plaintiff_evidence.append(item)
            return True
        if party_id == st.spec.defendant_id:
            st.defendant_evidence.append(item)
            return True
        return False

    def answer(
        self, *, lawsuit_id: str, defendant_id: str,
    ) -> bool:
        if lawsuit_id not in self._suits:
            return False
        st = self._suits[lawsuit_id]
        if st.spec.state != LawsuitState.FILED:
            return False
        if st.spec.defendant_id != defendant_id:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=LawsuitState.ANSWERED,
        )
        return True

    def rule(
        self, *, lawsuit_id: str, justice_id: str,
        verdict: Verdict,
    ) -> bool:
        if lawsuit_id not in self._suits:
            return False
        st = self._suits[lawsuit_id]
        if st.spec.state != LawsuitState.ANSWERED:
            return False
        if not justice_id:
            return False
        if justice_id in (
            st.spec.plaintiff_id,
            st.spec.defendant_id,
        ):
            return False
        st.spec = dataclasses.replace(
            st.spec, state=LawsuitState.JUDGED,
            verdict=verdict,
            presiding_justice_id=justice_id,
        )
        return True

    def dismiss(
        self, *, lawsuit_id: str,
        plaintiff_id: str,
    ) -> bool:
        """Plaintiff can withdraw before judgment."""
        if lawsuit_id not in self._suits:
            return False
        st = self._suits[lawsuit_id]
        if st.spec.state == LawsuitState.JUDGED:
            return False
        if st.spec.state == LawsuitState.DISMISSED:
            return False
        if st.spec.plaintiff_id != plaintiff_id:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=LawsuitState.DISMISSED,
        )
        return True

    def lawsuit(
        self, *, lawsuit_id: str,
    ) -> t.Optional[Lawsuit]:
        st = self._suits.get(lawsuit_id)
        return st.spec if st else None

    def evidence(
        self, *, lawsuit_id: str, party_id: str,
    ) -> list[str]:
        st = self._suits.get(lawsuit_id)
        if st is None:
            return []
        if party_id == st.spec.plaintiff_id:
            return list(st.plaintiff_evidence)
        if party_id == st.spec.defendant_id:
            return list(st.defendant_evidence)
        return []

    def suits_against(
        self, *, defendant_id: str,
    ) -> list[Lawsuit]:
        return [
            st.spec for st in self._suits.values()
            if st.spec.defendant_id == defendant_id
        ]


__all__ = [
    "LawsuitState", "Verdict", "Lawsuit",
    "PlayerLawsuitSystem",
]
