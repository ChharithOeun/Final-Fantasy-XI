"""Aggro tracker — sensory perception + state machine + persistence timer.

Per SEAMLESS_WORLD.md. Pure-Python deterministic logic; no I/O. The
LSB server feeds in world snapshots (positions, sounds, in-combat
flags) on each tick; the tracker outputs the current pursuit state
plus deaggro events when sensory-loss timers expire.
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


class AggroState(enum.IntEnum):
    NEUTRAL = 0          # mob doesn't care
    SUSPICIOUS = 1       # mob sensed something; investigating
    AGGRESSIVE = 2       # in combat; standard chase
    ENRAGED = 3          # extended chase persistence; cross-zone
    BOSS_ENRAGED = 4     # NM-tier; cross-multiple-zones


# Persistence per state (seconds). After this much time elapses with
# the player out of all sensory envelopes, the mob deaggros.
DEFAULT_PERSISTENCE_SECONDS: dict[AggroState, float] = {
    AggroState.NEUTRAL:      0.0,
    AggroState.SUSPICIOUS:   20.0,
    AggroState.AGGRESSIVE:   45.0,
    AggroState.ENRAGED:      300.0,    # 5 minutes
    AggroState.BOSS_ENRAGED: 1800.0,   # 30 minutes
}


@dataclasses.dataclass
class SensoryProfile:
    """Per-mob sensory configuration."""
    sight_range_cm: float = 1500.0
    sight_cone_deg: float = 180.0
    sight_requires_los: bool = True
    sound_range_cm: float = 800.0
    sound_passive_threshold: float = 0.3
    smell_range_cm: float = 0.0
    smell_decay_seconds: float = 30.0


@dataclasses.dataclass
class PlayerSnapshot:
    """A snapshot of player state for the tracker tick."""
    player_id: str
    x_cm: float
    y_cm: float
    z_cm: float
    in_combat: bool = False
    casting_vocal: bool = False
    weapon_just_swung: bool = False
    weight: float = 30.0
    movement_speed_pct: float = 1.0   # 0=still, 1=running, 1.4=sprint
    has_sneak: bool = False
    has_invisible: bool = False
    has_deodorize: bool = False
    is_in_sanctuary: bool = False


@dataclasses.dataclass
class _AggroRecord:
    state: AggroState = AggroState.NEUTRAL
    last_sensed_at: float = 0.0
    last_lost_at: t.Optional[float] = None
    aggro_started_at: t.Optional[float] = None


# ----------------------------------------------------------------------
# Pure perception helpers
# ----------------------------------------------------------------------

def _distance_cm(ax: float, ay: float, az: float,
                 bx: float, by: float, bz: float) -> float:
    return math.sqrt((ax-bx)**2 + (ay-by)**2 + (az-bz)**2)


def compute_player_sound_level(player: PlayerSnapshot) -> float:
    """Per SEAMLESS_WORLD.md: how loud the player is right now."""
    base = 0.2
    if player.in_combat:
        base += 0.5
    if player.casting_vocal:
        base += 0.3
    if player.weapon_just_swung:
        base += 0.4
    base += player.weight / 200.0
    base *= player.movement_speed_pct
    if player.has_sneak:
        base *= 0.1
    return base


def can_perceive_player(*, mob_x: float, mob_y: float, mob_z: float,
                         mob_facing_deg: float,
                         mob_health_pct: float,
                         mob_profile: SensoryProfile,
                         player: PlayerSnapshot,
                         line_of_sight_clear: bool = True,
                         smell_distance_cm: t.Optional[float] = None) -> dict:
    """Return a dict with sight/sound/smell perception flags + distance.

    The caller (LSB) provides:
      - line_of_sight_clear: True if no walls/cover between mob and player
      - smell_distance_cm: optional override of the actual smell-trail distance
        (defaults to euclidean distance if not provided)
    """
    dist = _distance_cm(mob_x, mob_y, mob_z,
                        player.x_cm, player.y_cm, player.z_cm)

    # SIGHT
    sight = False
    if not player.has_invisible and mob_profile.sight_range_cm > 0:
        # Wounded mobs see less far
        eff_sight = mob_profile.sight_range_cm * mob_health_pct
        if dist <= eff_sight:
            # Cone check
            dx = player.x_cm - mob_x
            dy = player.y_cm - mob_y
            angle_to_player = math.degrees(math.atan2(dy, dx))
            angle_diff = abs(_normalize_angle(angle_to_player - mob_facing_deg))
            if angle_diff <= mob_profile.sight_cone_deg / 2.0:
                if not mob_profile.sight_requires_los or line_of_sight_clear:
                    sight = True

    # SOUND
    sound = False
    if mob_profile.sound_range_cm > 0:
        sound_level = compute_player_sound_level(player)
        if (sound_level >= mob_profile.sound_passive_threshold
                and dist <= mob_profile.sound_range_cm):
            sound = True

    # SMELL
    smell = False
    if mob_profile.smell_range_cm > 0 and not player.has_deodorize:
        smell_d = smell_distance_cm if smell_distance_cm is not None else dist
        if smell_d <= mob_profile.smell_range_cm:
            smell = True

    return {
        "distance_cm": dist,
        "sight": sight,
        "sound": sound,
        "smell": smell,
        "any": sight or sound or smell,
    }


def _normalize_angle(a: float) -> float:
    """Normalize an angle to [-180, 180]."""
    while a > 180:
        a -= 360
    while a < -180:
        a += 360
    return a


# ----------------------------------------------------------------------
# AggroTracker
# ----------------------------------------------------------------------

class AggroTracker:
    """Tracks per (mob, player) aggro state.

    Each AggroTracker is owned by ONE mob. The mob's state vs each
    player it has interacted with is tracked separately. State is
    pure in-memory — for production the LSB server would persist
    through the orchestrator's DB.
    """

    def __init__(self, *,
                 mob_id: str,
                 mob_profile: SensoryProfile,
                 persistence_seconds: t.Optional[dict[AggroState, float]] = None,
                 escapable_at_distance_cm: float = 0.0):
        self.mob_id = mob_id
        self.profile = mob_profile
        self.persistence = persistence_seconds or DEFAULT_PERSISTENCE_SECONDS
        self.escapable_at_distance_cm = escapable_at_distance_cm
        self._records: dict[str, _AggroRecord] = {}

    # --- queries ---

    def state_toward(self, player_id: str) -> AggroState:
        rec = self._records.get(player_id)
        return rec.state if rec else AggroState.NEUTRAL

    def is_pursuing(self, player_id: str) -> bool:
        return self.state_toward(player_id) >= AggroState.AGGRESSIVE

    # --- inputs ---

    def notify_damage(self, *, player_id: str,
                       damage_pct: float,
                       now_seconds: float,
                       was_provoked: bool = False) -> AggroState:
        """A player just damaged this mob. Refresh persistence + maybe escalate."""
        rec = self._records.setdefault(player_id, _AggroRecord())

        # Promote to at least AGGRESSIVE
        if rec.state < AggroState.AGGRESSIVE:
            rec.state = AggroState.AGGRESSIVE
            rec.aggro_started_at = now_seconds

        # ENRAGED triggers
        if was_provoked:
            rec.state = max(rec.state, AggroState.ENRAGED)
        elif damage_pct > 0.50:
            rec.state = max(rec.state, AggroState.ENRAGED)

        rec.last_sensed_at = now_seconds
        rec.last_lost_at = None
        return rec.state

    def notify_perception(self, *, player_id: str,
                           perception: dict,
                           now_seconds: float) -> AggroState:
        """Called each tick with the mob's sensory perception of the player."""
        rec = self._records.setdefault(player_id, _AggroRecord())

        if perception["any"]:
            # Perceive: refresh
            if rec.state == AggroState.NEUTRAL:
                rec.state = AggroState.SUSPICIOUS
                rec.aggro_started_at = now_seconds
            rec.last_sensed_at = now_seconds
            rec.last_lost_at = None
        else:
            # Lost the player this tick
            if rec.state >= AggroState.SUSPICIOUS and rec.last_lost_at is None:
                rec.last_lost_at = now_seconds
        return rec.state

    def notify_intervention_proc(self, *, player_id: str,
                                   now_seconds: float) -> AggroState:
        """Player landed an intervention save vs this mob's chain."""
        rec = self._records.setdefault(player_id, _AggroRecord())
        rec.state = max(rec.state, AggroState.ENRAGED)
        rec.last_sensed_at = now_seconds
        rec.last_lost_at = None
        return rec.state

    def notify_skillchain_landed(self, *, player_id: str,
                                   chain_level: int,
                                   now_seconds: float) -> AggroState:
        """Player party landed a chain on this mob."""
        rec = self._records.setdefault(player_id, _AggroRecord())
        if chain_level >= 3:   # Light or Darkness
            rec.state = max(rec.state, AggroState.ENRAGED)
        else:
            rec.state = max(rec.state, AggroState.AGGRESSIVE)
        rec.last_sensed_at = now_seconds
        rec.last_lost_at = None
        return rec.state

    def notify_player_entered_sanctuary(self, *, player_id: str) -> AggroState:
        """Player crossed into a safe zone — drop aggro entirely."""
        rec = self._records.setdefault(player_id, _AggroRecord())
        prev = rec.state
        rec.state = AggroState.NEUTRAL
        rec.last_sensed_at = 0
        rec.last_lost_at = None
        rec.aggro_started_at = None
        return prev

    # --- tick (the deaggro check) ---

    def tick(self, *, now_seconds: float) -> dict[str, AggroState]:
        """Process per-tick deaggro decay. Returns mapping of any
        state changes that occurred this tick."""
        changes: dict[str, AggroState] = {}
        for player_id, rec in self._records.items():
            if rec.state == AggroState.NEUTRAL:
                continue
            if rec.last_lost_at is None:
                continue   # still in sensory contact
            elapsed = now_seconds - rec.last_lost_at
            allowed = self.persistence.get(rec.state, 45.0)
            if elapsed >= allowed:
                rec.state = AggroState.NEUTRAL
                rec.last_lost_at = None
                rec.aggro_started_at = None
                changes[player_id] = AggroState.NEUTRAL
        return changes

    def snapshot(self) -> dict:
        """Diagnostic snapshot for the orchestrator's monitoring."""
        return {
            "mob_id": self.mob_id,
            "tracked_players": len(self._records),
            "records": {
                pid: {
                    "state": rec.state.name,
                    "last_sensed_at": rec.last_sensed_at,
                    "last_lost_at": rec.last_lost_at,
                    "aggro_started_at": rec.aggro_started_at,
                }
                for pid, rec in self._records.items()
            },
        }
