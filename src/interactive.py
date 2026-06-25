from __future__ import annotations

import os
import sys
from typing import Optional

import chess

from .display import render_board, get_piece_symbol
from .game import Game, CommitMove


class InteractivePlayer:
    """Interactive terminal player for replaying commit history as chess moves."""

    def __init__(self, game: Game) -> None:
        self.game = game
        self.current_index = 0
        self.board = chess.Board()
        self.last_move: Optional[chess.Move] = None
        self._setup_initial_board()

    def _setup_initial_board(self) -> None:
        """Set up the board to the initial state before any commits."""
        self.board.reset()
        self.current_index = 0
        self.last_move = None

    def _apply_move(self, commit_move: CommitMove) -> None:
        """Apply a commit move to the current board."""
        if commit_move.move is not None:
            self.board.push(commit_move.move)
            self.last_move = commit_move.move

    def _undo_move(self) -> None:
        """Undo the last move on the board."""
        if self.board.move_stack:
            self.board.pop()
            self.last_move = self.board.move_stack[-1] if self.board.move_stack else None

    def _clear_screen(self) -> None:
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def _print_header(self) -> None:
        """Print the game header."""
        repo_name = self.game.repo_path.name
        branch = self.game.branch
        print(f"\n=== Git Blame Chess ===")
        print(f"Repo: {repo_name}  |  Branch: {branch}")
        print(f"Commit {self.current_index + 1}/{len(self.game.moves)}" if self.game.moves else "No commits found.")
        print()

    def _print_move_info(self) -> None:
        """Print information about the current move."""
        if not self.game.moves:
            return
        idx = min(self.current_index, len(self.game.moves) - 1)
        cm = self.game.moves[idx]
        print(f"Commit: {cm.commit_hex[:8]}...")
        print(f"Author: {cm.author}")
        print(f"Message: {cm.message}")
        if cm.move:
            print(f"Move: {cm.move.uci()}")
        print()

    def _print_help(self) -> None:
        """Print help text."""
        print("Commands:")
        print("  n / <space>  - next commit (forward)")
        print("  p / b        - previous commit (backward)")
        print("  r            - reset to initial state")
        print("  q / Ctrl+C   - quit")
        print("  ? / h        - show this help")
        print()

    def _get_legal_moves(self) -> set[chess.Square]:
        """Get the set of legal move destination squares from the current board."""
        return {move.to_square for move in self.board.legal_moves}

    def _render(self) -> None:
        """Render the board and UI."""
        self._clear_screen()
        self._print_header()
        if self.game.moves:
            self._print_move_info()
        print(render_board(self.board, last_move=self.last_move, legal_moves=self._get_legal_moves()))
        print()
        self._print_help()

    def run(self) -> None:
        """Run the interactive player loop."""
        if not self.game.moves:
            print("No commits found in this branch.")
            return

        self._setup_initial_board()
        self._render()

        try:
            while True:
                try:
                    key = sys.stdin.read(1)
                except (EOFError, KeyboardInterrupt):
                    break

                if key in ('n', ' ', 'N'):
                    if self.current_index < len(self.game.moves):
                        if self.current_index < len(self.game.moves):
                            cm = self.game.moves[self.current_index]
                            self._apply_move(cm)
                            self.current_index += 1
                            self._render()
                elif key in ('p', 'b', 'P', 'B'):
                    if self.current_index > 0:
                        self.current_index -= 1
                        self._undo_move()
                        self._render()
                elif key in ('r', 'R'):
                    self._setup_initial_board()
                    self._render()
                elif key in ('q', 'Q'):
                    break
                elif key in ('?', 'h', 'H'):
                    self._render()
                # ignore other keys
        except KeyboardInterrupt:
            pass
        finally:
            print("\nGoodbye!")
