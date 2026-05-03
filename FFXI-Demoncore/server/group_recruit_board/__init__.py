"""Group recruit board — LFG with role, level, objective.

Players post LFG ads to a board listing the role slots they
need (TANK / HEALER / DPS / SUPPORT / FREE_SLOT), the level
range, the objective tag (XP / NM / MISSION / CRAFT / EXPLORE
/ RESCUE), and an expiry. Other players browse, filter, and
APPLY. The poster ACCEPTS or REJECTS applicants. On accept,
the applicant slots into one of the open role pegs; when all
slots fill, the post auto-closes.

Public surface
--------------
    RoleSlot enum
    ObjectiveTag enum
    PostStatus enum
    LFGPost dataclass
    LFGApplication dataclass
    GroupRecruitBoard
        .post_listing(captain_id, slots, level_range,
                      objective, expires_at) -> LFGPost
        .browse(filter...) -> tuple[LFGPost]
        .apply_to(applicant_id, post_id, role_slot, level)
        .accept(post_id, application_id)
        .reject(post_id, application_id)
        .close(post_id)
        .expire_check(now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default duration before a post auto-expires.
DEFAULT_POST_DURATION_SECONDS = 4 * 3600    # 4 hours
MAX_SLOTS_PER_POST = 5      # captain + 5 others = 6 party cap


class RoleSlot(str, enum.Enum):
    TANK = "tank"
    HEALER = "healer"
    DPS = "dps"
    SUPPORT = "support"
    FREE_SLOT = "free_slot"   # "any role"


class ObjectiveTag(str, enum.Enum):
    XP = "xp"
    NM = "nm"
    MISSION = "mission"
    CRAFT = "craft"
    EXPLORE = "explore"
    RESCUE = "rescue"
    PVP = "pvp"


class PostStatus(str, enum.Enum):
    OPEN = "open"
    FULL = "full"
    EXPIRED = "expired"
    CLOSED = "closed"


class ApplicationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclasses.dataclass
class LFGPost:
    post_id: str
    captain_id: str
    slots: dict[RoleSlot, t.Optional[str]]   # role -> applicant_id or None
    level_min: int
    level_max: int
    objective: ObjectiveTag
    posted_at_seconds: float = 0.0
    expires_at_seconds: float = 0.0
    status: PostStatus = PostStatus.OPEN
    note: str = ""


@dataclasses.dataclass
class LFGApplication:
    application_id: str
    post_id: str
    applicant_id: str
    requested_role: RoleSlot
    applicant_level: int
    status: ApplicationStatus = ApplicationStatus.PENDING


@dataclasses.dataclass(frozen=True)
class ApplyResult:
    accepted: bool
    application: t.Optional[LFGApplication] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class AcceptResult:
    accepted: bool
    application: t.Optional[LFGApplication] = None
    post_full: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class GroupRecruitBoard:
    default_duration_seconds: float = DEFAULT_POST_DURATION_SECONDS
    _posts: dict[str, LFGPost] = dataclasses.field(
        default_factory=dict,
    )
    _applications: dict[str, LFGApplication] = dataclasses.field(
        default_factory=dict,
    )
    _next_post_id: int = 0
    _next_app_id: int = 0

    def post_listing(
        self, *, captain_id: str,
        slots: tuple[RoleSlot, ...],
        level_min: int, level_max: int,
        objective: ObjectiveTag,
        posted_at_seconds: float = 0.0,
        expires_at_seconds: t.Optional[float] = None,
        note: str = "",
    ) -> t.Optional[LFGPost]:
        if not slots or len(slots) > MAX_SLOTS_PER_POST:
            return None
        if level_min < 1 or level_max < level_min:
            return None
        # One open post per captain
        for p in self._posts.values():
            if (
                p.captain_id == captain_id
                and p.status == PostStatus.OPEN
            ):
                return None
        pid = f"lfg_{self._next_post_id}"
        self._next_post_id += 1
        # Build slots map keyed by role; same role can appear
        # multiple times, in which case we suffix indexes
        slot_map: dict[RoleSlot, t.Optional[str]] = {}
        for idx, role in enumerate(slots):
            # Allow duplicate keys by indexing the role enum to
            # distinct sub-slots — track count externally.
            # Simpler: duplicate roles use the FREE_SLOT bucket
            # for collisions; this is a recruiting tool, not a
            # full party-builder.
            if role in slot_map:
                slot_map[RoleSlot.FREE_SLOT] = None
            else:
                slot_map[role] = None
        post = LFGPost(
            post_id=pid, captain_id=captain_id,
            slots=slot_map,
            level_min=level_min, level_max=level_max,
            objective=objective,
            posted_at_seconds=posted_at_seconds,
            expires_at_seconds=(
                expires_at_seconds
                if expires_at_seconds is not None
                else (
                    posted_at_seconds
                    + self.default_duration_seconds
                )
            ),
            note=note,
        )
        self._posts[pid] = post
        return post

    def get(self, post_id: str) -> t.Optional[LFGPost]:
        return self._posts.get(post_id)

    def browse(
        self, *,
        objective: t.Optional[ObjectiveTag] = None,
        role_open: t.Optional[RoleSlot] = None,
        level: t.Optional[int] = None,
    ) -> tuple[LFGPost, ...]:
        out: list[LFGPost] = []
        for p in self._posts.values():
            if p.status != PostStatus.OPEN:
                continue
            if objective is not None and p.objective != objective:
                continue
            if role_open is not None:
                free_match = (
                    p.slots.get(role_open) is None
                    and role_open in p.slots
                )
                if not free_match:
                    continue
            if level is not None:
                if level < p.level_min or level > p.level_max:
                    continue
            out.append(p)
        return tuple(out)

    def apply_to(
        self, *, applicant_id: str, post_id: str,
        requested_role: RoleSlot,
        applicant_level: int,
    ) -> ApplyResult:
        post = self._posts.get(post_id)
        if post is None or post.status != PostStatus.OPEN:
            return ApplyResult(
                False, reason="post not open",
            )
        if applicant_id == post.captain_id:
            return ApplyResult(
                False, reason="captain cannot apply",
            )
        if (
            applicant_level < post.level_min
            or applicant_level > post.level_max
        ):
            return ApplyResult(
                False, reason="level outside band",
            )
        if requested_role not in post.slots:
            return ApplyResult(
                False, reason="role not in post",
            )
        if post.slots[requested_role] is not None:
            return ApplyResult(
                False, reason="role already filled",
            )
        # No duplicate pending application from same applicant
        for app in self._applications.values():
            if (
                app.post_id == post_id
                and app.applicant_id == applicant_id
                and app.status == ApplicationStatus.PENDING
            ):
                return ApplyResult(
                    False, reason="already applied",
                )
        aid = f"app_{self._next_app_id}"
        self._next_app_id += 1
        app = LFGApplication(
            application_id=aid, post_id=post_id,
            applicant_id=applicant_id,
            requested_role=requested_role,
            applicant_level=applicant_level,
        )
        self._applications[aid] = app
        return ApplyResult(accepted=True, application=app)

    def accept(
        self, *, post_id: str, application_id: str,
    ) -> AcceptResult:
        post = self._posts.get(post_id)
        app = self._applications.get(application_id)
        if post is None or app is None:
            return AcceptResult(
                False, reason="unknown post or application",
            )
        if app.status != ApplicationStatus.PENDING:
            return AcceptResult(
                False, reason="application not pending",
            )
        if post.status != PostStatus.OPEN:
            return AcceptResult(
                False, reason="post not open",
            )
        if post.slots.get(app.requested_role) is not None:
            return AcceptResult(
                False, reason="role already filled",
            )
        post.slots[app.requested_role] = app.applicant_id
        app.status = ApplicationStatus.ACCEPTED
        # Check if all slots full
        full = all(v is not None for v in post.slots.values())
        if full:
            post.status = PostStatus.FULL
        return AcceptResult(
            accepted=True, application=app,
            post_full=full,
        )

    def reject(
        self, *, post_id: str, application_id: str,
    ) -> bool:
        app = self._applications.get(application_id)
        if app is None or app.post_id != post_id:
            return False
        if app.status != ApplicationStatus.PENDING:
            return False
        app.status = ApplicationStatus.REJECTED
        return True

    def close(
        self, *, post_id: str,
    ) -> bool:
        post = self._posts.get(post_id)
        if post is None:
            return False
        if post.status not in (
            PostStatus.OPEN, PostStatus.FULL,
        ):
            return False
        post.status = PostStatus.CLOSED
        return True

    def expire_check(
        self, *, now_seconds: float,
    ) -> tuple[str, ...]:
        expired: list[str] = []
        for p in self._posts.values():
            if p.status != PostStatus.OPEN:
                continue
            if now_seconds >= p.expires_at_seconds:
                p.status = PostStatus.EXPIRED
                expired.append(p.post_id)
        return tuple(expired)

    def total_posts(self) -> int:
        return len(self._posts)


__all__ = [
    "DEFAULT_POST_DURATION_SECONDS",
    "MAX_SLOTS_PER_POST",
    "RoleSlot", "ObjectiveTag",
    "PostStatus", "ApplicationStatus",
    "LFGPost", "LFGApplication",
    "ApplyResult", "AcceptResult",
    "GroupRecruitBoard",
]
