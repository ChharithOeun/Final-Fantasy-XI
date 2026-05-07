"""Recipe publisher — mentor-cook gated recipe sharing.

Third application of the publishing pattern. Cooks,
smiths, alchemists who've actually mastered a recipe
publish it with their tested mat list, crystal, sub-craft
requirements, and expected HQ rate. Other players adopt
and get the recipe pinned in their synthesis UI with the
projected cost from recipe_economics.

Eligibility mirrors the others but with a craft-specific
gate:
    - mentor flag
    - crafted this recipe ≥ 5 times in the last N days
    - HQ rate ≥ 10% (proves you actually have the
      sub-craft skill levels claimed; not someone who
      crit-HQ'd once and called it a day)

CraftDiscipline mirrors the existing crafting module's
7 disciplines (Cooking, Smithing, etc.) plus the Master
Synthesis pseudo-discipline.

Publish status uses the same 4-state lifecycle pattern.

Public surface
--------------
    CraftDiscipline enum
    RecipeStatus enum
    CraftProof dataclass (frozen)  - synth count + HQ rate
    PublishedRecipe dataclass (frozen)
    PublishEligibility dataclass (frozen)
    RecipePublisher
        .set_mentor_status(...)
        .check_eligibility(author_id, discipline,
                           craft_proof) -> PublishEligibility
        .publish(...) -> Optional[str]   # recipe_id
        .lookup(recipe_id) -> Optional[PublishedRecipe]
        .by_author(author_id) -> list[PublishedRecipe]
        .by_discipline(discipline) -> list[PublishedRecipe]
        .unlist(author_id, recipe_id) -> bool
        .relist(author_id, recipe_id) -> bool
        .revoke(recipe_id, reason) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import hashlib
import typing as t


_MIN_SYNTHS_TO_PUBLISH = 5
_MIN_HQ_RATE = 0.10


class CraftDiscipline(str, enum.Enum):
    COOKING = "cooking"
    SMITHING = "smithing"
    GOLDSMITHING = "goldsmithing"
    LEATHERCRAFT = "leathercraft"
    BONECRAFT = "bonecraft"
    ALCHEMY = "alchemy"
    CLOTHCRAFT = "clothcraft"
    MASTER_SYNTHESIS = "master_synthesis"


class RecipeStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    UNLISTED = "unlisted"
    REVOKED = "revoked"


@dataclasses.dataclass(frozen=True)
class CraftProof:
    synths_count: int
    hq_count: int

    @property
    def hq_rate(self) -> float:
        return (
            self.hq_count / self.synths_count
            if self.synths_count else 0.0
        )


@dataclasses.dataclass(frozen=True)
class PublishEligibility:
    eligible: bool
    is_mentor: bool
    synths_seen: int
    hq_rate_seen: float
    failure_reason: str


@dataclasses.dataclass(frozen=True)
class PublishedRecipe:
    recipe_id: str
    author_id: str
    author_display_name: str
    discipline: CraftDiscipline
    title: str
    crystal: str               # "fire crystal"
    materials: tuple[str, ...] # canonical mat list
    sub_craft_caps: tuple[tuple[str, int], ...]
                              # e.g. (("smithing", 25),)
    body: str                  # prose tips
    content_hash: str
    synths_at_publish: int
    hq_rate_at_publish: float
    published_at: int
    status: RecipeStatus
    revoke_reason: str


def _content_hash(
    title: str, materials: tuple[str, ...], body: str,
) -> str:
    payload = title + "\n" + "|".join(materials) + "\n" + body
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclasses.dataclass
class RecipePublisher:
    _recipes: dict[str, PublishedRecipe] = dataclasses.field(
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
        self, *, author_id: str,
        discipline: CraftDiscipline,
        craft_proof: CraftProof,
    ) -> PublishEligibility:
        if not author_id:
            return PublishEligibility(
                eligible=False, is_mentor=False,
                synths_seen=0, hq_rate_seen=0.0,
                failure_reason="author_id_required",
            )
        is_mentor = self._mentor_flags.get(author_id, False)
        if not is_mentor:
            return PublishEligibility(
                eligible=False, is_mentor=False,
                synths_seen=craft_proof.synths_count,
                hq_rate_seen=craft_proof.hq_rate,
                failure_reason="not_mentor",
            )
        if craft_proof.synths_count < _MIN_SYNTHS_TO_PUBLISH:
            return PublishEligibility(
                eligible=False, is_mentor=True,
                synths_seen=craft_proof.synths_count,
                hq_rate_seen=craft_proof.hq_rate,
                failure_reason="insufficient_synths",
            )
        if craft_proof.hq_rate < _MIN_HQ_RATE:
            return PublishEligibility(
                eligible=False, is_mentor=True,
                synths_seen=craft_proof.synths_count,
                hq_rate_seen=craft_proof.hq_rate,
                failure_reason="hq_rate_too_low",
            )
        return PublishEligibility(
            eligible=True, is_mentor=True,
            synths_seen=craft_proof.synths_count,
            hq_rate_seen=craft_proof.hq_rate,
            failure_reason="",
        )

    def publish(
        self, *, author_id: str,
        discipline: CraftDiscipline, title: str,
        crystal: str, materials: list[str],
        sub_craft_caps: list[tuple[str, int]],
        body: str, craft_proof: CraftProof,
        published_at: int,
    ) -> t.Optional[str]:
        if not title.strip() or not crystal.strip():
            return None
        if not materials or any(not m.strip() for m in materials):
            return None
        if len(materials) > 8:
            return None  # FFXI synthesis caps at 8 mats
        elig = self.check_eligibility(
            author_id=author_id, discipline=discipline,
            craft_proof=craft_proof,
        )
        if not elig.eligible:
            return None
        rid = f"rec_{self._next_seq}"
        self._next_seq += 1
        mats_t = tuple(materials)
        recipe = PublishedRecipe(
            recipe_id=rid, author_id=author_id,
            author_display_name=self._display_names.get(
                author_id, author_id,
            ),
            discipline=discipline, title=title.strip(),
            crystal=crystal.strip(),
            materials=mats_t,
            sub_craft_caps=tuple(sub_craft_caps),
            body=body.strip(),
            content_hash=_content_hash(
                title, mats_t, body,
            ),
            synths_at_publish=craft_proof.synths_count,
            hq_rate_at_publish=craft_proof.hq_rate,
            published_at=published_at,
            status=RecipeStatus.PUBLISHED,
            revoke_reason="",
        )
        self._recipes[rid] = recipe
        self._by_author.setdefault(
            author_id, set(),
        ).add(rid)
        return rid

    def lookup(
        self, *, recipe_id: str,
    ) -> t.Optional[PublishedRecipe]:
        return self._recipes.get(recipe_id)

    def by_author(
        self, *, author_id: str,
    ) -> list[PublishedRecipe]:
        return [
            self._recipes[rid]
            for rid in self._by_author.get(author_id, set())
        ]

    def by_discipline(
        self, *, discipline: CraftDiscipline,
    ) -> list[PublishedRecipe]:
        return [
            r for r in self._recipes.values()
            if r.discipline == discipline
            and r.status == RecipeStatus.PUBLISHED
        ]

    def unlist(
        self, *, author_id: str, recipe_id: str,
    ) -> bool:
        r = self._recipes.get(recipe_id)
        if r is None or r.author_id != author_id:
            return False
        if r.status == RecipeStatus.REVOKED:
            return False
        self._recipes[recipe_id] = dataclasses.replace(
            r, status=RecipeStatus.UNLISTED,
        )
        return True

    def relist(
        self, *, author_id: str, recipe_id: str,
    ) -> bool:
        r = self._recipes.get(recipe_id)
        if r is None or r.author_id != author_id:
            return False
        if r.status != RecipeStatus.UNLISTED:
            return False
        self._recipes[recipe_id] = dataclasses.replace(
            r, status=RecipeStatus.PUBLISHED,
        )
        return True

    def revoke(
        self, *, recipe_id: str, reason: str,
    ) -> bool:
        if not reason.strip():
            return False
        r = self._recipes.get(recipe_id)
        if r is None:
            return False
        self._recipes[recipe_id] = dataclasses.replace(
            r, status=RecipeStatus.REVOKED,
            revoke_reason=reason.strip(),
        )
        return True

    def total_published(self) -> int:
        return sum(
            1 for r in self._recipes.values()
            if r.status == RecipeStatus.PUBLISHED
        )

    def total_entries(self) -> int:
        return len(self._recipes)


__all__ = [
    "CraftDiscipline", "RecipeStatus", "CraftProof",
    "PublishEligibility", "PublishedRecipe",
    "RecipePublisher",
]
