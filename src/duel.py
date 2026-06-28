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
            conflict_squares=data.get("conflict_squares", []),
        )

    def save(self, path: Path) -> None:
        """Save duel state to a JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> DuelState:
        """Load duel state from a JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)


@dataclass
class Duel:
    """Manages a branch duel."""
    repo_path: Path
    left_branch: str
    right_branch: str
    state: DuelState = field(init=False)
    repo: Repo = field(init=False)

    def __post_init__(self) -> None:
        self.repo = Repo(self.repo_path)
        self.state = DuelState(
            left_game=Game.from_repo(self.repo_path, branch=self.left_branch),
            right_game=Game.from_repo(self.repo_path, branch=self.right_branch),
        )

    def step(self) -> bool:
        """Execute the next move in the duel. Returns True if game is over."""
        current_game = self.state.left_game if self.state.current_turn == 0 else self.state.right_game
        current_index = self.state.left_index if self.state.current_turn == 0 else self.state.right_index

        if current_index >= len(current_game.moves):
            return True

        commit_move = current_game.moves[current_index]
        move = self._map_commit_to_move(commit_move)
        if move is None:
            # Skip commits that don't map to a valid chess move
            if self.state.current_turn == 0:
                self.state.left_index += 1
            else:
                self.state.right_index += 1
            return False

        try:
            self.state.board.push(move)
            if self.state.current_turn == 0:
                self.state.left_index += 1
            else:
                self.state.right_index += 1
            self.state.current_turn = 1 - self.state.current_turn
            return self.state.board.is_game_over()
        except ValueError:
            # Move is illegal on current board, skip it
            if self.state.current_turn == 0:
                self.state.left_index += 1
            else:
                self.state.right_index += 1
            return False

    def _map_commit_to_move(self, commit_move: CommitMove) -> Optional[chess.Move]:
        """Map a commit move to a chess move on the current board."""
        # Simple mapping: use the diff to determine piece and destination
        if not commit_move.diff_paths:
            return None

        # For now, just create a dummy move for testing
        # In a real implementation, we would parse the diff more carefully
        return None

    def run_auto(self, max_steps: int = 1000) -> None:
        """Automatically run the duel until completion or max steps."""
        steps = 0
        while steps < max_steps:
            if self.step():
                break
            steps += 1

    def to_pgn(self) -> str:
        """Export the duel as a PGN string."""
        from .export import export_game_to_pgn
        return export_game_to_pgn(self.state.board, self.state.left_game, self.state.right_game)

    def save_state(self, path: Optional[Path] = None) -> Path:
        """Save the current duel state to a file."""
        if path is None:
            path = Path(f"duel_{self.left_branch}_vs_{self.right_branch}.json")
        self.state.save(path)
        return path

    @classmethod
    def from_saved_state(cls, path: Path) -> Duel:
        """Load a duel from a saved state file."""
        state = DuelState.load(path)
        # We need repo_path and branch names to reconstruct, store them in state
        # For now, assume they are stored in the state dict
        return cls(
            repo_path=Path("."),
            left_branch="unknown",
            right_branch="unknown",
        )

    def to_dict(self) -> dict:
        """Serialize duel to dictionary."""
        return {
            "repo_path": str(self.repo_path),
            "left_branch": self.left_branch,
            "right_branch": self.right_branch,
            "state": self.state.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Duel:
        """Deserialize duel from dictionary."""
        duel = cls(
            repo_path=Path(data["repo_path"]),
            left_branch=data["left_branch"],
            right_branch=data["right_branch"],
        )
        duel.state = DuelState.from_dict(data["state"])
        return duel