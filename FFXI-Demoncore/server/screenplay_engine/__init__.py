"""Screenplay engine — industry-standard screenplay format.

The pre-production layer above ``ai_plot_generator`` and
``dynamic_quest_gen``. A scene the plot generator hands us
is a coarse beat-list; this module turns that beat-list into
a real screenplay — sluglines, action, character cues,
dialogue, parentheticals, transitions, shot directions —
that the storyboard, shot list, previs, voice direction, and
continuity layers all read as a common source of truth.

Format follows the WGA / Final Draft conventions: 1 page is
roughly 1 minute of screen time, dialogue weighs more per
word than action, sluglines parse "INT. BASTOK MARKETS - DAY"
into kind/location/time, and revisions get colour-coded
A-page bumps (white → blue → pink → yellow → green → ...).

Public surface
--------------
    ElementKind enum
    SluglineKind enum
    RevisionColor enum
    Slugline dataclass (frozen)
    Element dataclass (frozen)
    Scene dataclass (frozen)
    Sequence dataclass (frozen)
    parse_slugline(text)
    build_scene(slugline, elements)
    build_sequence(scenes)
    estimate_runtime_minutes(sequence)
    bump_revision(sequence, color)
    to_fountain(sequence)
    from_fountain(text)
    validate_sequence(sequence)
"""
from __future__ import annotations

import dataclasses
import enum
import re
import typing as t


class ElementKind(enum.Enum):
    SLUGLINE = "slugline"
    ACTION = "action"
    CHARACTER = "character"
    DIALOGUE = "dialogue"
    PARENTHETICAL = "parenthetical"
    TRANSITION = "transition"
    SHOT = "shot"
    DUAL_DIALOGUE = "dual_dialogue"


class SluglineKind(enum.Enum):
    INT = "INT"
    EXT = "EXT"
    INT_EXT = "INT/EXT"


class RevisionColor(enum.Enum):
    """WGA standard production revision colour cycle.

    Revisions cycle in this order; once a script burns through
    all eight, the next revision wraps back to the start with
    a "Double" prefix in production sheets.
    """
    WHITE = "white"
    BLUE = "blue"
    PINK = "pink"
    YELLOW = "yellow"
    GREEN = "green"
    GOLDENROD = "goldenrod"
    BUFF = "buff"
    SALMON = "salmon"
    CHERRY = "cherry"


_REVISION_ORDER: tuple[RevisionColor, ...] = (
    RevisionColor.WHITE,
    RevisionColor.BLUE,
    RevisionColor.PINK,
    RevisionColor.YELLOW,
    RevisionColor.GREEN,
    RevisionColor.GOLDENROD,
    RevisionColor.BUFF,
    RevisionColor.SALMON,
    RevisionColor.CHERRY,
)


# Industry word-counts per minute. 1 page ≈ 1 minute.
# Action averages ~36 words / page. Dialogue averages
# ~25 words / page (more whitespace). Slugline / transition
# / shot / parenthetical cost a fixed eighth-page each.
_WORDS_PER_PAGE_ACTION = 36
_WORDS_PER_PAGE_DIALOGUE = 25
_FIXED_EIGHTH = 0.125


@dataclasses.dataclass(frozen=True)
class Slugline:
    """Parsed slugline — kind / location / time."""
    kind: SluglineKind
    location: str
    time_of_day: str

    def render(self) -> str:
        return f"{self.kind.value}. {self.location} - {self.time_of_day}"


@dataclasses.dataclass(frozen=True)
class Element:
    """A single screenplay element."""
    kind: ElementKind
    text: str
    character: str = ""           # CHARACTER + DIALOGUE only
    parenthetical: str = ""       # PARENTHETICAL only
    dual_pair: tuple[str, str] = ("", "")  # DUAL_DIALOGUE only
    line_no: int = 0              # 1-indexed; 0 = unassigned


@dataclasses.dataclass(frozen=True)
class Scene:
    scene_id: str
    slugline: Slugline
    elements: tuple[Element, ...]


@dataclasses.dataclass(frozen=True)
class Sequence:
    sequence_id: str
    scenes: tuple[Scene, ...]
    revision_color: RevisionColor = RevisionColor.WHITE
    revision_number: int = 0


