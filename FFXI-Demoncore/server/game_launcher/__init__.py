"""Game launcher — the state machine that wraps the demo and
turns it into a shippable product.

FFXI's retail launcher was PlayOnline — a 2002 social
network the player had to walk through to get to the
game. Demoncore replaces it with a modern launcher: an
Anthropic-style splash fade-in, a title screen with a
looping background video and region-localized music, a
patch checker, a Discord OAuth flow (auth_discord does
the lifting), server selection, a 16-slot character
select rendered against the last-played zone's lighting
atlas hero shot, character creation if you have an open
slot, world load, and — on first play only — the
cinematic intro sequence "first_play_intro" from
showcase_choreography. Then in-game. Pause and
disconnect have their own states because every shipped
game needs them.

The state machine is the contract. Every transition is
either USER (triggered by a button press) or AUTO
(triggered by a background completion — download done,
load finished, fade complete). The directed graph lives
in ``_TRANSITIONS`` and is the single source of truth.
``transition_to`` validates against it and returns
ok|denied; ``advance_automatic`` walks AUTO edges as
their conditions become true.

LauncherState covers fourteen states — SPLASH (Anthropic-
style fade-in, 1.2s), TITLE_SCREEN (background video +
music, indefinite), PATCH_CHECK (probe the patch
server), PATCHING (download progress), LOGIN (Discord
button), DISCORD_OAUTH_FLOW (browser hand-off owned by
auth_discord), SERVER_SELECTION (US-East / EU-West /
JP-Tokyo / SEA-Singapore), CHARACTER_SELECT (the 16-
slot card UI), CHARACTER_CREATION (hand-off to
character_creation), WORLD_LOAD (zone fetch), CINEMATIC_
INTRO (first-play only, runs the showcase_choreography
"first_play_intro" sequence), IN_GAME, PAUSED,
DISCONNECTED, ERROR.

Character select renders each card with name, race
(from character_creation.Race), main job, level, and
last-played zone — the card art is the zone_lighting_
atlas hero shot for that zone. Last-played character is
highlighted.

Public surface
--------------
    LauncherState enum
    TransitionKind enum
    Transition dataclass (frozen)
    CharacterCard dataclass (frozen)
    LauncherPose dataclass (frozen)
    GameLauncherSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# How long the SPLASH fade-in plays (ms). After this elapses
# advance_automatic will move SPLASH -> TITLE_SCREEN.
SPLASH_DURATION_MS = 1200

# How long the CINEMATIC_INTRO is expected to run, after
# which it auto-advances into IN_GAME.
CINEMATIC_INTRO_DURATION_MS = 95_000

# Sequence name in showcase_choreography that fires on
# first launch only.
FIRST_PLAY_SEQUENCE_NAME = "first_play_intro"

# Max characters per account.
MAX_CHARACTERS_PER_ACCOUNT = 16


class LauncherState(enum.Enum):
    SPLASH = "splash"
    TITLE_SCREEN = "title_screen"
    PATCH_CHECK = "patch_check"
    PATCHING = "patching"
    LOGIN = "login"
    DISCORD_OAUTH_FLOW = "discord_oauth_flow"
    SERVER_SELECTION = "server_selection"
    CHARACTER_SELECT = "character_select"
    CHARACTER_CREATION = "character_creation"
    WORLD_LOAD = "world_load"
    CINEMATIC_INTRO = "cinematic_intro"
    IN_GAME = "in_game"
    PAUSED = "paused"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class TransitionKind(enum.Enum):
    USER = "user"      # explicit button press
    AUTO = "auto"      # background work finished


@dataclasses.dataclass(frozen=True)
class Transition:
    from_state: LauncherState
    to_state: LauncherState
    kind: TransitionKind
    # Auto-transition predicate name. The system checks if
    # the predicate is "due" inside advance_automatic.
    auto_predicate: str = ""


# Static transition graph. Anything not in this set is
# rejected by transition_to.
_TRANSITIONS: tuple[Transition, ...] = (
    # Splash -> Title (auto after fade)
    Transition(
        LauncherState.SPLASH,
        LauncherState.TITLE_SCREEN,
        TransitionKind.AUTO,
        auto_predicate="splash_elapsed",
    ),
    # Title -> Patch check (user click "Start")
    Transition(
        LauncherState.TITLE_SCREEN,
        LauncherState.PATCH_CHECK,
        TransitionKind.USER,
    ),
    # Patch check -> Patching (auto if patches found)
    Transition(
        LauncherState.PATCH_CHECK,
        LauncherState.PATCHING,
        TransitionKind.AUTO,
        auto_predicate="patches_pending",
    ),
    # Patch check -> Login (auto if up to date)
    Transition(
        LauncherState.PATCH_CHECK,
        LauncherState.LOGIN,
        TransitionKind.AUTO,
        auto_predicate="patches_clean",
    ),
    # Patching -> Login (auto when download finished)
    Transition(
        LauncherState.PATCHING,
        LauncherState.LOGIN,
        TransitionKind.AUTO,
        auto_predicate="download_finished",
    ),
    # Login -> Discord OAuth (user clicks Discord button)
    Transition(
        LauncherState.LOGIN,
        LauncherState.DISCORD_OAUTH_FLOW,
        TransitionKind.USER,
    ),
    # OAuth -> Server selection (auto when OAuth completes)
    Transition(
        LauncherState.DISCORD_OAUTH_FLOW,
        LauncherState.SERVER_SELECTION,
        TransitionKind.AUTO,
        auto_predicate="oauth_complete",
    ),
    # OAuth -> Login (cancel / failure)
    Transition(
        LauncherState.DISCORD_OAUTH_FLOW,
        LauncherState.LOGIN,
        TransitionKind.USER,
    ),
    # Server selection -> Character select (user picks server)
    Transition(
        LauncherState.SERVER_SELECTION,
        LauncherState.CHARACTER_SELECT,
        TransitionKind.USER,
    ),
    # Character select -> Character creation (open slot picked)
    Transition(
        LauncherState.CHARACTER_SELECT,
        LauncherState.CHARACTER_CREATION,
        TransitionKind.USER,
    ),
    # Character creation -> Character select (cancel / finish)
    Transition(
        LauncherState.CHARACTER_CREATION,
        LauncherState.CHARACTER_SELECT,
        TransitionKind.USER,
    ),
    # Character select -> World load (existing char chosen)
    Transition(
        LauncherState.CHARACTER_SELECT,
        LauncherState.WORLD_LOAD,
        TransitionKind.USER,
    ),
    # World load -> Cinematic intro (first play only)
    Transition(
        LauncherState.WORLD_LOAD,
        LauncherState.CINEMATIC_INTRO,
        TransitionKind.AUTO,
        auto_predicate="world_loaded_first_play",
    ),
    # World load -> In-game (returning player)
    Transition(
        LauncherState.WORLD_LOAD,
        LauncherState.IN_GAME,
        TransitionKind.AUTO,
        auto_predicate="world_loaded_returning",
    ),
    # Cinematic intro -> In-game (auto after sequence)
    Transition(
        LauncherState.CINEMATIC_INTRO,
        LauncherState.IN_GAME,
        TransitionKind.AUTO,
        auto_predicate="intro_complete",
    ),
    # Cinematic intro -> In-game (user skip)
    Transition(
        LauncherState.CINEMATIC_INTRO,
        LauncherState.IN_GAME,
        TransitionKind.USER,
    ),
    # In-game <-> Paused
    Transition(
        LauncherState.IN_GAME,
        LauncherState.PAUSED,
        TransitionKind.USER,
    ),
    Transition(
        LauncherState.PAUSED,
        LauncherState.IN_GAME,
        TransitionKind.USER,
    ),
    # Pause -> back to character select (quit)
    Transition(
        LauncherState.PAUSED,
        LauncherState.CHARACTER_SELECT,
        TransitionKind.USER,
    ),
    # Any -> Disconnected (auto on socket drop). Common
    # entries; we add the most likely ones.
    Transition(
        LauncherState.IN_GAME,
        LauncherState.DISCONNECTED,
        TransitionKind.AUTO,
        auto_predicate="socket_dropped",
    ),
    Transition(
        LauncherState.WORLD_LOAD,
        LauncherState.DISCONNECTED,
        TransitionKind.AUTO,
        auto_predicate="socket_dropped",
    ),
    Transition(
        LauncherState.CHARACTER_SELECT,
        LauncherState.DISCONNECTED,
        TransitionKind.AUTO,
        auto_predicate="socket_dropped",
    ),
    Transition(
        LauncherState.DISCONNECTED,
        LauncherState.LOGIN,
        TransitionKind.USER,
    ),
    # Any -> Error (auto on unrecoverable)
    Transition(
        LauncherState.PATCHING,
        LauncherState.ERROR,
        TransitionKind.AUTO,
        auto_predicate="fatal_error",
    ),
    Transition(
        LauncherState.WORLD_LOAD,
        LauncherState.ERROR,
        TransitionKind.AUTO,
        auto_predicate="fatal_error",
    ),
    Transition(
        LauncherState.ERROR,
        LauncherState.TITLE_SCREEN,
        TransitionKind.USER,
    ),
)


@dataclasses.dataclass(frozen=True)
class CharacterCard:
    char_id: str
    char_name: str
    race: str          # character_creation.Race value
    main_job: str
    level: int
    last_played_zone: str
    last_played_ms: int  # ms since epoch
    hero_shot_uri: str   # zone_lighting_atlas hero shot


@dataclasses.dataclass(frozen=True)
class LauncherPose:
    state: LauncherState
    region: str
    account_id: str
    selected_server: str
    selected_char_id: str
    state_entered_ms: int
    is_first_play: bool


@dataclasses.dataclass
class _AccountInternal:
    account_id: str
    region: str = "en"
    state: LauncherState = LauncherState.SPLASH
    state_entered_ms: int = 0
    cards: list[CharacterCard] = dataclasses.field(
        default_factory=list,
    )
    last_played_char_id: str = ""
    selected_server: str = ""
    selected_char_id: str = ""
    first_play_complete: bool = False
    # Predicates set externally as background work completes.
    predicates: set[str] = dataclasses.field(default_factory=set)


@dataclasses.dataclass
class GameLauncherSystem:
    # account_id -> internal
    _accounts: dict[str, _AccountInternal] = dataclasses.field(
        default_factory=dict,
    )

    # ---------------------------------------------- register
    def register_state(
        self,
        account_id: str,
        *,
        region: str = "en",
        now_ms: int = 0,
    ) -> None:
        if not account_id:
            raise ValueError("account_id required")
        if account_id in self._accounts:
            raise ValueError(
                f"duplicate account_id: {account_id}",
            )
        if region not in ("en", "ja", "fr", "de"):
            raise ValueError(
                f"unsupported region: {region}",
            )
        self._accounts[account_id] = _AccountInternal(
            account_id=account_id,
            region=region,
            state_entered_ms=now_ms,
        )

    def has_account(self, account_id: str) -> bool:
        return account_id in self._accounts

    def account_count(self) -> int:
        return len(self._accounts)

    def _acct(self, account_id: str) -> _AccountInternal:
        if account_id not in self._accounts:
            raise KeyError(
                f"unknown account: {account_id}",
            )
        return self._accounts[account_id]

    # ---------------------------------------------- current
    def current_state(self, account_id: str) -> LauncherState:
        return self._acct(account_id).state

    def region_for(self, account_id: str) -> str:
        return self._acct(account_id).region

    # ---------------------------------------------- graph
    def valid_transitions_from(
        self,
        state: LauncherState,
    ) -> tuple[Transition, ...]:
        return tuple(
            t_ for t_ in _TRANSITIONS if t_.from_state == state
        )

    def transitions_total(self) -> int:
        return len(_TRANSITIONS)

    # ---------------------------------------------- transition
    def transition_to(
        self,
        account_id: str,
        to_state: LauncherState,
        *,
        reason: str = "",
        now_ms: int = 0,
    ) -> str:
        """Returns 'ok' or 'denied'."""
        acct = self._acct(account_id)
        cur = acct.state
        if cur == to_state:
            return "ok"
        for tr in _TRANSITIONS:
            if tr.from_state == cur and tr.to_state == to_state:
                acct.state = to_state
                acct.state_entered_ms = now_ms
                # Entering CHARACTER_CREATION from CHARACTER_
                # SELECT clears the selected char (you're
                # making a new one).
                if to_state == LauncherState.CHARACTER_CREATION:
                    acct.selected_char_id = ""
                return "ok"
        return "denied"

    # ---------------------------------------------- automatic
    def set_predicate(
        self,
        account_id: str,
        predicate: str,
        value: bool = True,
    ) -> None:
        acct = self._acct(account_id)
        if value:
            acct.predicates.add(predicate)
        else:
            acct.predicates.discard(predicate)

    def has_predicate(
        self,
        account_id: str,
        predicate: str,
    ) -> bool:
        return predicate in self._acct(account_id).predicates

    def advance_automatic(
        self,
        account_id: str,
        now_ms: int,
    ) -> bool:
        """Walks any AUTO edges whose predicates are true.

        SPLASH auto-elapses based on elapsed time. Other AUTO
        edges check ``predicates`` set by external callers
        (download finished, OAuth complete, world loaded).
        Returns True if any transition fired.
        """
        acct = self._acct(account_id)
        # Time-based predicates.
        if acct.state == LauncherState.SPLASH:
            if now_ms - acct.state_entered_ms >= SPLASH_DURATION_MS:
                acct.predicates.add("splash_elapsed")
        if acct.state == LauncherState.CINEMATIC_INTRO:
            if (
                now_ms - acct.state_entered_ms
                >= CINEMATIC_INTRO_DURATION_MS
            ):
                acct.predicates.add("intro_complete")
        # First-time vs returning predicate at WORLD_LOAD.
        if acct.state == LauncherState.WORLD_LOAD:
            if "world_loaded" in acct.predicates:
                if acct.first_play_complete:
                    acct.predicates.add("world_loaded_returning")
                else:
                    acct.predicates.add("world_loaded_first_play")
        # Walk edges.
        for tr in _TRANSITIONS:
            if tr.from_state != acct.state:
                continue
            if tr.kind != TransitionKind.AUTO:
                continue
            if tr.auto_predicate and tr.auto_predicate not in acct.predicates:
                continue
            # Fire.
            acct.state = tr.to_state
            acct.state_entered_ms = now_ms
            # Predicates consumed.
            for p in (
                "splash_elapsed", "patches_pending", "patches_clean",
                "download_finished", "oauth_complete",
                "world_loaded_first_play",
                "world_loaded_returning", "intro_complete",
                "world_loaded",
            ):
                acct.predicates.discard(p)
            return True
        return False

    # ---------------------------------------------- characters
    def register_character_card(
        self,
        account_id: str,
        card: CharacterCard,
    ) -> None:
        acct = self._acct(account_id)
        if len(acct.cards) >= MAX_CHARACTERS_PER_ACCOUNT:
            raise ValueError(
                f"max {MAX_CHARACTERS_PER_ACCOUNT} characters",
            )
        if not card.char_id:
            raise ValueError("char_id required")
        for c in acct.cards:
            if c.char_id == card.char_id:
                raise ValueError(
                    f"duplicate char_id: {card.char_id}",
                )
        if not (1 <= card.level <= 99):
            raise ValueError("level out of range")
        acct.cards.append(card)

    def character_cards(
        self,
        account_id: str,
    ) -> tuple[CharacterCard, ...]:
        return tuple(self._acct(account_id).cards)

    def card_slots_free(self, account_id: str) -> int:
        return MAX_CHARACTERS_PER_ACCOUNT - len(
            self._acct(account_id).cards,
        )

    def last_played_card_id(self, account_id: str) -> str:
        acct = self._acct(account_id)
        if acct.last_played_char_id:
            return acct.last_played_char_id
        if not acct.cards:
            return ""
        # Auto-pick the most recent by last_played_ms.
        best = max(acct.cards, key=lambda c: c.last_played_ms)
        return best.char_id

    def select_character(
        self,
        account_id: str,
        char_id: str,
    ) -> CharacterCard:
        acct = self._acct(account_id)
        if acct.state != LauncherState.CHARACTER_SELECT:
            raise ValueError(
                "must be in CHARACTER_SELECT to select",
            )
        for c in acct.cards:
            if c.char_id == char_id:
                acct.selected_char_id = char_id
                acct.last_played_char_id = char_id
                return c
        raise KeyError(f"unknown char_id: {char_id}")

    def selected_character(
        self,
        account_id: str,
    ) -> str:
        return self._acct(account_id).selected_char_id

    # ---------------------------------------------- server
    def select_server(
        self,
        account_id: str,
        server_name: str,
    ) -> None:
        if server_name not in (
            "us_east", "eu_west", "jp_tokyo", "sea_singapore",
        ):
            raise ValueError(
                f"unknown server: {server_name}",
            )
        acct = self._acct(account_id)
        if acct.state != LauncherState.SERVER_SELECTION:
            raise ValueError(
                "must be in SERVER_SELECTION to select",
            )
        acct.selected_server = server_name

    def selected_server(self, account_id: str) -> str:
        return self._acct(account_id).selected_server

    # ---------------------------------------------- first play
    def is_first_play(self, account_id: str) -> bool:
        return not self._acct(account_id).first_play_complete

    def set_first_play_complete(
        self,
        account_id: str,
    ) -> None:
        self._acct(account_id).first_play_complete = True

    def first_play_sequence_name(self) -> str:
        return FIRST_PLAY_SEQUENCE_NAME

    # ---------------------------------------------- pose
    def launcher_pose(
        self,
        account_id: str,
    ) -> LauncherPose:
        acct = self._acct(account_id)
        return LauncherPose(
            state=acct.state,
            region=acct.region,
            account_id=acct.account_id,
            selected_server=acct.selected_server,
            selected_char_id=acct.selected_char_id,
            state_entered_ms=acct.state_entered_ms,
            is_first_play=not acct.first_play_complete,
        )


__all__ = [
    "LauncherState",
    "TransitionKind",
    "Transition",
    "CharacterCard",
    "LauncherPose",
    "GameLauncherSystem",
    "SPLASH_DURATION_MS",
    "CINEMATIC_INTRO_DURATION_MS",
    "FIRST_PLAY_SEQUENCE_NAME",
    "MAX_CHARACTERS_PER_ACCOUNT",
]
