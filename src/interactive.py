from __future__ import annotations

import sys
from typing import Optional

import chess

from .display import render_board, COLOR_RESET, COLOR_HIGHLIGHT, COLOR_LAST_MOVE, COLOR_LEGAL_MOVE
from .duel import BranchDuel, DuelState
from .game import Game, CommitMove


class InteractivePlayer:
    """Interactive player for playing through a game."""

    def __init__(self, game: Game) -> None:
        self.game = game
        self.index = 0
        self.board = chess.Board()
        self.last_move: Optional[chess.Move] = None

    def run(self) -> None:
        """Run the interactive player."""
        print("\n=== Git Blame Chess - Interactive Mode ===\n")
        print("Commands: [n]ext, [p]rev, [q]uit, [r]eset\n")
        self._show_board()
        while True:
            try:
                cmd = input("> ").strip().lower()
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
            else:
                print("Unknown command. Use n, p, q, r.")

    def _show_board(self) -> None:
        """Display the current board state."""
        commit = self.game.commits[self.index] if self.index < len(self.game.commits) else None
        move_str = ""
        if commit and commit.move:
            move_str = f"Move: {commit.move.uci()}"
        print(f"\nCommit {self.index + 1}/{len(self.game.commits)} {move_str}")
        print(render_board(self.board, last_move=self.last_move))

    def _next_move(self) -> None:
        """Advance to the next commit move."""
        if self.index >= len(self.game.commits):
            print("Already at the end of history.")
            return
        commit = self.game.commits[self.index]
        if commit.move:
            if commit.move in self.board.legal_moves:
                self.board.push(commit.move)
                self.last_move = commit.move
            else:
                print(f"WARNING: Move {commit.move.uci()} is not legal. Skipping.")
        self.index += 1
        self._show_board()

    def _prev_move(self) -> None:
        """Go back to the previous commit move."""
        if self.index == 0:
            print("Already at the beginning.")
            return
        self.index -= 1
        if self.game.commits[self.index].move:
            self.board.pop()
            self.last_move = self.game.commits[self.index - 1].move if self.index > 0 else None
        self._show_board()

    def _reset(self) -> None:
        """Reset to the beginning."""
        self.index = 0
        self.board = chess.Board()
        self.last_move = None
        self._show_board()


class InteractiveBranchDuel:
    """Interactive player for branch duel mode."""

    def __init__(self, duel: BranchDuel) -> None:
        self.duel = duel
        self.state: Optional[DuelState] = None
        self.board = chess.Board()
        self.last_move: Optional[chess.Move] = None

    def run(self) -> None:
        """Run the interactive branch duel."""
        print("\n=== Git Blame Chess - Branch Duel Mode ===\n")
        print("Commands: [n]ext, [p]rev, [q]uit, [r]eset\n")
        self.state = self.duel.initialize()
        self.board = self.state.board
        self._show_duel_state()
        while True:
            try:
                cmd = input("> ").strip().lower()
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
            else:
                print("Unknown command. Use n, p, q, r.")

    def _show_duel_state(self) -> None:
        """Display the current duel state."""
        if self.state is None:
            return
        left_name = self.duel.left_branch
        right_name = self.duel.right_branch
        turn = "White (Left)" if self.state.current_turn == 0 else "Black (Right)"
        print(f"\nBranch: {left_name} vs {right_name}")
        print(f"Turn: {turn}")
        print(f"Left index: {self.state.left_index}, Right index: {self.state.right_index}")
        if self.state.merge_commit:
            print(f"Merge commit: {self.state.merge_commit[:8]}