# ------------------------------------------------------------
# Slugline parsing
# ------------------------------------------------------------
_SLUG_RE = re.compile(
    r"^\s*(INT\.?/EXT\.?|INT\.?|EXT\.?)\s+(.+?)\s*-\s*(.+?)\s*$",
    re.IGNORECASE,
)


def parse_slugline(text: str) -> Slugline:
    """Parse "INT. BASTOK MARKETS - DAY" into a Slugline."""
    if not text or not text.strip():
        raise ValueError("empty slugline")
    m = _SLUG_RE.match(text.strip())
    if not m:
        raise ValueError(f"malformed slugline: {text!r}")
    raw_kind = m.group(1).upper().rstrip(".")
    if raw_kind in ("INT/EXT", "INT./EXT", "INT/EXT."):
        kind = SluglineKind.INT_EXT
    elif raw_kind == "INT":
        kind = SluglineKind.INT
    elif raw_kind == "EXT":
        kind = SluglineKind.EXT
    else:
        raise ValueError(f"unknown slugline kind: {raw_kind!r}")
    location = m.group(2).strip().upper()
    time_of_day = m.group(3).strip().upper()
    if not location:
        raise ValueError("slugline missing location")
    if not time_of_day:
        raise ValueError("slugline missing time-of-day")
    return Slugline(kind=kind, location=location, time_of_day=time_of_day)


# ------------------------------------------------------------
# Element / scene / sequence builders
# ------------------------------------------------------------
def _validate_elements(elements: t.Sequence[Element]) -> None:
    """Validate dialogue/parenthetical follows CHARACTER cue.

    Rules:
    - DIALOGUE only after CHARACTER or PARENTHETICAL.
    - PARENTHETICAL only after CHARACTER or DIALOGUE.
    - CHARACTER must precede DIALOGUE eventually.
    - DUAL_DIALOGUE has both characters baked in; stands alone.
    """
    prev_kind: t.Optional[ElementKind] = None
    for i, el in enumerate(elements):
        if el.kind == ElementKind.DIALOGUE:
            if prev_kind not in (
                ElementKind.CHARACTER,
                ElementKind.PARENTHETICAL,
            ):
                raise ValueError(
                    f"DIALOGUE at index {i} must follow CHARACTER "
                    f"or PARENTHETICAL, got {prev_kind}",
                )
            if not el.character:
                raise ValueError(
                    f"DIALOGUE at index {i} missing character",
                )
        elif el.kind == ElementKind.PARENTHETICAL:
            if prev_kind not in (
                ElementKind.CHARACTER,
                ElementKind.DIALOGUE,
            ):
                raise ValueError(
                    f"PARENTHETICAL at index {i} must follow "
                    f"CHARACTER or DIALOGUE, got {prev_kind}",
                )
        elif el.kind == ElementKind.CHARACTER:
            if not el.text or not el.text.strip():
                raise ValueError(
                    f"CHARACTER at index {i} cannot be empty",
                )
            if el.text != el.text.upper():
                raise ValueError(
                    f"CHARACTER cue must be uppercased: {el.text!r}",
                )
        elif el.kind == ElementKind.DUAL_DIALOGUE:
            a, b = el.dual_pair
            if not a or not b:
                raise ValueError(
                    f"DUAL_DIALOGUE at index {i} must name both",
                )
        prev_kind = el.kind


def validate_sequence(sequence: Sequence) -> None:
    """Walk every scene; raise on malformed element ordering."""
    for scene in sequence.scenes:
        _validate_elements(scene.elements)


def build_scene(
    scene_id: str,
    slugline: Slugline,
    elements: t.Sequence[Element],
) -> Scene:
    if not scene_id:
        raise ValueError("scene_id required")
    _validate_elements(elements)
    return Scene(
        scene_id=scene_id,
        slugline=slugline,
        elements=tuple(elements),
    )


def build_sequence(
    sequence_id: str,
    scenes: t.Sequence[Scene],
) -> Sequence:
    if not sequence_id:
        raise ValueError("sequence_id required")
    if not scenes:
        raise ValueError("sequence requires at least one scene")
    return Sequence(
        sequence_id=sequence_id,
        scenes=tuple(scenes),
    )


# ------------------------------------------------------------
# Page count / runtime estimation
# ------------------------------------------------------------
def _word_count(text: str) -> int:
    if not text:
        return 0
    return len([w for w in text.split() if w.strip()])


