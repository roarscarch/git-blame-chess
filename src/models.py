# src/models.py
"""Data models and mapping logic for git-blame-chess."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Optional

import chess

# Mapping from file extension to chess piece type.
EXTENSION_PIECE_MAP: Dict[str, chess.PieceType] = {
    ".py": chess.PAWN,
    ".js": chess.KNIGHT,
    ".ts": chess.KNIGHT,
    ".rs": chess.ROOK,
    ".go": chess.BISHOP,
    ".java": chess.QUEEN,
    ".c": chess.ROOK,
    ".cpp": chess.ROOK,
    ".h": chess.BISHOP,
    ".hpp": chess.BISHOP,
    ".css": chess.KNIGHT,
    ".html": chess.PAWN,
    ".json": chess.PAWN,
    ".yaml": chess.PAWN,
    ".yml": chess.PAWN,
    ".toml": chess.PAWN,
    ".md": chess.PAWN,
    ".txt": chess.PAWN,
    ".sql": chess.BISHOP,
    ".sh": chess.KNIGHT,
    ".pl": chess.BISHOP,
    ".rb": chess.KNIGHT,
    ".php": chess.PAWN,
    ".swift": chess.KNIGHT,
    ".kt": chess.KNIGHT,
    ".scala": chess.KNIGHT,
    ".ex": chess.BISHOP,
    ".exs": chess.BISHOP,
}

# Default piece type for unknown extensions.
DEFAULT_PIECE = chess.PAWN


def get_piece_for_path(file_path: str) -> chess.PieceType:
    """Determine the piece type based on file extension."""
    path = Path(file_path)
    suffix = path.suffix.lower()
    return EXTENSION_PIECE_MAP.get(suffix, DEFAULT_PIECE)


def path_to_square(file_path: str, line_number: int) -> chess.Square:
    """
    Deterministically map a file path and line number to a chess square.

    Uses SHA-256 to hash the combination, then maps the hash to a board
    square (0-63).
    """
    raw = f"{file_path}:{line_number}"
    digest = hashlib.sha256(raw.encode()).digest()
    # Use first 2 bytes mod 64
    index = (digest[0] << 8 | digest[1]) % 64
    return chess.Square(index)


def piece_from_diff(file_path: str, lines_added: int, lines_deleted: int) -> chess.Piece:
    """
    Create a chess piece based on the diff statistics.

    Args:
        file_path: Path of the changed file.
        lines_added: Number of lines added.
        lines_deleted: Number of lines deleted.

    Returns:
        A chess.Piece with appropriate type and color.
    """
    piece_type = get_piece_for_path(file_path)
    # Determine color: if more lines added than deleted, treat as white; else black.
    color = chess.WHITE if lines_added >= lines_deleted else chess.BLACK
    return chess.Piece(piece_type=piece_type, color=color)


def square_from_commit_hash(commit_hash: str) -> chess.Square:
    """
    Map a commit hash to a starting square for the piece.

    Uses the first 2 bytes of the SHA-1 hash (after converting from hex).
    """
    # Take first 4 hex chars (2 bytes) from the hash
    hex_bytes = commit_hash[:4]
    index = int(hex_bytes, 16) % 64
    return chess.Square(index)
