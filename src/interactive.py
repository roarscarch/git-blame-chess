from __future__ import annotations

import sys
from typing import Optional

from .game import Game, CommitMove
from .display import render_board, COLOR_RESET, COLOR_HIGHLIGHT


class InteractivePlayer:
    """Interactive terminal-based chess player for git blame chess."""

    def __init__(self, game: Game) -> None:
        self.game = game
        self.move_index = 0
        self.board = game.initial_board.copy()
        self.moves: list[CommitMove] = game.moves

    def run(self) -> None:
        """Main loop for interactive play."""
        print("\n=== Git Blame Chess ===")
        print("Controls: [n]ext move, [p]revious, [q]uit, [r]eset")
        print("Type a chess move (e.g. e2e4) to make your own move.\n")

        while True:
            self._display_board()
            self._display_status()

            try:
                cmd = input("\n> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if cmd == "q":
                break
            elif cmd == "n":
                self._next_move()
            elif cmd == "p":
                self._prev_move()
            elif cmd == "r":
                self._reset()
            elif cmd:
                self._handle_uci_move(cmd)

        print("Goodbye!")

    def _display_board(self) -> None:
        """Render the current board state."""
        last_move = self.moves[self.move_index - 1].move if self.move_index > 0 else None
        legal_moves = {move.to_square for move in self.board.legal_moves}
        output = render_board(self.board, last_move=last_move, legal_moves=legal_moves)
        print(output)

    def _display_status(self) -> None:
        """Show current move index and game info."""
        total = len(self.moves)
        print(f"Move {self.move_index}/{total}", end="")
        if self.move_index < total:
            commit = self.moves[self.move_index]
            print(f" | Commit: {commit.commit_hash[:8]} by {commit.author} on {commit.date}")
            print(f"Message: {commit.message}")
        else:
            print()

    def _next_move(self) -> None:
        """Advance to the next move."""
        if self.move_index < len(self.moves):
            commit_move = self.moves[self.move_index]
            if commit_move.move in self.board.legal_moves:
                self.board.push(commit_move.move)
                self.move_index += 1
            else:
                print(f"Illegal move: {commit_move.move.uci()} - skipping commit {commit_move.commit_hash[:8]}")
                self.move_index += 1
        else:
            print("No more moves.")

    def _prev_move(self) -> None:
        """Go back one move."""
        if self.move_index > 0:
            self.board.pop()
            self.move_index -= 1
        else:
            print("Already at start.")

    def _reset(self) -> None:
        """Reset to initial position."""
        self.board = self.game.initial_board.copy()
        self.move_index = 0
        print("Game reset.")

    def _handle_uci_move(self, uci: str) -> None:
        """Attempt to apply a user-entered UCI move."""
        try:
            move = chess.Move.from_uci(uci)
        except ValueError:
            print(f"Invalid UCI move format: {uci}")
            return
        if move in self.board.legal_moves:
            self.board.push(move)
            self.move_index += 1
            print(f"Applied user move: {uci}")
        else:
            print(f"Illegal move: {uci}")

    def _get_commit_at_index(self, index: int) -> Optional[CommitMove]:
        """Return the CommitMove at the given index, or None."""
        if 0 <= index < len(self.moves):
            return self.moves[index]
        return None

    def get_current_move(self) -> Optional[CommitMove]:
        """Return the current commit move being viewed."""
        return self._get_commit_at_index(self.move_index)

    def get_total_moves(self) -> int:
        """Return total number of moves in the game."""
        return len(self.moves)

    def is_at_end(self) -> bool:
        """Check if we are at the last move."""
        return self.move_index >= len(self.moves)

    def is_at_start(self) -> bool:
        """Check if we are at the first move."""
        return self.move_index == 0
