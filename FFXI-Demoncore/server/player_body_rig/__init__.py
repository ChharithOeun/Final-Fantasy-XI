"""Player body rig — avatar visibility, weapon-draw state,
per-race adjustments.

In a third-person game the player's body is the most-shown
asset on screen. In a first-person game the same body is
absent except for hands. The rig has to switch between the
two cleanly — and during cutscenes hand control over to the
puppeteer (cinematic_camera, showcase_choreography). This
module is the single source of truth for "what of the
player's avatar is currently visible, and what pose is the
weapon in".

VisibilityKind: FIRST_PERSON_HANDS_ONLY (HUD-leaning view),
FIRST_PERSON_ARMS_TORSO (immersive sword games),
THIRD_PERSON_FULL (the FFXI default), THIRD_PERSON_HEADLESS
(when wearing a helmet in 1P-toggle scenarios — the hat
clips through the camera so the head hides), MAP_VIEW_TOP_
DOWN (when minimap takes over the screen), CUTSCENE_PUPPETED
(showcase_choreography drives the bones; we just report
"yes there is a body").

Weapon draw runs through SHEATHED -> DRAWING -> DRAWN ->
SHEATHING -> SHEATHED, with DUAL_DRAWN for ninja/dancer dual
wield, and CASTING for spellbook/staff pose. Each transition
fires an animation_id the character_animation module knows
how to play.

Per-race adjustments scale the rig — Galka shoulders are
1.3x, Mithra always shows tail, Tarutaru hand position
sits lower relative to the torso because the weapon scale
is different.

Public surface
--------------
    VisibilityKind enum
    WeaponDrawState enum
    Race enum
    PlayerBodyState dataclass (frozen)
    PlayerBodyRigSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class VisibilityKind(enum.Enum):
    FIRST_PERSON_HANDS_ONLY = "first_person_hands_only"
    FIRST_PERSON_ARMS_TORSO = "first_person_arms_torso"
    THIRD_PERSON_FULL = "third_person_full"
    THIRD_PERSON_HEADLESS = "third_person_headless"
    MAP_VIEW_TOP_DOWN = "map_view_top_down"
    CUTSCENE_PUPPETED = "cutscene_puppeted"


class WeaponDrawState(enum.Enum):
    SHEATHED = "sheathed"
    DRAWING = "drawing"
    DRAWN = "drawn"
    SHEATHING = "sheathing"
    DUAL_DRAWN = "dual_drawn"
    CASTING = "casting"


class Race(enum.Enum):
    HUME = "hume"
    ELVAAN = "elvaan"
    TARUTARU = "tarutaru"
    MITHRA = "mithra"
    GALKA = "galka"


# Per-race shoulder-width multiplier on the rig skeleton.
_SHOULDER_SCALE: dict[Race, float] = {
    Race.HUME: 1.0,
    Race.ELVAAN: 1.05,
    Race.TARUTARU: 0.6,
    Race.MITHRA: 0.85,
    Race.GALKA: 1.3,
}


# Per-race hand-bone vertical offset relative to torso
# midline (meters). Tarutaru holds weapons closer to torso.
_HAND_HEIGHT: dict[Race, float] = {
    Race.HUME: 0.0,
    Race.ELVAAN: 0.05,
    Race.TARUTARU: -0.18,
    Race.MITHRA: -0.02,
    Race.GALKA: 0.08,
}


# Animation duration constants (seconds).
_DRAW_DURATION_S = 0.35
_SHEATHE_DURATION_S = 0.5


@dataclasses.dataclass(frozen=True)
class PlayerBodyState:
    player_id: str
    race: Race
    gender: str
    visibility_kind: VisibilityKind
    helmet_visible: bool
    gloves_visible: bool
    main_hand_weapon_id: str
    off_hand_weapon_or_shield_id: str
    sub_weapon_id: str
    shoulder_capes_visible: bool
    has_blood_decal: bool
    wet_decal_intensity: float
    main_hand_state: WeaponDrawState = WeaponDrawState.SHEATHED
    off_hand_state: WeaponDrawState = WeaponDrawState.SHEATHED


@dataclasses.dataclass
class PlayerBodyRigSystem:
    _bodies: dict[str, PlayerBodyState] = dataclasses.field(
        default_factory=dict,
    )

    # ---------------------------------------------- register
    def register_body(
        self,
        player_id: str,
        race: Race,
        gender: str,
    ) -> PlayerBodyState:
        if not player_id:
            raise ValueError("player_id required")
        if player_id in self._bodies:
            raise ValueError(
                f"duplicate player_id: {player_id}",
            )
        if gender not in ("male", "female"):
            raise ValueError(
                "gender must be 'male' or 'female'",
            )
        state = PlayerBodyState(
            player_id=player_id,
            race=race,
            gender=gender,
            visibility_kind=VisibilityKind.THIRD_PERSON_FULL,
            helmet_visible=True,
            gloves_visible=True,
            main_hand_weapon_id="",
            off_hand_weapon_or_shield_id="",
            sub_weapon_id="",
            shoulder_capes_visible=True,
            has_blood_decal=False,
            wet_decal_intensity=0.0,
            main_hand_state=WeaponDrawState.SHEATHED,
            off_hand_state=WeaponDrawState.SHEATHED,
        )
        self._bodies[player_id] = state
        return state

    def state_of(self, player_id: str) -> PlayerBodyState:
        if player_id not in self._bodies:
            raise KeyError(f"unknown player_id: {player_id}")
        return self._bodies[player_id]

    def body_count(self) -> int:
        return len(self._bodies)

    # ---------------------------------------------- visibility
    def set_visibility(
        self,
        player_id: str,
        kind: VisibilityKind,
    ) -> PlayerBodyState:
        state = self.state_of(player_id)
        new_state = dataclasses.replace(
            state, visibility_kind=kind,
        )
        self._bodies[player_id] = new_state
        return new_state

    def helmet_toggle(self, player_id: str) -> PlayerBodyState:
        state = self.state_of(player_id)
        new_state = dataclasses.replace(
            state, helmet_visible=not state.helmet_visible,
        )
        self._bodies[player_id] = new_state
        return new_state

    def set_gloves_visible(
        self, player_id: str, visible: bool,
    ) -> PlayerBodyState:
        state = self.state_of(player_id)
        new_state = dataclasses.replace(
            state, gloves_visible=visible,
        )
        self._bodies[player_id] = new_state
        return new_state

    def set_capes_visible(
        self, player_id: str, visible: bool,
    ) -> PlayerBodyState:
        state = self.state_of(player_id)
        new_state = dataclasses.replace(
            state, shoulder_capes_visible=visible,
        )
        self._bodies[player_id] = new_state
        return new_state

    def set_decals(
        self,
        player_id: str,
        blood: bool | None = None,
        wet_intensity: float | None = None,
    ) -> PlayerBodyState:
        state = self.state_of(player_id)
        if (
            wet_intensity is not None
            and not (0.0 <= wet_intensity <= 1.0)
        ):
            raise ValueError(
                "wet_intensity must be in [0, 1]",
            )
        new_state = dataclasses.replace(
            state,
            has_blood_decal=(
                state.has_blood_decal
                if blood is None else blood
            ),
            wet_decal_intensity=(
                state.wet_decal_intensity
                if wet_intensity is None else wet_intensity
            ),
        )
        self._bodies[player_id] = new_state
        return new_state

    # ---------------------------------------------- weapons
    def equip_main_hand(
        self, player_id: str, weapon_id: str,
    ) -> PlayerBodyState:
        state = self.state_of(player_id)
        new_state = dataclasses.replace(
            state, main_hand_weapon_id=weapon_id,
        )
        self._bodies[player_id] = new_state
        return new_state

    def equip_off_hand(
        self, player_id: str, item_id: str,
    ) -> PlayerBodyState:
        state = self.state_of(player_id)
        new_state = dataclasses.replace(
            state, off_hand_weapon_or_shield_id=item_id,
        )
        self._bodies[player_id] = new_state
        return new_state

    def equip_sub_weapon(
        self, player_id: str, weapon_id: str,
    ) -> PlayerBodyState:
        state = self.state_of(player_id)
        new_state = dataclasses.replace(
            state, sub_weapon_id=weapon_id,
        )
        self._bodies[player_id] = new_state
        return new_state

    def draw_weapon(
        self, player_id: str, slot: str,
    ) -> str:
        """slot in ('main', 'off'). Sets state to DRAWING and
        returns the animation_id to play."""
        state = self.state_of(player_id)
        if slot not in ("main", "off"):
            raise ValueError("slot must be 'main' or 'off'")
        if slot == "main":
            if not state.main_hand_weapon_id:
                raise ValueError("no main-hand weapon equipped")
            cur = state.main_hand_state
            if cur in (
                WeaponDrawState.DRAWN, WeaponDrawState.DRAWING,
                WeaponDrawState.DUAL_DRAWN,
            ):
                return ""
            new_state = dataclasses.replace(
                state, main_hand_state=WeaponDrawState.DRAWING,
            )
        else:
            if not state.off_hand_weapon_or_shield_id:
                raise ValueError("no off-hand weapon equipped")
            cur = state.off_hand_state
            if cur in (
                WeaponDrawState.DRAWN, WeaponDrawState.DRAWING,
                WeaponDrawState.DUAL_DRAWN,
            ):
                return ""
            new_state = dataclasses.replace(
                state, off_hand_state=WeaponDrawState.DRAWING,
            )
        self._bodies[player_id] = new_state
        return f"anim_draw_{slot}_{state.race.value}"

    def complete_draw(
        self, player_id: str, slot: str,
    ) -> PlayerBodyState:
        """Called at end of DRAWING animation to move to
        DRAWN (or DUAL_DRAWN if both hands armed)."""
        state = self.state_of(player_id)
        if slot == "main":
            new_state = dataclasses.replace(
                state, main_hand_state=WeaponDrawState.DRAWN,
            )
        elif slot == "off":
            new_state = dataclasses.replace(
                state, off_hand_state=WeaponDrawState.DRAWN,
            )
        else:
            raise ValueError("slot must be 'main' or 'off'")
        # If both drawn AND off-hand is a weapon (not shield),
        # promote to DUAL_DRAWN.
        if (
            new_state.main_hand_state == WeaponDrawState.DRAWN
            and new_state.off_hand_state == WeaponDrawState.DRAWN
            and new_state.off_hand_weapon_or_shield_id
            and not new_state.off_hand_weapon_or_shield_id.startswith(
                "shield_",
            )
        ):
            new_state = dataclasses.replace(
                new_state,
                main_hand_state=WeaponDrawState.DUAL_DRAWN,
                off_hand_state=WeaponDrawState.DUAL_DRAWN,
            )
        self._bodies[player_id] = new_state
        return new_state

    def sheathe_weapon(
        self, player_id: str, slot: str,
    ) -> str:
        state = self.state_of(player_id)
        if slot not in ("main", "off"):
            raise ValueError("slot must be 'main' or 'off'")
        if slot == "main":
            cur = state.main_hand_state
            if cur in (
                WeaponDrawState.SHEATHED,
                WeaponDrawState.SHEATHING,
            ):
                return ""
            new_state = dataclasses.replace(
                state,
                main_hand_state=WeaponDrawState.SHEATHING,
            )
            # Drop dual flag on the off-hand too.
            if state.off_hand_state == WeaponDrawState.DUAL_DRAWN:
                new_state = dataclasses.replace(
                    new_state,
                    off_hand_state=WeaponDrawState.DRAWN,
                )
        else:
            cur = state.off_hand_state
            if cur in (
                WeaponDrawState.SHEATHED,
                WeaponDrawState.SHEATHING,
            ):
                return ""
            new_state = dataclasses.replace(
                state,
                off_hand_state=WeaponDrawState.SHEATHING,
            )
            if state.main_hand_state == WeaponDrawState.DUAL_DRAWN:
                new_state = dataclasses.replace(
                    new_state,
                    main_hand_state=WeaponDrawState.DRAWN,
                )
        self._bodies[player_id] = new_state
        return f"anim_sheathe_{slot}_{state.race.value}"

    def complete_sheathe(
        self, player_id: str, slot: str,
    ) -> PlayerBodyState:
        state = self.state_of(player_id)
        if slot == "main":
            new_state = dataclasses.replace(
                state, main_hand_state=WeaponDrawState.SHEATHED,
            )
        elif slot == "off":
            new_state = dataclasses.replace(
                state, off_hand_state=WeaponDrawState.SHEATHED,
            )
        else:
            raise ValueError("slot must be 'main' or 'off'")
        self._bodies[player_id] = new_state
        return new_state

    def begin_casting(self, player_id: str) -> PlayerBodyState:
        state = self.state_of(player_id)
        new_state = dataclasses.replace(
            state, main_hand_state=WeaponDrawState.CASTING,
        )
        self._bodies[player_id] = new_state
        return new_state

    def is_weapon_drawn(
        self, player_id: str, slot: str,
    ) -> bool:
        state = self.state_of(player_id)
        if slot == "main":
            return state.main_hand_state in (
                WeaponDrawState.DRAWN, WeaponDrawState.DUAL_DRAWN,
                WeaponDrawState.CASTING,
            )
        if slot == "off":
            return state.off_hand_state in (
                WeaponDrawState.DRAWN, WeaponDrawState.DUAL_DRAWN,
            )
        raise ValueError("slot must be 'main' or 'off'")

    # ---------------------------------------------- per-race
    def shoulder_scale(self, race: Race) -> float:
        return _SHOULDER_SCALE[race]

    def hand_height_offset(self, race: Race) -> float:
        return _HAND_HEIGHT[race]

    def has_visible_tail(self, race: Race) -> bool:
        # Mithra always show tail; Galka only sometimes — we
        # default Mithra true, others false.
        return race == Race.MITHRA

    def draw_duration_s(self) -> float:
        return _DRAW_DURATION_S

    def sheathe_duration_s(self) -> float:
        return _SHEATHE_DURATION_S


__all__ = [
    "VisibilityKind",
    "WeaponDrawState",
    "Race",
    "PlayerBodyState",
    "PlayerBodyRigSystem",
]
