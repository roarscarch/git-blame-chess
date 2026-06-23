from __future__ import annotations

import chess
import chess.pgn
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from .game import Game, CommitMove


def import_pgn(pgn_path: Path, repo_path: Optional[Path] = None, branch: Optional[str] = None) -> Game:
    """
    Import a PGN file and reconstruct a Game object with dummy CommitMoves.

    Args:
        pgn_path: Path to the PGN file.
        repo_path: Optional path to associate with the game.
        branch: Optional branch name.

    Returns:
        A Game object populated with moves from the PGN.

    Raises:
        FileNotFoundError: If the PGN file does not exist.
        ValueError: If the PGN file is invalid.
    """
    if not pgn_path.exists():
        raise FileNotFoundError(f"PGN file not found: {pgn_path}")

    with open(pgn_path, "r") as f:
        pgn_game = chess.pgn.read_game(f)

    if pgn_game is None:
        raise ValueError("Failed to parse PGN file: empty or invalid.")

    # Extract headers
    game_branch = branch or pgn_game.headers.get("Event", "imported")
    game_repo = repo_path or Path(pgn_game.headers.get("Site", "."))

    # Build game
    game = Game(repo_path=game_repo, branch=game_branch)

    # Walk through mainline moves
    node = pgn_game
    move_number = 1
    while node.variations:
        node = node.variations[0]
        move = node.move
        comment = node.comment if node.comment else ""

        # Determine side (white/black) based on ply count
        # In PGN, ply 0 is white's first move
        ply = len(game.moves)
        side = "white" if ply % 2 == 0 else "black"

        # Create a dummy CommitMove
        cm = CommitMove(
            commit_hash=f"imported-{move_number}",
            author=side,
            message=comment or f"Imported move {move_number}