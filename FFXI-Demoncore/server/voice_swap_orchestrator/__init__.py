"""Voice swap orchestrator — AI <-> human VA hot-swap.

The line-level state machine that lets a single line transition
from an AI default to a human take and (if needed) back again,
with QC gates between every move. This module is what
``voiced_cutscene`` and ``dialogue_lipsync`` actually ask
"which audio do I play?" — we own that answer per line.

Per-line provisioning lifecycle:

    AI_DEFAULT -> HUMAN_RECORDING -> HUMAN_QC -> HUMAN_LIVE
                                          \\
                                           -> DEPRECATED -> AI_DEFAULT

QC is deterministic in tests via a stub: any audio_uri
containing the substring ``"good"`` passes; ``"bad"`` fails. In
prod, ``QcReport`` is produced by Whisper transcription
(alignment_cer), ffprobe (duration_delta_pct), and a loudness
analyser.

Public surface
--------------
    LineProvisioning enum
    QcReport dataclass (frozen)
    LineState dataclass
    VoiceSwapOrchestrator
"""
from __future__ import annotations

import dataclasses
import datetime as _dt
import enum
import typing as t


class LineProvisioning(enum.Enum):
    AI_DEFAULT = "ai_default"
    HUMAN_RECORDING = "human_recording"
    HUMAN_QC = "human_qc"
    HUMAN_LIVE = "human_live"
    DEPRECATED = "deprecated"


# ---- QC thresholds — published targets ----
_QC_MAX_CER = 0.05            # 5% character error rate
_QC_MAX_DURATION_DELTA = 0.10  # +/- 10% vs AI version
_QC_LUFS_MIN = -23.0
_QC_LUFS_MAX = -16.0


@dataclasses.dataclass(frozen=True)
class QcReport:
    passed: bool
    alignment_cer: float
    duration_delta_pct: float
    loudness_lufs: float
    issues: tuple[str, ...]


@dataclasses.dataclass
class LineState:
    line_id: str
    role_id: str
    ai_track_uri: str
    state: LineProvisioning = LineProvisioning.AI_DEFAULT
    human_audio_uri: str = ""
    recorded_at: t.Optional[_dt.datetime] = None
    va_name: str = ""
    qc_report: t.Optional[QcReport] = None
    deprecation_reason: str = ""

    @property
    def active_uri(self) -> str:
        if self.state == LineProvisioning.HUMAN_LIVE:
            return self.human_audio_uri
        return self.ai_track_uri


# Pluggable QC stub — tests inject deterministic outcomes by
# putting "good" or "bad" in the human audio URI.
def _stub_qc(
    state: LineState, expected_duration_s: float,
) -> QcReport:
    uri = state.human_audio_uri.lower()
    if "bad" in uri:
        return QcReport(
            passed=False,
            alignment_cer=0.18,
            duration_delta_pct=0.22,
            loudness_lufs=-12.0,
            issues=(
                "stub qc: filename marked bad",
                "alignment_cer > 5%",
                "duration_delta > 10%",
                "loudness above -16 LUFS",
            ),
        )
    return QcReport(
        passed=True,
        alignment_cer=0.012,
        duration_delta_pct=0.04,
        loudness_lufs=-19.5,
        issues=(),
    )


