"""Puzzle assembly journal — collected hints assemble into pieces.

A player who has seen a hint (and the hint was visible
to them per attentiveness gating) gets that hint
RECORDED in their journal. Hints map to puzzle pieces;
puzzle pieces map to puzzle solutions.

A puzzle piece is CONFIRMED when the player has seen
ENOUGH hints for it (the threshold is per-piece and
typically 1..3 — redundant hints make pieces easier to
hit, but the most subtle pieces require multiple
corroborating fragments).

Once enough puzzle pieces are confirmed for a SOLUTION,
that solution unlocks and is added to the player's
endgame_solution_journal.

Public surface
--------------
    PuzzlePiece dataclass (frozen)
    Solution dataclass (frozen)
    PuzzleAssemblyJournal
        .define_piece(piece_id, label, hints_needed)
        .define_solution(solution_id, label, piece_ids)
        .observe_hint(player_id, hint_id, piece_id)
        .piece_confirmed(player_id, piece_id) -> bool
        .solutions_unlocked(player_id) -> tuple[Solution, ...]
        .pieces_for(player_id) -> tuple[PuzzlePiece, ...]
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class PuzzlePiece:
    piece_id: str
    label: str
    hints_needed: int = 1   # how many distinct hints to confirm


@dataclasses.dataclass(frozen=True)
class Solution:
    solution_id: str
    label: str
    piece_ids: tuple[str, ...]


@dataclasses.dataclass
class _PlayerJournal:
    # piece_id -> set of hint_ids observed for that piece
    observed: dict[str, set[str]] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class PuzzleAssemblyJournal:
    _pieces: dict[str, PuzzlePiece] = dataclasses.field(default_factory=dict)
    _solutions: dict[str, Solution] = dataclasses.field(default_factory=dict)
    _journals: dict[str, _PlayerJournal] = dataclasses.field(
        default_factory=dict,
    )

    def define_piece(
        self, *, piece_id: str, label: str, hints_needed: int = 1,
    ) -> bool:
        if not piece_id or piece_id in self._pieces or hints_needed < 1:
            return False
        self._pieces[piece_id] = PuzzlePiece(
            piece_id=piece_id, label=label, hints_needed=hints_needed,
        )
        return True

    def define_solution(
        self, *, solution_id: str, label: str,
        piece_ids: t.Iterable[str],
    ) -> bool:
        if not solution_id or solution_id in self._solutions:
            return False
        ids = tuple(piece_ids)
        if not ids:
            return False
        # all referenced pieces must exist
        for pid in ids:
            if pid not in self._pieces:
                return False
        self._solutions[solution_id] = Solution(
            solution_id=solution_id, label=label, piece_ids=ids,
        )
        return True

    def _journal(self, player_id: str) -> _PlayerJournal:
        if player_id not in self._journals:
            self._journals[player_id] = _PlayerJournal()
        return self._journals[player_id]

    def observe_hint(
        self, *, player_id: str, hint_id: str, piece_id: str,
    ) -> bool:
        if not player_id or not hint_id:
            return False
        if piece_id not in self._pieces:
            return False
        j = self._journal(player_id)
        bucket = j.observed.setdefault(piece_id, set())
        if hint_id in bucket:
            return False
        bucket.add(hint_id)
        return True

    def piece_confirmed(
        self, *, player_id: str, piece_id: str,
    ) -> bool:
        piece = self._pieces.get(piece_id)
        if piece is None:
            return False
        j = self._journals.get(player_id)
        if j is None:
            return False
        return len(j.observed.get(piece_id, set())) >= piece.hints_needed

    def pieces_for(
        self, *, player_id: str,
    ) -> tuple[PuzzlePiece, ...]:
        """Return the pieces this player has CONFIRMED."""
        j = self._journals.get(player_id)
        if j is None:
            return ()
        out: list[PuzzlePiece] = []
        for piece_id, observed in j.observed.items():
            piece = self._pieces.get(piece_id)
            if piece and len(observed) >= piece.hints_needed:
                out.append(piece)
        # stable order: by piece_id
        return tuple(sorted(out, key=lambda p: p.piece_id))

    def solutions_unlocked(
        self, *, player_id: str,
    ) -> tuple[Solution, ...]:
        confirmed_ids = {
            p.piece_id for p in self.pieces_for(player_id=player_id)
        }
        out: list[Solution] = []
        for sol in self._solutions.values():
            if all(pid in confirmed_ids for pid in sol.piece_ids):
                out.append(sol)
        return tuple(sorted(out, key=lambda s: s.solution_id))

    def hints_observed_count(
        self, *, player_id: str, piece_id: str,
    ) -> int:
        j = self._journals.get(player_id)
        if j is None:
            return 0
        return len(j.observed.get(piece_id, set()))


__all__ = [
    "PuzzlePiece", "Solution", "PuzzleAssemblyJournal",
]
