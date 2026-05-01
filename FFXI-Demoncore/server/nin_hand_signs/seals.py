"""The twelve zodiac seals.

Per NIN_HAND_SIGNS.md, each seal is a held pose (~0.15s at base
speed) authored on the NIN base skeleton + blended additively onto
the locomotion layer so a sprinting NIN can sign without breaking
their lower-body run.

Element bias is *informational* — it tells the predictor + the
renderer which elemental schools a seal participates in. Final
spell identity comes from the full sequence, not any single seal.
"""
from __future__ import annotations

import dataclasses
import enum


class Seal(str, enum.Enum):
    """Twelve zodiac seals (Tora/I/Inu/Tatsu/Mi/Tori/Hitsuji/Uma/Saru/U/Ushi/Ne)."""
    TIGER = "tiger"
    BOAR = "boar"
    DOG = "dog"
    DRAGON = "dragon"
    SNAKE = "snake"
    BIRD = "bird"
    RAM = "ram"
    HORSE = "horse"
    MONKEY = "monkey"
    RABBIT = "rabbit"
    OX = "ox"
    RAT = "rat"


@dataclasses.dataclass(frozen=True)
class SealSpec:
    seal: Seal
    japanese: str           # "Tora" / "I" / "Inu" / etc.
    mnemonic: str           # short pose description
    element_bias: tuple[str, ...]


SEAL_SPECS: dict[Seal, SealSpec] = {
    Seal.TIGER: SealSpec(
        seal=Seal.TIGER, japanese="Tora",
        mnemonic="both hands up, index+middle vertical",
        element_bias=("fire", "kai"),
    ),
    Seal.BOAR: SealSpec(
        seal=Seal.BOAR, japanese="I",
        mnemonic="hands fist-pressed, thumbs out",
        element_bias=("earth",),
    ),
    Seal.DOG: SealSpec(
        seal=Seal.DOG, japanese="Inu",
        mnemonic="left fist closed, right palm covers",
        element_bias=("water",),
    ),
    Seal.DRAGON: SealSpec(
        seal=Seal.DRAGON, japanese="Tatsu",
        mnemonic="right hand on left, fingers interlaced",
        element_bias=("wind", "spec"),
    ),
    Seal.SNAKE: SealSpec(
        seal=Seal.SNAKE, japanese="Mi",
        mnemonic="hands palm-pressed, fingers interlaced",
        element_bias=("earth",),
    ),
    Seal.BIRD: SealSpec(
        seal=Seal.BIRD, japanese="Tori",
        mnemonic="hands palm-pressed, thumbs interlocked",
        element_bias=("wind",),
    ),
    Seal.RAM: SealSpec(
        seal=Seal.RAM, japanese="Hitsuji",
        mnemonic="hands palm-pressed, fingers wiggling",
        element_bias=("balance",),
    ),
    Seal.HORSE: SealSpec(
        seal=Seal.HORSE, japanese="Uma",
        mnemonic="left fist + right palm, slight hinge",
        element_bias=("fire",),
    ),
    Seal.MONKEY: SealSpec(
        seal=Seal.MONKEY, japanese="Saru",
        mnemonic="left fingers crossed over right thumb",
        element_bias=("metal", "ice"),
    ),
    Seal.RABBIT: SealSpec(
        seal=Seal.RABBIT, japanese="U",
        mnemonic="both hands fingers up, index extended",
        element_bias=("wind", "agility"),
    ),
    Seal.OX: SealSpec(
        seal=Seal.OX, japanese="Ushi",
        mnemonic="right hand cupped over left fist",
        element_bias=("thunder",),
    ),
    Seal.RAT: SealSpec(
        seal=Seal.RAT, japanese="Ne",
        mnemonic="both hands fingers wiggling, palm-down",
        element_bias=("utility",),
    ),
}
