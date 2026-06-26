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
        """Initialize the duel state from the two branches."""
        left_game = Game.from_repo(self.repo.working_tree_dir, branch=self.left_branch)
        right_game = Game.from_repo(self.repo.working_tree_dir, branch=self.right_branch)
        self.state = DuelState(
            left_game=left_game,
            right_game=right_game,
            board=chess.Board(),
        )

    def get_current_move(self) -> Optional[CommitMove]:
        """Get the current move for the active branch."""
        if self.state is None:
            return None
        if self.state.current_turn == 0:
            if self.state.left_index < len(self.state.left_game.moves):
                return self.state.left_game.moves[self.state.left_index]
        else:
            if self.state.right_index < len(self.state.right_game.moves):
                return self.state.right_game.moves[self.state.right_index]
        return None

    def advance_turn(self) -> None:
        """Advance the turn to the next branch."""
        if self.state is None:
            return
        # Check if current branch has a merge commit that triggers conflict resolution
        if self.state.current_turn == 0:
            self.state.left_index += 1
        else:
            self.state.right_index += 1
        self.state.current_turn = 1 - self.state.current_turn

    def apply_move(self) -> bool:
        """Apply the current move to the board. Returns True if successful."""
        if self.state is None:
            return False
        move = self.get_current_move()
        if move is None:
            return False
        # Validate the move against the current board
        legal_moves = list(self.state.board.legal_moves)
        # Check if any legal move matches the square mapping
        for legal in legal_moves:
            # We map the move squares to the commit move's squares
            if legal.from_square == move.from_square and legal.to_square == move.to_square:
                self.state.board.push(legal)
                return True
        # If no exact match, try to find a legal move that has same to_square (capture)
        for legal in legal_moves:
            if legal.to_square == move.to_square:
                self.state.board.push(legal)
                return True
        # If still no match, it might be a conflict or illegal move
        self.state.conflict_squares.append(move.to_square)
        return False

    def detect_conflicts(self) -> List[Tuple[str, chess.Square]]:
        """Detect conflicts between the two branches at the current state.
        Returns list of (branch_name, square) tuples where conflicts exist."""
        if self.state is None:
            return []
        conflicts: List[Tuple[str, chess.Square]] = []
        # Compare the next moves from both branches
        left_move = None
        right_move = None
        if self.state.left_index < len(self.state.left_game.moves):
            left_move = self.state.left_game.moves[self.state.left_index]
        if self.state.right_index < len(self.state.right_game.moves):
            right_move = self.state.right_game.moves[self.state.right_index]
        if left_move and right_move:
            # A conflict occurs if both moves try to move to the same square
            if left_move.to_square == right_move.to_square:
                conflicts.append((self.left_branch, left_move.to_square))
                conflicts.append((self.right_branch, right_move.to_square))
            # Also conflict if one move captures a piece that the other needs
            if self.state.board.piece_at(left_move.to_square) and self.state.board.piece_at(right_move.to_square):
                if left_move.to_square == right_move.to_square:
                    pass  # already added
        return conflicts

    def resolve_conflict(self, square: chess.Square) -> bool:
        """Resolve a conflict by merging the two moves at the given square.
        This simulates a merge commit by combining the two moves.
        Returns True if the conflict was resolved."""
        if self.state is None:
            return False
        # Get the conflicting moves
        left_move = None
        right_move = None
        if self.state.left_index < len(self.state.left_game.moves):
            left_move = self.state.left_game.moves[self.state.left_index]
        if self.state.right_index < len(self.state.right_game.moves):
            right_move = self.state.right_game.moves[self.state.right_index]
        if left_move is None or right_move is None:
            return False
        # Create a merge move that combines both: move left piece to square, then right piece to square
        # This is a simplified resolution; in practice, we'd need to handle the merge commit properly
        merge_move = chess.Move(left_move.from_square, square)
        if merge_move in self.state.board.legal_moves:
            self.state.board.push(merge_move)
            # Now advance both branches past the conflict
            self.state.left_index += 1
            self.state.right_index += 1
            # Remove from conflict list
            if square in self.state.conflict_squares:
                self.state.conflict_squares.remove(square)
            return True
        return False

    def is_finished(self) -> bool:
        """Check if the duel is finished (both branches have no more moves)."""
        if self.state is None:
            return True
        return (self.state.left_index >= len(self.state.left_game.moves) and
                self.state.right_index >= len(self.state.right_game.moves))

    def get_scores(self) -> Tuple[int, int]:
        """Get the scores (number of pieces captured) for left and right branches."""
        if self.state is None:
            return (0, 0)
        # Count captures as the number of pieces that have been taken
        # This is a simple heuristic; in practice, we'd track captures more precisely
        left_captures = 0
        right_captures = 0
        # Walk through the move history and count captures
        for move in self.state.board.move_stack:
            if self.state.board.is_capture(move):
                # Determine which branch made this move
                # This is a simplified approach; we'd need to track which branch made each move
                if len(self.state.board.move_stack) % 2 == 0:
                    right_captures += 1
                else:
                    left_captures += 1
        return (left_captures, right_captures)

    def get_board_state(self) -> chess.Board:
        """Get the current board state."""
        if self.state is None:
            return chess.Board()