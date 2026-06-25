from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import chess

from .game import Game, CommitMove


@dataclass
class GameState:
    """Tracks the current state of an interactive game replay."""

    game: Game
    move_index: int = 0
    board: chess.Board = field(default_factory=chess.Board)
    history: List[chess.Board] = field(default_factory=list)

    @classmethod
    def from_game(cls, game: Game) -> GameState:
        """Create a new GameState starting at the initial board."""
        return cls(game=game)

    def apply_move(self, move: chess.Move) -> None:
        """Apply a chess move and record the board state."""
        self.history.append(self.board.copy())
        self.board.push(move)
        self.move_index += 1

    def undo_move(self) -> Optional[chess.Move]:
        """Undo the last move and return it, or None if at start."""
        if not self.history:
            return None
        popped = self.board.pop()
        self.board = self.history.pop()
        self.move_index -= 1
        return popped

    def reset_to_start(self) -> None:
        """Reset to the initial board state."""
        self.board = chess.Board()
        self.history.clear()
        self.move_index = 0

    def get_current_move(self) -> Optional[CommitMove]:
        """Get the CommitMove at the current index, if any."""
        if 0 <= self.move_index < len(self.game.moves):
            return self.game.moves[self.move_index]
        return None

    def forward(self) -> Optional[CommitMove]:
        """Advance one move forward and return it, or None if at end."""
        cm = self.get_current_move()
        if cm is None:
            return None
        self.apply_move(cm.move)
        return cm

    def backward(self) -> Optional[CommitMove]:
        """Go back one move and return the undone move, or None if at start."""
        undone = self.undo_move()
        if undone is None:
            return None
        # Return the CommitMove that was undone
        if 0 <= self.move_index < len(self.game.moves):
            return self.game.moves[self.move_index]
        return None

    def go_to_move(self, index: int) -> None:
        """Jump to a specific move index (0 = start)."""
        if index < 0 or index > len(self.game.moves):
            raise ValueError(f"Move index {index} out of range (0-{len(self.game.moves)})")
        self.reset_to_start()
        for i in range(index):
            self.forward()

    @property
    def at_start(self) -> bool:
        """True if at the initial board state."""
        return self.move_index == 0

    @property
    def at_end(self) -> bool:
        """True if at the last move."""
        return self.move_index >= len(self.game.moves)

    @property
    def total_moves(self) -> int:
        """Total number of moves in the game."""
        return len(self.game.moves)