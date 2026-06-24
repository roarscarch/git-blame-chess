"""Interactive terminal player for git-blame-chess."""

from __future__ import annotations

import sys
from typing import Optional

import chess

from .display import render_board, get_move_notation, COLOR_RESET
from .display import COLOR_HIGHLIGHT, COLOR_WHITE_SQUARE, COLOR_BLACK_SQUARE
from .duel import BranchDuel


class InteractivePlayer:
    """Interactive player for a single-branch game."""

    def __init__(self, game) -> None:
        self.game = game
        self.current_index = 0
        self.board = chess.Board()

    def run(self) -> None:
        """Run the interactive loop."""
        print("\n=== Git Blame Chess - Interactive Play ===\n")
        print("Commands: [n]ext, [p]revious, [q]uit, [h]elp, [r]eset\n")

        self._show_board()

        while True:
            try:
                cmd = input("Enter command: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if cmd in ('q', 'quit', 'exit'):
                break
            elif cmd in ('n', 'next'):
                self._next_move()
            elif cmd in ('p', 'prev', 'previous'):
                self._previous_move()
            elif cmd in ('r', 'reset'):
                self._reset()
            elif cmd in ('h', 'help'):
                self._show_help()
            else:
                print("Unknown command. Type 'h' for help.")

    def _next_move(self) -> None:
        """Advance one move forward."""
        if self.current_index >= len(self.game.moves):
            print("Already at the latest commit.")
            return
        move = self.game.moves[self.current_index]
        self.board.push(chess.Move.from_uci(move.uci))
        self.current_index += 1
        self._show_board()

    def _previous_move(self) -> None:
        """Go back one move."""
        if self.current_index == 0:
            print("Already at the initial position.")
            return
        self.current_index -= 1
        self.board.pop()
        self._show_board()

    def _reset(self) -> None:
        """Reset to initial position."""
        self.board.reset()
        self.current_index = 0
        self._show_board()

    def _show_board(self) -> None:
        """Display the current board state."""
        last_move = None
        if self.current_index > 0:
            last_move = chess.Move.from_uci(self.game.moves[self.current_index - 1].uci)
        print(render_board(self.board, last_move=last_move))
        move_count = self.current_index
        total = len(self.game.moves)
        print(f"\nMove {move_count}/{total}")
        if self.current_index > 0:
            move = self.game.moves[self.current_index - 1]
            notation = get_move_notation(self.board, chess.Move.from_uci(move.uci))
            print(f"Last move: {notation} ({move.commit_sha[:8]})")

    def _show_help(self) -> None:
        """Show help text."""
        print("\nCommands:")
        print("  n - Next move")
        print("  p - Previous move")
        print("  r - Reset to start")
        print("  h - Show this help")
        print("  q - Quit\n")


class InteractiveDuel:
    """Interactive player for branch duel mode."""

    def __init__(self, duel: BranchDuel) -> None:
        self.duel = duel
        self.state = duel.state
        self.board = duel.state.board

    def run(self) -> None:
        """Run the interactive duel loop."""
        print("\n=== Git Blame Chess - Branch Duel ===\n")
        print(f"Left branch:  {self.duel.left_branch}")
        print(f"Right branch: {self.duel.right_branch}")
        print("\nCommands: [n]ext, [q]uit, [h]elp, [s]tatus\n")

        self._show_board()

        while True:
            try:
                cmd = input("Enter command: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if cmd in ('q', 'quit', 'exit'):
                break
            elif cmd in ('n', 'next'):
                self._next_move()
            elif cmd in ('s', 'status'):
                self._show_status()
            elif cmd in ('h', 'help'):
                self._show_help()
            else:
                print("Unknown command. Type 'h' for help.")

    def _next_move(self) -> None:
        """Advance one move in the duel."""
        result = self.duel.next_move()
        if result is None:
            print("Both branches have been fully played.")
            return

        move, branch = result
        self.board.push(chess.Move.from_uci(move.uci))

        # Check for conflict after the move
        conflict = self.duel.check_conflict()
        if conflict:
            print(f"\n*** CONFLICT on squares: {conflict} ***")
            print("Merging branches at this point...")
            self.duel.handle_merge()
            print("Merge complete. Resuming play from common ancestor.\n")

        self._show_board()
        branch_name = self.duel.left_branch if branch == 'left' else self.duel.right_branch
        print(f"Move from {branch_name}: {get_move_notation(self.board, chess.Move.from_uci(move.uci))}")

    def _show_board(self) -> None:
        """Display the current board state."""
        last_move = None
        if self.board.move_stack:
            last_move = self.board.move_stack[-1]
        print(render_board(self.board, last_move=last_move))
        print(f"\nTurn: {'Left' if self.state.current_turn == 0 else 'Right'}")
        print(f"Left index: {self.state.left_index}/{len(self.state.left_game.moves)}")
        print(f"Right index: {self.state.right_index}/{len(self.state.right_game.moves)}")

    def _show_status(self) -> None:
        """Show current duel status."""
        print("\n=== Duel Status ===")
        print(f"Left branch:  {self.duel.left_branch}")
        print(f"Right branch: {self.duel.right_branch}")
        print(f"Turn: {'Left' if self.state.current_turn == 0 else 'Right'}")
        print(f"Left moves played: {self.state.left_index}")
        print(f"Right moves played: {self.state.right_index}")
        print(f"Total moves on board: {len(self.board.move_stack)}")
        print(f"Merge commit: {self.state.merge_commit or 'None'}