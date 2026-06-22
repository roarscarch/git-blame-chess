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

    def build_duel(self) -> DuelState:
        """Build the duel state from the two branches."""
        left_game = Game.from_repo(Path(self.repo.working_dir), branch=self.left_branch)
        right_game = Game.from_repo(Path(self.repo.working_dir), branch=self.right_branch)
        
        # Find common ancestor (merge base)
        try:
            merge_base = self.repo.merge_base(self.left_branch, self.right_branch)[0]
        except GitCommandError:
            # Fallback: use the first commit of the left branch as merge base
            merge_base = list(self.repo.iter_commits(self.left_branch, max_count=1))[0]
        
        merge_base_hex = merge_base.hexsha
        
        # Find the merge commit (if any) that merges right into left
        merge_commit = None
        for commit in self.repo.iter_commits(self.left_branch):
            if len(commit.parents) > 1:
                # This is a merge commit; check if one parent is on right branch
                for parent in commit.parents:
                    if parent.hexsha in [c.hexsha for c in self.repo.iter_commits(self.right_branch, max_count=100)]:
                        merge_commit = commit.hexsha
                        break
                if merge_commit:
                    break
        
        # Build initial state
        return DuelState(
            left_game=left_game,
            right_game=right_game,
            left_index=0,
            right_index=0,
            current_turn=0,
            board=left_game.starting_board.copy(),
            merge_commit=merge_commit,
            conflict_squares=[],
        )

    def apply_move(self, state: DuelState, move: CommitMove) -> None:
        """Apply a CommitMove to the board and update state."""
        state.board = move.board_after.copy()
        if state.current_turn == 0:
            state.left_index += 1
        else:
            state.right_index += 1

    def detect_conflicts(self, state: DuelState) -> List[chess.Square]:
        """
        Detect conflicts between the two branches at the current state.
        Returns a list of squares where both branches have made moves.
        """
        left_idx = state.left_index
        right_idx = state.right_index
        
        left_moves = state.left_game.moves[:left_idx]
        right_moves = state.right_game.moves[:right_idx]
        
        left_squares: set[chess.Square] = set()
        right_squares: set[chess.Square] = set()
        
        for cm in left_moves:
            left_squares.add(cm.move.from_square)
            left_squares.add(cm.move.to_square)
        for cm in right_moves:
            right_squares.add(cm.move.from_square)
            right_squares.add(cm.move.to_square)
        
        conflicts = list(left_squares & right_squares)
        state.conflict_squares = conflicts
        return conflicts

    def get_next_move(self, state: DuelState) -> Optional[CommitMove]:
        """Get the next move for the current turn."""
        if state.current_turn == 0:
            if state.left_index < len(state.left_game.moves):
                return state.left_game.moves[state.left_index]
        else:
            if state.right_index < len(state.right_game.moves):
                return state.right_game.moves[state.right_index]
        return None

    def advance_turn(self, state: DuelState) -> bool:
        """Switch turns. Returns False if both branches are exhausted."""
        # Check if we've reached the merge commit
        if state.merge_commit:
            # If the current turn's branch has reached the merge commit, handle it
            if state.current_turn == 0:
                current_moves = state.left_game.moves
                current_idx = state.left_index
            else:
                current_moves = state.right_game.moves
                current_idx = state.right_index
            
            if current_idx < len(current_moves) and current_moves[current_idx].commit_hash == state.merge_commit:
                # Merge point: reset board to common ancestor
                # For simplicity, we reset to the starting board and replay all moves from both branches
                self._handle_merge(state)
                return True
        
        # Normal turn switch
        state.current_turn = 1 - state.current_turn
        
        # Check if the next player has moves left
        if state.current_turn == 0:
            return state.left_index < len(state.left_game.moves)
        else:
            return state.right_index < len(state.right_game.moves)

    def _handle_merge(self, state: DuelState) -> None:
        """Handle a merge commit by resetting the board to common ancestor and replaying."""
        # Find the common ancestor (the merge base)
        try:
            merge_base = self.repo.merge_base(self.left_branch, self.right_branch)[0]
        except GitCommandError:
            return
        
        # Reset board to the state at merge base
        # We'll rebuild the games from the merge base
        base_game = Game.from_repo(Path(self.repo.working_dir), branch=merge_base.hexsha)
        state.board = base_game.starting_board.copy()
        
        # Replay all moves from both branches up to the merge commit
        # This is a simplified approach; in reality, we'd replay all moves after merge base
        left_idx = 0
        right_idx = 0
        
        while left_idx < state.left_index and right_idx < state.right_index:
            # Alternate turns, but skip the merge commit itself
            cm_left = state.left_game.moves[left_idx] if left_idx < len(state.left_game.moves) else None
            cm_right = state.right_game.moves[right_idx] if right_idx < len(state.right_game.moves) else None
            
            if cm_left and cm_left.commit_hash == state.merge_commit:
                left_idx += 1
                continue
            if cm_right and cm_right.commit_hash == state.merge_commit:
                right_idx += 1
                continue
            
            # Apply left move
            if cm_left:
                state.board = cm_left.board_after.copy()
                left_idx += 1
            # Apply right move
            if cm_right:
                state.board = cm_right.board_after.copy()
                right_idx += 1
        
        # Reset indices to continue from merge point
        state.left_index = left_idx
        state.right_index = right_idx