from __future__ import annotations

import hashlib
import json
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

    def to_dict(self) -> dict:
        """Serialize duel state to dictionary for persistence."""
        return {
            "left_game": self.left_game.to_dict(),
            "right_game": self.right_game.to_dict(),
            "left_index": self.left_index,
            "right_index": self.right_index,
            "current_turn": self.current_turn,
            "board_fen": self.board.fen(),
            "merge_commit": self.merge_commit,
            "conflict_squares": [s for s in self.conflict_squares],
        }

    @classmethod
    def from_dict(cls, data: dict) -> DuelState:
        """Deserialize duel state from dictionary."""
        left_game = Game.from_dict(data["left_game"])
        right_game = Game.from_dict(data["right_game"])
        board = chess.Board(data["board_fen"])
        return cls(
            left_game=left_game,
            right_game=right_game,
            left_index=data["left_index"],
            right_index=data["right_index"],
            current_turn=data["current_turn"],
            board=board,
            merge_commit=data.get("merge_commit"),
            conflict_squares=[chess.Square(s) for s in data.get("conflict_squares", [])],
        )


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
        self.state_file: Optional[Path] = None

    def save_state(self, filepath: Path) -> None:
        """Save current duel state to a JSON file."""
        if self.state is None:
            raise ValueError("No duel state to save")
        data = self.state.to_dict()
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        self.state_file = filepath

    def load_state(self, filepath: Path) -> None:
        """Load duel state from a JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)
        self.state = DuelState.from_dict(data)
        self.state_file = filepath

    def resume(self) -> None:
        """Resume duel from saved state. Must call load_state first."""
        if self.state is None:
            raise ValueError("No state loaded. Call load_state first.")
        print(f"Resuming duel between {self.left_branch} and {self.right_branch}")
        print(f"Turn {self.state.current_turn}: {'Left' if self.state.current_turn == 0 else 'Right'}")
        print(f"Board:\n{self.state.board}")

    def init_duel(self, start_from_common_ancestor: bool = True) -> None:
        """Initialize the duel by loading commit histories from both branches."""
        left_game = Game.from_repo(Path(self.repo.working_dir), branch=self.left_branch)
        right_game = Game.from_repo(Path(self.repo.working_dir), branch=self.right_branch)

        if start_from_common_ancestor:
            # Find merge base
            try:
                merge_base = self.repo.merge_base(self.left_branch, self.right_branch)
                if merge_base:
                    base_sha = merge_base[0].hexsha
                    # Optionally reset both games to start from that commit
                    # For simplicity, we keep full history but note the merge base
                    print(f"Common ancestor: {base_sha[:8]}")
            except GitCommandError:
                print("Could not find common ancestor, starting from beginning")

        self.state = DuelState(left_game=left_game, right_game=right_game)
        print(f"Duel initialized: {len(left_game.moves)} moves on left, {len(right_game.moves)} on right")

    def next_move(self) -> Optional[CommitMove]:
        """Get the next move based on current turn."""
        if self.state is None:
            return None

        if self.state.current_turn == 0:
            moves = self.state.left_game.moves
            idx = self.state.left_index
        else:
            moves = self.state.right_game.moves
            idx = self.state.right_index

        if idx >= len(moves):
            return None

        return moves[idx]

    def apply_move(self) -> bool:
        """Apply the next move to the board. Returns True if move was applied, False if game over."""
        if self.state is None:
            return False

        move = self.next_move()
        if move is None:
            print(f"Branch {'Left' if self.state.current_turn == 0 else 'Right'} has no more moves")
            return False

        # Apply the move to the board
        # In a real implementation, we would map the commit diff to a chess move
        # For now, we simulate with a random legal move for demonstration
        legal_moves = list(self.state.board.legal_moves)
        if not legal_moves:
            print("Stalemate or checkmate")
            return False

        # Placeholder: use the commit's hash to deterministically choose a move
        import hashlib
        hash_int = int(hashlib.sha256(move.commit_hash.encode()).hexdigest(), 16)
        chosen_move = legal_moves[hash_int % len(legal_moves)]
        self.state.board.push(chosen_move)

        print(f"Applied move: {chosen_move} from commit {move.commit_hash[:8]}")

        # Update indices and turn
        if self.state.current_turn == 0:
            self.state.left_index += 1
        else:
            self.state.right_index += 1
        self.state.current_turn = 1 - self.state.current_turn

        # Check for merge commits
        if move.commit_hash and self._is_merge_commit(move.commit_hash):
            self._handle_merge(move.commit_hash)

        return True

    def _is_merge_commit(self, commit_hash: str) -> bool:
        """Check if a commit is a merge commit."""
        try:
            commit = self.repo.commit(commit_hash)
            return len(commit.parents) > 1
        except (GitCommandError, ValueError):
            return False

    def _handle_merge(self, commit_hash: str) -> None:
        """Handle a merge commit by resetting the board."""
        print(f"Merge commit detected: {commit_hash[:8]}