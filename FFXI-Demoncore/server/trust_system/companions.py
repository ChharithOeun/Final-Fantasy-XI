"""Companion engine — PUP automatons / SMN avatars / BST jugs+charm /
BLU spell library.

Per the user direction: pet-class trusts (PUP, SMN, BST, BLU) carry
companions that the AI can deploy. PUPs activate their automatons,
SMN summons avatars (and primes for the avatar->prime escalation),
BST throws jug pets or charms a wild target, BLU casts learned blue
magic.

The same engine works for fomor PUPs/SMNs/BSTs (per the user spec —
'fomors that are smn, pup, bst can also use the same skills'). The
caller passes a CompanionAttachment owner_id; the engine doesn't
care whether the owner is a player, a trust, or a fomor.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class CompanionType(str, enum.Enum):
    AUTOMATON = "automaton"      # PUP
    AVATAR = "avatar"            # SMN — Carbuncle / 4 elemental primes / etc.
    JUG_PET = "jug_pet"          # BST — Carrie / Dipper Yuly / etc.
    CHARMED = "charmed"          # BST — wild monster currently charmed
    BLU_SPELL = "blu_spell"      # BLU — learned spell library entries


# Aphmau is the unique 3-slot exception per the user direction.
# All other PUPs read their slot count from pup_progression.
APHMAU_OWNER_IDS = frozenset({"aphmau"})

# Automaton skillchain + magic-burst window rules (user direction):
# A SC opened by an automaton stays open 5s; a SC closed by an
# automaton opens a 15s MB window allowing up to 3 MBs depending on
# SC tier (Lv1 = 1 MB; Lv2 = 2 MBs; Lv3+ Light/Darkness = 3 MBs).
AUTOMATON_SC_OPEN_WINDOW_SECONDS = 5.0
AUTOMATON_SC_CLOSE_MB_WINDOW_SECONDS = 15.0
AUTOMATON_MB_BY_SC_TIER: dict[int, int] = {
    1: 1,
    2: 2,
    3: 3,    # Light / Darkness apex chains
    4: 3,    # any higher chain caps at 3 per the spec
}

# Tank-automaton AOE-hate scaling: base 3x, +1x per fire/light maneuver
# active (per the user direction).
TANK_AOE_HATE_BASE_MULTIPLIER = 3.0
TANK_AOE_HATE_PER_FIRE_OR_LIGHT_MANEUVER = 1.0


class CompanionRole(str, enum.Enum):
    TANK = "tank"
    MELEE_DPS = "melee_dps"
    RANGED_DPS = "ranged_dps"
    HEALER = "healer"
    SUPPORT = "support"
    NUKER = "nuker"
    UTILITY = "utility"          # BLU spells, debuffs, status


@dataclasses.dataclass(frozen=True)
class CompanionSpec:
    """Static definition of a companion that can be activated."""
    companion_id: str
    name: str
    companion_type: CompanionType
    role: CompanionRole
    base_hp: int
    base_damage: int
    abilities: tuple[str, ...] = ()
    duration_seconds: t.Optional[float] = None     # None = until despawned
    cooldown_seconds: float = 0.0
    notes: str = ""


# ----------------------------------------------------------------------
# Catalog
# ----------------------------------------------------------------------

# Aphmau's pair + the 4 PUP frames the other PUP trusts deploy.
# Frame names mirror canonical FFXI PUP frames.
_AUTOMATONS = {
    "automaton_mnejing": CompanionSpec(
        companion_id="automaton_mnejing", name="Mnejing",
        companion_type=CompanionType.AUTOMATON, role=CompanionRole.TANK,
        base_hp=1200, base_damage=80,
        abilities=("provoke", "shield_bash", "iron_palisade",
                     "aoe_provoke", "aoe_flash", "aoe_strobe",
                     "cure_other_automaton"),
        notes="Aphmau's tank-twin; AOE hate kit on tank automatons",
    ),
    "automaton_sharpshot": CompanionSpec(
        companion_id="automaton_sharpshot", name="Sharpshot Frame",
        companion_type=CompanionType.AUTOMATON, role=CompanionRole.RANGED_DPS,
        base_hp=900, base_damage=110,
        abilities=("ranged_shot", "heat_seeker", "armor_piercer",
                     "magic_burst_ranged"),
    ),
    "automaton_valoredge": CompanionSpec(
        companion_id="automaton_valoredge", name="Valoredge Frame",
        companion_type=CompanionType.AUTOMATON, role=CompanionRole.TANK,
        base_hp=1100, base_damage=95,
        abilities=("provoke", "smite_of_rage", "armor_shatter",
                     "aoe_provoke", "aoe_flash", "aoe_strobe"),
    ),
    "automaton_soulsoother": CompanionSpec(
        companion_id="automaton_soulsoother", name="Soulsoother Frame",
        companion_type=CompanionType.AUTOMATON, role=CompanionRole.HEALER,
        base_hp=850, base_damage=40,
        abilities=("cure_ii", "cure_iii", "regen_ii", "stoneskin",
                     "cure_other_automaton", "regen_other_automaton",
                     "raise_other_automaton", "haste_other_automaton"),
        notes="heals + revives the rest of the automaton party",
    ),
    "automaton_spiritreaver": CompanionSpec(
        companion_id="automaton_spiritreaver", name="Spiritreaver Frame",
        companion_type=CompanionType.AUTOMATON, role=CompanionRole.NUKER,
        base_hp=750, base_damage=60,
        abilities=("firaga_ii", "blizzaga_ii", "thundaga_ii", "stun",
                     "magic_burst", "self_skillchain_starter"),
        notes="caster-frame; can self-SC into MB during overdrive",
    ),
    "automaton_stormwaker": CompanionSpec(
        companion_id="automaton_stormwaker", name="Stormwaker Frame",
        companion_type=CompanionType.AUTOMATON, role=CompanionRole.SUPPORT,
        base_hp=900, base_damage=55,
        abilities=("haste", "slow", "magic_finale",
                     "haste_other_automaton", "buff_other_automaton"),
    ),

    # ---------- New frames per user direction ----------

    "automaton_ninja": CompanionSpec(
        companion_id="automaton_ninja", name="Shinobi Frame",
        companion_type=CompanionType.AUTOMATON, role=CompanionRole.MELEE_DPS,
        base_hp=950, base_damage=130,
        abilities=("utsusemi_ichi_no_tools", "utsusemi_ni_no_tools",
                     "utsusemi_san_no_tools", "throwing_assault",
                     "katon_san_no_tools", "huton_ichi_no_tools",
                     "weave_signs", "haste_self",
                     "high_evasion_passive", "high_accuracy_passive"),
        notes=("lvl 75 fully-merit unlock (head + frame separate quests). "
                 "High evasion + haste + accuracy. Weaves signs without "
                 "tools. Up to 3 utsusemi shadows per wind maneuver up. "
                 "Hard-hitting throwing ranged skill."),
    ),
    "automaton_dragoon": CompanionSpec(
        companion_id="automaton_dragoon", name="Wyrmwarden Frame",
        companion_type=CompanionType.AUTOMATON, role=CompanionRole.MELEE_DPS,
        base_hp=1300, base_damage=140,
        abilities=("jump", "high_jump", "spirit_jump",
                     "wheeling_thrust", "drakesbane",
                     "self_skillchain_starter"),
        notes=("hidden frame. lvl 99 + job mastered + secret "
                 "questline. lance reach + jump SC starters."),
    ),
    "automaton_blue": CompanionSpec(
        companion_id="automaton_blue", name="Azure Frame",
        companion_type=CompanionType.AUTOMATON, role=CompanionRole.MELEE_DPS,
        base_hp=1100, base_damage=120,
        abilities=("blue_magic_chain_affinity",
                     "blue_magic_burst_affinity",
                     "azure_lore_self_sc", "1000_needles",
                     "self_skillchain_starter", "self_magic_burst"),
        notes=("hidden frame. lvl 99 + job mastered + secret "
                 "questline. learns + casts BLU spells; can self-SC "
                 "into MB during SP."),
    ),
}


# SMN avatars — Carbuncle, 4 elemental primes, plus the canonical 8
# elemental + light/dark.
_AVATARS = {
    "avatar_carbuncle": CompanionSpec(
        companion_id="avatar_carbuncle", name="Carbuncle",
        companion_type=CompanionType.AVATAR, role=CompanionRole.HEALER,
        base_hp=900, base_damage=60,
        abilities=("healing_ruby", "soothing_ruby", "ruby_glow"),
        duration_seconds=600.0,
    ),
    "avatar_ifrit": CompanionSpec(
        companion_id="avatar_ifrit", name="Ifrit",
        companion_type=CompanionType.AVATAR, role=CompanionRole.NUKER,
        base_hp=1300, base_damage=140,
        abilities=("flaming_crush", "inferno", "punch"),
        duration_seconds=600.0,
        notes="fire prime",
    ),
    "avatar_shiva": CompanionSpec(
        companion_id="avatar_shiva", name="Shiva",
        companion_type=CompanionType.AVATAR, role=CompanionRole.NUKER,
        base_hp=1200, base_damage=130,
        abilities=("diamond_dust", "double_slap", "frost_armor"),
        duration_seconds=600.0,
        notes="ice prime",
    ),
    "avatar_ramuh": CompanionSpec(
        companion_id="avatar_ramuh", name="Ramuh",
        companion_type=CompanionType.AVATAR, role=CompanionRole.NUKER,
        base_hp=1250, base_damage=130,
        abilities=("judgment_bolt", "thunder_iv", "shock_strike"),
        duration_seconds=600.0,
        notes="lightning prime",
    ),
    "avatar_garuda": CompanionSpec(
        companion_id="avatar_garuda", name="Garuda",
        companion_type=CompanionType.AVATAR, role=CompanionRole.SUPPORT,
        base_hp=1200, base_damage=120,
        abilities=("aerial_blast", "predator_claws", "hastega"),
        duration_seconds=600.0,
        notes="wind prime",
    ),
    "avatar_titan": CompanionSpec(
        companion_id="avatar_titan", name="Titan",
        companion_type=CompanionType.AVATAR, role=CompanionRole.TANK,
        base_hp=1800, base_damage=110,
        abilities=("earthen_fury", "rock_buster", "geocrush"),
        duration_seconds=600.0,
        notes="earth prime",
    ),
    "avatar_leviathan": CompanionSpec(
        companion_id="avatar_leviathan", name="Leviathan",
        companion_type=CompanionType.AVATAR, role=CompanionRole.NUKER,
        base_hp=1300, base_damage=120,
        abilities=("tidal_wave", "spinning_dive", "barrier_tusk"),
        duration_seconds=600.0,
        notes="water prime",
    ),
    "avatar_fenrir": CompanionSpec(
        companion_id="avatar_fenrir", name="Fenrir",
        companion_type=CompanionType.AVATAR, role=CompanionRole.MELEE_DPS,
        base_hp=1400, base_damage=140,
        abilities=("howling_moon", "ecliptic_howl", "lunar_bay"),
        duration_seconds=600.0,
        notes="dark prime",
    ),
    "avatar_diabolos": CompanionSpec(
        companion_id="avatar_diabolos", name="Diabolos",
        companion_type=CompanionType.AVATAR, role=CompanionRole.UTILITY,
        base_hp=1200, base_damage=110,
        abilities=("ruinous_omen", "nightmare", "noctoshield"),
        duration_seconds=600.0,
        notes="dream prime; sleeps the field",
    ),
}


# BST jug pets + charmable target placeholder.
_JUG_PETS = {
    "jug_carrie": CompanionSpec(
        companion_id="jug_carrie", name="Carrie",
        companion_type=CompanionType.JUG_PET, role=CompanionRole.MELEE_DPS,
        base_hp=900, base_damage=85,
        abilities=("scythe_tail", "harden_shell"),
        duration_seconds=900.0,
        notes="rabbit jug; mid-tier",
    ),
    "jug_dipper_yuly": CompanionSpec(
        companion_id="jug_dipper_yuly", name="Dipper Yuly",
        companion_type=CompanionType.JUG_PET, role=CompanionRole.MELEE_DPS,
        base_hp=1300, base_damage=120,
        abilities=("rage", "dipper_lunge"),
        duration_seconds=900.0,
        notes="raptor jug; late-game tier",
    ),
    "jug_funguar_familiar": CompanionSpec(
        companion_id="jug_funguar_familiar", name="Funguar Familiar",
        companion_type=CompanionType.JUG_PET, role=CompanionRole.UTILITY,
        base_hp=850, base_damage=60,
        abilities=("frogkick", "dark_spore", "queasyshroom"),
        duration_seconds=900.0,
        notes="status-spamming jug",
    ),
    "jug_lifedrinker_lars": CompanionSpec(
        companion_id="jug_lifedrinker_lars", name="Lifedrinker Lars",
        companion_type=CompanionType.JUG_PET, role=CompanionRole.MELEE_DPS,
        base_hp=1100, base_damage=110,
        abilities=("blood_pact", "smite_of_rage", "siphon_charge"),
        duration_seconds=900.0,
        notes="weapon-skill heavy jug",
    ),
    "charmed_wild_target": CompanionSpec(
        companion_id="charmed_wild_target", name="Charmed Beast",
        companion_type=CompanionType.CHARMED, role=CompanionRole.MELEE_DPS,
        base_hp=0, base_damage=0,         # filled at charm time
        abilities=(),
        duration_seconds=180.0,            # charm duration
        notes="placeholder; species filled at charm time",
    ),
}


# BLU spell library entries the BLU trust can mimic.
_BLU_SPELLS = {
    "blu_cocoon": CompanionSpec(
        companion_id="blu_cocoon", name="Cocoon",
        companion_type=CompanionType.BLU_SPELL, role=CompanionRole.SUPPORT,
        base_hp=0, base_damage=0,
        abilities=("self_defense_buff",),
        duration_seconds=120.0,
    ),
    "blu_filamented_hold": CompanionSpec(
        companion_id="blu_filamented_hold", name="Filamented Hold",
        companion_type=CompanionType.BLU_SPELL, role=CompanionRole.UTILITY,
        base_hp=0, base_damage=0,
        abilities=("slow",),
        duration_seconds=180.0,
    ),
    "blu_1000_needles": CompanionSpec(
        companion_id="blu_1000_needles", name="1000 Needles",
        companion_type=CompanionType.BLU_SPELL, role=CompanionRole.NUKER,
        base_hp=0, base_damage=1000,
        abilities=("fixed_damage_aoe",),
        cooldown_seconds=60.0,
    ),
    "blu_blood_drain": CompanionSpec(
        companion_id="blu_blood_drain", name="Blood Drain",
        companion_type=CompanionType.BLU_SPELL, role=CompanionRole.UTILITY,
        base_hp=0, base_damage=80,
        abilities=("hp_drain",),
    ),
    "blu_self_destruct": CompanionSpec(
        companion_id="blu_self_destruct", name="Self-Destruct",
        companion_type=CompanionType.BLU_SPELL, role=CompanionRole.NUKER,
        base_hp=0, base_damage=2000,
        abilities=("hp_proportional_aoe",),
        cooldown_seconds=120.0,
    ),
    "blu_blank_gaze": CompanionSpec(
        companion_id="blu_blank_gaze", name="Blank Gaze",
        companion_type=CompanionType.BLU_SPELL, role=CompanionRole.UTILITY,
        base_hp=0, base_damage=0,
        abilities=("dispel",),
    ),
    "blu_jettatura": CompanionSpec(
        companion_id="blu_jettatura", name="Jettatura",
        companion_type=CompanionType.BLU_SPELL, role=CompanionRole.UTILITY,
        base_hp=0, base_damage=0,
        abilities=("aoe_terror",),
        cooldown_seconds=90.0,
    ),
    "blu_hysteric_barrage": CompanionSpec(
        companion_id="blu_hysteric_barrage", name="Hysteric Barrage",
        companion_type=CompanionType.BLU_SPELL, role=CompanionRole.MELEE_DPS,
        base_hp=0, base_damage=600,
        abilities=("multi_hit_physical", "skillchain_starter_distortion"),
        cooldown_seconds=45.0,
    ),
    # Self-SC + MB capability per user direction — BLU during SP
    "blu_quad_continuum": CompanionSpec(
        companion_id="blu_quad_continuum", name="Quad Continuum",
        companion_type=CompanionType.BLU_SPELL, role=CompanionRole.MELEE_DPS,
        base_hp=0, base_damage=550,
        abilities=("multi_hit_physical", "skillchain_starter_fragmentation"),
        cooldown_seconds=40.0,
        notes="opener for self-SC during Azure Lore SP",
    ),
    "blu_disseverment": CompanionSpec(
        companion_id="blu_disseverment", name="Disseverment",
        companion_type=CompanionType.BLU_SPELL, role=CompanionRole.MELEE_DPS,
        base_hp=0, base_damage=480,
        abilities=("multi_hit_physical", "skillchain_closer_distortion"),
        cooldown_seconds=30.0,
        notes="closer; Distortion chain = ice/water MB window",
    ),
    "blu_chant_du_cygne": CompanionSpec(
        companion_id="blu_chant_du_cygne", name="Chant du Cygne",
        companion_type=CompanionType.BLU_SPELL, role=CompanionRole.MELEE_DPS,
        base_hp=0, base_damage=620,
        abilities=("multi_hit_physical", "skillchain_closer_light"),
        cooldown_seconds=50.0,
        notes="apex closer for Light skillchain",
    ),
    "blu_blastbomb": CompanionSpec(
        companion_id="blu_blastbomb", name="Blastbomb",
        companion_type=CompanionType.BLU_SPELL, role=CompanionRole.NUKER,
        base_hp=0, base_damage=400,
        abilities=("magic_burst_capable", "fire_element"),
        cooldown_seconds=20.0,
        notes="MB-capable into Liquefaction or Fusion windows",
    ),
    "blu_thunderbolt": CompanionSpec(
        companion_id="blu_thunderbolt", name="Thunderbolt",
        companion_type=CompanionType.BLU_SPELL, role=CompanionRole.NUKER,
        base_hp=0, base_damage=420,
        abilities=("magic_burst_capable", "lightning_element"),
        cooldown_seconds=20.0,
        notes="MB-capable into Impaction / Fusion windows",
    ),
    "blu_silent_storm": CompanionSpec(
        companion_id="blu_silent_storm", name="Silent Storm",
        companion_type=CompanionType.BLU_SPELL, role=CompanionRole.NUKER,
        base_hp=0, base_damage=380,
        abilities=("magic_burst_capable", "wind_element"),
        cooldown_seconds=18.0,
        notes="MB-capable into Detonation / Light windows",
    ),
    "blu_azure_lore_sp": CompanionSpec(
        companion_id="blu_azure_lore_sp", name="Azure Lore",
        companion_type=CompanionType.BLU_SPELL, role=CompanionRole.UTILITY,
        base_hp=0, base_damage=0,
        abilities=("sp_buff", "double_blue_magic", "instant_cast",
                     "self_skillchain_window"),
        cooldown_seconds=3600.0,
        notes=("2-hour SP. Doubles BLU output and lets the BLU trust "
                 "open and close their own skillchain back-to-back, then "
                 "magic burst up to 3 times into the resulting window."),
    ),
}


COMPANION_CATALOG: dict[str, CompanionSpec] = {
    **_AUTOMATONS,
    **_AVATARS,
    **_JUG_PETS,
    **_BLU_SPELLS,
}


def companion_for(companion_id: str) -> t.Optional[CompanionSpec]:
    return COMPANION_CATALOG.get(companion_id.lower())


def companions_by_type(companion_type: CompanionType) -> list[CompanionSpec]:
    return [c for c in COMPANION_CATALOG.values()
              if c.companion_type == companion_type]


# ----------------------------------------------------------------------
# Attachment — per-instance live state
# ----------------------------------------------------------------------

@dataclasses.dataclass
class CompanionAttachment:
    """A companion currently active under an owner (player/trust/fomor)."""
    spec: CompanionSpec
    owner_id: str
    owner_kind: str                              # "player" / "trust" / "fomor"
    current_hp: int
    max_hp: int
    is_active: bool = True
    activated_at: float = 0.0
    expires_at: t.Optional[float] = None         # for timed companions

    def is_expired(self, *, now: float) -> bool:
        return self.expires_at is not None and now >= self.expires_at


class CompanionManager:
    """Owns the live companion attachments per owner. Each owner has
    a maximum of one PRIMARY companion (the avatar / current jug),
    BUT PUPs are special: per the user direction, Aphmau (and
    auto_activate_companions PUPs) field BOTH automatons at once.

    BLU spells are not 'attached' the same way — BLU casts learned
    spells on demand. The catalog still lives here so the engine can
    look them up uniformly.
    """

    def __init__(self) -> None:
        self._by_owner: dict[str, list[CompanionAttachment]] = {}

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def activate(self,
                   *,
                   companion_id: str,
                   owner_id: str,
                   owner_kind: str = "player",
                   now: float = 0,
                   max_active_for_pup: int = 1,
                   ) -> t.Optional[CompanionAttachment]:
        """Activate a companion under an owner. Returns the attachment
        on success; None if the owner already maxed out their slots
        for this companion type or the spec doesn't exist.

        For AUTOMATON: default max_active_for_pup=1 per the user
        direction. Aphmau is the unique exception — she fields 3
        regardless of `max_active_for_pup`. Other PUPs pass 2 / 3
        from pup_progression.automaton_slot_capacity() once they've
        completed the ML25 / ML50 quest gates.
        For AVATAR / JUG_PET / CHARMED: only one active at a time
        (matching FFXI canon — releasing the current avatar to summon
        another).
        For BLU_SPELL: not 'attached'; this method returns None and
        the caller uses cast_blu_spell() instead.
        """
        # Aphmau exception: she fields 3 automatons at any level.
        if owner_id.lower() in APHMAU_OWNER_IDS:
            max_active_for_pup = max(max_active_for_pup, 3)
        spec = companion_for(companion_id)
        if spec is None:
            return None

        if spec.companion_type == CompanionType.BLU_SPELL:
            # BLU spells aren't attached; caller uses cast_blu_spell
            return None

        active = self._by_owner.setdefault(owner_id, [])

        if spec.companion_type == CompanionType.AUTOMATON:
            existing_automatons = [a for a in active
                                      if a.spec.companion_type
                                      == CompanionType.AUTOMATON
                                      and a.is_active]
            if len(existing_automatons) >= max_active_for_pup:
                return None
        else:
            # AVATAR / JUG_PET / CHARMED: only one of that type at a time
            existing_same_type = [a for a in active
                                     if a.spec.companion_type == spec.companion_type
                                     and a.is_active]
            if existing_same_type:
                # Release the existing companion of this type
                for a in existing_same_type:
                    a.is_active = False

        expires_at = (now + spec.duration_seconds
                       if spec.duration_seconds is not None else None)
        att = CompanionAttachment(
            spec=spec, owner_id=owner_id, owner_kind=owner_kind,
            max_hp=spec.base_hp, current_hp=spec.base_hp,
            activated_at=now, expires_at=expires_at,
        )
        active.append(att)
        return att

    def release(self, owner_id: str, companion_id: str) -> bool:
        """Manually deactivate a specific companion."""
        active = self._by_owner.get(owner_id, [])
        for a in active:
            if a.spec.companion_id == companion_id and a.is_active:
                a.is_active = False
                return True
        return False

    def release_all(self, owner_id: str) -> int:
        active = self._by_owner.get(owner_id, [])
        count = 0
        for a in active:
            if a.is_active:
                a.is_active = False
                count += 1
        return count

    def tick_expirations(self, *, now: float) -> list[str]:
        """Walk all attachments and mark expired ones inactive.
        Returns the list of companion_ids that just expired."""
        expired: list[str] = []
        for owner_attachments in self._by_owner.values():
            for a in owner_attachments:
                if a.is_active and a.is_expired(now=now):
                    a.is_active = False
                    expired.append(a.spec.companion_id)
        return expired

    # ------------------------------------------------------------------
    # BLU spell casting (special path)
    # ------------------------------------------------------------------

    @staticmethod
    def cast_blu_spell(spell_id: str) -> t.Optional[CompanionSpec]:
        """Look up a BLU spell. The caller resolves the actual cast
        (damage, effect) via the standard combat pipeline."""
        spell = companion_for(spell_id)
        if spell is None or spell.companion_type != CompanionType.BLU_SPELL:
            return None
        return spell

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def active_for_owner(self, owner_id: str) -> list[CompanionAttachment]:
        return [a for a in self._by_owner.get(owner_id, []) if a.is_active]

    def has_active(self, owner_id: str, companion_id: str) -> bool:
        for a in self._by_owner.get(owner_id, []):
            if a.is_active and a.spec.companion_id == companion_id:
                return True
        return False
