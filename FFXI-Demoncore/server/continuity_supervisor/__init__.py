"""Continuity supervisor — visual continuity tracker.

The script-supervisor / continuity-script in code. Per
shot, per character, snapshot the visible state of that
character: wardrobe (ordered list of clothing items),
props in hand, blood splatter locations, weather, time of
day, hair state, wounds, accessories, and the camera
position. On the next shot the supervisor compares the
new snapshot to the previous one for the same character
and flags discrepancies.

Severity is graded the way real on-set supervisors do it:
NOTE for cosmetic things the audience will probably not
notice, WARNING for things they probably will, ERROR for
things that break scene logic outright (a prop that
appears with no on-screen reason).

Costume changes that the script intends — Curilla strips
out of armour for a bath scene — are handled by reset_for,
which clears the previous snapshot for the character so
the next shot is treated as a fresh starting point rather
than a discrepancy from the old.

Public surface
--------------
    Severity enum
    Snapshot dataclass (frozen)
    ContinuityIssue dataclass (frozen)
    ContinuityReport dataclass (frozen)
    ContinuitySupervisor
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Severity(enum.Enum):
    NOTE = "note"          # cosmetic
    WARNING = "warning"    # audience-visible
    ERROR = "error"        # breaks scene logic


@dataclasses.dataclass(frozen=True)
class Snapshot:
    shot_id: str
    scene_id: str
    character_id: str
    wardrobe: tuple[str, ...] = ()
    props_in_hand: tuple[str, ...] = ()
    blood_on_face_locations: tuple[str, ...] = ()
    weather: str = ""
    time_of_day: str = ""
    hair_state: str = "clean"          # clean|messy|wet|bloodied
    wounds: tuple[str, ...] = ()
    accessories: tuple[str, ...] = ()
    camera_position: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclasses.dataclass(frozen=True)
class ContinuityIssue:
    shot_a: str
    shot_b: str
    character_id: str
    field: str
    detail: str
    severity: Severity


@dataclasses.dataclass(frozen=True)
class ContinuityReport:
    sequence_id: str
    issues: tuple[ContinuityIssue, ...]

    @property
    def worst_severity(self) -> t.Optional[Severity]:
        if not self.issues:
            return None
        order = {
            Severity.NOTE: 0,
            Severity.WARNING: 1,
            Severity.ERROR: 2,
        }
        return max(self.issues, key=lambda i: order[i.severity]).severity


_VALID_HAIR = ("clean", "messy", "wet", "bloodied")


def _diff_set(a: tuple[str, ...], b: tuple[str, ...]) -> tuple[
    tuple[str, ...], tuple[str, ...],
]:
    """Returns (added_in_b, removed_from_a)."""
    sa, sb = set(a), set(b)
    return tuple(sorted(sb - sa)), tuple(sorted(sa - sb))


def _wardrobe_changed(
    a: tuple[str, ...], b: tuple[str, ...],
) -> bool:
    return tuple(a) != tuple(b)


@dataclasses.dataclass
class ContinuitySupervisor:
    """In-memory script-supervisor."""
    _snapshots: dict[tuple[str, str], Snapshot] = dataclasses.field(
        default_factory=dict,
    )
    # (sequence_id) -> list of issues observed
    _logs: dict[str, list[ContinuityIssue]] = dataclasses.field(
        default_factory=dict,
    )

    def register_snapshot(self, snap: Snapshot) -> Snapshot:
        if not snap.shot_id:
            raise ValueError("shot_id required")
        if not snap.character_id:
            raise ValueError("character_id required")
        if snap.hair_state not in _VALID_HAIR:
            raise ValueError(
                f"hair_state must be one of {_VALID_HAIR}, got "
                f"{snap.hair_state!r}",
            )
        key = (snap.shot_id, snap.character_id)
        if key in self._snapshots:
            raise ValueError(
                f"snapshot already registered for "
                f"({snap.shot_id}, {snap.character_id})",
            )
        self._snapshots[key] = snap
        return snap

    def lookup(
        self, shot_id: str, character_id: str,
    ) -> Snapshot:
        key = (shot_id, character_id)
        if key not in self._snapshots:
            raise KeyError(
                f"no snapshot for ({shot_id}, {character_id})",
            )
        return self._snapshots[key]

    def check_continuity(
        self, shot_id_a: str, shot_id_b: str, character_id: str,
    ) -> tuple[ContinuityIssue, ...]:
        a = self.lookup(shot_id_a, character_id)
        b = self.lookup(shot_id_b, character_id)
        issues: list[ContinuityIssue] = []
        # Wardrobe — order matters; a re-order is also a flag.
        if _wardrobe_changed(a.wardrobe, b.wardrobe):
            added, removed = _diff_set(a.wardrobe, b.wardrobe)
            detail_parts = []
            if added:
                detail_parts.append(f"added {list(added)}")
            if removed:
                detail_parts.append(f"removed {list(removed)}")
            if not detail_parts:
                detail_parts.append(
                    f"reordered {list(a.wardrobe)} -> "
                    f"{list(b.wardrobe)}",
                )
            issues.append(
                ContinuityIssue(
                    shot_a=shot_id_a, shot_b=shot_id_b,
                    character_id=character_id,
                    field="wardrobe",
                    detail="; ".join(detail_parts),
                    severity=Severity.WARNING,
                ),
            )
        # Props — appearing or disappearing without reason.
        added, removed = _diff_set(a.props_in_hand, b.props_in_hand)
        if added:
            issues.append(
                ContinuityIssue(
                    shot_a=shot_id_a, shot_b=shot_id_b,
                    character_id=character_id,
                    field="props_in_hand",
                    detail=f"appeared from nowhere: {list(added)}",
                    severity=Severity.ERROR,
                ),
            )
        if removed:
            issues.append(
                ContinuityIssue(
                    shot_a=shot_id_a, shot_b=shot_id_b,
                    character_id=character_id,
                    field="props_in_hand",
                    detail=f"vanished: {list(removed)}",
                    severity=Severity.ERROR,
                ),
            )
        # Blood — appearing/disappearing on face.
        added_b, removed_b = _diff_set(
            a.blood_on_face_locations, b.blood_on_face_locations,
        )
        if added_b:
            issues.append(
                ContinuityIssue(
                    shot_a=shot_id_a, shot_b=shot_id_b,
                    character_id=character_id,
                    field="blood_on_face",
                    detail=f"appeared on {list(added_b)}",
                    severity=Severity.WARNING,
                ),
            )
        if removed_b:
            issues.append(
                ContinuityIssue(
                    shot_a=shot_id_a, shot_b=shot_id_b,
                    character_id=character_id,
                    field="blood_on_face",
                    detail=f"disappeared from {list(removed_b)}",
                    severity=Severity.WARNING,
                ),
            )
        # Hair state — clean to bloodied without combat is weird.
        if a.hair_state != b.hair_state:
            sev = Severity.NOTE
            if (
                a.hair_state == "clean" and b.hair_state == "bloodied"
            ):
                sev = Severity.WARNING
            issues.append(
                ContinuityIssue(
                    shot_a=shot_id_a, shot_b=shot_id_b,
                    character_id=character_id,
                    field="hair_state",
                    detail=f"{a.hair_state} -> {b.hair_state}",
                    severity=sev,
                ),
            )
        # Wounds — disappearing wounds are an error; new wounds are
        # warnings (could be off-screen action).
        added_w, removed_w = _diff_set(a.wounds, b.wounds)
        if added_w:
            issues.append(
                ContinuityIssue(
                    shot_a=shot_id_a, shot_b=shot_id_b,
                    character_id=character_id,
                    field="wounds",
                    detail=f"new wound: {list(added_w)}",
                    severity=Severity.WARNING,
                ),
            )
        if removed_w:
            issues.append(
                ContinuityIssue(
                    shot_a=shot_id_a, shot_b=shot_id_b,
                    character_id=character_id,
                    field="wounds",
                    detail=f"healed wound: {list(removed_w)}",
                    severity=Severity.ERROR,
                ),
            )
        # Accessories — necklaces, scars, tattoos, rings.
        added_a, removed_a = _diff_set(a.accessories, b.accessories)
        if added_a or removed_a:
            issues.append(
                ContinuityIssue(
                    shot_a=shot_id_a, shot_b=shot_id_b,
                    character_id=character_id,
                    field="accessories",
                    detail=(
                        f"+{list(added_a)} -{list(removed_a)}"
                    ),
                    severity=Severity.NOTE,
                ),
            )
        # Weather / time-of-day — environmental shifts are warnings
        # because the audience will see them through windows.
        if a.weather and b.weather and a.weather != b.weather:
            issues.append(
                ContinuityIssue(
                    shot_a=shot_id_a, shot_b=shot_id_b,
                    character_id=character_id,
                    field="weather",
                    detail=f"{a.weather} -> {b.weather}",
                    severity=Severity.WARNING,
                ),
            )
        if (
            a.time_of_day and b.time_of_day
            and a.time_of_day != b.time_of_day
        ):
            issues.append(
                ContinuityIssue(
                    shot_a=shot_id_a, shot_b=shot_id_b,
                    character_id=character_id,
                    field="time_of_day",
                    detail=f"{a.time_of_day} -> {b.time_of_day}",
                    severity=Severity.WARNING,
                ),
            )
        return tuple(issues)

    def reset_for(
        self, scene_id: str, character_id: str,
    ) -> int:
        """Clear all snapshots for character in this scene.

        Use when the script intends a costume change, a
        bandaging beat, etc. Returns the number of cleared
        snapshots.
        """
        keys_to_drop = [
            k for k, snap in self._snapshots.items()
            if snap.scene_id == scene_id
            and snap.character_id == character_id
        ]
        for k in keys_to_drop:
            del self._snapshots[k]
        return len(keys_to_drop)

    def log_for(
        self, sequence_id: str,
        issues: t.Sequence[ContinuityIssue],
    ) -> None:
        self._logs.setdefault(sequence_id, []).extend(issues)

    def report_for(self, sequence_id: str) -> ContinuityReport:
        return ContinuityReport(
            sequence_id=sequence_id,
            issues=tuple(self._logs.get(sequence_id, ())),
        )

    def worst_severity_in(
        self, sequence_id: str,
    ) -> t.Optional[Severity]:
        return self.report_for(sequence_id).worst_severity

    def export_pdf_stub(
        self, sequence_id: str,
    ) -> dict[str, t.Any]:
        """Stub manifest for a PDF report. Real PDF rendering
        lives in the ftrack/Kitsu/Frame.io plugin."""
        rep = self.report_for(sequence_id)
        return {
            "format": "pdf",
            "sequence_id": sequence_id,
            "issue_count": len(rep.issues),
            "by_severity": {
                "note": sum(
                    1 for i in rep.issues
                    if i.severity == Severity.NOTE
                ),
                "warning": sum(
                    1 for i in rep.issues
                    if i.severity == Severity.WARNING
                ),
                "error": sum(
                    1 for i in rep.issues
                    if i.severity == Severity.ERROR
                ),
            },
            "title": (
                f"Continuity report — sequence {sequence_id}"
            ),
        }

    def all_snapshots(self) -> tuple[Snapshot, ...]:
        return tuple(self._snapshots.values())

    def snapshots_for_character(
        self, character_id: str,
    ) -> tuple[Snapshot, ...]:
        return tuple(
            s for s in self._snapshots.values()
            if s.character_id == character_id
        )


__all__ = [
    "Severity",
    "Snapshot", "ContinuityIssue", "ContinuityReport",
    "ContinuitySupervisor",
]
