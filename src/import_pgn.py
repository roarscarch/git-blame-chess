from __future__ import annotations

import chess
import chess.pgn
from pathlib import Path
from typing import Optional, List

from .game import Game, CommitMove


def import_pgn(pgn_path: Path, repo_path: Optional[Path] = None) -> Game:
    """
    Import a PGN file and reconstruct a Game object.

    Args:
        pgn_path: Path to the PGN file.
        repo_path: Optional path to the git repository (required for full Game).

    Returns:
        A Game object with moves populated from the PGN.

    Raises:
        FileNotFoundError: If the PGN file does not exist.
        ValueError: If the PGN file is invalid or contains no moves.
    """
    if not pgn_path.exists():
        raise FileNotFoundError(f"PGN file not found: {pgn_path}")

    with open(pgn_path, "r") as f:
        pgn_game = chess.pgn.read_game(f)

    if pgn_game is None:
        raise ValueError(f"Failed to parse PGN file: {pgn_path}")

    # Extract headers
    event = pgn_game.headers.get("Event", "Imported Game")
    site = pgn_game.headers.get("Site", "")
    white = pgn_game.headers.get("White", "Unknown")
    black = pgn_game.headers.get("Black", "Unknown")
    result = pgn_game.headers.get("Result", "*")

    # Convert moves to CommitMove objects
    moves: List[CommitMove] = []
    node = pgn_game
    move_number = 0
    while node.variations:
        node = node.variations[0]
        move_number += 1
        # Create a CommitMove from the chess.Move
        # We don't have git commit data, so we create synthetic commits
        cm = CommitMove(
            commit_hash=f"pgn-import-{move_number:06d}",
            author=white if move_number % 2 == 1 else black,
            message=f"Move {move_number}: {node.move}",
            move=node.move,
            board_before=node.parent.board(),
            board_after=node.board(),
            diff_stats={"files_changed": 0, "lines_added": 0, "lines_deleted": 0},
        )
        moves.append(cm)

    # Create a Game object
    # We need a repo path; if not provided, use current directory
    if repo_path is None:
        repo_path = Path.cwd()

    game = Game(
        repo_path=repo_path,
        branch=event,
        moves=moves,
        metadata={
            "event": event,
            "site": site,
            "white": white,
            "black": black,
            "result": result,
        },
    )
    return game
