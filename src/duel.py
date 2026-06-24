from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import chess
from git import Repo, GitCommandError

from .game import Game, CommitMove
from .models import EXTENSION_PIECE_MAP, DEFAULT_PIECE, get_piece_for_path, path_to_square


@dataclass
class DuelState:
    """State for a branch duel."""
    left_game: Game
    right_game: Game
    left_index: int = 0
    right_index: int = 0
    current_turn: int = 0  # 0 = left, 1 = right
    board: chess.Board = field(default_factory=chess.Board)
    merge_commit: Optional[str] = None
    conflict_squares: List[chess.Square] = field(default_factory=list)


class BranchDuel:
    """
    Duel mode: two branches play against each other.
    Each branch's commit history is converted to moves.
    Turns alternate between branches. When a merge commit is encountered,
    the board is reset to the common ancestor and play continues from there.
    """

    def __init__(self, repo_path: Path, left_branch: str, right_branch: str) -> None:
        self.repo = Repo(repo_path)
        self.left_branch = left_branch
        self.right_branch = right_branch
        self.state: Optional[DuelState] = None

    def initialize(self) -> None:
        """Initialize duel state from both branches."""
        try:
            left_game = Game.from_repo(Path(self.repo.working_dir), branch=self.left_branch)
            right_game = Game.from_repo(Path(self.repo.working_dir), branch=self.right_branch)
        except (GitCommandError, ValueError) as e:
            raise ValueError(f"Failed to load branches: {e}")

        self.state = DuelState(
            left_game=left_game,
            right_game=right_game,
            board=chess.Board()
        )

    def get_next_move(self) -> Optional[Tuple[str, chess.Move, int]]:
        """
        Get the next move from the current branch.
        Returns (branch_name, move, commit_index) or None if no more moves.
        """
        if self.state is None:
            return None

        state = self.state
        if state.current_turn == 0:
            game = state.left_game
            idx = state.left_index
            branch_name = self.left_branch
        else:
            game = state.right_game
            idx = state.right_index
            branch_name = self.right_branch

        if idx >= len(game.moves):
            return None

        commit_move = game.moves[idx]
        move = self._commit_move_to_chess_move(commit_move, state.board)
        return (branch_name, move, idx)

    def advance_turn(self) -> None:
        """Advance to the next turn after a move has been made."""
        if self.state is None:
            return

        state = self.state
        if state.current_turn == 0:
            state.left_index += 1
        else:
            state.right_index += 1
        state.current_turn = 1 - state.current_turn

    def _commit_move_to_chess_move(self, commit_move: CommitMove, board: chess.Board) -> chess.Move:
        """Convert a CommitMove to a chess.Move, handling piece mapping."""
        from_square = path_to_square(commit_move.file_path, commit_move.added_lines)
        to_square = path_to_square(commit_move.file_path, commit_move.removed_lines)

        if from_square is None or to_square is None:
            raise ValueError(f"Could not determine move squares for {commit_move.file_path}")

        piece_type = get_piece_for_path(commit_move.file_path)
        promotion = None

        # Check for promotion (last rank)
        if piece_type == chess.PAWN:
            rank = chess.square_rank(to_square)
            if rank == 7 or rank == 0:
                promotion = chess.QUEEN  # auto-queen for now

        move = chess.Move(from_square, to_square, promotion=promotion)

        # Validate move is legal
        if board.is_legal(move):
            return move

        # Try to find a legal move that matches the diff
        for legal_move in board.legal_moves:
            if legal_move.from_square == from_square and legal_move.to_square == to_square:
                return legal_move

        raise ValueError(f"No legal move found from {chess.square_name(from_square)} to {chess.square_name(to_square)}")

    def detect_merge_conflict(self) -> bool:
        """Check if the current position would cause a merge conflict.
        Returns True if both branches have moved to the same square."""
        if self.state is None:
            return False

        state = self.state
        if state.left_index >= len(state.left_game.moves) or state.right_index >= len(state.right_game.moves):
            return False

        left_move = state.left_game.moves[state.left_index]
        right_move = state.right_game.moves[state.right_index]

        left_to = path_to_square(left_move.file_path, left_move.removed_lines)
        right_to = path_to_square(right_move.file_path, right_move.removed_lines)

        if left_to is not None and right_to is not None and left_to == right_to:
            state.conflict_squares.append(left_to)
            return True
        return False

    def resolve_conflict(self) -> Optional[chess.Move]:
        """Resolve a merge conflict by choosing a move that avoids conflict.
        Returns the resolved move or None if cannot resolve."""
        if self.state is None or not self.state.conflict_squares:
            return None

        state = self.state
        conflict_square = state.conflict_squares[-1]

        # Try to find alternative moves for the current branch
        if state.current_turn == 0:
            game = state.left_game
            idx = state.left_index
        else:
            game = state.right_game
            idx = state.right_index

        if idx >= len(game.moves):
            return None

        commit_move = game.moves[idx]
        board = state.board.copy()

        # Try all legal moves that don't go to conflict square
        for legal_move in board.legal_moves:
            if legal_move.to_square != conflict_square:
                # Check if this move is somewhat related to the diff
                from_square = path_to_square(commit_move.file_path, commit_move.added_lines)
                if from_square is not None and legal_move.from_square == from_square:
                    return legal_move

        return None

    def apply_merge(self) -> None:
        """Apply a merge commit: reset board to common ancestor and continue."""
        if self.state is None:
            return

        state = self.state
        # Find common ancestor (for simplicity, reset to initial board)
        state.board = chess.Board()
        state.left_index = 0
        state.right_index = 0
        state.current_turn = 0
        state.merge_commit = None
        state.conflict_squares.clear()

    def get_game_status(self) -> Dict[str, object]:
        """Get current status of the duel."""
        if self.state is None:
            return {"error": "Not initialized"}