"""Shadow Genkai — Fomor beastmen quest chain unlocking ML 100-150.

After a job hits Job Master (2100 JP), the level cap stays at 99
until the player completes the first Shadow Genkai. Each
subsequent Shadow Genkai unlocks +5 cap, all the way to 150.

Quest givers are Fomor beastmen — corrupted, hollow shadows of
the canonical beastmen races, hiding in zones the original game
never opened up. Each one is a multi-stage challenge: defeat
the Fomor lord at his lair, often with a unique gimmick.

The Shadow Genkai chain is per-job. WAR Shadow Genkai unlocks
WAR's ML 100, but does NOT unlock RDM's ML 100 — each job
walks the chain independently. (Same pattern as Job Points.)

Public surface
--------------
    ShadowGenkai dataclass / SHADOW_GENKAI_CHAIN
    ShadowGenkaiBoss dataclass (the Fomor beastman)
    SHADOW_GENKAI_BY_TARGET (target_level -> quest)
    PlayerShadowGenkai
        .available_quest(current_cap, has_job_master) -> Optional[ShadowGenkai]
        .complete(quest_id) -> bool
        .completed_target_levels property
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class ShadowGenkaiBoss:
    """The Fomor beastman quest-giver / final fight."""
    boss_id: str
    name: str
    title: str
    race: str       # Fomor variant of canonical beastman race
    zone: str       # unreleased shadow zone


@dataclasses.dataclass(frozen=True)
class ShadowGenkai:
    """One link in the chain. Completing it raises the cap to
    *raises_cap_to*. Requires the previous link in the chain
    (or Job Master, for the first link)."""
    quest_id: str
    label: str
    requires_cap: int          # current cap must be at least this
    raises_cap_to: int         # cap after completion
    boss: ShadowGenkaiBoss
    flavor: str = ""


# ---------------------------------------------------------------------
# The Fomor beastmen — quest givers and final fights.
# These are the Shadow Lords of the Hollow Reaches; each rules a
# corrupted echo of a canonical beastman zone.
# ---------------------------------------------------------------------
_BOSSES: tuple[ShadowGenkaiBoss, ...] = (
    ShadowGenkaiBoss(
        "vorgath_sundered_crown",
        "Vorgath",
        "the Sundered Crown",
        race="Fomor Orc Warlord",
        zone="shadow_davoi",
    ),
    ShadowGenkaiBoss(
        "khaavex_iceblood",
        "Khaa'Vex",
        "Iceblood, Matron of the Withered Mire",
        race="Fomor Quadav Matron",
        zone="shadow_beadeaux",
    ),
    ShadowGenkaiBoss(
        "zharzag_hollow_sage",
        "Zharzag",
        "the Hollow Sage",
        race="Fomor Yagudo Prelate",
        zone="shadow_castle_oztroja",
    ),
    ShadowGenkaiBoss(
        "morrho_wordless",
        "Mor'rho",
        "the Wordless Tyrant",
        race="Fomor Goblin Overlord",
        zone="shadow_movalpolos",
    ),
    ShadowGenkaiBoss(
        "skhalya_drowned_tide",
        "Skhal'ya",
        "the Drowned Tide",
        race="Fomor Sahagin Patriarch",
        zone="shadow_sea_serpent_grotto",
    ),
    ShadowGenkaiBoss(
        "trokhaeb_black_lantern",
        "Tro'Khaeb",
        "the Black Lantern, Inquisitor of the Sunless",
        race="Fomor Tonberry Inquisitor",
        zone="shadow_kuftal_tunnel",
    ),
    ShadowGenkaiBoss(
        "kael_nox_forge_heart",
        "Kael Nox",
        "the Forge-Heart",
        race="Fomor Imp Mistress",
        zone="shadow_temple_of_uggalepih",
    ),
    ShadowGenkaiBoss(
        "ssylvyrr_hollow_voice",
        "Ssylvyrr",
        "the Hollow Voice, Choirmaster of Echoing Halls",
        race="Fomor Lamia Choirmaster",
        zone="shadow_aydeewa_subterrane",
    ),
    ShadowGenkaiBoss(
        "moktor_iron_verdict",
        "Mok'tor",
        "the Iron Verdict, Magistrate of Ironward",
        race="Fomor Troll Magistrate",
        zone="shadow_halvung_keep",
    ),
    ShadowGenkaiBoss(
        "hriath_echoed_storm",
        "Hriath",
        "the Echoed Storm",
        race="Fomor Mamool Ja Warlock",
        zone="shadow_mamool_ja_isle",
    ),
    ShadowGenkaiBoss(
        "asmodeus_voice_shadowlands",
        "Asmodeus",
        "Voice of the Shadowlands",
        race="Fomor Lord of Lords (final phase)",
        zone="shadow_sanctum",
    ),
)


def _quest(idx: int, *, requires_cap: int, raises_cap_to: int,
           label: str, flavor: str) -> ShadowGenkai:
    return ShadowGenkai(
        quest_id=f"shadow_genkai_{raises_cap_to}",
        label=label,
        requires_cap=requires_cap,
        raises_cap_to=raises_cap_to,
        boss=_BOSSES[idx],
        flavor=flavor,
    )


# Eleven Shadow Genkai quests: ML 100, 105, 110, ..., 150.
SHADOW_GENKAI_CHAIN: tuple[ShadowGenkai, ...] = (
    _quest(0, requires_cap=99, raises_cap_to=100,
           label="The Sundered Crown",
           flavor="Vorgath claims the right of dominion. "
                  "Prove your blade transcends the mortal cap."),
    _quest(1, requires_cap=100, raises_cap_to=105,
           label="Iceblood Matron",
           flavor="Khaa'Vex's lullaby freezes time itself. "
                  "Break the song to break the cap."),
    _quest(2, requires_cap=105, raises_cap_to=110,
           label="The Hollow Sage",
           flavor="Zharzag has read every prophecy of your "
                  "death. Author a different one."),
    _quest(3, requires_cap=110, raises_cap_to=115,
           label="The Wordless Tyrant",
           flavor="Mor'rho speaks through machinery alone. "
                  "Silence the engine."),
    _quest(4, requires_cap=115, raises_cap_to=120,
           label="The Drowned Tide",
           flavor="Skhal'ya's grotto answers every spell with "
                  "its own dark mirror."),
    _quest(5, requires_cap=120, raises_cap_to=125,
           label="The Black Lantern",
           flavor="Tro'Khaeb's lantern judges by what you carry. "
                  "Carry only what matters."),
    _quest(6, requires_cap=125, raises_cap_to=130,
           label="The Forge-Heart",
           flavor="Kael Nox is the temple's last forge. "
                  "Outlast her hammer."),
    _quest(7, requires_cap=130, raises_cap_to=135,
           label="The Hollow Voice",
           flavor="Ssylvyrr's choir sings a name that is "
                  "almost yours. Reject it."),
    _quest(8, requires_cap=135, raises_cap_to=140,
           label="The Iron Verdict",
           flavor="Mok'tor presides over a court of one. "
                  "Answer all charges."),
    _quest(9, requires_cap=140, raises_cap_to=145,
           label="The Echoed Storm",
           flavor="Hriath's storm turns your own spells back. "
                  "Cast carefully."),
    _quest(10, requires_cap=145, raises_cap_to=150,
           label="Voice of the Shadowlands",
           flavor="Asmodeus speaks for everything you have "
                  "ever lost. End the conversation."),
)


SHADOW_GENKAI_BY_TARGET: dict[int, ShadowGenkai] = {
    q.raises_cap_to: q for q in SHADOW_GENKAI_CHAIN
}


@dataclasses.dataclass
class PlayerShadowGenkai:
    """Per-player + per-job Shadow Genkai progress."""
    player_id: str
    job: str            # job_id key from jp_gifts.JobId
    completed_target_levels: set[int] = dataclasses.field(
        default_factory=set,
    )

    @property
    def current_cap(self) -> int:
        if not self.completed_target_levels:
            return 99
        return max(self.completed_target_levels)

    def available_quest(self, *, has_job_master: bool
                         ) -> t.Optional[ShadowGenkai]:
        """Next quest the player is eligible to attempt."""
        # Job Master is required for the very first quest only;
        # once you've cleared at least one Shadow Genkai you've
        # already proven Job Master, so we skip the gate.
        if not self.completed_target_levels and not has_job_master:
            return None
        for q in SHADOW_GENKAI_CHAIN:
            if q.raises_cap_to in self.completed_target_levels:
                continue
            if self.current_cap < q.requires_cap:
                return None
            return q
        return None

    def complete(self, *, quest_id: str,
                  has_job_master: bool) -> bool:
        avail = self.available_quest(has_job_master=has_job_master)
        if avail is None or avail.quest_id != quest_id:
            return False
        self.completed_target_levels.add(avail.raises_cap_to)
        return True


__all__ = [
    "ShadowGenkaiBoss", "ShadowGenkai",
    "SHADOW_GENKAI_CHAIN", "SHADOW_GENKAI_BY_TARGET",
    "PlayerShadowGenkai",
]
