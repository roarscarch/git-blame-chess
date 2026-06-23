"""Import a PGN file into a Game object for replay or analysis."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

import chess
import chess.pgn

from .game import Game, CommitMove
from .models import get_piece_for_path, path_to_square


def import_pgn(source: str | Path) -> Game:
    """
    Parse a PGN string or file and return a Game object.

    Args:
        source: PGN string or path to a PGN file.

    Returns:
        A Game object with moves reconstructed from the PGN.

    Raises:
        ValueError: If the PGN is invalid or cannot be parsed.
    """
    if isinstance(source, Path):
        with open(source, "r") as f:
            pgn_str = f.read()
    else:
        pgn_str = source

    pgn_game = chess.pgn.read_game(io.StringIO(pgn_str))
    if pgn_game is None:
        raise ValueError("Invalid PGN: could not parse.")

    # Extract metadata from headers
    repo_path = Path(pgn_game.headers.get("Site", "."))
    branch = pgn_game.headers.get("Event", "imported").replace("Git Blame Chess - ", "")

    # Reconstruct moves
    moves: list[CommitMove] = []
    node = pgn_game
    move_number = 0
    while node.variations:
        node = node.variations[0]
        move = node.move
        if move is None:
            continue
        # Build a CommitMove from the chess.Move
        # We use deterministic dummy values for fields that are not available
        # The piece type is derived from the move's piece (if available via board context)
        # but we can approximate by the move's promotion or capture flag
        from_square = chess.square_name(move.from_square)
        to_square = chess.square_name(move.to_square)
        piece = chess.PAWN  # default, will be adjusted if possible
        # Try to get the board state before this move to determine piece type
        # Since we don't have the board, we infer from the move itself
        if move.promotion:
            piece = move.promotion
        elif move.drop:
            piece = move.drop
        # Fallback: parse from SAN (slow but works for simple cases)
        # We'll set a placeholder author
        author = node.comment if node.comment else "unknown"
        cm = CommitMove(
            commit_hash=f"imported-{move_number}",
            author=author,
            message=node.comment or "",
            from_square=from_square,
            to_square=to_square,
            piece=piece,
            capture=node.board().is_capture(move) if node.board() else False,
            check=node.board().is_check() if node.board() else False,
            timestamp="",
            diff_stats={},
        )
        moves.append(cm)
        move_number += 1

    # Create a dummy Game object (no actual repo needed)
    game = Game.__new__(Game)
    game.repo_path = repo_path
    game.branch = branch
    game.moves = moves
    game.current_index = 0
    game.board = chess.Board()
    # Replay moves onto the board
    for cm in moves:
        move = chess.Move.from_uci(cm.from_square + cm.to_square)
        if move in game.board.legal_moves:
            game.board.push(move)
        else:
            # Try to find the correct move by SAN
            san_move = None
            for legal in game.board.legal_moves:
                if game.board.san(legal) == cm.message.split()[0] if cm.message else None:
                    san_move = legal
                    break
            if san_move:
                game.board.push(san_move)
            else:
                # Push anyway (may raise)
                game.board.push(move)
    return game
