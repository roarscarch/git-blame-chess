"""Interactive terminal player for git-blame-chess."""

from __future__ import annotations

import os
import sys
from typing import Optional

import chess

from .game import Game


class InteractivePlayer:
    """Allows the user to step through a chess game derived from git history interactively."""

    def __init__(self, game: Game) -> None:
        self.game = game
        self.current_move_index = 0
        self.board = game.starting_board.copy()

    def run(self) -> None:
        """Main interactive loop."""
        self._print_banner()
        while True:
            self._print_board()
            self._print_status()
            try:
                cmd = input("\nEnter command (n=next, p=prev, q=quit, r=reset, j=go to move #): ").strip()
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
            elif cmd.startswith("j"):
                parts = cmd.split()
                if len(parts) == 2 and parts[1].isdigit():
                    self._jump_to(int(parts[1]))
                else:
                    print("Usage: j <move number>")
            else:
                print("Unknown command. Available: n, p, q, r, j <num>")

    def _print_banner(self) -> None:
        """Print the welcome banner."""
        print("=" * 60)
        print("  Git Blame Chess - Interactive Player")
        print("=" * 60)
        print("Commands: n=next move, p=previous move, q=quit, r=reset, j <num>=jump to move")
        print()

    def _print_board(self) -> None:
        """Print the current board with colors."""
        os.system("clear" if sys.platform == "linux" else "cls" if sys.platform == "win32" else "")
        print(self.game.board_to_unicode(self.board))

    def _print_status(self) -> None:
        """Print the current move index and other status."""
        total = len(self.game.moves)
        print(f"\nMove {self.current_move_index} / {total}")
        if self.current_move_index < total:
            move = self.game.moves[self.current_move_index]
            print(f"Current move: {move.uci()} ({move})")
            if self.current_move_index < len(self.game.commit_messages):
                print(f"Commit: {self.game.commit_messages[self.current_move_index][:60]}")
        if self.board.is_check():
            print("Check!")
        if self.board.is_checkmate():
            print("Checkmate!")
        if self.board.is_stalemate():
            print("Stalemate!")

    def _next_move(self) -> None:
        """Advance to the next move."""
        if self.current_move_index >= len(self.game.moves):
            print("Already at the last move.")
            return
        move = self.game.moves[self.current_move_index]
        self.board.push(move)
        self.current_move_index += 1

    def _prev_move(self) -> None:
        """Go back one move."""
        if self.current_move_index <= 0:
            print("Already at the first move.")
            return
        self.board.pop()
        self.current_move_index -= 1

    def _reset(self) -> None:
        """Reset to the starting position."""
        self.board = self.game.starting_board.copy()
        self.current_move_index = 0

    def _jump_to(self, target: int) -> None:
        """Jump to a specific move number (0-based)."""
        total = len(self.game.moves)
        if target < 0 or target > total:
            print(f"Move number must be between 0 and {total}")
            return
        self.board = self.game.starting_board.copy()
        for i in range(target):
            self.board.push(self.game.moves[i])
        self.current_move_index = target
