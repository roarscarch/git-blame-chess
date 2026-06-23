from __future__ import annotations

import chess
import chess.pgn
from pathlib import Path
from typing import List, Optional, Tuple

from .game import Game, CommitMove
from .models import path_to_square


def import_pgn(pgn_path: Path) -> Game:
    """
    Import a PGN file and reconstruct a Game object.

    Args:
        pgn_path: Path to the PGN file.

    Returns:
        A Game object with moves reconstructed from the PGN.

    Raises:
        ValueError: If the PGN file cannot be parsed or contains invalid data.
    """
    with open(pgn_path, 'r') as f:
        pgn_text = f.read()

    pgn_game = chess.pgn.read_game(pgn_text)
    if pgn_game is None:
        raise ValueError(f"Could not parse PGN file: {pgn_path}")

    # Extract metadata from headers
    repo_path_str = pgn_game.headers.get("Site", "")
    repo_path = Path(repo_path_str) if repo_path_str else Path.cwd()
    branch = pgn_game.headers.get("Event", "").replace("Git Blame Chess - ", "")
    if not branch:
        branch = "imported"

    # Reconstruct moves from PGN
    moves: List[CommitMove] = []
    node = pgn_game
    move_number = 0
    while node.variations:
        node = node.variations[0]
        move = node.move
        if move is None:
            continue

        # Determine author from comment or default
        comment = node.comment
        author = "Imported Game"
        if comment and "author:" in comment:
            # Parse author from comment
            for line in comment.split('\n'):
                if line.startswith("author:"):
                    author = line[len("author:"):].strip()
                    break

        # Reconstruct file path and line number from move UCI if possible
        # For imported PGNs, we may not have the original file info.
        # We'll store the move UCI and a placeholder path.
        uci = move.uci()
        # Attempt to derive a plausible file path from the move's source square
        from_square = chess.square_name(move.from_square)
        to_square = chess.square_name(move.to_square)
        # Use a heuristic: map board coordinates to a pseudo-file path
        # This is best-effort; the original file mapping is lost.
        file_path = f"imported/{from_square}-{to_square}.txt"
        line_number = move_number + 1

        cm = CommitMove(
            commit_hash=f"imported-{move_number}",
            author=author,
            timestamp="",
            message=f"{uci}",
            file_path=file_path,
            line_number=line_number,
            from_square=move.from_square,
            to_square=move.to_square,
            promotion=move.promotion,
            piece_type=move.piece_type if hasattr(move, 'piece_type') else None,
        )
        moves.append(cm)
        move_number += 1

    # Create a Game object with the reconstructed moves
    game = Game(repo_path=repo_path, branch=branch)
    game.moves = moves

    # Replay moves to set the board state
    board = chess.Board()
    for cm in moves:
        chess_move = chess.Move(from_square=cm.from_square, to_square=cm.to_square, promotion=cm.promotion)
        if chess_move in board.legal_moves:
            board.push(chess_move)
        else:
            # If the move is illegal, we still push it for consistency
            board.push(chess_move)
    game.board = board

    return game
