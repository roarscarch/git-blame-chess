from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, List, Tuple

import chess
import chess.pgn

from .game import Game, CommitMove
from .models import EXTENSION_PIECE_MAP, DEFAULT_PIECE, get_piece_for_path, path_to_square


def parse_pgn_file(filepath: Path) -> Optional[Game]:
    """
    Parse a PGN file and reconstruct a Game object.

    Args:
        filepath: Path to the PGN file.

    Returns:
        A Game object if parsing succeeds, None otherwise.
    """
    try:
        with open(filepath, "r") as f:
            pgn_text = f.read()
        return parse_pgn_string(pgn_text)
    except (IOError, OSError) as e:
        print(f"Error reading PGN file: {e}")
        return None


def parse_pgn_string(pgn_text: str) -> Optional[Game]:
    """
    Parse a PGN string and reconstruct a Game object.

    Args:
        pgn_text: The PGN game data as a string.

    Returns:
        A Game object if parsing succeeds, None otherwise.
    """
    try:
        pgn_game = chess.pgn.read_game(pgn_text)
    except ValueError as e:
        print(f"Error parsing PGN: {e}")
        return None

    if pgn_game is None:
        return None

    # Extract headers
    headers = pgn_game.headers
    repo_path = headers.get("Site", "")
    branch = headers.get("Event", "").replace("Git Blame Chess - ", "")
    author = headers.get("White", "Unknown")

    # Reconstruct moves from the PGN
    moves: List[CommitMove] = []
    node = pgn_game
    move_number = 0
    while node.variations:
        node = node.variations[0]
        move = node.move
        if move is None:
            continue
        # Reconstruct the CommitMove from the chess.Move
        # We need to map the UCI move back to a file/line change
        # Since the original mapping is lost, we create a synthetic CommitMove
        # that stores the UCI string for replay purposes
        uci_str = move.uci()
        # Determine piece type from the move (promotion piece if any)
        piece_type = None
        if move.promotion:
            piece_type = chess.PIECE_SYMBOLS[move.promotion]
        # Create a dummy file path based on the move
        # Format: pgn_move_{move_number}_{uci_str}
        file_path = f"pgn_move_{move_number}_{uci_str}.txt"
        # Determine the piece based on the move's piece type (if available)
        # Fall back to DEFAULT_PIECE
        piece = EXTENSION_PIECE_MAP.get(".txt", DEFAULT_PIECE)
        if piece_type:
            # Map chess piece symbols to our piece types
            symbol_to_piece = {
                "p": "pawn",
                "n": "knight",
                "b": "bishop",
                "r": "rook",
                "q": "queen",
                "k": "king",
            }
            piece = symbol_to_piece.get(piece_type, piece)
        # Compute a square from the destination square of the move
        dest_square = move.to_square
        # Convert square index to board coordinate string (e.g., "e4")
        square_name = chess.SQUARE_NAMES[dest_square]
        # Create the CommitMove
        cm = CommitMove(
            commit_hash=f"pgn-import-{move_number}",
            author=author,
            message=f"PGN move {move_number + 1}: {uci_str}