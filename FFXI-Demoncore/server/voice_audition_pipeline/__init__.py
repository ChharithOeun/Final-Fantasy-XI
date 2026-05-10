"""Voice audition pipeline — the funnel for real voice actors.

When the project is ready to upgrade a role from AI to a real
human, the producer opens an audition. VAs submit demo reads
against the canon-aware ``AuditionPacket``. Screening is a
human pass; callbacks are a live read with the director;
booking flips ``voice_role_registry`` to HUMAN_VA.

Lifecycle:

    SUBMITTED -> SCREENED -> CALLBACK -> BOOKED
                                   \\
                                    -> REJECTED  (terminal)
                       \\
                        -> REJECTED  (terminal)

Recording spec is enforced on submit so we never burn screener
time on bad audio. Anyone whose mic floor isn't 48k/24bit gets
a polite hard reject with the spec attached.

Public surface
--------------
    AuditionState enum
    Decision enum
    RecordingSpec dataclass (frozen)
    AuditionPacket dataclass (frozen)
    Submission dataclass
    AuditionPipeline
"""
from __future__ import annotations

import dataclasses
import enum
import itertools
import typing as t


class AuditionState(enum.Enum):
    SUBMITTED = "submitted"
    SCREENED = "screened"
    CALLBACK = "callback"
    BOOKED = "booked"
    REJECTED = "rejected"


class Decision(enum.Enum):
    PASS = "pass"   # advances toward callback / booking
    HOLD = "hold"   # stay in current state
    REJECT = "reject"


class AudioFormat(enum.Enum):
    WAV = "wav"
    FLAC = "flac"
    AIFF = "aiff"


# Broadcast loudness window — EBU R128-ish, the band working
# studios accept for spoken-word delivery.
_LUFS_MIN = -23.0
_LUFS_MAX = -16.0
_MIN_SAMPLE_RATE = 48_000
_MIN_BIT_DEPTH = 24
_MIN_ROOM_TONE_S = 3.0


@dataclasses.dataclass(frozen=True)
class RecordingSpec:
    sample_rate_hz: int
    bit_depth: int
    fmt: AudioFormat
    room_tone_seconds: float
    broadcast_loudness_lufs: float


def _validate_spec(spec: RecordingSpec) -> None:
    if spec.sample_rate_hz < _MIN_SAMPLE_RATE:
        raise ValueError(
            f"sample_rate_hz must be >= {_MIN_SAMPLE_RATE}: "
            f"{spec.sample_rate_hz}",
        )
    if spec.bit_depth < _MIN_BIT_DEPTH:
        raise ValueError(
            f"bit_depth must be >= {_MIN_BIT_DEPTH}: "
            f"{spec.bit_depth}",
        )
    if spec.room_tone_seconds < _MIN_ROOM_TONE_S:
        raise ValueError(
            f"room_tone_seconds must be >= "
            f"{_MIN_ROOM_TONE_S}: {spec.room_tone_seconds}",
        )
    lufs = spec.broadcast_loudness_lufs
    if not (_LUFS_MIN <= lufs <= _LUFS_MAX):
        raise ValueError(
            f"broadcast_loudness_lufs out of range "
            f"[{_LUFS_MIN}..{_LUFS_MAX}]: {lufs}",
        )


@dataclasses.dataclass(frozen=True)
class AuditionPacket:
    """The packet the casting director hands a VA. 3-5 canon
    sample lines, 1 wild line in character, plus director
    notes describing the vibe.
    """
    role_id: str
    sample_lines: tuple[str, ...]
    wild_line: str
    performance_notes: str

    def __post_init__(self) -> None:
        if not (3 <= len(self.sample_lines) <= 5):
            raise ValueError(
                f"need 3-5 sample lines; got "
                f"{len(self.sample_lines)}",
            )
        if not self.wild_line:
            raise ValueError("wild_line required")


@dataclasses.dataclass
class Submission:
    submission_id: str
    role_id: str
    va_name: str
    spec: RecordingSpec
    state: AuditionState
    flags: list[str] = dataclasses.field(default_factory=list)
    screener: str = ""
    director_notes: str = ""
    rejection_reason: str = ""
    contract_id: str = ""


