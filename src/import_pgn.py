"""Import PGN files into a Game object."""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Optional, Tuple

import chess
import chess.pgn

from .game import Game, CommitMove
from .models import path_to_square


class PGNImportError(Exception):
    """Raised when PGN import fails."""


def pgn_to_game(pgn_content: str, repo_path: Optional[Path] = None) -> Game:
    """
    Convert a PGN string into a Game object.

    Args:
        pgn_content: PGN string.
        repo_path: Optional repository path for metadata.

    Returns:
        A Game instance reconstructed from the PGN.

    Raises:
        PGNImportError: If parsing fails or the PGN is invalid.
    """
    pgn = io.StringIO(pgn_content)
    try:
        chess_game = chess.pgn.read_game(pgn)
    except Exception as e:
        raise PGNImportError(f"Failed to parse PGN: {e}")

    if chess_game is None:
        raise PGNImportError("No game found in PGN data")

    # Extract metadata
    headers = chess_game.headers
    branch_name = headers.get("Branch", "pgn-import")
    repo_path_str = headers.get("RepoPath", str(repo_path or Path.cwd()))
    start_sq = int(headers.get("StartSquare", "0"))
    end_sq = int(headers.get("EndSquare", "63"))

    # Create Game instance
    game = Game(
        repo_path=Path(repo_path_str),
        branch=branch_name,
        start_square=start_sq,
        end_square=end_sq,
    )

    # Replay moves
    board = chess.Board()
    node = chess_game
    while node.variations:
        node = node.variations[0]
        move = node.move
        if move is None:
            continue
        # Generate a synthetic commit based on the move
        # Use SAN notation as commit message placeholder
        san = board.san(move)
        # Determine piece type and capture info from move
        piece = board.piece_at(move.from_square)
        captured = board.piece_at(move.to_square)
        commit_info = f"PGN move {san}"
        commit_hash = _generate_commit_hash(board, move, san)
        board.push(move)
        # Build CommitMove (without real git data)
        from .models import EXTENSION_PIECE_MAP, DEFAULT_PIECE
        # Map piece type to extension
        ext_map = {v: k for k, v in EXTENSION_PIECE_MAP.items()}
        ext = ext_map.get(piece.piece_type if piece else DEFAULT_PIECE, ".txt")
        commit_move = CommitMove(
            commit_hash=commit_hash,
            message=commit_info,
            author="pgn-import",
            files_changed=[f"{san.replace(' ', '_')}{ext}"],
            lines_added=1,
            lines_deleted=1 if captured else 0,
            square_from=move.from_square,
            square_to=move.to_square,
            piece_type=piece.piece_type if piece else DEFAULT_PIECE,
            is_capture=captured is not None,
            is_king_side_castle=board.is_king_side_castle(move),
            is_queen_side_castle=board.is_queen_side_castle(move),
            is_en_passant=board.is_en_passant(move),
            promotion=move.promotion,
        )
        game.moves.append(commit_move)
        game.board_states.append(board.copy())
        # Update end square if not set
        if game.end_square == 0 and len(game.moves) > 1:
            game.end_square = move.to_square

    return game


def _generate_commit_hash(board: chess.Board, move: chess.Move, san: str) -> str:
    """Generate a deterministic hash for a PGN move."""
    import hashlib
    fen = board.fen()
    raw = f"{fen}:{san}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def validate_pgn(pgn_content: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a PGN string without importing it.

    Args:
        pgn_content: PGN string.

    Returns:
        Tuple of (is_valid, error_message).
    """
    try:
        pgn = io.StringIO(pgn_content)
        game = chess.pgn.read_game(pgn)
        if game is None:
            return False, "No game found"
        # Check basic structure
        headers = game.headers
        if not headers.get("Event"):
            return False, "Missing Event header"
        board = chess.Board()
        node = game
        move_count = 0
        while node.variations:
            node = node.variations[0]
            move = node.move
            if move is None:
                continue
            try:
                board.push(move)
                move_count += 1
            except ValueError as e:
                return False, f"Illegal move at move {move_count + 1}: {e}"
        if move_count == 0:
            return False, "No moves in game"
        return True, None
    except Exception as e:
        return False, str(e)


def load_pgn_file(path: Path) -> str:
    """Read PGN file content."""
    if not path.exists():
        raise PGNImportError(f"File not found: {path}")
    if path.suffix.lower() != ".pgn":
        raise PGNImportError(f"Not a .pgn file: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        raise PGNImportError(f"Failed to read file: {e}