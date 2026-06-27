from __future__ import annotations

import re
from typing import List, Optional, Tuple

import chess
import chess.pgn

from .game import Game, CommitMove
from .models import EXTENSION_PIECE_MAP, DEFAULT_PIECE, get_piece_for_path, path_to_square


def parse_pgn(pgn_string: str) -> Optional[Game]:
    """
    Parse a PGN string and return a Game object.
    Returns None if the PGN is invalid.
    """
    try:
        game = chess.pgn.read_game(pgn_string)
    except Exception:
        return None
    if game is None:
        return None
    return _pgn_game_to_git_blame_chess(game)


def _pgn_game_to_git_blame_chess(pgn_game: chess.pgn.Game) -> Optional[Game]:
    """
    Convert a chess.pgn.Game to a git-blame-chess Game.
    """
    headers = pgn_game.headers
    # Extract metadata
    event = headers.get("Event", "")
    site = headers.get("Site", "")
    date = headers.get("Date", "")
    round_ = headers.get("Round", "")
    white = headers.get("White", "")
    black = headers.get("Black", "")
    result = headers.get("Result", "*")
    # Build repo path from site (if it looks like a path)
    repo_path = site if site and not site.startswith("http") else "."
    # Build branch from event (if present)
    branch = event if event else None
    # Parse moves
    board = chess.Board()
    moves: List[CommitMove] = []
    node = pgn_game
    move_index = 0
    while node.variations:
        node = node.variations[0]
        move = node.move
        if move is None:
            continue
        # Create a CommitMove from the chess move
        # We need to map the move to a file change
        # Use a deterministic mapping: piece type to extension, square to path
        piece = board.piece_at(move.from_square)
        if piece is None:
            continue
        piece_type = piece.piece_type
        # Determine extension based on piece type
        ext = _piece_type_to_extension(piece_type)
        # Determine path from square
        from_file = chess.square_file(move.from_square)
        from_rank = chess.square_rank(move.from_square)
        to_file = chess.square_file(move.to_square)
        to_rank = chess.square_rank(move.to_square)
        # Construct a pseudo-path
        from_path = f"src/{chr(ord('a') + from_file)}{from_rank + 1}.{ext}"
        to_path = f"src/{chr(ord('a') + to_file)}{to_rank + 1}.{ext}"
        # Determine if it's a capture
        is_capture = board.is_capture(move)
        # Promote?
        promotion = move.promotion
        # Build commit message from move SAN
        san = board.san(move)
        commit_message = f"{san}: {node.comment if node.comment else 'move'}"
        # Create CommitMove
        commit_move = CommitMove(
            commit_hash=f"pgn:{move_index}",
            author=white if board.turn == chess.WHITE else black,
            message=commit_message,
            timestamp=date,
            parent_hashes=[],
            changed_files=[from_path, to_path],
            lines_added=1,
            lines_deleted=1 if is_capture else 0,
            chess_move=move,
            piece_type=piece_type,
            from_square=move.from_square,
            to_square=move.to_square,
            is_capture=is_capture,
            promotion=promotion,
        )
        moves.append(commit_move)
        board.push(move)
        move_index += 1
    if not moves:
        return None
    # Create Game object
    game = Game(
        repo_path=repo_path,
        branch=branch or "unknown",
        board=board,
        moves=moves,
        current_index=len(moves) - 1 if result != "*" else 0,
    )
    return game


def _piece_type_to_extension(piece_type: int) -> str:
    """Map chess piece type to file extension."""
    mapping = {
        chess.PAWN: "py",
        chess.KNIGHT: "js",
        chess.BISHOP: "rs",
        chess.ROOK: "go",
        chess.QUEEN: "java",
        chess.KING: "c",
    }
    return mapping.get(piece_type, "txt")


def validate_pgn(pgn_string: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a PGN string.
    Returns (is_valid, error_message).
    """
    try:
        game = chess.pgn.read_game(pgn_string)
    except Exception as e:
        return False, str(e)
    if game is None:
        return False, "Failed to parse PGN: no game found"
    board = chess.Board()
    for node in game.mainline():
        move = node.move
        if move is None:
            continue
        if move not in board.legal_moves:
            return False, f"Illegal move: {board.san(move)}