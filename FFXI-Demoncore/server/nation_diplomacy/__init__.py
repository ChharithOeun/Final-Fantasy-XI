"""Nation diplomacy — embassies, ambassadors, incidents.

The treaty module defines what nations have agreed to.
The diplomacy module handles the live machinery: each
nation maintains EMBASSIES in foreign capitals, run by
AMBASSADORS. Diplomatic INCIDENTS — escalating chains
of provocation — happen between nations, with severity
levels that the caller may use to trigger treaty
breach declarations or military mobilization.

EmbassyState:
    OPEN              normal operations
    RECALLED          ambassador withdrawn (downgrade)
    CLOSED            mission shut, staff expelled

IncidentSeverity:
    MINOR             diplomatic note exchanged
    MODERATE          formal protest filed
    MAJOR             ambassador summoned
    GRAVE             ambassador expelled
    CRITICAL          severance of ties (treaty
                      breach territory)

Public surface
--------------
    EmbassyState enum
    IncidentSeverity enum
    Embassy dataclass (frozen)
    DiplomaticIncident dataclass (frozen)
    NationDiplomacySystem
        .open_embassy(host_nation, sending_nation,
                      ambassador_id, opened_day) ->
                      Optional[str]
        .replace_ambassador(embassy_id,
                            new_ambassador) -> bool
        .recall(embassy_id, now_day, reason) -> bool
        .close_embassy(embassy_id, now_day,
                       reason) -> bool
        .reopen(embassy_id, ambassador_id,
                now_day) -> bool
        .file_incident(complainant, accused, severity,
                       summary, day) -> Optional[str]
        .resolve_incident(incident_id, day,
                          resolution) -> bool
        .embassy(embassy_id) -> Optional[Embassy]
        .embassies_in(host_nation) -> list[Embassy]
        .incidents_between(a, b) ->
                            list[DiplomaticIncident]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class EmbassyState(str, enum.Enum):
    OPEN = "open"
    RECALLED = "recalled"
    CLOSED = "closed"


class IncidentSeverity(str, enum.Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    GRAVE = "grave"
    CRITICAL = "critical"


@dataclasses.dataclass(frozen=True)
class Embassy:
    embassy_id: str
    host_nation: str
    sending_nation: str
    ambassador_id: str
    opened_day: int
    closed_day: t.Optional[int]
    state: EmbassyState
    state_reason: str


@dataclasses.dataclass(frozen=True)
class DiplomaticIncident:
    incident_id: str
    complainant: str
    accused: str
    severity: IncidentSeverity
    summary: str
    occurred_day: int
    resolved_day: t.Optional[int]
    resolution: str


@dataclasses.dataclass
class NationDiplomacySystem:
    _embassies: dict[str, Embassy] = dataclasses.field(
        default_factory=dict,
    )
    _incidents: dict[str, DiplomaticIncident] = (
        dataclasses.field(default_factory=dict)
    )
    _next_emb: int = 1
    _next_inc: int = 1

    def open_embassy(
        self, *, host_nation: str,
        sending_nation: str, ambassador_id: str,
        opened_day: int,
    ) -> t.Optional[str]:
        if not host_nation or not sending_nation:
            return None
        if host_nation == sending_nation:
            return None
        if not ambassador_id:
            return None
        if opened_day < 0:
            return None
        # Block duplicate OPEN embassy for the same
        # sending->host pair.
        for e in self._embassies.values():
            if (e.host_nation == host_nation
                    and e.sending_nation
                    == sending_nation
                    and e.state in (
                        EmbassyState.OPEN,
                        EmbassyState.RECALLED)):
                return None
        eid = f"emb_{self._next_emb}"
        self._next_emb += 1
        self._embassies[eid] = Embassy(
            embassy_id=eid, host_nation=host_nation,
            sending_nation=sending_nation,
            ambassador_id=ambassador_id,
            opened_day=opened_day,
            closed_day=None, state=EmbassyState.OPEN,
            state_reason="",
        )
        return eid

    def replace_ambassador(
        self, *, embassy_id: str,
        new_ambassador: str,
    ) -> bool:
        if embassy_id not in self._embassies:
            return False
        if not new_ambassador:
            return False
        e = self._embassies[embassy_id]
        if e.state == EmbassyState.CLOSED:
            return False
        self._embassies[embassy_id] = (
            dataclasses.replace(
                e, ambassador_id=new_ambassador,
            )
        )
        return True

    def recall(
        self, *, embassy_id: str, now_day: int,
        reason: str,
    ) -> bool:
        if embassy_id not in self._embassies:
            return False
        if not reason:
            return False
        e = self._embassies[embassy_id]
        if e.state != EmbassyState.OPEN:
            return False
        self._embassies[embassy_id] = (
            dataclasses.replace(
                e, state=EmbassyState.RECALLED,
                state_reason=reason,
            )
        )
        return True

    def close_embassy(
        self, *, embassy_id: str, now_day: int,
        reason: str,
    ) -> bool:
        if embassy_id not in self._embassies:
            return False
        if not reason:
            return False
        e = self._embassies[embassy_id]
        if e.state == EmbassyState.CLOSED:
            return False
        self._embassies[embassy_id] = (
            dataclasses.replace(
                e, state=EmbassyState.CLOSED,
                state_reason=reason,
                closed_day=now_day,
            )
        )
        return True

    def reopen(
        self, *, embassy_id: str,
        ambassador_id: str, now_day: int,
    ) -> bool:
        if embassy_id not in self._embassies:
            return False
        if not ambassador_id:
            return False
        e = self._embassies[embassy_id]
        if e.state not in (
            EmbassyState.RECALLED,
            EmbassyState.CLOSED,
        ):
            return False
        self._embassies[embassy_id] = (
            dataclasses.replace(
                e, state=EmbassyState.OPEN,
                ambassador_id=ambassador_id,
                state_reason="",
            )
        )
        return True

    def file_incident(
        self, *, complainant: str, accused: str,
        severity: IncidentSeverity, summary: str,
        occurred_day: int,
    ) -> t.Optional[str]:
        if not complainant or not accused:
            return None
        if complainant == accused:
            return None
        if not summary or occurred_day < 0:
            return None
        iid = f"inc_{self._next_inc}"
        self._next_inc += 1
        self._incidents[iid] = DiplomaticIncident(
            incident_id=iid, complainant=complainant,
            accused=accused, severity=severity,
            summary=summary,
            occurred_day=occurred_day,
            resolved_day=None, resolution="",
        )
        return iid

    def resolve_incident(
        self, *, incident_id: str,
        resolved_day: int, resolution: str,
    ) -> bool:
        if incident_id not in self._incidents:
            return False
        if not resolution:
            return False
        i = self._incidents[incident_id]
        if i.resolved_day is not None:
            return False
        if resolved_day < i.occurred_day:
            return False
        self._incidents[incident_id] = (
            dataclasses.replace(
                i, resolved_day=resolved_day,
                resolution=resolution,
            )
        )
        return True

    def embassy(
        self, *, embassy_id: str,
    ) -> t.Optional[Embassy]:
        return self._embassies.get(embassy_id)

    def embassies_in(
        self, *, host_nation: str,
    ) -> list[Embassy]:
        return [
            e for e in self._embassies.values()
            if e.host_nation == host_nation
        ]

    def incidents_between(
        self, *, a: str, b: str,
    ) -> list[DiplomaticIncident]:
        return [
            i for i in self._incidents.values()
            if ((i.complainant == a
                 and i.accused == b)
                or (i.complainant == b
                    and i.accused == a))
        ]


__all__ = [
    "EmbassyState", "IncidentSeverity", "Embassy",
    "DiplomaticIncident", "NationDiplomacySystem",
]
