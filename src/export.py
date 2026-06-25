from __future__ import annotations

import chess
import chess.pgn
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from .game import Game, CommitMove
from .models import EXTENSION_PIECE_MAP, DEFAULT_PIECE


def export_game_to_pgn(
    game: Game,
    output_path: Path,
    repo_name: str = "",
    branch: str = "",
    author: str = "",
    date: Optional[datetime] = None,
    annotations: Optional[List[str]] = None,
) -> Path:
    """
    Export a Game object to a PGN file with metadata and move annotations.

    Args:
        game: The Game instance to export.
        output_path: Path where the PGN file will be written.
        repo_name: Name of the repository (for event tag).
        branch: Branch name (for site tag).
        author: Author of the game (for player names).
        date: Date of the game (default: current date).
        annotations: Optional list of comment strings per move (in order).

    Returns:
        The Path to the written PGN file.
    """
    if date is None:
        date = datetime.now()

    # Create a new PGN game node
    pgn_game = chess.pgn.Game()
    pgn_game.headers["Event"] = f"Git Blame Chess: {repo_name}" if repo_name else "Git Blame Chess"
    pgn_game.headers["Site"] = branch if branch else "local"
    pgn_game.headers["Date"] = date.strftime("%Y.%m.%d")
    pgn_game.headers["Round"] = "1"
    pgn_game.headers["White"] = author if author else "White"
    pgn_game.headers["Black"] = "Black"
    pgn_game.headers["Result"] = "*"  # Unknown result

    # Build the move list with optional annotations
    node = pgn_game
    for i, move in enumerate(game.history):
        # Convert CommitMove to a chess.Move
        chess_move = chess.Move(move.from_square, move.to_square, move.promotion)
        if not game.board.is_legal(chess_move):
            continue  # Skip illegal moves (should not happen in valid games)
        game.board.push(chess_move)
        node = node.add_variation(chess_move)
        # Add annotation if provided
        if annotations and i < len(annotations):
            node.comment = annotations[i]
        # Add commit hash as a comment
        node.comment = f"commit: {move.commit_hash[:7]}