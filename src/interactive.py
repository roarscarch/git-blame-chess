from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import chess

from .display import render_board, get_move_notation
from .duel import DuelState, DuelRunner
from .game import Game


class InteractivePlayer:
    """Interactive terminal player for game mode."""

    def __init__(self, game: Game) -> None:
        self.game = game
        self.move_index = 0
        self.board = chess.Board()

    def run(self) -> None:
        """Run the interactive session."""
        print("\nGit Blame Chess - Interactive Mode")
        print("Controls: n=next, p=previous, q=quit, r=restart, h=help\n")

        while True:
            self._display_board()
            cmd = input("> ").strip().lower()

            if cmd == "n":
                if self.move_index < len(self.game.moves):
                    move = self.game.moves[self.move_index]
                    self.board.push(move.uci_move)
                    self.move_index += 1
                else:
                    print("No more moves.")
            elif cmd == "p":
                if self.move_index > 0:
                    self.move_index -= 1
                    self.board.pop()
                else:
                    print("At the beginning.")
            elif cmd == "q":
                print("Goodbye!")
                break
            elif cmd == "r":
                self.board = chess.Board()
                self.move_index = 0
                print("Game restarted.")
            elif cmd == "h":
                print("n - next move")
                print("p - previous move")
                print("q - quit")
                print("r - restart")
                print("h - this help")
            else:
                print("Unknown command. Type h for help.")

    def _display_board(self) -> None:
        """Display the current board state."""
        last_move = self.game.moves[self.move_index - 1].uci_move if self.move_index > 0 else None
        print(f"\nMove {self.move_index}/{len(self.game.moves)}")
        print(render_board(self.board, last_move=last_move))
        if self.move_index > 0:
            move = self.game.moves[self.move_index - 1]
            print(f"Last move: {get_move_notation(self.board, move.uci_move)}")


class InteractiveDuelPlayer:
    """Interactive terminal player for duel mode."""

    def __init__(self, duel_state: DuelState) -> None:
        self.duel_state = duel_state
        self.runner = DuelRunner(duel_state)

    @classmethod
    def from_state_file(cls, path: Path) -> InteractiveDuelPlayer:
        """Load duel state from a JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        left_game = Game.from_dict(data["left_game"])
        right_game = Game.from_dict(data["right_game"])
        state = DuelState(
            left_game=left_game,
            right_game=right_game,
            left_index=data["left_index"],
            right_index=data["right_index"],
            current_turn=data["current_turn"],
            board=chess.Board(data["board_fen"]),
            merge_commit=data.get("merge_commit"),
            conflict_squares=data.get("conflict_squares", []),
        )
        return cls(state)

    def run(self) -> None:
        """Run the interactive duel session."""
        print("\nGit Blame Chess - Duel Mode")
        print("Controls: n=next, p=previous, q=quit, r=restart, h=help, s=save\n")

        while True:
            self._display_board()

            if self.duel_state.current_turn == 0:
                branch_name = self.duel_state.left_game.branch or "left"
            else:
                branch_name = self.duel_state.right_game.branch or "right"

            cmd = input(f"[{branch_name}] > ").strip().lower()

            if cmd == "n":
                move = self.runner.next_move()
                if move is None:
                    print("No more moves available.")
                else:
                    print(f"Move: {get_move_notation(self.duel_state.board, move)}")
            elif cmd == "p":
                if not self.runner.undo_move():
                    print("Cannot undo further.")
            elif cmd == "q":
                print("Goodbye!")
                break
            elif cmd == "r":
                self.duel_state.board = chess.Board()
                self.duel_state.left_index = 0
                self.duel_state.right_index = 0
                self.duel_state.current_turn = 0
                self.duel_state.merge_commit = None
                self.duel_state.conflict_squares = []
                print("Duel restarted.")
            elif cmd == "h":
                print("n - next move from current branch")
                print("p - undo last move")
                print("q - quit")
                print("r - restart")
                print("s - save state to file")
                print("h - this help")
            elif cmd == "s":
                path = Path("duel_state.json")
                with open(path, "w") as f:
                    json.dump(self.duel_state.to_dict(), f, indent=2)
                print(f"State saved to {path}")
            else:
                print("Unknown command. Type h for help.")

    def _display_board(self) -> None:
        """Display the current board state with duel info."""
        left_branch = self.duel_state.left_game.branch or "left"
        right_branch = self.duel_state.right_game.branch or "right"
        turn_name = left_branch if self.duel_state.current_turn == 0 else right_branch
        print(f"\nDuel: {left_branch} vs {right_branch} | Turn: {turn_name}")
        print(f"Left commits: {self.duel_state.left_index}/{len(self.duel_state.left_game.moves)}")
        print(f"Right commits: {self.duel_state.right_index}/{len(self.duel_state.right_game.moves)}