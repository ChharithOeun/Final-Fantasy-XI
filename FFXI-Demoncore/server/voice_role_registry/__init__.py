"""Voice role registry — per-character voice provisioning.

The casting layer above ``voice_pipeline``. Each named FFXI
hero / villain / boss / vendor is a *role*, and the role's
``provisioned_by`` field decides who currently speaks for
that character in the build:

    AI_ENGINE  — voice_pipeline drives a Higgs / TTS clone
    HUMAN_VA   — a real voice actor under contract
    VACANT     — slot is open; no audio is generated yet

Hot-swap is by design. Today the project ships entirely on
AI clones; tomorrow a real VA can be slotted into Curilla
without churn to ``voiced_cutscene`` or ``dialogue_lipsync``
— those layers ask the registry "who voices ``curilla``?"
and the registry answers with whatever is current.

Public surface
--------------
    Archetype enum
    ProvisionKind enum
    RoleSpec dataclass (frozen)
    VoiceRole dataclass (frozen)
    VoiceRoleRegistry
    BUILTIN_ROLES tuple
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Archetype(enum.Enum):
    HERO = "hero"
    VILLAIN = "villain"
    MENTOR = "mentor"
    COMIC_RELIEF = "comic_relief"
    NM_BOSS = "nm_boss"
    VENDOR = "vendor"
    NARRATOR = "narrator"


class ProvisionKind(enum.Enum):
    AI_ENGINE = "ai_engine"
    HUMAN_VA = "human_va"
    VACANT = "vacant"


@dataclasses.dataclass(frozen=True)
class RoleSpec:
    """The voice prescription a casting director hands the
    AI engine OR the human VA. Same data both ways.
    """
    pitch_hz_target: float
    accent: str
    vibe: str
    age_range: tuple[int, int]
    gender: str  # 'm' / 'f' / 'nb' / 'unknown'
    language_primary: str
    language_secondaries: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class RateCard:
    """Cost knobs — one of the two fields is meaningful per
    provisioning kind. Human VAs charge per word; AI engines
    charge per inference-minute.
    """
    per_word_usd_for_human: float
    per_minute_inference_cost_for_ai: float


@dataclasses.dataclass(frozen=True)
class Provisioning:
    kind: ProvisionKind
    ref: str           # engine_name | va_name | ""
    contract_id: str   # required for HUMAN_VA, "" otherwise


@dataclasses.dataclass(frozen=True)
class VoiceRole:
    role_id: str
    character_name: str
    archetype: Archetype
    provisioned_by: Provisioning
    spec: RoleSpec
    rate_card: RateCard
    reserved: bool = False
    notes: str = ""


# ---------------------------------------------------------------
# Built-in canon roles. Every spec is a casting brief — when a
# real VA auditions for a role, this is the doc they read.
# ---------------------------------------------------------------
def _ai(engine: str = "higgs_v2") -> Provisioning:
    return Provisioning(ProvisionKind.AI_ENGINE, engine, "")


def _vacant() -> Provisioning:
    return Provisioning(ProvisionKind.VACANT, "", "")


_DEFAULT_RATE = RateCard(
    per_word_usd_for_human=0.45,
    per_minute_inference_cost_for_ai=0.08,
)


BUILTIN_ROLES: tuple[VoiceRole, ...] = (
    # ---- Sandoria ----
    VoiceRole(
        role_id="curilla",
        character_name="Curilla",
        archetype=Archetype.HERO,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=205.0, accent="elvaan_noble",
            vibe="stern_captain", age_range=(35, 45),
            gender="f", language_primary="en",
            language_secondaries=("ja",),
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="trion",
        character_name="Prince Trion",
        archetype=Archetype.HERO,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=130.0, accent="elvaan_royal",
            vibe="earnest_prince", age_range=(22, 30),
            gender="m", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="halver",
        character_name="Halver",
        archetype=Archetype.MENTOR,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=110.0, accent="elvaan_old",
            vibe="weary_general", age_range=(55, 70),
            gender="m", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="pieuje",
        character_name="Pieuje",
        archetype=Archetype.HERO,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=175.0, accent="elvaan_clergy",
            vibe="ascetic_devout", age_range=(28, 38),
            gender="m", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    # ---- Bastok ----
    VoiceRole(
        role_id="volker",
        character_name="Volker",
        archetype=Archetype.HERO,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=125.0, accent="hume_bastokan",
            vibe="grizzled_musketeer", age_range=(35, 50),
            gender="m", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="cid",
        character_name="Cid",
        archetype=Archetype.MENTOR,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=120.0, accent="hume_bastokan",
            vibe="genius_engineer", age_range=(40, 55),
            gender="m", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="naja_salaheem",
        character_name="Naja Salaheem",
        archetype=Archetype.COMIC_RELIEF,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=290.0, accent="mithran_brassy",
            vibe="loud_mercenary", age_range=(28, 40),
            gender="f", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="ayame",
        character_name="Ayame",
        archetype=Archetype.HERO,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=215.0, accent="hume_norg",
            vibe="dutiful_samurai", age_range=(25, 32),
            gender="f", language_primary="en",
            language_secondaries=("ja",),
        ),
        rate_card=_DEFAULT_RATE,
    ),
    # ---- Windurst ----
    VoiceRole(
        role_id="ovjang",
        character_name="Ovjang",
        archetype=Archetype.MENTOR,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=300.0, accent="tarutaru_minister",
            vibe="bureaucratic_scholar", age_range=(35, 50),
            gender="f", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="shantotto",
        character_name="Shantotto",
        archetype=Archetype.HERO,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=320.0, accent="tarutaru_rhyming",
            vibe="cackling_archmage", age_range=(50, 200),
            gender="f", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="nanaa_mihgo",
        character_name="Nanaa Mihgo",
        archetype=Archetype.COMIC_RELIEF,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=275.0, accent="mithran_streetwise",
            vibe="purring_thief", age_range=(20, 28),
            gender="f", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    # ---- Jeuno ----
    VoiceRole(
        role_id="maat",
        character_name="Maat",
        archetype=Archetype.MENTOR,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=110.0, accent="hume_jeuno_old",
            vibe="weathered_master", age_range=(60, 75),
            gender="m", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="aldo",
        character_name="Aldo",
        archetype=Archetype.MENTOR,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=128.0, accent="hume_norg",
            vibe="careful_spymaster", age_range=(40, 55),
            gender="m", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="lion",
        character_name="Lion",
        archetype=Archetype.HERO,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=235.0, accent="hume_jeuno_yng",
            vibe="quick_witted_thief", age_range=(18, 24),
            gender="f", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    # ---- Crystal Warriors of yore (RoZ) ----
    VoiceRole(
        role_id="cw_archduke_kam",
        character_name="Archduke Kam'lanaut",
        archetype=Archetype.VILLAIN,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=120.0, accent="zilart_courtly",
            vibe="velvet_menace", age_range=(40, 60),
            gender="m", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="cw_eald_narche",
        character_name="Eald'narche",
        archetype=Archetype.VILLAIN,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=210.0, accent="zilart_aloof",
            vibe="ageless_child", age_range=(10, 14),
            gender="m", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="cw_zeid",
        character_name="Zeid",
        archetype=Archetype.HERO,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=95.0, accent="galkan_drk",
            vibe="laconic_warrior", age_range=(50, 65),
            gender="m", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="cw_lilisette",
        character_name="Lilisette",
        archetype=Archetype.HERO,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=265.0, accent="hume_dancer",
            vibe="stagey_dramatic", age_range=(20, 25),
            gender="f", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="cw_iroha",
        character_name="Iroha",
        archetype=Archetype.HERO,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=240.0, accent="hume_far_eastern",
            vibe="bright_samurai", age_range=(18, 24),
            gender="f", language_primary="en",
            language_secondaries=("ja",),
        ),
        rate_card=_DEFAULT_RATE,
    ),
    # ---- CoP ----
    VoiceRole(
        role_id="prishe",
        character_name="Prishe",
        archetype=Archetype.HERO,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=255.0, accent="elvaan_temple",
            vibe="brash_orphan", age_range=(15, 20),
            gender="f", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="ulmia",
        character_name="Ulmia",
        archetype=Archetype.HERO,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=230.0, accent="elvaan_temple",
            vibe="lyrical_bard", age_range=(20, 26),
            gender="f", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="selh_teus",
        character_name="Selh'teus",
        archetype=Archetype.MENTOR,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=140.0, accent="kuluu_archaic",
            vibe="ageless_calm", age_range=(20, 1000),
            gender="m", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="tenzen",
        character_name="Tenzen",
        archetype=Archetype.HERO,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=120.0, accent="hume_far_eastern",
            vibe="taciturn_warrior", age_range=(28, 36),
            gender="m", language_primary="en",
            language_secondaries=("ja",),
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="mihli_aliapoh",
        character_name="Mihli Aliapoh",
        archetype=Archetype.HERO,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=270.0, accent="mithran_clergy",
            vibe="meek_priestess", age_range=(20, 28),
            gender="f", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="esha_ntarl",
        character_name="Esha'ntarl",
        archetype=Archetype.MENTOR,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=250.0, accent="kuluu_archaic",
            vibe="grieving_seer", age_range=(28, 1000),
            gender="f", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="atomos",
        character_name="Atomos",
        archetype=Archetype.NM_BOSS,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=70.0, accent="cosmic_abstract",
            vibe="enigmatic_void", age_range=(0, 10000),
            gender="nb", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    # ---- The Shadow Lord (BCNM finale) ----
    VoiceRole(
        role_id="shadow_lord",
        character_name="The Shadow Lord",
        archetype=Archetype.VILLAIN,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=85.0, accent="cthonic_resonant",
            vibe="hateful_spectre", age_range=(0, 10000),
            gender="m", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    # ---- Five Crystal Warrior heroes (vintage BCNM) ----
    VoiceRole(
        role_id="cw_volker_old",
        character_name="Volker (Crystal Warrior)",
        archetype=Archetype.HERO,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=125.0, accent="hume_bastokan",
            vibe="young_legend_volker", age_range=(20, 28),
            gender="m", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="cw_excenmille",
        character_name="Excenmille (Crystal Warrior)",
        archetype=Archetype.HERO,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=130.0, accent="elvaan_knight",
            vibe="proud_paladin", age_range=(22, 32),
            gender="m", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="cw_ayame_old",
        character_name="Ayame (Crystal Warrior)",
        archetype=Archetype.HERO,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=215.0, accent="hume_norg",
            vibe="young_legend_ayame", age_range=(20, 28),
            gender="f", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="cw_kuyin_hathdenna",
        character_name="Kuyin Hathdenna",
        archetype=Archetype.HERO,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=160.0, accent="tarutaru_archaic",
            vibe="ancient_sage", age_range=(50, 80),
            gender="m", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    VoiceRole(
        role_id="cw_raogrimm",
        character_name="Raogrimm",
        archetype=Archetype.HERO,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=80.0, accent="galkan_drk_proto",
            vibe="brooding_galka", age_range=(40, 60),
            gender="m", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
    # ---- Generic narrator slot ----
    VoiceRole(
        role_id="narrator_main",
        character_name="Main Narrator",
        archetype=Archetype.NARRATOR,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=140.0, accent="neutral_broadcast",
            vibe="storybook_intimate", age_range=(35, 55),
            gender="unknown", language_primary="en",
            language_secondaries=("ja", "fr", "de"),
        ),
        rate_card=_DEFAULT_RATE,
    ),
    # ---- Vendor / open archetype role for testing ----
    VoiceRole(
        role_id="vendor_jeuno_chocobo",
        character_name="Chocobo Stable Hand",
        archetype=Archetype.VENDOR,
        provisioned_by=_ai(),
        spec=RoleSpec(
            pitch_hz_target=180.0, accent="hume_jeuno_yng",
            vibe="cheerful_handler", age_range=(20, 30),
            gender="m", language_primary="en",
        ),
        rate_card=_DEFAULT_RATE,
    ),
)


@dataclasses.dataclass
class VoiceRoleRegistry:
    """In-memory canon role book. Mutable provisioning;
    immutable everything else.
    """
    _roles: dict[str, VoiceRole] = dataclasses.field(
        default_factory=dict,
    )

    @classmethod
    def with_canon(cls) -> "VoiceRoleRegistry":
        reg = cls()
        for role in BUILTIN_ROLES:
            reg.register_role(role)
        return reg

    def register_role(self, role: VoiceRole) -> VoiceRole:
        if role.role_id in self._roles:
            raise ValueError(
                f"role_id already registered: {role.role_id}",
            )
        self._roles[role.role_id] = role
        return role

    def lookup(self, role_id: str) -> VoiceRole:
        if role_id not in self._roles:
            raise KeyError(f"unknown role_id: {role_id}")
        return self._roles[role_id]

    def all_roles(self) -> tuple[VoiceRole, ...]:
        return tuple(self._roles.values())

    def _replace_provisioning(
        self, role_id: str, prov: Provisioning,
    ) -> VoiceRole:
        role = self.lookup(role_id)
        new_role = dataclasses.replace(
            role, provisioned_by=prov,
        )
        self._roles[role_id] = new_role
        return new_role

    def provision_with_ai(
        self, role_id: str, engine_name: str,
    ) -> VoiceRole:
        if not engine_name:
            raise ValueError("engine_name required")
        return self._replace_provisioning(
            role_id,
            Provisioning(
                ProvisionKind.AI_ENGINE, engine_name, "",
            ),
        )

    def provision_with_human(
        self, role_id: str, va_name: str, contract_id: str,
    ) -> VoiceRole:
        if not va_name:
            raise ValueError("va_name required")
        if not contract_id:
            raise ValueError(
                "contract_id required for HUMAN_VA "
                "provisioning",
            )
        return self._replace_provisioning(
            role_id,
            Provisioning(
                ProvisionKind.HUMAN_VA, va_name, contract_id,
            ),
        )

    def vacate(self, role_id: str) -> VoiceRole:
        return self._replace_provisioning(
            role_id,
            Provisioning(ProvisionKind.VACANT, "", ""),
        )

    def roles_with_kind(
        self, kind: ProvisionKind,
    ) -> tuple[VoiceRole, ...]:
        return tuple(
            r for r in self._roles.values()
            if r.provisioned_by.kind == kind
        )

    def roles_for_archetype(
        self, archetype: Archetype,
    ) -> tuple[VoiceRole, ...]:
        return tuple(
            r for r in self._roles.values()
            if r.archetype == archetype
        )

    def provisioning_summary(self) -> dict[str, int]:
        out: dict[str, int] = {
            ProvisionKind.AI_ENGINE.value: 0,
            ProvisionKind.HUMAN_VA.value: 0,
            ProvisionKind.VACANT.value: 0,
            "total": 0,
        }
        for role in self._roles.values():
            out[role.provisioned_by.kind.value] += 1
            out["total"] += 1
        return out


__all__ = [
    "Archetype", "ProvisionKind",
    "RoleSpec", "RateCard", "Provisioning",
    "VoiceRole", "VoiceRoleRegistry",
    "BUILTIN_ROLES",
]
