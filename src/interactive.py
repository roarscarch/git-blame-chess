from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import chess

from .display import render_board, get_piece_symbol, COLOR_RESET, COLOR_WHITE_SQUARE, COLOR_BLACK_SQUARE, COLOR_WHITE_PIECE, COLOR_BLACK_PIECE, COLOR_COORD_LABEL, COLOR_HIGHLIGHT, COLOR_LAST_MOVE, COLOR_LEGAL_MOVE
from .game import Game, CommitMove
from .models import EXTENSION_PIECE_MAP, DEFAULT_PIECE, get_piece_for_path, path_to_square


class InteractivePlayer:
    """Interactive terminal player for replaying commit history as chess moves."""

    def __init__(self, game: Game) -> None:
        self.game = game
        self.current_index = 0
        self.board = chess.Board()
        self.last_move: Optional[chess.Move] = None
        self.highlight_squares: set[chess.Square] = set()
        self.legal_moves: set[chess.Square] = set()
        self.selected_square: Optional[chess.Square] = None

    def run(self) -> None:
        """Main loop for interactive play."""
        self._print_help()
        while True:
            self._render()
            try:
                cmd = input('\n> ').strip().lower()
            except (EOFError, KeyboardInterrupt):
                print('\nGoodbye!')
                break

            if cmd in ('q', 'quit', 'exit'):
                print('Goodbye!')
                break
            elif cmd in ('h', 'help'):
                self._print_help()
            elif cmd in ('n', 'next'):
                self._next_move()
            elif cmd in ('p', 'prev', 'back'):
                self._prev_move()
            elif cmd in ('r', 'reset'):
                self._reset()
            elif cmd in ('s', 'select'):
                self._select_square()
            elif cmd.startswith('move '):
                try:
                    move_str = cmd[5:].strip()
                    move = chess.Move.from_uci(move_str)
                    if self._validate_and_apply_move(move):
                        print(f'Move {move_str} applied.')
                    else:
                        print('Illegal move.')
                except ValueError:
                    print('Invalid move format. Use UCI (e.g., e2e4).')
            else:
                print('Unknown command. Type h for help.')

    def _print_help(self) -> None:
        """Print help text."""
        print()
        print('Interactive Chess Replay')
        print('=' * 40)
        print('Commands:')
        print('  n, next      - advance to next commit move')
        print('  p, prev      - go back to previous commit move')
        print('  r, reset     - reset to start of game')
        print('  s, select    - select a square to see legal moves')
        print('  move <uci>   - make a custom move (e.g., move e2e4)')
        print('  q, quit      - exit')
        print('  h, help      - show this help')
        print()

    def _render(self) -> None:
        """Render the current board state."""
        # Clear screen (simple approach)
        print('\033[2J\033[H', end='')

        # Show game info
        commit = self.game.get_commit(self.current_index) if self.current_index < len(self.game.commits) else None
        if commit:
            print(f'Commit {self.current_index + 1}/{len(self.game.commits)}: {commit.commit_hash[:8]}')
            print(f'Author: {commit.author}')
            print(f'Message: {commit.message}')
            print(f'Move: {commit.move.uci()}')
        else:
            print(f'Position {self.current_index}')

        print()

        # Render the board
        board_str = render_board(
            self.board,
            last_move=self.last_move,
            legal_moves=self.legal_moves if self.selected_square is not None else None,
            highlight=self.highlight_squares
        )
        print(board_str)

    def _next_move(self) -> None:
        """Advance to the next commit move."""
        if self.current_index >= len(self.game.commits):
            print('Already at the latest commit.')
            return

        commit = self.game.commits[self.current_index]
        if self._validate_and_apply_move(commit.move):
            self.current_index += 1
            self.last_move = commit.move
            self.highlight_squares = {commit.move.from_square, commit.move.to_square}
            self.legal_moves.clear()
            self.selected_square = None
        else:
            print(f'Warning: Commit move {commit.move.uci()} is illegal on this board. Skipping.')
            self.current_index += 1
            self._next_move()

    def _prev_move(self) -> None:
        """Go back to the previous commit move."""
        if self.current_index == 0:
            print('Already at the beginning.')
            return

        self.current_index -= 1
        self._reset_board_to_index(self.current_index)
        self.last_move = self.game.commits[self.current_index - 1].move if self.current_index > 0 else None
        self.highlight_squares.clear()
        self.legal_moves.clear()
        self.selected_square = None

    def _reset(self) -> None:
        """Reset to the initial position."""
        self.current_index = 0
        self.board = chess.Board()
        self.last_move = None
        self.highlight_squares.clear()
        self.legal_moves.clear()
        self.selected_square = None
        print('Reset to start.')

    def _select_square(self) -> None:
        """Prompt user to select a square to see legal moves."""
        try:
            sq_str = input('Enter square (e.g., e2): ').strip().lower()
            square = chess.parse_square(sq_str)
            piece = self.board.piece_at(square)
            if piece is None:
                print('No piece at that square.')
                return
            if piece.color != self.board.turn:
                print('Not your turn.')
                return
            self.selected_square = square
            self.legal_moves = {move.to_square for move in self.board.legal_moves if move.from_square == square}
        except ValueError:
            print('Invalid square.')

    def _validate_and_apply_move(self, move: chess.Move) -> bool:
        """Validate a move and apply it to the board if legal.

        Returns True if the move was applied, False otherwise.
        """
        if move in self.board.legal_moves:
            self.board.push(move)
            return True
        return False

    def _reset_board_to_index(self, index: int) -> None:
        """Reset the board to the state at the given commit index."""
        self.board = chess.Board()
        for i in range(index):
            commit = self.game.commits[i]
            if commit.move in self.board.legal_moves:
                self.board.push(commit.move)
            else:
                print(f'Warning: Skipping illegal move {commit.move.uci()} at commit {i}')
