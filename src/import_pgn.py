from __future__ import annotations

import chess
import chess.pgn
from typing import Optional, List


def import_pgn(pgn_string: str) -> Optional[chess.Board]:
    """Import a PGN string and return the final board state.
    Returns None if the PGN is invalid.
    """
    try:
        game = chess.pgn.read_game(pgn_string)
        if game is None:
            return None
        board = game.board()
        for move in game.mainline_moves():
            if move in board.legal_moves:
                board.push(move)
            else:
                return None
        return board
    except Exception:
        return None


def import_pgn_from_file(filepath: str) -> Optional[chess.Board]:
    """Import a PGN file and return the final board state.
    Returns None if the file cannot be read or is invalid.
    """
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        return import_pgn(content)
    except (FileNotFoundError, IOError):
        return None


def validate_pgn(pgn_string: str) -> bool:
    """Validate a PGN string without returning board state."""
    return import_pgn(pgn_string) is not None


def get_move_list(pgn_string: str) -> Optional[List[str]]:
    """Extract the list of UCI move strings from a PGN."""
    try:
        game = chess.pgn.read_game(pgn_string)
        if game is None:
            return None
        moves = []
        for move in game.mainline_moves():
            moves.append(move.uci())
        return moves
    except Exception:
        return None