@dataclasses.dataclass
class VoiceSwapOrchestrator:
    _lines: dict[str, LineState] = dataclasses.field(
        default_factory=dict,
    )
    _expected_duration: dict[str, float] = dataclasses.field(
        default_factory=dict,
    )
    _incident_log: list[str] = dataclasses.field(
        default_factory=list,
    )
    qc_fn: t.Callable[
        [LineState, float], QcReport,
    ] = dataclasses.field(default=_stub_qc)

    def register_line(
        self, line_id: str, role_id: str,
        ai_track_uri: str,
        *, expected_duration_s: float = 2.0,
    ) -> LineState:
        if not line_id:
            raise ValueError("line_id required")
        if line_id in self._lines:
            raise ValueError(
                f"line_id already registered: {line_id}",
            )
        if not ai_track_uri:
            raise ValueError("ai_track_uri required")
        if expected_duration_s <= 0:
            raise ValueError(
                "expected_duration_s must be > 0: "
                f"{expected_duration_s}",
            )
        st = LineState(
            line_id=line_id, role_id=role_id,
            ai_track_uri=ai_track_uri,
        )
        self._lines[line_id] = st
        self._expected_duration[line_id] = float(
            expected_duration_s,
        )
        return st

    def _get(self, line_id: str) -> LineState:
        if line_id not in self._lines:
            raise KeyError(
                f"unknown line_id: {line_id}",
            )
        return self._lines[line_id]

    def deliver_human_take(
        self, line_id: str, audio_uri: str,
        recorded_at: _dt.datetime, va_name: str,
    ) -> LineState:
        st = self._get(line_id)
        if st.state == LineProvisioning.HUMAN_LIVE:
            raise RuntimeError(
                "line is already HUMAN_LIVE; deprecate "
                "before re-delivering",
            )
        if not audio_uri:
            raise ValueError("audio_uri required")
        if not va_name:
            raise ValueError("va_name required")
        st.human_audio_uri = audio_uri
        st.recorded_at = recorded_at
        st.va_name = va_name
        st.state = LineProvisioning.HUMAN_RECORDING
        st.qc_report = None  # reset previous QC
        return st

    def qc_check(self, line_id: str) -> QcReport:
        st = self._get(line_id)
        if st.state not in (
            LineProvisioning.HUMAN_RECORDING,
            LineProvisioning.HUMAN_QC,
        ):
            raise RuntimeError(
                "qc_check requires HUMAN_RECORDING or "
                "HUMAN_QC state; got "
                f"{st.state.value}",
            )
        report = self.qc_fn(
            st, self._expected_duration[line_id],
        )
        st.qc_report = report
        st.state = LineProvisioning.HUMAN_QC
        return report

    def promote_to_live(self, line_id: str) -> LineState:
        st = self._get(line_id)
        if st.state != LineProvisioning.HUMAN_QC:
            raise RuntimeError(
                "promote_to_live requires HUMAN_QC; got "
                f"{st.state.value}",
            )
        if st.qc_report is None or not st.qc_report.passed:
            raise RuntimeError(
                "cannot promote — QC did not pass",
            )
        st.state = LineProvisioning.HUMAN_LIVE
        return st

    def deprecate(
        self, line_id: str, reason: str,
    ) -> LineState:
        st = self._get(line_id)
        if st.state == LineProvisioning.AI_DEFAULT:
            raise RuntimeError(
                "line is on AI_DEFAULT; nothing to "
                "deprecate",
            )
        st.state = LineProvisioning.DEPRECATED
        st.deprecation_reason = reason
        self._incident_log.append(
            f"{line_id}: {reason}",
        )
        # Roll back to AI track for serving — DEPRECATED is a
        # logical marker, but ``active_uri`` should fall back
        # to the AI track until a fresh delivery comes in.
        return st

    def rollback_to_ai(self, line_id: str) -> LineState:
        """After deprecate, drop the line back to AI_DEFAULT
        and clear the human delivery slot. This is the actual
        production-rollback knob — DEPRECATED is the audit
        receipt; AI_DEFAULT is the served state.
        """
        st = self._get(line_id)
        if st.state != LineProvisioning.DEPRECATED:
            raise RuntimeError(
                "rollback_to_ai requires DEPRECATED; got "
                f"{st.state.value}",
            )
        st.state = LineProvisioning.AI_DEFAULT
        st.human_audio_uri = ""
        st.recorded_at = None
        st.va_name = ""
        st.qc_report = None
        return st

    def state_of(self, line_id: str) -> LineProvisioning:
        return self._get(line_id).state

    def active_uri_for(self, line_id: str) -> str:
        return self._get(line_id).active_uri

    def percent_human_voiced(self, role_id: str) -> float:
        lines = [
            l for l in self._lines.values()
            if l.role_id == role_id
        ]
        if not lines:
            return 0.0
        live = sum(
            1 for l in lines
            if l.state == LineProvisioning.HUMAN_LIVE
        )
        return round(100.0 * live / len(lines), 2)

    def provisioning_dashboard(self) -> dict[str, float]:
        roles = sorted({
            l.role_id for l in self._lines.values()
        })
        return {
            r: self.percent_human_voiced(r) for r in roles
        }

    def incident_log(self) -> tuple[str, ...]:
        return tuple(self._incident_log)


__all__ = [
    "LineProvisioning", "QcReport", "LineState",
    "VoiceSwapOrchestrator",
]
