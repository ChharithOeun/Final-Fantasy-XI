"""Net lag compensation — rewinds server time to verify hits
based on what the client saw.

The eternal problem in netcode: the client clicks "fire" at
T=1.000s. The server receives the packet at T=1.080s (80ms
of network latency). By the time the server processes the
shot, the target — who was at position X when the client
clicked — has moved 80ms further along. If the server
checks the *current* position, the client's well-aimed shot
misses. If the server trusts the *client*, cheaters win.

The compromise — and it's what every shooter from
Counter-Strike to Overwatch to Valorant uses — is
server-side rewind. The server keeps the last 1000ms of
authoritative snapshots for every entity. When a hit claim
arrives, the server rewinds the *target* to where the
*client saw it*, checks the geometry, and accepts or
rejects.

This module is that rewind + the anti-cheat checks that go
with it.

Anti-cheat philosophy: trust the server, verify the client.
The client can claim "I hit X at position Y at time T".
The server validates that:
    - ping is sane (0-500ms, anything beyond was probably
      packet loss or a hack)
    - the attacker's claimed position is reachable from
      their last server snapshot (no teleport hacks)
    - the weapon was actually in range
    - line-of-sight wasn't broken
    - the rate-of-fire matches the weapon catalog

Detected cheat signals are logged per-player. The
anti_cheese module subscribes to detect_cheats_for; multiple
signals across short windows lead to escalation (warn ->
shadowban -> ban).

Public surface
--------------
    WeaponKind enum
    CheatSignal enum
    HitClaim dataclass (frozen)
    ClaimResult dataclass (frozen)
    NetLagCompensationSystem
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


# How far back the server keeps history (ms). Anything older
# than this is pruned; claims that ask for older are
# rejected with REWIND_PAST_HISTORY.
HISTORY_WINDOW_MS = 1000

# Allowed ping window. Anything outside this and we reject
# the claim + flag PING_TOO_HIGH.
MIN_PING_MS = 0
MAX_PING_MS = 500

# Server-side jitter buffer — target position can be +/- this
# many cm from the rewound position.
POSITION_TOLERANCE_CM = 30.0

# Max believable movement speed (m/s). If the attacker
# claims to be further from their last snapshot than
# (MAX_SPEED * dt + tolerance), they teleported.
MAX_MOVE_SPEED_MS = 15.0  # sprint speed cap

# Reach tolerance for "physically reachable" (meters).
REACH_TOLERANCE_M = 1.0


class WeaponKind(enum.Enum):
    DAGGER = "dagger"
    SWORD = "sword"
    GREAT_SWORD = "great_sword"
    KATANA = "katana"
    POLEARM = "polearm"
    STAFF = "staff"
    BOW = "bow"
    CROSSBOW = "crossbow"
    SPELL_SHORT = "spell_short"
    SPELL_LONG = "spell_long"
    HAND_TO_HAND = "h2h"


# Effective range in meters per weapon kind.
_RANGE_BY_WEAPON: dict[WeaponKind, float] = {
    WeaponKind.HAND_TO_HAND: 2.0,
    WeaponKind.DAGGER: 2.5,
    WeaponKind.SWORD: 3.0,
    WeaponKind.KATANA: 3.0,
    WeaponKind.GREAT_SWORD: 3.5,
    WeaponKind.POLEARM: 4.5,
    WeaponKind.STAFF: 3.5,
    WeaponKind.BOW: 25.0,
    WeaponKind.CROSSBOW: 22.0,
    WeaponKind.SPELL_SHORT: 20.0,
    WeaponKind.SPELL_LONG: 35.0,
}

# Minimum seconds between consecutive hits for the weapon
# (rapid-fire detection floor).
_MIN_INTERVAL_BY_WEAPON: dict[WeaponKind, float] = {
    WeaponKind.HAND_TO_HAND: 0.5,
    WeaponKind.DAGGER: 0.7,
    WeaponKind.SWORD: 1.0,
    WeaponKind.KATANA: 0.9,
    WeaponKind.GREAT_SWORD: 2.5,
    WeaponKind.POLEARM: 2.0,
    WeaponKind.STAFF: 1.5,
    WeaponKind.BOW: 1.2,
    WeaponKind.CROSSBOW: 1.5,
    WeaponKind.SPELL_SHORT: 2.0,
    WeaponKind.SPELL_LONG: 3.5,
}


class CheatSignal(enum.Enum):
    TELEPORT_HACK = "teleport_hack"
    IMPOSSIBLE_REACH = "impossible_reach"
    PING_TOO_HIGH = "ping_too_high"
    RAPID_FIRE_BEYOND_RATE = "rapid_fire_beyond_rate"
    OUT_OF_RANGE_REPEATED = "out_of_range_repeated"
    BROKEN_LOS = "broken_los"
    REWIND_PAST_HISTORY = "rewind_past_history"
    POSITION_MISMATCH = "position_mismatch"


@dataclasses.dataclass(frozen=True)
class HitClaim:
    claimer_player_id: str
    target_entity_id: str
    weapon_kind: WeaponKind
    claimed_at_client_ms: int
    claimed_target_pos_xyz: tuple[float, float, float]
    claimed_attacker_pos_xyz: tuple[float, float, float]
    server_received_ms: int
    has_line_of_sight: bool = True


@dataclasses.dataclass(frozen=True)
class ClaimResult:
    accepted: bool
    reason: str
    cheat_signals: tuple[CheatSignal, ...]
    rewound_target_pos_xyz: tuple[float, float, float] | None
    effective_range_m: float
    measured_distance_m: float


@dataclasses.dataclass(frozen=True)
class _HistoryEntry:
    timestamp_ms: int
    position_xyz: tuple[float, float, float]


def _distance_m(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    dz = a[2] - b[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def weapon_range_m(kind: WeaponKind) -> float:
    return _RANGE_BY_WEAPON[kind]


def weapon_min_interval_s(kind: WeaponKind) -> float:
    return _MIN_INTERVAL_BY_WEAPON[kind]


@dataclasses.dataclass
class NetLagCompensationSystem:
    _history: dict[str, list[_HistoryEntry]] = dataclasses.field(
        default_factory=dict,
    )
    # player_id -> list[CheatSignal]
    _cheat_log: dict[str, list[CheatSignal]] = dataclasses.field(
        default_factory=dict,
    )
    # player_id -> last claim timestamp (server-received).
    _last_claim_ts: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )
    # player_id -> consecutive out-of-range hits.
    _oor_streak: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )

    # ---------------------------------------------- history
    def register_history(
        self,
        entity_id: str,
        timestamp_ms: int,
        position_xyz: tuple[float, float, float],
    ) -> None:
        if not entity_id:
            raise ValueError("entity_id required")
        if timestamp_ms < 0:
            raise ValueError("timestamp_ms must be >= 0")
        hist = self._history.setdefault(entity_id, [])
        hist.append(
            _HistoryEntry(
                timestamp_ms=timestamp_ms,
                position_xyz=position_xyz,
            )
        )
        # Keep history ordered by timestamp.
        hist.sort(key=lambda e: e.timestamp_ms)

    def history_size(self, entity_id: str) -> int:
        return len(self._history.get(entity_id, []))

    def prune_history(self, now_ms: int) -> int:
        cutoff = now_ms - HISTORY_WINDOW_MS
        removed = 0
        for eid, hist in self._history.items():
            keep = [e for e in hist if e.timestamp_ms >= cutoff]
            removed += len(hist) - len(keep)
            self._history[eid] = keep
        return removed

    def rewound_position(
        self,
        entity_id: str,
        rewind_to_ms: int,
    ) -> tuple[float, float, float] | None:
        hist = self._history.get(entity_id)
        if not hist:
            return None
        # Pick the entry whose timestamp is closest to rewind_to_ms
        # but does not exceed it. If none, return None.
        candidates = [
            e for e in hist if e.timestamp_ms <= rewind_to_ms
        ]
        if not candidates:
            # Try newest if rewind target is before our history.
            return None
        # If there's a later one to interpolate to, do linear.
        latest_at_or_before = max(
            candidates, key=lambda e: e.timestamp_ms,
        )
        after = [
            e for e in hist if e.timestamp_ms > rewind_to_ms
        ]
        if not after:
            return latest_at_or_before.position_xyz
        nxt = min(after, key=lambda e: e.timestamp_ms)
        span = nxt.timestamp_ms - latest_at_or_before.timestamp_ms
        if span <= 0:
            return latest_at_or_before.position_xyz
        u = (
            rewind_to_ms - latest_at_or_before.timestamp_ms
        ) / span
        a = latest_at_or_before.position_xyz
        b = nxt.position_xyz
        return (
            a[0] + (b[0] - a[0]) * u,
            a[1] + (b[1] - a[1]) * u,
            a[2] + (b[2] - a[2]) * u,
        )

    # ---------------------------------------------- attacker check
    def can_attacker_reach(
        self,
        attacker_id: str,
        target_pos: tuple[float, float, float],
        weapon_kind: WeaponKind,
        ping_ms: int,
    ) -> bool:
        # Where the attacker actually was at server time (now).
        hist = self._history.get(attacker_id, [])
        if not hist:
            return False
        latest = hist[-1]
        d = _distance_m(latest.position_xyz, target_pos)
        rng = _RANGE_BY_WEAPON[weapon_kind] + REACH_TOLERANCE_M
        return d <= rng

    # ---------------------------------------------- claims
    def submit_claim(self, claim: HitClaim) -> ClaimResult:
        signals: list[CheatSignal] = []
        # 1. Ping check.
        ping = claim.server_received_ms - claim.claimed_at_client_ms
        if ping < MIN_PING_MS or ping > MAX_PING_MS:
            signals.append(CheatSignal.PING_TOO_HIGH)
            self._record(claim.claimer_player_id, signals)
            return ClaimResult(
                accepted=False,
                reason="ping_out_of_window",
                cheat_signals=tuple(signals),
                rewound_target_pos_xyz=None,
                effective_range_m=_RANGE_BY_WEAPON[claim.weapon_kind],
                measured_distance_m=0.0,
            )

        # 2. Rewind target to claim time.
        rewind_to = claim.claimed_at_client_ms
        rewound = self.rewound_position(
            claim.target_entity_id, rewind_to,
        )
        if rewound is None:
            signals.append(CheatSignal.REWIND_PAST_HISTORY)
            self._record(claim.claimer_player_id, signals)
            return ClaimResult(
                accepted=False,
                reason="no_history_at_rewind_time",
                cheat_signals=tuple(signals),
                rewound_target_pos_xyz=None,
                effective_range_m=_RANGE_BY_WEAPON[claim.weapon_kind],
                measured_distance_m=0.0,
            )

        # 3. Position match — claimed_target_pos must agree
        #    with rewound position within tolerance.
        pos_delta_cm = _distance_m(
            rewound, claim.claimed_target_pos_xyz,
        ) * 100.0
        if pos_delta_cm > POSITION_TOLERANCE_CM:
            signals.append(CheatSignal.POSITION_MISMATCH)

        # 4. Teleport check on attacker — claimed attacker
        #    position must be reachable from the previous
        #    server snapshot at MAX_MOVE_SPEED_MS.
        attacker_hist = self._history.get(
            claim.claimer_player_id, [],
        )
        if attacker_hist:
            prev = attacker_hist[-1]
            dt_s = max(
                0.001,
                (claim.server_received_ms - prev.timestamp_ms) / 1000.0,
            )
            max_d = MAX_MOVE_SPEED_MS * dt_s + REACH_TOLERANCE_M
            actual_d = _distance_m(
                prev.position_xyz, claim.claimed_attacker_pos_xyz,
            )
            if actual_d > max_d:
                signals.append(CheatSignal.TELEPORT_HACK)

        # 5. Weapon range check on claimed positions.
        measured_d = _distance_m(
            claim.claimed_attacker_pos_xyz, rewound,
        )
        weapon_r = _RANGE_BY_WEAPON[claim.weapon_kind]
        eff_r = weapon_r + REACH_TOLERANCE_M
        out_of_range = measured_d > eff_r
        if out_of_range:
            signals.append(CheatSignal.IMPOSSIBLE_REACH)
            self._oor_streak[claim.claimer_player_id] = (
                self._oor_streak.get(claim.claimer_player_id, 0)
                + 1
            )
            if self._oor_streak[claim.claimer_player_id] >= 3:
                signals.append(CheatSignal.OUT_OF_RANGE_REPEATED)
        else:
            self._oor_streak[claim.claimer_player_id] = 0

        # 6. Rate-of-fire check.
        last = self._last_claim_ts.get(claim.claimer_player_id)
        if last is not None:
            dt_s = (
                claim.server_received_ms - last
            ) / 1000.0
            min_iv = _MIN_INTERVAL_BY_WEAPON[claim.weapon_kind]
            # 80% tolerance — slight network jitter ok.
            if dt_s < min_iv * 0.8:
                signals.append(CheatSignal.RAPID_FIRE_BEYOND_RATE)
        self._last_claim_ts[claim.claimer_player_id] = (
            claim.server_received_ms
        )

        # 7. LoS check.
        if not claim.has_line_of_sight:
            signals.append(CheatSignal.BROKEN_LOS)

        # Accept iff no cheat signals AND in-range.
        blocking = {
            CheatSignal.IMPOSSIBLE_REACH,
            CheatSignal.OUT_OF_RANGE_REPEATED,
            CheatSignal.TELEPORT_HACK,
            CheatSignal.BROKEN_LOS,
            CheatSignal.RAPID_FIRE_BEYOND_RATE,
            CheatSignal.POSITION_MISMATCH,
        }
        accepted = not any(s in blocking for s in signals)
        reason = "ok" if accepted else "blocked_by_signal"
        self._record(claim.claimer_player_id, signals)
        return ClaimResult(
            accepted=accepted,
            reason=reason,
            cheat_signals=tuple(signals),
            rewound_target_pos_xyz=rewound,
            effective_range_m=eff_r,
            measured_distance_m=measured_d,
        )

    # ---------------------------------------------- cheat log
    def _record(
        self,
        player_id: str,
        signals: list[CheatSignal],
    ) -> None:
        if not signals:
            return
        self._cheat_log.setdefault(player_id, []).extend(signals)

    def detect_cheats_for(self, player_id: str) -> tuple[CheatSignal, ...]:
        return tuple(self._cheat_log.get(player_id, []))

    def clear_cheat_log(self, player_id: str) -> None:
        self._cheat_log.pop(player_id, None)


__all__ = [
    "WeaponKind",
    "CheatSignal",
    "HitClaim",
    "ClaimResult",
    "NetLagCompensationSystem",
    "HISTORY_WINDOW_MS",
    "MIN_PING_MS",
    "MAX_PING_MS",
    "POSITION_TOLERANCE_CM",
    "MAX_MOVE_SPEED_MS",
    "REACH_TOLERANCE_M",
    "weapon_range_m",
    "weapon_min_interval_s",
]
