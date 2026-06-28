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