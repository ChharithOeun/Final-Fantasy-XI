"""Strategy publisher — mentor-gated fight strategy guides.

GearSwap publishing solved "share your gear setup". This
solves "share your fight plan". A player who beat Maat
or downed Aerial Manta writes up the strategy: what to
position where, when to use 2-hours, which mechanics
require interrupts. Other players who haven't done that
fight yet can adopt the guide and have it pin in their
encounter UI.

Eligibility mirrors the GS publisher: must be a mentor
flag, must have actually CLEARED the encounter at least
N times (so newcomers can't publish "I think this works"
guides). The clear-count gate is parameterized via
ClearProof, which the caller supplies from their
combat-log audit trail.

EncounterRefs cover all the FFXI fight types we already
have modules for:
    NM            -> notorious_monsters
    HTBC          -> high_tier_battlefields
    INSTANCE      -> instance_engine (Limbus/Einherjar/Sortie/etc)
    MISSION       -> missions (CoP boss fights etc)
    REIVE         -> wildskeeper_reives / domain_invasion

Status mirrors GS publisher's lifecycle (DRAFT/PUBLISHED/
UNLISTED/REVOKED) — REVOKED is terminal.

Public surface
--------------
    EncounterKind enum
    GuideStatus enum
    EncounterRef dataclass (frozen)
    ClearProof dataclass (frozen)   - clears count + win rate
    PublishedGuide dataclass (frozen)
    PublishEligibility dataclass (frozen)
    StrategyPublisher
        .set_mentor_status(...)  - mirrors GS publisher
        .check_eligibility(author_id, encounter,
                           clear_proof) -> PublishEligibility
        .publish(...) -> Optional[str]   # guide_id
        .lookup(guide_id) -> Optional[PublishedGuide]
        .by_author(author_id) -> list[PublishedGuide]
        .by_encounter(encounter) -> list[PublishedGuide]
        .unlist(author_id, guide_id) -> bool
        .relist(author_id, guide_id) -> bool
        .revoke(guide_id, reason) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import hashlib
import typing as t


_MIN_CLEARS_TO_PUBLISH = 3
_MIN_WIN_RATE = 0.5


class EncounterKind(str, enum.Enum):
    NM = "nm"
    HTBC = "htbc"
    INSTANCE = "instance"
    MISSION = "mission"
    REIVE = "reive"


class GuideStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    UNLISTED = "unlisted"
    REVOKED = "revoked"


@dataclasses.dataclass(frozen=True)
class EncounterRef:
    kind: EncounterKind
    encounter_id: str   # NM_id, htbc_id, instance key, etc.
    display_name: str   # "Aerial Manta", "Maat (HTBC)"


@dataclasses.dataclass(frozen=True)
class ClearProof:
    clears_count: int
    wins_count: int

    @property
    def win_rate(self) -> float:
        return (
            self.wins_count / self.clears_count
            if self.clears_count else 0.0
        )


@dataclasses.dataclass(frozen=True)
class PublishEligibility:
    eligible: bool
    is_mentor: bool
    clears_seen: int
    win_rate_seen: float
    failure_reason: str


@dataclasses.dataclass(frozen=True)
class PublishedGuide:
    guide_id: str
    author_id: str
    author_display_name: str
    encounter: EncounterRef
    title: str
    body: str
    content_hash: str
    clears_at_publish: int
    win_rate_at_publish: float
    published_at: int
    status: GuideStatus
    revoke_reason: str


def _content_hash(title: str, body: str) -> str:
    return hashlib.sha256(
        (title + "\n" + body).encode("utf-8"),
    ).hexdigest()


@dataclasses.dataclass
class StrategyPublisher:
    _guides: dict[str, PublishedGuide] = dataclasses.field(
        default_factory=dict,
    )
    _by_author: dict[str, set[str]] = dataclasses.field(
        default_factory=dict,
    )
    _mentor_flags: dict[str, bool] = dataclasses.field(
        default_factory=dict,
    )
    _display_names: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )
    _next_seq: int = 1

    def set_mentor_status(
        self, *, author_id: str, is_mentor: bool,
        display_name: str = "",
    ) -> bool:
        if not author_id:
            return False
        self._mentor_flags[author_id] = is_mentor
        if display_name:
            self._display_names[author_id] = display_name
        return True

    def check_eligibility(
        self, *, author_id: str, encounter: EncounterRef,
        clear_proof: ClearProof,
    ) -> PublishEligibility:
        if not author_id:
            return PublishEligibility(
                eligible=False, is_mentor=False,
                clears_seen=0, win_rate_seen=0.0,
                failure_reason="author_id_required",
            )
        if not encounter.encounter_id:
            return PublishEligibility(
                eligible=False, is_mentor=False,
                clears_seen=clear_proof.clears_count,
                win_rate_seen=clear_proof.win_rate,
                failure_reason="encounter_required",
            )
        is_mentor = self._mentor_flags.get(author_id, False)
        if not is_mentor:
            return PublishEligibility(
                eligible=False, is_mentor=False,
                clears_seen=clear_proof.clears_count,
                win_rate_seen=clear_proof.win_rate,
                failure_reason="not_mentor",
            )
        if clear_proof.clears_count < _MIN_CLEARS_TO_PUBLISH:
            return PublishEligibility(
                eligible=False, is_mentor=True,
                clears_seen=clear_proof.clears_count,
                win_rate_seen=clear_proof.win_rate,
                failure_reason="insufficient_clears",
            )
        if clear_proof.win_rate < _MIN_WIN_RATE:
            return PublishEligibility(
                eligible=False, is_mentor=True,
                clears_seen=clear_proof.clears_count,
                win_rate_seen=clear_proof.win_rate,
                failure_reason="win_rate_too_low",
            )
        return PublishEligibility(
            eligible=True, is_mentor=True,
            clears_seen=clear_proof.clears_count,
            win_rate_seen=clear_proof.win_rate,
            failure_reason="",
        )

    def publish(
        self, *, author_id: str, encounter: EncounterRef,
        title: str, body: str,
        clear_proof: ClearProof, published_at: int,
    ) -> t.Optional[str]:
        if not title.strip() or not body.strip():
            return None
        elig = self.check_eligibility(
            author_id=author_id, encounter=encounter,
            clear_proof=clear_proof,
        )
        if not elig.eligible:
            return None
        gid = f"sg_{self._next_seq}"
        self._next_seq += 1
        guide = PublishedGuide(
            guide_id=gid, author_id=author_id,
            author_display_name=self._display_names.get(
                author_id, author_id,
            ),
            encounter=encounter, title=title.strip(),
            body=body.strip(),
            content_hash=_content_hash(title, body),
            clears_at_publish=clear_proof.clears_count,
            win_rate_at_publish=clear_proof.win_rate,
            published_at=published_at,
            status=GuideStatus.PUBLISHED,
            revoke_reason="",
        )
        self._guides[gid] = guide
        self._by_author.setdefault(
            author_id, set(),
        ).add(gid)
        return gid

    def lookup(
        self, *, guide_id: str,
    ) -> t.Optional[PublishedGuide]:
        return self._guides.get(guide_id)

    def by_author(
        self, *, author_id: str,
    ) -> list[PublishedGuide]:
        return [
            self._guides[gid]
            for gid in self._by_author.get(author_id, set())
        ]

    def by_encounter(
        self, *, encounter: EncounterRef,
    ) -> list[PublishedGuide]:
        return [
            g for g in self._guides.values()
            if g.encounter.kind == encounter.kind
            and g.encounter.encounter_id == encounter.encounter_id
            and g.status == GuideStatus.PUBLISHED
        ]

    def unlist(
        self, *, author_id: str, guide_id: str,
    ) -> bool:
        g = self._guides.get(guide_id)
        if g is None or g.author_id != author_id:
            return False
        if g.status == GuideStatus.REVOKED:
            return False
        self._guides[guide_id] = dataclasses.replace(
            g, status=GuideStatus.UNLISTED,
        )
        return True

    def relist(
        self, *, author_id: str, guide_id: str,
    ) -> bool:
        g = self._guides.get(guide_id)
        if g is None or g.author_id != author_id:
            return False
        if g.status != GuideStatus.UNLISTED:
            return False
        self._guides[guide_id] = dataclasses.replace(
            g, status=GuideStatus.PUBLISHED,
        )
        return True

    def revoke(
        self, *, guide_id: str, reason: str,
    ) -> bool:
        if not reason.strip():
            return False
        g = self._guides.get(guide_id)
        if g is None:
            return False
        self._guides[guide_id] = dataclasses.replace(
            g, status=GuideStatus.REVOKED,
            revoke_reason=reason.strip(),
        )
        return True

    def total_published(self) -> int:
        return sum(
            1 for g in self._guides.values()
            if g.status == GuideStatus.PUBLISHED
        )

    def total_entries(self) -> int:
        return len(self._guides)


__all__ = [
    "EncounterKind", "GuideStatus", "EncounterRef",
    "ClearProof", "PublishEligibility", "PublishedGuide",
    "StrategyPublisher",
]
