from __future__ import annotations

import chess
import chess.pgn
from pathlib import Path
from typing import List, Optional

from .game import Game, CommitMove
from .models import CommitInfo


def import_pgn(pgn_path: Path) -> Game:
    """
    Import a PGN file and reconstruct a Game object.

    Args:
        pgn_path: Path to the PGN file.

    Returns:
        A Game object with moves reconstructed from the PGN.

    Raises:
        FileNotFoundError: If the PGN file does not exist.
        ValueError: If the PGN cannot be parsed.
    """
    if not pgn_path.exists():
        raise FileNotFoundError(f"PGN file not found: {pgn_path}")

    with open(pgn_path, "r") as f:
        pgn_game = chess.pgn.read_game(f)

    if pgn_game is None:
        raise ValueError(f"Could not parse PGN file: {pgn_path}")

    # Reconstruct the board from the PGN moves
    board = chess.Board()
    moves: List[CommitMove] = []

    # Extract metadata from headers
    event = pgn_game.headers.get("Event", "Imported Game")
    site = pgn_game.headers.get("Site", "")
    white = pgn_game.headers.get("White", "Unknown")
    black = pgn_game.headers.get("Black", "Unknown")
    result = pgn_game.headers.get("Result", "*")

    # Build a dummy CommitInfo for each move
    # We don't have real git info, so we create placeholders
    node = pgn_game
    move_number = 0
    while node.variations:
        node = node.variations[0]
        move = node.move
        if move is None:
            break
        move_number += 1
        # Determine side based on move number (1 = white, 2 = black, etc.)
        is_white = (move_number % 2 == 1)
        author = white if is_white else black

        # Create a CommitInfo with dummy data
        commit_info = CommitInfo(
            hexsha=f"pgn-import-{move_number}",
            author=author,
            message=f"Move {move_number}: {board.san(move)}",
            committed_date=0.0,
        )

        # Create a CommitMove
        cm = CommitMove(
            move=move,
            commit=commit_info,
            piece=board.piece_at(move.from_square),
            from_square=move.from_square,
            to_square=move.to_square,
            is_capture=board.is_capture(move),
            is_check=board.is_check(),
            file_changes=[],  # No file-level info from PGN
        )
        moves.append(cm)

        # Apply the move to the board for next iteration
        board.push(move)

    # Build the Game object
    game = Game(
        repo_path=Path(site) if site else Path.cwd(),
        branch=event,
        moves=moves,
        board=chess.Board(),  # Reset board; caller can replay
        current_index=-1,
    )

    return game