def _element_pages(el: Element) -> float:
    if el.kind == ElementKind.ACTION:
        wc = _word_count(el.text)
        return wc / _WORDS_PER_PAGE_ACTION
    if el.kind == ElementKind.DIALOGUE:
        wc = _word_count(el.text)
        return wc / _WORDS_PER_PAGE_DIALOGUE
    if el.kind == ElementKind.DUAL_DIALOGUE:
        # Two columns side-by-side; total page cost is the
        # longer of the two halves.
        wc = max(
            _word_count(el.text),
            _word_count(el.parenthetical),
        )
        return wc / _WORDS_PER_PAGE_DIALOGUE
    if el.kind in (
        ElementKind.SLUGLINE,
        ElementKind.CHARACTER,
        ElementKind.PARENTHETICAL,
        ElementKind.TRANSITION,
        ElementKind.SHOT,
    ):
        return _FIXED_EIGHTH
    return 0.0


def estimate_runtime_minutes(sequence: Sequence) -> float:
    """1 page ≈ 1 minute of screen time."""
    total = 0.0
    for scene in sequence.scenes:
        # Every scene starts with its slugline (one eighth).
        total += _FIXED_EIGHTH
        for el in scene.elements:
            total += _element_pages(el)
    return round(total, 3)


def page_count(sequence: Sequence) -> float:
    """Alias — pages and minutes are the same number."""
    return estimate_runtime_minutes(sequence)


# ------------------------------------------------------------
# Revision bumps
# ------------------------------------------------------------
def bump_revision(
    sequence: Sequence,
    color: t.Optional[RevisionColor] = None,
) -> Sequence:
    """Advance to the next revision color (or jump to one).

    If no colour given, advance one step in the WGA cycle.
    """
    if color is None:
        try:
            idx = _REVISION_ORDER.index(sequence.revision_color)
        except ValueError:
            idx = 0
        nxt = _REVISION_ORDER[(idx + 1) % len(_REVISION_ORDER)]
    else:
        nxt = color
    return dataclasses.replace(
        sequence,
        revision_color=nxt,
        revision_number=sequence.revision_number + 1,
    )


def assign_line_numbers(scene: Scene) -> Scene:
    """Number elements 1..N for revision tracking."""
    new_els = tuple(
        dataclasses.replace(el, line_no=i + 1)
        for i, el in enumerate(scene.elements)
    )
    return dataclasses.replace(scene, elements=new_els)


def a_page_label(line_no: int, revision: int) -> str:
    """Standard A-page label — "12A" for the line inserted
    after line 12 in revision 1, "12B" for revision 2, etc.
    """
    if line_no < 1:
        raise ValueError("line_no must be >= 1")
    if revision < 1:
        raise ValueError("revision must be >= 1")
    # 1 → A, 2 → B, ..., 26 → Z, 27 → AA
    letters = ""
    n = revision
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters = chr(ord("A") + rem) + letters
    return f"{line_no}{letters}"


# ------------------------------------------------------------
# Fountain (open-source plain-text screenplay format)
# ------------------------------------------------------------
def to_fountain(sequence: Sequence) -> str:
    """Emit Fountain markdown — open-source format used by
    Highland, Slugline, Trelby, Beat, Logline, FadeIn.
    """
    out: list[str] = []
    out.append(f"Title: {sequence.sequence_id}")
    out.append(
        f"Revision: {sequence.revision_color.value} "
        f"({sequence.revision_number})",
    )
    out.append("")
    for scene in sequence.scenes:
        out.append(scene.slugline.render())
        out.append("")
        for el in scene.elements:
            if el.kind == ElementKind.ACTION:
                out.append(el.text)
                out.append("")
            elif el.kind == ElementKind.CHARACTER:
                out.append(el.text)
            elif el.kind == ElementKind.PARENTHETICAL:
                out.append(f"({el.text})")
            elif el.kind == ElementKind.DIALOGUE:
                out.append(el.text)
                out.append("")
            elif el.kind == ElementKind.TRANSITION:
                out.append(f"> {el.text}")
                out.append("")
            elif el.kind == ElementKind.SHOT:
                out.append(f"!{el.text}")
                out.append("")
            elif el.kind == ElementKind.DUAL_DIALOGUE:
                a, b = el.dual_pair
                out.append(f"{a} ^")
                out.append(el.text)
                out.append("")
                out.append(b)
                out.append(el.parenthetical)
                out.append("")
    return "\n".join(out).rstrip() + "\n"