@dataclasses.dataclass
class AuditionPipeline:
    """Stateful audition queue. ``open_audition`` registers a
    packet for a role; subsequent submissions are pinned to
    that role.
    """
    _packets: dict[str, AuditionPacket] = dataclasses.field(
        default_factory=dict,
    )
    _submissions: dict[str, Submission] = dataclasses.field(
        default_factory=dict,
    )
    _id_seq: t.Iterator[int] = dataclasses.field(
        default_factory=lambda: itertools.count(1),
    )

    def open_audition(
        self, role_id: str, packet: AuditionPacket,
    ) -> AuditionPacket:
        if packet.role_id != role_id:
            raise ValueError(
                "packet.role_id mismatches argument: "
                f"{packet.role_id} != {role_id}",
            )
        if role_id in self._packets:
            raise ValueError(
                f"audition already open for {role_id}",
            )
        self._packets[role_id] = packet
        return packet

    def has_open_audition(self, role_id: str) -> bool:
        return role_id in self._packets

    def submit(
        self, role_id: str, va_name: str,
        recording_spec: RecordingSpec,
    ) -> Submission:
        if role_id not in self._packets:
            raise ValueError(
                f"no open audition for {role_id}",
            )
        if not va_name:
            raise ValueError("va_name required")
        _validate_spec(recording_spec)
        sub_id = f"sub_{next(self._id_seq):05d}"
        sub = Submission(
            submission_id=sub_id, role_id=role_id,
            va_name=va_name, spec=recording_spec,
            state=AuditionState.SUBMITTED,
        )
        self._submissions[sub_id] = sub
        return sub

    def _get(self, submission_id: str) -> Submission:
        if submission_id not in self._submissions:
            raise KeyError(
                f"unknown submission_id: {submission_id}",
            )
        return self._submissions[submission_id]

    def screen(
        self, submission_id: str,
        decision: Decision, screener: str,
    ) -> Submission:
        sub = self._get(submission_id)
        if sub.state != AuditionState.SUBMITTED:
            raise RuntimeError(
                f"can only screen SUBMITTED, not "
                f"{sub.state.value}",
            )
        if not screener:
            raise ValueError("screener required")
        sub.screener = screener
        if decision == Decision.PASS:
            sub.state = AuditionState.SCREENED
        elif decision == Decision.REJECT:
            sub.state = AuditionState.REJECTED
            sub.rejection_reason = "screened_reject"
        # HOLD leaves state unchanged
        return sub

    def callback(
        self, submission_id: str, director_notes: str,
    ) -> Submission:
        sub = self._get(submission_id)
        if sub.state != AuditionState.SCREENED:
            raise RuntimeError(
                f"can only callback SCREENED, not "
                f"{sub.state.value}",
            )
        sub.state = AuditionState.CALLBACK
        sub.director_notes = director_notes
        return sub

    def book(
        self, submission_id: str, contract_id: str,
    ) -> Submission:
        sub = self._get(submission_id)
        if sub.state != AuditionState.CALLBACK:
            raise RuntimeError(
                "can't book without callback first; "
                f"current state: {sub.state.value}",
            )
        if not contract_id:
            raise ValueError("contract_id required to book")
        sub.state = AuditionState.BOOKED
        sub.contract_id = contract_id
        return sub

    def reject(
        self, submission_id: str, reason: str,
    ) -> Submission:
        sub = self._get(submission_id)
        if sub.state in (
            AuditionState.BOOKED, AuditionState.REJECTED,
        ):
            raise RuntimeError(
                f"cannot reject from terminal state "
                f"{sub.state.value}",
            )
        sub.state = AuditionState.REJECTED
        sub.rejection_reason = reason
        return sub

    def submissions_for(
        self, role_id: str,
    ) -> tuple[Submission, ...]:
        return tuple(
            s for s in self._submissions.values()
            if s.role_id == role_id
        )

    def state_of(self, submission_id: str) -> AuditionState:
        return self._get(submission_id).state

    def flag(
        self, submission_id: str, flagger: str, reason: str,
    ) -> Submission:
        """Peer flag — booked VAs may leave a screening flag.
        Anti-gatekeep: flags do NOT veto, they're advisory.
        """
        sub = self._get(submission_id)
        sub.flags.append(f"{flagger}:{reason}")
        return sub


__all__ = [
    "AuditionState", "Decision", "AudioFormat",
    "RecordingSpec", "AuditionPacket",
    "Submission", "AuditionPipeline",
]
