from __future__ import annotations

import chess
import chess.pgn
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from .game import Game, CommitMove
from .models import EXTENSION_PIECE_MAP, DEFAULT_PIECE, get_piece_for_path, path_to_square


def import_pgn(pgn_path: Path, repo_path: Optional[Path] = None) -> Game:
    """
    Import a PGN file and reconstruct a Game object with synthetic commits.

    Args:
        pgn_path: Path to the PGN file.
        repo_path: Optional path to associate with the game (default: current directory).

    Returns:
        A Game object populated with moves from the PGN.
    """
    if not pgn_path.exists():
        raise FileNotFoundError(f"PGN file not found: {pgn_path}")

    with open(pgn_path, "r") as f:
        pgn_game = chess.pgn.read_game(f)

    if pgn_game is None:
        raise ValueError("Invalid or empty PGN file.")

    repo_path = repo_path or Path.cwd()
    branch = pgn_game.headers.get("Event", "Imported PGN").replace("Git Blame Chess - ", "")

    # Build a list of CommitMove objects from the mainline moves
    moves: List[CommitMove] = []
    node = pgn_game
    move_number = 1
    while node.variations:
        next_node = node.variations[0]
        move = next_node.move
        if move is None:
            break

        # Create a synthetic commit for each move
        # We'll assign a deterministic but fake commit hash and author
        commit_hash = f"pgn-import-{move_number:06d}"
        author = pgn_game.headers.get("White", "Unknown")
        # Alternate author for black moves (every other move starting from second)
        if move_number % 2 == 0:
            author = pgn_game.headers.get("Black", "Unknown")

        # Build a message describing the move
        san = next_node.san()
        message = f"{san} ({chess.SQUARE_NAMES[move.from_square]}-{chess.SQUARE_NAMES[move.to_square]})"

        cm = CommitMove(
            commit_hash=commit_hash,
            author=author,
            message=message,
            timestamp=datetime.now(),
            san=san,
            piece_type=move.piece_type,
            from_square=move.from_square,
            to_square=move.to_square,
            promotion=move.promotion,
            capture=node.parent.board().is_capture(move) if node.parent else False,
            is_check=node.board().is_check(),
            is_checkmate=node.board().is_checkmate(),
        )
        moves.append(cm)

        node = next_node
        move_number += 1

    # Create a Game instance
    game = Game(
        repo_path=repo_path,
        branch=branch,
        moves=moves,
    )
    # Replay moves to set initial board and final board
    game.board = chess.Board()
    for cm in moves:
        uci_move = chess.Move(from_square=cm.from_square, to_square=cm.to_square, promotion=cm.promotion)
        if uci_move in game.board.legal_moves:
            game.board.push(uci_move)
        else:
            # Fallback: try to parse SAN directly
            try:
                game.board.push_san(cm.san)
            except ValueError:
                # If neither works, skip this move
                pass

    return game
