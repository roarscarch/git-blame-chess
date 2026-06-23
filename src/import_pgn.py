from __future__ import annotations

import chess
import chess.pgn
from pathlib import Path
from typing import Iterator, List, Optional

from .game import Game, CommitMove
from .models import path_to_square, get_piece_for_path, EXTENSION_PIECE_MAP, DEFAULT_PIECE


def import_pgn(pgn_path: Path, repo_path: Optional[Path] = None, branch: Optional[str] = None) -> Game:
    """
    Import a PGN file into a Game object.

    Args:
        pgn_path: Path to the PGN file.
        repo_path: Optional path to the git repository (for metadata).
        branch: Optional branch name.

    Returns:
        A Game object reconstructed from the PGN.
    """
    with open(pgn_path) as f:
        pgn_game = chess.pgn.read_game(f)
    if pgn_game is None:
        raise ValueError(f"Could not read PGN from {pgn_path}")

    # Reconstruct moves from PGN
    moves: List[CommitMove] = []
    node = pgn_game
    move_number = 0
    while node.variations:
        node = node.variations[0]
        move = node.move
        if move is None:
            continue
        # Determine piece type from the move
        piece_type = node.board().piece_at(move.from_square)
        piece_symbol = chess.piece_symbol(piece_type) if piece_type else "?"
        # Try to reconstruct file path from PGN comment if present
        comment = node.comment
        file_path = None
        lines_changed = 1
        if comment and comment.startswith("file:"):
            parts = comment.split("\n")
            for part in parts:
                if part.startswith("file:"):
                    file_path = part[5:].strip()
                elif part.startswith("lines:"):
                    try:
                        lines_changed = int(part[6:].strip())
                    except ValueError:
                        pass
        # Create a CommitMove
        cm = CommitMove(
            move=move,
            piece_symbol=piece_symbol,
            from_square=chess.square_name(move.from_square),
            to_square=chess.square_name(move.to_square),
            piece_type=piece_type,
            author="imported",
            commit_hash="",
            timestamp="",
            message=f"Move {move_number + 1}: {piece_symbol} from {chess.square_name(move.from_square)} to {chess.square_name(move.to_square)}