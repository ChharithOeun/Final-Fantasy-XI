"""MetaHuman driver — FFXI NPC ↔ MetaHuman avatar mapping.

Demoncore drives Epic's MetaHuman framework via Live Link.
Each FFXI hero or PC archetype is bound to a MetaHuman
template (face blueprint + body skeleton variant + skin /
costume rig). When the world layer raises an emotion event
(HAPPY / ANGRY / AFRAID / SAD / SURPRISED / NEUTRAL), this
module converts it into an ARKit 52-blendshape weight set
that UE5's MetaHuman face control rig consumes.

Public surface
--------------
    Race enum
    Emotion enum
    AvatarBinding dataclass (frozen)
    AVATARS dict
    ARKIT_BLENDSHAPES tuple (the 52 ARKit names)
    MetaHumanDriver
    list_avatars, lookup
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Race(enum.Enum):
    HUME = "hume"
    ELVAAN = "elvaan"
    TARUTARU = "tarutaru"
    MITHRA = "mithra"
    GALKA = "galka"


class Emotion(enum.Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    ANGRY = "angry"
    AFRAID = "afraid"
    SAD = "sad"
    SURPRISED = "surprised"


# Apple ARKit 52 facial blendshape names (canonical order).
ARKIT_BLENDSHAPES: tuple[str, ...] = (
    "browDownLeft", "browDownRight",
    "browInnerUp",
    "browOuterUpLeft", "browOuterUpRight",
    "cheekPuff",
    "cheekSquintLeft", "cheekSquintRight",
    "eyeBlinkLeft", "eyeBlinkRight",
    "eyeLookDownLeft", "eyeLookDownRight",
    "eyeLookInLeft", "eyeLookInRight",
    "eyeLookOutLeft", "eyeLookOutRight",
    "eyeLookUpLeft", "eyeLookUpRight",
    "eyeSquintLeft", "eyeSquintRight",
    "eyeWideLeft", "eyeWideRight",
    "jawForward", "jawLeft", "jawOpen", "jawRight",
    "mouthClose",
    "mouthDimpleLeft", "mouthDimpleRight",
    "mouthFrownLeft", "mouthFrownRight",
    "mouthFunnel",
    "mouthLeft",
    "mouthLowerDownLeft", "mouthLowerDownRight",
    "mouthPressLeft", "mouthPressRight",
    "mouthPucker",
    "mouthRight",
    "mouthRollLower", "mouthRollUpper",
    "mouthShrugLower", "mouthShrugUpper",
    "mouthSmileLeft", "mouthSmileRight",
    "mouthStretchLeft", "mouthStretchRight",
    "mouthUpperUpLeft", "mouthUpperUpRight",
    "noseSneerLeft", "noseSneerRight",
    "tongueOut",
)
assert len(ARKIT_BLENDSHAPES) == 52, len(ARKIT_BLENDSHAPES)


# Allowed body skeleton variants per race (M/F).
_SKELETON_FOR_RACE: dict[Race, frozenset[str]] = {
    Race.HUME:     frozenset({"Hume_M", "Hume_F"}),
    Race.ELVAAN:   frozenset({"Elvaan_M", "Elvaan_F"}),
    Race.TARUTARU: frozenset({"TaruTaru_M", "TaruTaru_F"}),
    Race.MITHRA:   frozenset({"Mithra_F"}),  # female-only race
    Race.GALKA:    frozenset({"Galka_M"}),    # male-only race
}


@dataclasses.dataclass(frozen=True)
class AvatarBinding:
    ffxi_npc_id: str
    metahuman_template: str
    face_blueprint_id: str
    body_skeleton_variant: str
    skin_tone_id: str
    costume_rig_id: str
    race: Race


def _b(
    npc_id: str, *,
    template: str, face_bp: str, skel: str,
    skin: str, costume: str, race: Race,
) -> AvatarBinding:
    return AvatarBinding(
        ffxi_npc_id=npc_id,
        metahuman_template=template,
        face_blueprint_id=face_bp,
        body_skeleton_variant=skel,
        skin_tone_id=skin,
        costume_rig_id=costume,
        race=race,
    )


# Hero NPCs + PC archetypes (5 races × M/F). The PC roster
# uses synthetic ids; bespoke heroes use canon names.
AVATARS: dict[str, AvatarBinding] = {a.ffxi_npc_id: a for a in (
    # --- canon heroes ---
    _b("curilla",   template="Adult Female Athletic",
       face_bp="MH_F_Asian_Curilla",
       skel="Elvaan_F", skin="elvaan_pale_01",
       costume="san_doria_kingsguard", race=Race.ELVAAN),
    _b("volker",    template="Adult Male Athletic",
       face_bp="MH_M_Hume_Volker",
       skel="Hume_M", skin="hume_olive_03",
       costume="bastok_iron_musk", race=Race.HUME),
    _b("ayame",     template="Adult Female Athletic",
       face_bp="MH_F_Asian_Ayame",
       skel="Hume_F", skin="hume_warm_02",
       costume="norg_ayame_armor", race=Race.HUME),
    _b("maat",      template="Adult Male Athletic",
       face_bp="MH_M_Hume_Maat",
       skel="Hume_M", skin="hume_tan_04",
       costume="maat_doublet", race=Race.HUME),
    _b("trion",     template="Adult Male Athletic",
       face_bp="MH_M_Elvaan_Trion",
       skel="Elvaan_M", skin="elvaan_pale_02",
       costume="san_doria_prince", race=Race.ELVAAN),
    _b("nanaa_mihgo", template="Petite Female",
       face_bp="MH_F_Mithra_Nanaa",
       skel="Mithra_F", skin="mithra_tan_01",
       costume="windurst_thief_lord", race=Race.MITHRA),
    _b("aldo",      template="Adult Male Athletic",
       face_bp="MH_M_Hume_Aldo",
       skel="Hume_M", skin="hume_warm_03",
       costume="tenshodo_silks", race=Race.HUME),
    _b("cid",       template="Adult Male Heavy",
       face_bp="MH_M_Hume_Cid",
       skel="Hume_M", skin="hume_tan_03",
       costume="bastok_metalworks_smock", race=Race.HUME),
    # --- PC archetypes (5 races × M/F = 10) ---
    _b("pc_hume_m", template="Adult Male Athletic",
       face_bp="MH_M_Hume_Default",
       skel="Hume_M", skin="hume_default_m",
       costume="adventurer_starting", race=Race.HUME),
    _b("pc_hume_f", template="Adult Female Athletic",
       face_bp="MH_F_Hume_Default",
       skel="Hume_F", skin="hume_default_f",
       costume="adventurer_starting", race=Race.HUME),
    _b("pc_elvaan_m", template="Tall Male Athletic",
       face_bp="MH_M_Elvaan_Default",
       skel="Elvaan_M", skin="elvaan_default_m",
       costume="adventurer_starting", race=Race.ELVAAN),
    _b("pc_elvaan_f", template="Tall Female Athletic",
       face_bp="MH_F_Elvaan_Default",
       skel="Elvaan_F", skin="elvaan_default_f",
       costume="adventurer_starting", race=Race.ELVAAN),
    _b("pc_tarutaru_m", template="Petite Male Child-Scaled",
       face_bp="MH_M_TaruTaru_Default",
       skel="TaruTaru_M", skin="taru_default_m",
       costume="adventurer_starting", race=Race.TARUTARU),
    _b("pc_tarutaru_f", template="Petite Female Child-Scaled",
       face_bp="MH_F_TaruTaru_Default",
       skel="TaruTaru_F", skin="taru_default_f",
       costume="adventurer_starting", race=Race.TARUTARU),
    _b("pc_mithra_f", template="Petite Female",
       face_bp="MH_F_Mithra_Default",
       skel="Mithra_F", skin="mithra_default_f",
       costume="adventurer_starting", race=Race.MITHRA),
    _b("pc_mithra_m", template="Petite Female",  # M variant
       face_bp="MH_F_Mithra_DefaultM",
       skel="Mithra_F", skin="mithra_default_m",
       costume="adventurer_starting", race=Race.MITHRA),
    _b("pc_galka_m", template="Heavy Male",
       face_bp="MH_M_Galka_Default",
       skel="Galka_M", skin="galka_default_m",
       costume="adventurer_starting", race=Race.GALKA),
    _b("pc_galka_f", template="Heavy Male",  # F variant
       face_bp="MH_M_Galka_DefaultF",
       skel="Galka_M", skin="galka_default_f",
       costume="adventurer_starting", race=Race.GALKA),
)}


# Emotion → ARKit 52 weight templates. Values are conservative
# shorthands that the cinematographer can scale via intensity.
_EMOTION_KEYS: dict[Emotion, dict[str, float]] = {
    Emotion.NEUTRAL: {},  # all zero
    Emotion.HAPPY: {
        "mouthSmileLeft": 0.85,
        "mouthSmileRight": 0.85,
        "cheekSquintLeft": 0.5,
        "cheekSquintRight": 0.5,
        "eyeSquintLeft": 0.3,
        "eyeSquintRight": 0.3,
    },
    Emotion.ANGRY: {
        "browDownLeft": 0.9,
        "browDownRight": 0.9,
        "noseSneerLeft": 0.6,
        "noseSneerRight": 0.6,
        "mouthFrownLeft": 0.6,
        "mouthFrownRight": 0.6,
        "jawForward": 0.3,
    },
    Emotion.AFRAID: {
        "browInnerUp": 0.9,
        "browOuterUpLeft": 0.7,
        "browOuterUpRight": 0.7,
        "eyeWideLeft": 0.85,
        "eyeWideRight": 0.85,
        "mouthStretchLeft": 0.5,
        "mouthStretchRight": 0.5,
        "jawOpen": 0.25,
    },
    Emotion.SAD: {
        "browInnerUp": 0.7,
        "mouthFrownLeft": 0.7,
        "mouthFrownRight": 0.7,
        "mouthLowerDownLeft": 0.3,
        "mouthLowerDownRight": 0.3,
    },
    Emotion.SURPRISED: {
        "browInnerUp": 0.9,
        "browOuterUpLeft": 0.9,
        "browOuterUpRight": 0.9,
        "eyeWideLeft": 0.8,
        "eyeWideRight": 0.8,
        "jawOpen": 0.55,
    },
}


@dataclasses.dataclass
class MetaHumanDriver:
    _avatars: dict[str, AvatarBinding] = dataclasses.field(
        default_factory=lambda: dict(AVATARS),
    )

    def register_avatar(
        self, binding: AvatarBinding,
    ) -> AvatarBinding:
        # Validate skeleton-race coupling.
        allowed = _SKELETON_FOR_RACE[binding.race]
        if binding.body_skeleton_variant not in allowed:
            raise ValueError(
                f"skeleton {binding.body_skeleton_variant!r} "
                f"not allowed for race {binding.race.value}",
            )
        self._avatars[binding.ffxi_npc_id] = binding
        return binding

    def lookup(self, ffxi_npc_id: str) -> AvatarBinding:
        if ffxi_npc_id not in self._avatars:
            raise KeyError(
                f"unknown FFXI NPC: {ffxi_npc_id}",
            )
        return self._avatars[ffxi_npc_id]

    def apply_emotion(
        self, ffxi_npc_id: str,
        emotion: Emotion, intensity: float = 1.0,
    ) -> dict[str, float]:
        # Validate NPC + intensity, then expand the template
        # to the full 52-key weight dict.
        if ffxi_npc_id not in self._avatars:
            raise KeyError(
                f"unknown FFXI NPC: {ffxi_npc_id}",
            )
        if not (0.0 <= intensity <= 1.0):
            raise ValueError(
                f"intensity must be in [0,1]: {intensity}",
            )
        out: dict[str, float] = {
            k: 0.0 for k in ARKIT_BLENDSHAPES
        }
        for k, v in _EMOTION_KEYS[emotion].items():
            out[k] = round(v * intensity, 4)
        return out

    def bind_costume(
        self, ffxi_npc_id: str, costume_id: str,
    ) -> AvatarBinding:
        if not costume_id:
            raise ValueError("costume_id required")
        cur = self.lookup(ffxi_npc_id)
        new = dataclasses.replace(
            cur, costume_rig_id=costume_id,
        )
        self._avatars[ffxi_npc_id] = new
        return new

    def retarget_animation(
        self, skeleton_a: str, skeleton_b: str,
    ) -> dict:
        """Return a retarget intent UE5 can hand the IK
        Retargeter. We don't compute joint deltas here — the
        IK rig in UE5 owns that — we just check that both
        skeletons are known + describe the retarget.
        """
        known: set[str] = set()
        for s in _SKELETON_FOR_RACE.values():
            known.update(s)
        if skeleton_a not in known:
            raise ValueError(
                f"unknown skeleton: {skeleton_a}",
            )
        if skeleton_b not in known:
            raise ValueError(
                f"unknown skeleton: {skeleton_b}",
            )
        # Cross-race retarget needs a different IK rig than
        # same-race scale.
        same_race = (
            skeleton_a.split("_")[0]
            == skeleton_b.split("_")[0]
        )
        return {
            "from": skeleton_a,
            "to": skeleton_b,
            "ik_rig": (
                "MH_SameRace_IK" if same_race
                else "MH_CrossRace_IK"
            ),
            "needs_height_normalize": not same_race,
        }


def list_avatars() -> tuple[str, ...]:
    return tuple(sorted(AVATARS))


def lookup(ffxi_npc_id: str) -> AvatarBinding:
    if ffxi_npc_id not in AVATARS:
        raise KeyError(f"unknown FFXI NPC: {ffxi_npc_id}")
    return AVATARS[ffxi_npc_id]


__all__ = [
    "Race", "Emotion",
    "AvatarBinding", "AVATARS",
    "ARKIT_BLENDSHAPES", "MetaHumanDriver",
    "list_avatars", "lookup",
]
