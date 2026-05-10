"""Showcase choreography — demo walkthrough scripted beats.

The five-minute Bastok Markets demo's running order in
code. Each beat is one scripted moment — the player
spawning into the Mines tutorial, emerging into Markets
under god-rays through smelter haze, Cid forging mid-
cinematic, Volker handing off the quest, the crowd's
ambient walk, the bandit raid trigger, the magic-burst
skillchain demo on Iron Eater's shadow, the cinematic
boss intro of Iron Eater himself — wired to a trigger,
a duration, an optional dialogue handoff, an optional
mob spawn list, a music cue, and a fallback if the
player skips it.

The director_ai layer reads ``camera_handoff`` to pick a
matching shot kind. The voice_role_registry layer resolves
``dialogue_line_ids`` against the casting book. The render
queue picks up ``music_cue_id`` for the trailer master.

Public surface
--------------
    BeatTrigger enum
    Beat dataclass (frozen)
    ChoreographySequence dataclass (frozen)
    ShowcaseChoreography
    BUILTIN_BASTOK_MARKETS_DEMO ChoreographySequence
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class BeatTrigger(enum.Enum):
    PLAYER_ENTERS_VOLUME = "player_enters_volume"
    TIMER_AT_T = "timer_at_t"
    DIALOGUE_END = "dialogue_end"
    SKILLCHAIN_COMPLETED = "skillchain_completed"
    MOB_PHASE_X = "mob_phase_x"


@dataclasses.dataclass(frozen=True)
class Beat:
    beat_id: str
    sequence_index: int
    trigger: BeatTrigger
    zone_id: str
    location_volume_id: str
    camera_handoff: str  # director_ai shot_kind hint
    dialogue_line_ids: tuple[str, ...]
    expected_duration_s: float
    mob_spawns: tuple[str, ...]
    music_cue_id: str
    fallback_if_skipped: str  # beat_id to jump to, or ""


@dataclasses.dataclass(frozen=True)
class ChoreographySequence:
    seq_name: str
    title: str
    beats: tuple[Beat, ...]


# ----------------------------------------------------------------
# Bastok Markets demo sequence — eight beats end-to-end.
# ----------------------------------------------------------------
def _beat(
    beat_id: str,
    idx: int,
    trigger: BeatTrigger,
    volume: str,
    handoff: str,
    dialogue: tuple[str, ...] = (),
    duration: float = 8.0,
    spawns: tuple[str, ...] = (),
    music: str = "",
    fallback: str = "",
) -> Beat:
    return Beat(
        beat_id=beat_id,
        sequence_index=idx,
        trigger=trigger,
        zone_id="bastok_markets",
        location_volume_id=volume,
        camera_handoff=handoff,
        dialogue_line_ids=dialogue,
        expected_duration_s=duration,
        mob_spawns=spawns,
        music_cue_id=music,
        fallback_if_skipped=fallback,
    )


def _build_bastok_demo() -> ChoreographySequence:
    beats = (
        _beat(
            "spawn_in_mines", 0,
            BeatTrigger.PLAYER_ENTERS_VOLUME,
            volume="vol_mines_spawn",
            handoff="ESTABLISHING_INT_TIGHT",
            dialogue=("vline_narrator_intro_001",),
            duration=12.0,
            music="cue_mines_amb_intro",
            fallback="emerge_to_markets",
        ),
        _beat(
            "emerge_to_markets", 1,
            BeatTrigger.PLAYER_ENTERS_VOLUME,
            volume="vol_markets_north_arch",
            handoff="WIDE_GOD_RAYS",
            dialogue=(),
            duration=14.0,
            music="cue_markets_arrival",
            fallback="cid_forging",
        ),
        _beat(
            "cid_forging", 2,
            BeatTrigger.PLAYER_ENTERS_VOLUME,
            volume="vol_cid_workshop",
            handoff="MEDIUM_OVER_SHOULDER",
            dialogue=(
                "vline_cid_forging_001",
                "vline_cid_forging_002",
            ),
            duration=22.0,
            music="cue_workshop_loop",
            fallback="volker_quest_handoff",
        ),
        _beat(
            "volker_quest_handoff", 3,
            BeatTrigger.DIALOGUE_END,
            volume="vol_volker_briefing",
            handoff="TWO_SHOT_EYE_LINE",
            dialogue=(
                "vline_volker_handoff_001",
                "vline_volker_handoff_002",
                "vline_volker_handoff_003",
            ),
            duration=28.0,
            music="cue_volker_theme",
            fallback="crowd_ambient_walk",
        ),
        _beat(
            "crowd_ambient_walk", 4,
            BeatTrigger.TIMER_AT_T,
            volume="vol_markets_main_concourse",
            handoff="DOLLY_FOLLOW",
            dialogue=(),
            duration=20.0,
            music="cue_markets_loop",
            fallback="bandit_raid_trigger",
        ),
        _beat(
            "bandit_raid_trigger", 5,
            BeatTrigger.PLAYER_ENTERS_VOLUME,
            volume="vol_markets_clutter_alley",
            handoff="HANDHELD_WHIP",
            dialogue=("vline_bandit_yell_001",),
            duration=10.0,
            spawns=(
                "mob_bandit_a", "mob_bandit_b", "mob_bandit_c",
            ),
            music="cue_combat_bandits",
            fallback="iron_eater_shadow_skillchain",
        ),
        _beat(
            "iron_eater_shadow_skillchain", 6,
            BeatTrigger.SKILLCHAIN_COMPLETED,
            volume="vol_iron_eater_shadow",
            handoff="LOW_HERO_ANGLE",
            dialogue=("vline_skillchain_callout_001",),
            duration=8.0,
            spawns=("mob_iron_eater_shadow",),
            music="cue_skillchain_burst",
            fallback="iron_eater_intro",
        ),
        _beat(
            "iron_eater_intro", 7,
            BeatTrigger.MOB_PHASE_X,
            volume="vol_iron_eater_arena",
            handoff="CINEMATIC_BOSS_REVEAL",
            dialogue=(
                "vline_iron_eater_intro_001",
                "vline_iron_eater_intro_002",
            ),
            duration=18.0,
            spawns=("mob_iron_eater_boss",),
            music="cue_iron_eater_theme",
            fallback="",  # terminal beat
        ),
    )
    return ChoreographySequence(
        seq_name="bastok_markets_demo",
        title="Bastok Markets — Five-Minute Demo",
        beats=beats,
    )


BUILTIN_BASTOK_MARKETS_DEMO: ChoreographySequence = (
    _build_bastok_demo()
)


# ----------------------------------------------------------------
# ShowcaseChoreography
# ----------------------------------------------------------------
@dataclasses.dataclass
class ShowcaseChoreography:
    """In-memory choreography book.

    Holds named sequences. Beats can be looked up by id within
    a sequence; advance() returns the next beat to play given
    the current state.
    """
    _sequences: dict[str, ChoreographySequence] = (
        dataclasses.field(default_factory=dict)
    )

    @classmethod
    def with_bastok_demo(cls) -> "ShowcaseChoreography":
        sc = cls()
        sc.register_sequence(BUILTIN_BASTOK_MARKETS_DEMO)
        return sc

    def register_sequence(
        self, seq: ChoreographySequence,
    ) -> ChoreographySequence:
        if not seq.seq_name:
            raise ValueError("seq_name required")
        if seq.seq_name in self._sequences:
            raise ValueError(
                f"sequence already registered: {seq.seq_name}",
            )
        if not seq.beats:
            raise ValueError(
                "sequence requires at least one beat",
            )
        # Beat-id uniqueness within the sequence.
        ids = [b.beat_id for b in seq.beats]
        if len(set(ids)) != len(ids):
            raise ValueError(
                "duplicate beat_id within sequence",
            )
        # sequence_index must be monotonic non-decreasing.
        for i in range(1, len(seq.beats)):
            if (
                seq.beats[i].sequence_index
                < seq.beats[i - 1].sequence_index
            ):
                raise ValueError(
                    "sequence_index must be monotonic",
                )
        self._sequences[seq.seq_name] = seq
        return seq

    def register_beat(
        self,
        seq_name: str,
        beat: Beat,
    ) -> ChoreographySequence:
        if seq_name not in self._sequences:
            raise KeyError(
                f"unknown sequence: {seq_name}",
            )
        seq = self._sequences[seq_name]
        for b in seq.beats:
            if b.beat_id == beat.beat_id:
                raise ValueError(
                    f"duplicate beat_id: {beat.beat_id}",
                )
        if seq.beats and (
            beat.sequence_index < seq.beats[-1].sequence_index
        ):
            raise ValueError(
                "appended beat must have non-decreasing index",
            )
        new_beats = seq.beats + (beat,)
        new_seq = dataclasses.replace(seq, beats=new_beats)
        self._sequences[seq_name] = new_seq
        return new_seq

    def lookup_sequence(
        self, seq_name: str,
    ) -> ChoreographySequence:
        if seq_name not in self._sequences:
            raise KeyError(
                f"unknown sequence: {seq_name}",
            )
        return self._sequences[seq_name]

    def sequence_for_demo(
        self, seq_name: str,
    ) -> tuple[Beat, ...]:
        return self.lookup_sequence(seq_name).beats

    def beat_at_index(
        self, seq_name: str, idx: int,
    ) -> Beat:
        beats = self.sequence_for_demo(seq_name)
        for b in beats:
            if b.sequence_index == idx:
                return b
        raise KeyError(
            f"no beat at index {idx} in {seq_name}",
        )

    def advance(
        self,
        seq_name: str,
        current_beat_id: str,
    ) -> t.Optional[Beat]:
        beats = self.sequence_for_demo(seq_name)
        for i, b in enumerate(beats):
            if b.beat_id == current_beat_id:
                if i + 1 < len(beats):
                    return beats[i + 1]
                return None
        raise KeyError(
            f"unknown beat_id in {seq_name}: {current_beat_id}",
        )

    def fallback_for(
        self,
        seq_name: str,
        beat_id: str,
    ) -> t.Optional[Beat]:
        beats = self.sequence_for_demo(seq_name)
        target_fallback = ""
        for b in beats:
            if b.beat_id == beat_id:
                target_fallback = b.fallback_if_skipped
                break
        else:
            raise KeyError(
                f"unknown beat: {beat_id}",
            )
        if not target_fallback:
            return None
        for b in beats:
            if b.beat_id == target_fallback:
                return b
        raise ValueError(
            f"fallback target {target_fallback!r} not found",
        )

    def total_duration_s(self, seq_name: str) -> float:
        return round(sum(
            b.expected_duration_s
            for b in self.sequence_for_demo(seq_name)
        ), 3)

    def all_dialogue_line_ids(
        self, seq_name: str,
    ) -> tuple[str, ...]:
        out: list[str] = []
        for b in self.sequence_for_demo(seq_name):
            out.extend(b.dialogue_line_ids)
        return tuple(out)

    def all_mob_spawns(
        self, seq_name: str,
    ) -> tuple[str, ...]:
        out: list[str] = []
        for b in self.sequence_for_demo(seq_name):
            out.extend(b.mob_spawns)
        return tuple(out)

    def all_music_cues(
        self, seq_name: str,
    ) -> tuple[str, ...]:
        return tuple(
            b.music_cue_id
            for b in self.sequence_for_demo(seq_name)
            if b.music_cue_id
        )

    def validate_sequence(self, seq_name: str) -> None:
        """Raise if any beat's fallback points to a beat that
        doesn't exist in the sequence, or if a beat is
        unreachable.
        """
        seq = self.lookup_sequence(seq_name)
        beat_ids = {b.beat_id for b in seq.beats}
        for b in seq.beats:
            if (
                b.fallback_if_skipped
                and b.fallback_if_skipped not in beat_ids
            ):
                raise ValueError(
                    f"beat {b.beat_id} has unknown fallback "
                    f"{b.fallback_if_skipped!r}",
                )
        # Reachability — first beat is always reachable; every
        # subsequent beat must be either a fallback target or
        # an immediate successor.
        if not seq.beats:
            return
        reachable: set[str] = {seq.beats[0].beat_id}
        for i, b in enumerate(seq.beats):
            if b.beat_id not in reachable:
                raise ValueError(
                    f"beat {b.beat_id} is unreachable",
                )
            # Successor.
            if i + 1 < len(seq.beats):
                reachable.add(seq.beats[i + 1].beat_id)
            # Fallback target.
            if b.fallback_if_skipped:
                reachable.add(b.fallback_if_skipped)


__all__ = [
    "BeatTrigger", "Beat", "ChoreographySequence",
    "ShowcaseChoreography",
    "BUILTIN_BASTOK_MARKETS_DEMO",
]
