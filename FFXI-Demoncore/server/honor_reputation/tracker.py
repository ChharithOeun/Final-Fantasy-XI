"""Honor + Reputation dual-gauge tracker.

The single source of truth for a character's morality state.

Two gauges:
- Honor: internal moral standing. 0-1000. Private. Moves only on
  *major moral acts* — kills, oath-breaking, heroic deeds. Does NOT
  decay toward neutral; rebuilding is the work of months.
- Reputation: public, per-nation. -1000 to 5000. Moves on *visible
  deeds* — completed quests, public scandals, NM kills. Rebuilds
  through community service + time decay (+1/day toward neutral).

The two are independent but correlated: bad-honor acts often produce
witnesses, which also tank rep. A character can't trivially "honor up"
by farming visible deeds while doing private evil — honor doesn't
move from public stuff. They have to actually change behavior.

This module is mutator + reader; persistence is the caller's job.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------

HONOR_FLOOR = 0
HONOR_CEILING = 1000
HONOR_DEFAULT = 600              # new char: well-regarded mid-high

REP_FLOOR = -1000
REP_CEILING = 5000
REP_DEFAULT = 0                  # new char: neutral

GLOBAL_NATION_KEY = "global"
NATIONS = ("bastok", "sandoria", "windurst", "ahturhgan", GLOBAL_NATION_KEY)

# Per HONOR_REPUTATION.md "Outlaw safe havens"
SAFE_HAVEN_TOWNS = frozenset({"norg", "selbina", "mhaura"})

# Cities that enforce honor gates at the gate
GATED_CITIES = frozenset({"bastok", "sandoria", "windurst", "jeuno", "ahturhgan"})

# Honor thresholds
HONOR_THRESHOLD_REFUSED = 200    # < 200: refused at gates, no teleports
HONOR_THRESHOLD_WATCHED = 600    # 200-599: watched but allowed
# >= 600: welcomed

# Reputation tier thresholds (per-nation; tier_of() works on a single rep value)
REP_PARIAH = -1000
REP_DESPISED = -200              # -1000..-200 = pariah; vendors refuse
REP_NEUTRAL_LO = -200            # -200..200 = neutral
REP_NEUTRAL_HI = 200
REP_LIKED_HI = 1000              # 200..1000 = liked; 5% discount
# >= 1000 = loved; vendors greet by name

# Recovery + special acts
PILGRIMAGE_HONOR_GAIN = 200
PILGRIMAGE_COOLDOWN_SECONDS = 365 * 86400   # one per real year
DONATION_GIL_PER_REP_POINT = 100_000 / 5    # 100k gil = +5 rep
LOYAL_CUSTOMER_GIL_PER_REP = 100_000        # 100k gil spent at vendor = +1 rep
REP_DAILY_DECAY_PER_DAY = 1                 # towards 0


# ----------------------------------------------------------------------
# Data classes
# ----------------------------------------------------------------------

class ReputationTier(str, enum.Enum):
    PARIAH = "pariah"          # rep <= -1000
    DESPISED = "despised"      # -1000 < rep < -200
    NEUTRAL = "neutral"        # -200 <= rep <= 200
    LIKED = "liked"            # 200 < rep < 1000
    LOVED = "loved"            # 1000 <= rep < 3000
    LEGENDARY = "legendary"    # rep >= 3000


class QuestDisposition(str, enum.Enum):
    WELCOMED = "welcomed"
    WATCHED = "watched"
    REFUSED = "refused"


class MoralAct(str, enum.Enum):
    """Known moral-act kinds. Each maps to honor / rep deltas in
    `MORAL_ACT_TABLE`. Custom magnitude lets the caller scale (e.g.
    theft of a 10k vs 1m gil item)."""
    # Honor-dominant
    SAME_RACE_KILL_DELIBERATE = "same_race_kill_deliberate"
    SAME_RACE_KILL_ACCIDENTAL = "same_race_kill_accidental"
    OATH_BREAKING = "oath_breaking"
    MURDERED_QUEST_GIVER = "murdered_quest_giver"
    AIDING_OUTLAW = "aiding_outlaw"
    FAILED_TO_DEFEND_ALLY = "failed_to_defend_ally"
    HEROIC_DEED = "heroic_deed"
    SLAYING_HIGH_BOUNTY_OUTLAW = "slaying_high_bounty_outlaw"
    LONG_TERM_ALLY_SERVICE = "long_term_ally_service"   # +5 honor / week

    # Reputation-dominant
    QUEST_COMPLETED = "quest_completed"
    MISSION_COMPLETED = "mission_completed"
    NM_SLAIN_PUBLICLY = "nm_slain_publicly"
    PVP_DUEL_LOST = "pvp_duel_lost"
    PVP_DUEL_WON = "pvp_duel_won"
    DEFEATED_OUTLAW_PUBLICLY = "defeated_outlaw_publicly"
    BECAME_OUTLAW = "became_outlaw"
    PUBLIC_MISBEHAVIOR = "public_misbehavior"

    # Bilateral (both gauges; witness flag controls rep side)
    THEFT_FROM_NPC = "theft_from_npc"


# Each entry: (honor_delta, reputation_delta_when_witnessed,
#              reputation_delta_when_unwitnessed)
# Magnitudes for MoralAct kinds where the user-supplied `magnitude`
# argument scales them (e.g. theft scales by item value).
MORAL_ACT_TABLE: dict[MoralAct, tuple[int, int, int]] = {
    MoralAct.SAME_RACE_KILL_DELIBERATE:    (-200,  -100,  -20),
    MoralAct.SAME_RACE_KILL_ACCIDENTAL:    (-50,   -10,   0),
    MoralAct.OATH_BREAKING:                (-100,  -20,   -20),
    MoralAct.MURDERED_QUEST_GIVER:         (-150,  -100,  -20),
    MoralAct.AIDING_OUTLAW:                (-50,   -30,   0),
    MoralAct.FAILED_TO_DEFEND_ALLY:        (-10,   -5,    0),
    MoralAct.HEROIC_DEED:                  (+200,  +200,  +200),
    MoralAct.SLAYING_HIGH_BOUNTY_OUTLAW:   (+50,   +20,   +20),
    MoralAct.LONG_TERM_ALLY_SERVICE:       (+5,    +2,    +2),

    MoralAct.QUEST_COMPLETED:              (0,     +5,    +5),
    MoralAct.MISSION_COMPLETED:            (0,     +100,  +100),
    MoralAct.NM_SLAIN_PUBLICLY:            (0,     +50,   +25),
    MoralAct.PVP_DUEL_LOST:                (0,     +5,    0),
    MoralAct.PVP_DUEL_WON:                 (0,     +10,   0),
    MoralAct.DEFEATED_OUTLAW_PUBLICLY:     (0,     +20,   +5),
    MoralAct.BECAME_OUTLAW:                (-100,  -500,  -500),
    MoralAct.PUBLIC_MISBEHAVIOR:           (0,     -25,   0),

    MoralAct.THEFT_FROM_NPC:               (-30,   -100,  0),
}


@dataclasses.dataclass
class MoralityGauges:
    """The persistent per-character morality snapshot. Caller persists
    this dataclass and rehydrates it before each operation."""
    actor_id: str
    honor: int = HONOR_DEFAULT
    rep_per_nation: dict[str, int] = dataclasses.field(default_factory=dict)
    last_pilgrimage_at: t.Optional[float] = None
    is_outlaw_faction_member: bool = False
    bounty_hunter_pass_until: t.Optional[float] = None
    courier_pass_until: t.Optional[float] = None

    def __post_init__(self) -> None:
        # Ensure every nation key is initialized so subsequent reads
        # never need to special-case missing entries.
        for nation in NATIONS:
            self.rep_per_nation.setdefault(nation, REP_DEFAULT)


# ----------------------------------------------------------------------
# Tracker
# ----------------------------------------------------------------------

def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def tier_of(rep: int) -> ReputationTier:
    """Map a single reputation value to a tier label."""
    if rep <= REP_PARIAH:
        return ReputationTier.PARIAH
    if rep < REP_DESPISED:
        return ReputationTier.DESPISED
    if rep <= REP_NEUTRAL_HI:
        return ReputationTier.NEUTRAL
    if rep < REP_LIKED_HI:
        return ReputationTier.LIKED
    if rep < 3000:
        return ReputationTier.LOVED
    return ReputationTier.LEGENDARY


class HonorRepTracker:
    """Operates on a MoralityGauges snapshot in-place.

    Construct with the snapshot, call apply_act() for each event, and
    use the read-helpers (can_enter_city, vendor_will_sell, etc.) to
    drive game logic.
    """

    def __init__(self, snapshot: MoralityGauges) -> None:
        self.snapshot = snapshot

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def apply_act(self,
                   kind: MoralAct,
                   *,
                   was_witnessed: bool = True,
                   nation: str = GLOBAL_NATION_KEY,
                   magnitude: float = 1.0) -> None:
        """Apply a moral act to the gauges.

        was_witnessed - some acts only ding rep when seen (theft is the
        canonical case).
        nation - which nation's rep gauge to ding (defaults to global).
        magnitude - scalar multiplier for value-scaled acts (theft of a
        10k vs 1m gil item; 1.0 = baseline).
        """
        honor_delta, rep_witnessed, rep_unwitnessed = MORAL_ACT_TABLE[kind]
        rep_delta = rep_witnessed if was_witnessed else rep_unwitnessed

        honor_delta = int(round(honor_delta * magnitude))
        rep_delta = int(round(rep_delta * magnitude))

        self.snapshot.honor = _clamp(
            self.snapshot.honor + honor_delta,
            HONOR_FLOOR, HONOR_CEILING,
        )

        # Rep tracks per-nation and global. Big public acts ding the
        # nation where it happened AND echo half-strength to global so
        # other nations know.
        if nation == GLOBAL_NATION_KEY:
            self.snapshot.rep_per_nation[GLOBAL_NATION_KEY] = _clamp(
                self.snapshot.rep_per_nation[GLOBAL_NATION_KEY] + rep_delta,
                REP_FLOOR, REP_CEILING,
            )
        else:
            self.snapshot.rep_per_nation.setdefault(nation, REP_DEFAULT)
            self.snapshot.rep_per_nation[nation] = _clamp(
                self.snapshot.rep_per_nation[nation] + rep_delta,
                REP_FLOOR, REP_CEILING,
            )
            # Echo half to global
            global_echo = rep_delta // 2
            self.snapshot.rep_per_nation[GLOBAL_NATION_KEY] = _clamp(
                self.snapshot.rep_per_nation[GLOBAL_NATION_KEY] + global_echo,
                REP_FLOOR, REP_CEILING,
            )

    def donate_to_treasury(self, gil: int, nation: str) -> int:
        """Public donation: +1 rep per 20k gil (5 per 100k). Returns
        rep gained."""
        if gil <= 0:
            return 0
        gain = int(gil // DONATION_GIL_PER_REP_POINT)
        if gain <= 0:
            return 0
        self.snapshot.rep_per_nation.setdefault(nation, REP_DEFAULT)
        self.snapshot.rep_per_nation[nation] = _clamp(
            self.snapshot.rep_per_nation[nation] + gain,
            REP_FLOOR, REP_CEILING,
        )
        return gain

    def loyal_customer_spend(self, gil: int, nation: str) -> int:
        """Spending substantial gil at a vendor builds rep slowly:
        +1 per 100k gil. Returns rep gained."""
        if gil <= 0:
            return 0
        gain = int(gil // LOYAL_CUSTOMER_GIL_PER_REP)
        if gain <= 0:
            return 0
        self.snapshot.rep_per_nation.setdefault(nation, REP_DEFAULT)
        self.snapshot.rep_per_nation[nation] = _clamp(
            self.snapshot.rep_per_nation[nation] + gain,
            REP_FLOOR, REP_CEILING,
        )
        return gain

    def daily_decay(self, days_elapsed: int) -> None:
        """Reputation drifts toward 0 at +1/day. Honor never decays —
        it's permanent until an act reverses it."""
        if days_elapsed <= 0:
            return
        for nation, rep in list(self.snapshot.rep_per_nation.items()):
            if rep == 0:
                continue
            step = REP_DAILY_DECAY_PER_DAY * days_elapsed
            if rep > 0:
                self.snapshot.rep_per_nation[nation] = max(0, rep - step)
            else:
                self.snapshot.rep_per_nation[nation] = min(0, rep + step)

    def pilgrimage_complete(self, now: float) -> bool:
        """Visit shrines in proper order → +200 honor. Allowed once per
        real year. Returns True if applied, False if on cooldown."""
        last = self.snapshot.last_pilgrimage_at
        if last is not None and (now - last) < PILGRIMAGE_COOLDOWN_SECONDS:
            return False
        self.snapshot.honor = _clamp(
            self.snapshot.honor + PILGRIMAGE_HONOR_GAIN,
            HONOR_FLOOR, HONOR_CEILING,
        )
        self.snapshot.last_pilgrimage_at = now
        return True

    # ------------------------------------------------------------------
    # Readers / gates
    # ------------------------------------------------------------------

    def reputation_for(self, nation: str) -> int:
        return self.snapshot.rep_per_nation.get(nation, REP_DEFAULT)

    def reputation_tier(self, nation: str = GLOBAL_NATION_KEY) -> ReputationTier:
        return tier_of(self.reputation_for(nation))

    def is_in_safe_haven(self, location: str) -> bool:
        return location.lower() in SAFE_HAVEN_TOWNS

    def has_active_pass(self, now: float) -> bool:
        """Bounty-hunter or courier pass currently grants honor immunity."""
        if (self.snapshot.bounty_hunter_pass_until is not None
                and now < self.snapshot.bounty_hunter_pass_until):
            return True
        if (self.snapshot.courier_pass_until is not None
                and now < self.snapshot.courier_pass_until):
            return True
        return False

    def can_enter_city(self, city: str, now: float = 0) -> bool:
        """Honor < 200 → guards refuse. Safe havens always admit.
        Active bounty-hunter / courier passes override the gate."""
        city_lc = city.lower()
        if city_lc in SAFE_HAVEN_TOWNS:
            return True
        if city_lc not in GATED_CITIES:
            return True   # overland zones: no gate
        if self.has_active_pass(now):
            return True
        return self.snapshot.honor >= HONOR_THRESHOLD_REFUSED

    def can_teleport_to(self, destination: str, now: float = 0) -> bool:
        """Wilderness markers always work. Major-city teleports gated
        on Honor ≥ 200."""
        wilderness_markers = {"holla", "dem", "mea", "altep", "vahzl", "yhoat"}
        d = destination.lower()
        if d in wilderness_markers:
            return True
        if self.has_active_pass(now):
            return True
        return self.snapshot.honor >= HONOR_THRESHOLD_REFUSED

    def mog_house_accessible(self) -> bool:
        return self.snapshot.honor >= HONOR_THRESHOLD_REFUSED

    def auction_house_disposition(self) -> dict[str, t.Any]:
        """Returns {'can_list', 'can_buy', 'slot_count_factor'}."""
        if self.snapshot.honor < HONOR_THRESHOLD_REFUSED:
            return {"can_list": True, "can_buy": False, "slot_count_factor": 1.0}
        global_rep = self.reputation_for(GLOBAL_NATION_KEY)
        if global_rep < REP_DESPISED:
            return {"can_list": True, "can_buy": True, "slot_count_factor": 1/3}
        return {"can_list": True, "can_buy": True, "slot_count_factor": 1.0}

    def vendor_will_sell(self, vendor_city: str) -> tuple[bool, float]:
        """(allowed, price_multiplier).

        Safe havens: allowed but +20% black-market markup.
        Honor < 200: refused (allowed=False).
        Rep < -200: refused-by-this-vendor.
        Rep 200-1000: -5% loyalty discount.
        Rep 1000+: -5% (cap; above that it's a relationship not a discount).
        """
        if self.is_in_safe_haven(vendor_city):
            return True, 1.20
        if self.snapshot.honor < HONOR_THRESHOLD_REFUSED:
            return False, 1.0
        # Use the relevant nation's rep if known, else global
        nation = self._city_to_nation(vendor_city)
        rep = self.reputation_for(nation)
        if rep < REP_DESPISED:
            return False, 1.0   # despised: vendor refuses to sell
        if rep > REP_NEUTRAL_HI:
            return True, 0.95
        return True, 1.0

    def quest_acceptance_disposition(self) -> QuestDisposition:
        """Honor < 200 → most NPCs refuse. 200-599 → watched. ≥600 → welcomed."""
        h = self.snapshot.honor
        if h < HONOR_THRESHOLD_REFUSED:
            return QuestDisposition.REFUSED
        if h < HONOR_THRESHOLD_WATCHED:
            return QuestDisposition.WATCHED
        return QuestDisposition.WELCOMED

    def npc_will_converse(self) -> bool:
        """Pariahs are ignored — NPCs walk away. Used by ambient NPCs."""
        return self.reputation_for(GLOBAL_NATION_KEY) > REP_PARIAH + 1

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _city_to_nation(city: str) -> str:
        c = city.lower()
        if c in ("bastok", "bastok_markets", "bastok_mines", "bastok_metalworks"):
            return "bastok"
        if c in ("sandoria", "sandy", "northern_sandoria", "southern_sandoria"):
            return "sandoria"
        if c in ("windurst", "windy", "windurst_walls", "windurst_woods", "windurst_waters"):
            return "windurst"
        if c in ("ahturhgan", "aht_urhgan", "whitegate"):
            return "ahturhgan"
        return GLOBAL_NATION_KEY
