from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

import chess
import chess.pgn

from .models import CommitMove, EXTENSION_PIECE_MAP


class PgnImportError(Exception):
    """Custom exception for PGN import errors."""
    pass


def parse_pgn_file(filepath: Path) -> chess.pgn.Game:
    """Parse a PGN file and return a chess.pgn.Game object."""
    if not filepath.exists():
        raise PgnImportError(f"File not found: {filepath}")
    with open(filepath, "r") as f:
        game = chess.pgn.read_game(f)
    if game is None:
        raise PgnImportError("Invalid or empty PGN file")
    return game


def extract_metadata(game: chess.pgn.Game) -> Dict[str, str]:
    """Extract metadata tags from a PGN game."""
    headers = {}
    for key in ["Event", "Site", "Date", "Round", "White", "Black", "Result"]:
        val = game.headers.get(key)
        if val:
            headers[key] = val
    return headers


def extract_moves(game: chess.pgn.Game) -> List[str]:
    """Extract move SAN strings from a PGN game, excluding variations."""
    moves = []
    node = game
    while node.variations:
        node = node.variations[0]
        moves.append(node.san())
    return moves


def validate_game_metadata(headers: Dict[str, str]) -> None:
    """Validate that required metadata is present."""
    required = ["Event", "White", "Black"]
    missing = [r for r in required if r not in headers]
    if missing:
        raise PgnImportError(f"Missing required metadata: {', '.join(missing)}")


def convert_pgn_to_commit_moves(pgn_file: Path) -> List[CommitMove]:
    """
    Convert a PGN file to a list of CommitMove objects.
    Each move is treated as a commit with a generated hash.
    """
    game = parse_pgn_file(pgn_file)
    headers = extract_metadata(game)
    validate_game_metadata(headers)
    moves_san = extract_moves(game)

    # Create a board to parse SAN moves into UCI
    board = chess.Board()
    commit_moves = []
    for i, san in enumerate(moves_san):
        try:
            move = board.parse_san(san)
            board.push(move)
        except ValueError as e:
            raise PgnImportError(f"Invalid move at index {i}: {san} - {e}")
        commit_moves.append(
            CommitMove(
                commit_hash=f"pgn-import-{i}",
                author=headers.get("White") if board.turn == chess.WHITE else headers.get("Black"),
                message=headers.get("Event", "Imported PGN"),
                move=move,
                timestamp="",
            )
        )
    return commit_moves


def import_pgn_to_game(pgn_file: Path, repo_path: Optional[Path] = None) -> "Game":
    """
    Import a PGN file and create a Game object.
    If repo_path is provided, it will be used for display purposes only.
    """
    from .game import Game
    commit_moves = convert_pgn_to_commit_moves(pgn_file)
    # We don't have a real repo, so we create a minimal Game instance
    game = Game(
        repo_path=repo_path or Path("."),
        branch="imported",
        commit_moves=commit_moves,
    )
    return game