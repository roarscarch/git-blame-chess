from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Optional

import chess

# Default piece type for unknown file extensions
DEFAULT_PIECE = chess.PAWN

# Map file extensions to chess piece types
EXTENSION_PIECE_MAP: Dict[str, int] = {
    '.py': chess.BISHOP,        # Python files: bishops (logic)
    '.js': chess.KNIGHT,        # JavaScript: knights (agile)
    '.ts': chess.KNIGHT,        # TypeScript: knights
    '.java': chess.ROOK,        # Java: rooks (structured)
    '.cpp': chess.ROOK,         # C++: rooks
    '.c': chess.ROOK,           # C: rooks
    '.h': chess.PAWN,           # Headers: pawns
    '.hpp': chess.PAWN,
    '.rs': chess.BISHOP,        # Rust: bishops
    '.go': chess.BISHOP,        # Go: bishops
    '.rb': chess.BISHOP,        # Ruby: bishops
    '.swift': chess.KNIGHT,
    '.kt': chess.KNIGHT,
    '.scala': chess.BISHOP,
    '.html': chess.PAWN,        # HTML: pawns (foundation)
    '.css': chess.PAWN,
    '.scss': chess.PAWN,
    '.less': chess.PAWN,
    '.json': chess.PAWN,
    '.yaml': chess.PAWN,
    '.yml': chess.PAWN,
    '.toml': chess.PAWN,
    '.xml': chess.PAWN,
    '.md': chess.PAWN,          # Markdown: pawns
    '.rst': chess.PAWN,
    '.txt': chess.PAWN,
    '.sh': chess.KNIGHT,        # Shell scripts: knights (quick)
    '.bash': chess.KNIGHT,
    '.zsh': chess.KNIGHT,
    '.ps1': chess.KNIGHT,
    '.sql': chess.ROOK,         # SQL: rooks (data structures)
    '.proto': chess.ROOK,
    '.graphql': chess.ROOK,
    '.vue': chess.KNIGHT,
    '.svelte': chess.KNIGHT,
    '.jsx': chess.KNIGHT,
    '.tsx': chess.KNIGHT,
    '.dockerfile': chess.PAWN,
    'Dockerfile': chess.PAWN,
    '.gitignore': chess.PAWN,
    '.gitattributes': chess.PAWN,
    '.env': chess.PAWN,
    '.editorconfig': chess.PAWN,
    'Makefile': chess.ROOK,
    'CMakeLists.txt': chess.ROOK,
    'Cargo.toml': chess.PAWN,
    'package.json': chess.PAWN,
    'requirements.txt': chess.PAWN,
    'Pipfile': chess.PAWN,
    'Gemfile': chess.PAWN,
}


def get_piece_for_path(file_path: str) -> int:
    """Determine chess piece type based on file extension."""
    path_lower = file_path.lower()
    # Check exact filenames first
    base = Path(path_lower).name
    if base in EXTENSION_PIECE_MAP:
        return EXTENSION_PIECE_MAP[base]
    # Then check extensions
    suffix = Path(path_lower).suffix
    return EXTENSION_PIECE_MAP.get(suffix, DEFAULT_PIECE)


def path_to_square(file_path: str, line_number: int) -> chess.Square:
    """
    Map a file path and line number to a chess board square (0-63).
    Uses a deterministic hash of the path and line number.
    """
    hash_input = f"{file_path}:{line_number}