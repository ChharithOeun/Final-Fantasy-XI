"""Animation retargeting — mocap → FFXI race skeletons.

Body mocap from Rokoko, OptiTrack Prime, Mixamo, or
MetaHuman default lands on a generic-human skeleton. FFXI's
five races have wildly different proportions: galka
shoulders +30 %, mithra hip sway +20 %, taru head 1.6× and
arms 0.7×, elvaan +15 % height, mithra +tail bones. We
can't just bind clips to those skeletons; the captures
have to be *retargeted* — bone-by-bone, with per-target
scale + rotation offset.

This module models the retarget table. ``RetargetMap`` is
a tuple of ``BoneMapping`` rows, one per source bone, each
naming a target bone, a scale, and a rotation offset
quaternion. ``retarget_clip(clip_uri, source, target)``
returns a stub URI for the retargeted clip. The actual
retargeting math is delegated to UE5 IK Rig + Cascadeur
free tier in production; this module is the catalog +
validator.

Body skeletons can't be retargeted to face skeletons (and
vice versa). ``validate_retarget`` catches that case and
also enforces that all the target's mandatory bones are
present in the registered map.

IK rules: foot-locking + ground-snapping (the standard pair)
plus hand-prop attachment sockets (smith holds hammer at
``HAND_R_PROP``, vendor holds scroll at ``HAND_L_PROP``).

Public surface
--------------
    SourceSkeleton enum
    TargetSkeleton enum
    SkeletonKind enum
    BoneMapping dataclass (frozen)
    RetargetMap dataclass (frozen)
    PropKind enum
    RetargetingSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SkeletonKind(enum.Enum):
    BODY = "body"
    FACE = "face"


class SourceSkeleton(enum.Enum):
    LIVE_LINK_FACE_52 = "live_link_face_52"  # ARKit blends
    ROKOKO_BODY_82 = "rokoko_body_82"
    OPTITRACK_PRIME = "optitrack_prime"
    MIXAMO_STANDARD = "mixamo_standard"
    METAHUMAN_DEFAULT = "metahuman_default"
    FFXI_RETAIL_HUMAN = "ffxi_retail_human"


class TargetSkeleton(enum.Enum):
    FFXI_HUME_M = "ffxi_hume_m"
    FFXI_HUME_F = "ffxi_hume_f"
    FFXI_ELVAAN_M = "ffxi_elvaan_m"
    FFXI_ELVAAN_F = "ffxi_elvaan_f"
    FFXI_TARUTARU_M = "ffxi_tarutaru_m"
    FFXI_TARUTARU_F = "ffxi_tarutaru_f"
    FFXI_MITHRA = "ffxi_mithra"
    FFXI_GALKA = "ffxi_galka"


_SOURCE_KIND: dict[SourceSkeleton, SkeletonKind] = {
    SourceSkeleton.LIVE_LINK_FACE_52: SkeletonKind.FACE,
    SourceSkeleton.ROKOKO_BODY_82: SkeletonKind.BODY,
    SourceSkeleton.OPTITRACK_PRIME: SkeletonKind.BODY,
    SourceSkeleton.MIXAMO_STANDARD: SkeletonKind.BODY,
    SourceSkeleton.METAHUMAN_DEFAULT: SkeletonKind.BODY,
    SourceSkeleton.FFXI_RETAIL_HUMAN: SkeletonKind.BODY,
}


# Target adjustments — the scale_offsets table. Used as the
# default scale for the spine/limbs of each race's body
# skeleton when retargeting from a generic human.
_RACE_SCALE: dict[
    TargetSkeleton, dict[str, float],
] = {
    TargetSkeleton.FFXI_HUME_M: {
        "shoulder_l": 1.0, "shoulder_r": 1.0,
        "hip": 1.0, "head": 1.0,
        "arm": 1.0, "spine": 1.0,
    },
    TargetSkeleton.FFXI_HUME_F: {
        "shoulder_l": 0.95, "shoulder_r": 0.95,
        "hip": 1.05, "head": 1.0,
        "arm": 0.97, "spine": 0.98,
    },
    TargetSkeleton.FFXI_ELVAAN_M: {
        "shoulder_l": 1.05, "shoulder_r": 1.05,
        "hip": 1.0, "head": 0.95,
        "arm": 1.1, "spine": 1.15,
    },
    TargetSkeleton.FFXI_ELVAAN_F: {
        "shoulder_l": 1.0, "shoulder_r": 1.0,
        "hip": 1.05, "head": 0.95,
        "arm": 1.1, "spine": 1.15,
    },
    TargetSkeleton.FFXI_TARUTARU_M: {
        "shoulder_l": 0.7, "shoulder_r": 0.7,
        "hip": 0.7, "head": 1.6,
        "arm": 0.7, "spine": 0.65,
    },
    TargetSkeleton.FFXI_TARUTARU_F: {
        "shoulder_l": 0.7, "shoulder_r": 0.7,
        "hip": 0.7, "head": 1.6,
        "arm": 0.7, "spine": 0.65,
    },
    TargetSkeleton.FFXI_MITHRA: {
        "shoulder_l": 0.95, "shoulder_r": 0.95,
        "hip": 1.20, "head": 1.0,
        "arm": 1.0, "spine": 1.0,
        "tail_root": 1.0, "tail_mid": 1.0, "tail_tip": 1.0,
    },
    TargetSkeleton.FFXI_GALKA: {
        "shoulder_l": 1.30, "shoulder_r": 1.30,
        "hip": 1.10, "head": 1.05,
        "arm": 1.20, "spine": 1.10,
    },
}


# Mandatory bones for body targets.
_BODY_MANDATORY: frozenset[str] = frozenset({
    "root",
    "spine",
    "neck",
    "head",
    "shoulder_l", "shoulder_r",
    "arm_l", "arm_r",
    "hand_l", "hand_r",
    "hip",
    "leg_l", "leg_r",
    "foot_l", "foot_r",
})


# Targets that require additional bones.
_EXTRA_BONES: dict[TargetSkeleton, frozenset[str]] = {
    TargetSkeleton.FFXI_MITHRA: frozenset({
        "tail_root", "tail_mid", "tail_tip",
    }),
}


_FACE_MANDATORY: frozenset[str] = frozenset({
    "jaw_open", "mouth_smile_l", "mouth_smile_r",
    "brow_inner_up", "eye_blink_l", "eye_blink_r",
})


class PropKind(enum.Enum):
    HAMMER = "hammer"
    SCROLL = "scroll"
    SWORD = "sword"
    STAFF = "staff"
    LANTERN = "lantern"
    CUP = "cup"
    BOOK = "book"
    BOW = "bow"


_PROP_SOCKET: dict[PropKind, str] = {
    PropKind.HAMMER: "HAND_R_PROP",
    PropKind.SCROLL: "HAND_L_PROP",
    PropKind.SWORD: "HAND_R_PROP",
    PropKind.STAFF: "HAND_R_PROP",
    PropKind.LANTERN: "HAND_L_PROP",
    PropKind.CUP: "HAND_R_PROP",
    PropKind.BOOK: "HAND_L_PROP",
    PropKind.BOW: "HAND_L_PROP",
}


@dataclasses.dataclass(frozen=True)
class BoneMapping:
    source_bone: str
    target_bone: str
    scale_factor: float = 1.0
    rotation_offset_quat: tuple[
        float, float, float, float,
    ] = (0.0, 0.0, 0.0, 1.0)


@dataclasses.dataclass(frozen=True)
class RetargetMap:
    source: SourceSkeleton
    target: TargetSkeleton
    mappings: tuple[BoneMapping, ...]

    def target_bones(self) -> frozenset[str]:
        return frozenset(m.target_bone for m in self.mappings)


@dataclasses.dataclass
class RetargetingSystem:
    _registered_sources: set[SourceSkeleton] = (
        dataclasses.field(default_factory=set)
    )
    _registered_targets: set[TargetSkeleton] = (
        dataclasses.field(default_factory=set)
    )
    _maps: dict[
        tuple[SourceSkeleton, TargetSkeleton],
        RetargetMap,
    ] = dataclasses.field(default_factory=dict)
    _foot_lock_enabled: dict[TargetSkeleton, bool] = (
        dataclasses.field(default_factory=dict)
    )

    def register_skeleton(
        self,
        source: SourceSkeleton | None = None,
        target: TargetSkeleton | None = None,
    ) -> None:
        if source is not None:
            self._registered_sources.add(source)
        if target is not None:
            self._registered_targets.add(target)
            # Foot-lock on by default for all body targets.
            self._foot_lock_enabled.setdefault(target, True)

    def known_source(self, source: SourceSkeleton) -> bool:
        return source in self._registered_sources

    def known_target(self, target: TargetSkeleton) -> bool:
        return target in self._registered_targets

    def kind_of(self, source: SourceSkeleton) -> SkeletonKind:
        return _SOURCE_KIND[source]

    def register_retarget_map(
        self,
        source: SourceSkeleton,
        target: TargetSkeleton,
        mappings: tuple[BoneMapping, ...] | list[BoneMapping],
    ) -> RetargetMap:
        if _SOURCE_KIND[source] == SkeletonKind.FACE:
            # Faces can't retarget to body targets.
            raise ValueError(
                "face source cannot retarget to body target",
            )
        rm = RetargetMap(
            source=source,
            target=target,
            mappings=tuple(mappings),
        )
        self._maps[(source, target)] = rm
        self._registered_sources.add(source)
        self._registered_targets.add(target)
        self._foot_lock_enabled.setdefault(target, True)
        return rm

    def get_map(
        self,
        source: SourceSkeleton,
        target: TargetSkeleton,
    ) -> RetargetMap:
        key = (source, target)
        if key not in self._maps:
            raise KeyError(
                f"no map: {source} -> {target}",
            )
        return self._maps[key]

    def has_map(
        self,
        source: SourceSkeleton,
        target: TargetSkeleton,
    ) -> bool:
        return (source, target) in self._maps

    def mandatory_bones_for(
        self, target: TargetSkeleton,
    ) -> frozenset[str]:
        return _BODY_MANDATORY | _EXTRA_BONES.get(
            target, frozenset(),
        )

    def validate_retarget(
        self,
        source: SourceSkeleton,
        target: TargetSkeleton,
    ) -> bool:
        """True iff a valid map exists between source and
        target. Raises ValueError on incompatibility (e.g.
        body source to a registered face context). Raises
        ValueError if mandatory bones are missing in the
        retarget map."""
        # Face-source rejected.
        if _SOURCE_KIND[source] == SkeletonKind.FACE:
            raise ValueError(
                "face source cannot retarget to body target",
            )
        if not self.has_map(source, target):
            raise ValueError(
                f"no retarget map: {source} -> {target}",
            )
        rm = self.get_map(source, target)
        required = self.mandatory_bones_for(target)
        present = rm.target_bones()
        missing = required - present
        if missing:
            raise ValueError(
                "missing mandatory target bones: "
                + ", ".join(sorted(missing))
            )
        return True

    def retarget_clip(
        self,
        clip_uri: str,
        source: SourceSkeleton,
        target: TargetSkeleton,
    ) -> str:
        """Returns a stub URI for the retargeted clip. Real
        engine produces a binary; here we return the
        deterministic naming scheme."""
        if not clip_uri:
            raise ValueError("clip_uri required")
        if _SOURCE_KIND[source] == SkeletonKind.FACE:
            raise ValueError(
                "face source cannot retarget to body target",
            )
        if not self.has_map(source, target):
            raise ValueError(
                f"no retarget map: {source} -> {target}",
            )
        return (
            f"retarget://{source.value}->{target.value}/"
            f"{clip_uri}"
        )

    # ---- IK ----

    def foot_lock_for(
        self, target: TargetSkeleton,
    ) -> bool:
        return self._foot_lock_enabled.get(target, True)

    def set_foot_lock(
        self, target: TargetSkeleton, enabled: bool,
    ) -> None:
        self._foot_lock_enabled[target] = enabled

    def prop_attachment_socket(
        self,
        target: TargetSkeleton,
        prop_kind: PropKind,
    ) -> str:
        if target not in self._registered_targets:
            self.register_skeleton(target=target)
        if prop_kind not in _PROP_SOCKET:
            raise ValueError(
                f"no socket mapping for prop: {prop_kind}",
            )
        return _PROP_SOCKET[prop_kind]

    # ---- introspection ----

    def race_scale_table(
        self, target: TargetSkeleton,
    ) -> dict[str, float]:
        if target not in _RACE_SCALE:
            raise KeyError(f"no scale table: {target}")
        return dict(_RACE_SCALE[target])

    def all_targets(self) -> tuple[TargetSkeleton, ...]:
        return tuple(
            sorted(
                self._registered_targets,
                key=lambda t_: t_.value,
            )
        )

    def all_sources(self) -> tuple[SourceSkeleton, ...]:
        return tuple(
            sorted(
                self._registered_sources,
                key=lambda s: s.value,
            )
        )


def standard_body_mappings(
    target: TargetSkeleton,
) -> tuple[BoneMapping, ...]:
    """Build a standard mapping list that covers all
    mandatory bones for the given target, using the
    per-race scale table where it has an entry."""
    scales = _RACE_SCALE.get(target, {})
    mappings: list[BoneMapping] = []
    bones = sorted(
        _BODY_MANDATORY | _EXTRA_BONES.get(
            target, frozenset(),
        )
    )
    for bone in bones:
        # Pick scale: try exact match, then a stem match
        # (arm_l -> arm), default 1.0.
        if bone in scales:
            sc = scales[bone]
        else:
            stem = bone.split("_")[0]
            sc = scales.get(stem, 1.0)
        mappings.append(BoneMapping(
            source_bone=bone,
            target_bone=bone,
            scale_factor=sc,
        ))
    return tuple(mappings)


__all__ = [
    "SkeletonKind",
    "SourceSkeleton",
    "TargetSkeleton",
    "BoneMapping",
    "RetargetMap",
    "PropKind",
    "RetargetingSystem",
    "standard_body_mappings",
]