def from_fountain(text: str) -> Sequence:
    """Best-effort Fountain parser stub.

    Recognises sluglines (INT./EXT./INT./EXT.), uppercase
    CHARACTER cues followed by dialogue, parentheticals
    in (parens), transitions starting with ">", and shots
    starting with "!". Plain prose lines become ACTION.
    """
    lines = text.splitlines()
    title = "untitled"
    revision_color = RevisionColor.WHITE
    revision_number = 0
    body_start = 0
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith("Title:"):
            title = s.split(":", 1)[1].strip() or title
        elif s.startswith("Revision:"):
            r = s.split(":", 1)[1].strip().lower()
            for rc in RevisionColor:
                if rc.value in r:
                    revision_color = rc
                    break
            m = re.search(r"\((\d+)\)", r)
            if m:
                revision_number = int(m.group(1))
        elif s == "":
            body_start = i + 1
            break
        else:
            body_start = i
            break
    scenes: list[Scene] = []
    current_slug: t.Optional[Slugline] = None
    current_elements: list[Element] = []
    scene_idx = 0
    prev_kind: t.Optional[ElementKind] = None

    def _flush() -> None:
        nonlocal scene_idx, current_slug, current_elements
        if current_slug is not None:
            scenes.append(
                Scene(
                    scene_id=f"s{scene_idx:03d}",
                    slugline=current_slug,
                    elements=tuple(current_elements),
                ),
            )
            scene_idx += 1
        current_slug = None
        current_elements = []

    i = body_start
    while i < len(lines):
        ln = lines[i].rstrip()
        s = ln.strip()
        if not s:
            i += 1
            continue
        # Slugline?
        try:
            slug = parse_slugline(s)
            _flush()
            current_slug = slug
            prev_kind = ElementKind.SLUGLINE
            i += 1
            continue
        except ValueError:
            pass
        if s.startswith(">"):
            current_elements.append(
                Element(
                    kind=ElementKind.TRANSITION,
                    text=s[1:].strip(),
                ),
            )
            prev_kind = ElementKind.TRANSITION
            i += 1
            continue
        if s.startswith("!"):
            current_elements.append(
                Element(
                    kind=ElementKind.SHOT,
                    text=s[1:].strip(),
                ),
            )
            prev_kind = ElementKind.SHOT
            i += 1
            continue
        if s.startswith("(") and s.endswith(")") and prev_kind in (
            ElementKind.CHARACTER, ElementKind.DIALOGUE,
        ):
            current_elements.append(
                Element(
                    kind=ElementKind.PARENTHETICAL,
                    text=s[1:-1].strip(),
                ),
            )
            prev_kind = ElementKind.PARENTHETICAL
            i += 1
            continue
        if s == s.upper() and len(s) >= 2 and not s.endswith(":"):
            # CHARACTER cue
            current_elements.append(
                Element(
                    kind=ElementKind.CHARACTER,
                    text=s,
                ),
            )
            prev_kind = ElementKind.CHARACTER
            i += 1
            continue
        if prev_kind in (
            ElementKind.CHARACTER, ElementKind.PARENTHETICAL,
        ):
            char_name = ""
            for el in reversed(current_elements):
                if el.kind == ElementKind.CHARACTER:
                    char_name = el.text
                    break
            current_elements.append(
                Element(
                    kind=ElementKind.DIALOGUE,
                    text=s,
                    character=char_name,
                ),
            )
            prev_kind = ElementKind.DIALOGUE
            i += 1
            continue
        # Default: action.
        current_elements.append(
            Element(kind=ElementKind.ACTION, text=s),
        )
        prev_kind = ElementKind.ACTION
        i += 1
    _flush()
    if not scenes:
        raise ValueError("Fountain text has no scenes")
    return Sequence(
        sequence_id=title,
        scenes=tuple(scenes),
        revision_color=revision_color,
        revision_number=revision_number,
    )


__all__ = [
    "ElementKind", "SluglineKind", "RevisionColor",
    "Slugline", "Element", "Scene", "Sequence",
    "parse_slugline",
    "build_scene", "build_sequence",
    "estimate_runtime_minutes", "page_count",
    "bump_revision", "assign_line_numbers", "a_page_label",
    "to_fountain", "from_fountain",
    "validate_sequence",
]
