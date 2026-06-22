"""Core data models and mapping logic for converting git history into chess moves."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Dict, List, Optional, Tuple

import chess

# Mapping from file extension to chess piece type (uppercase = white, lowercase = black)
# We treat files as white pieces (the committing branch's pieces).
# In a duel, the other branch's files become black pieces.
EXTENSION_PIECE_MAP: Dict[str, chess.PieceType] = {
    '.py': chess.PAWN,
    '.js': chess.KNIGHT,
    '.ts': chess.BISHOP,
    '.java': chess.ROOK,
    '.c': chess.QUEEN,
    '.cpp': chess.QUEEN,
    '.h': chess.KING,
    '.rs': chess.KNIGHT,
    '.go': chess.BISHOP,
    '.rb': chess.ROOK,
    '.swift': chess.KNIGHT,
    '.kt': chess.BISHOP,
    '.scala': chess.QUEEN,
    '.php': chess.PAWN,
    '.pl': chess.PAWN,
    '.sh': chess.PAWN,
    '.yaml': chess.PAWN,
    '.yml': chess.PAWN,
    '.json': chess.PAWN,
    '.xml': chess.PAWN,
    '.md': chess.PAWN,
    '.txt': chess.PAWN,
    '.css': chess.PAWN,
    '.html': chess.PAWN,
    '.sql': chess.PAWN,
    '.r': chess.PAWN,
    '.m': chess.PAWN,
    '.mm': chess.PAWN,
}

DEFAULT_PIECE = chess.PAWN

# Chess board squares are 0-63 (a1=0, h8=63). We map a (file_path, line_number) pair
# to a deterministic square index using a hash.
HASH_SQUARE_MOD = 64


def file_to_piece_type(file_path: str) -> chess.PieceType:
    """Determine the chess piece type based on file extension."""
    ext = PurePosixPath(file_path).suffix.lower()
    return EXTENSION_PIECE_MAP.get(ext, DEFAULT_PIECE)


def hash_to_square(file_path: str, line_number: int) -> chess.Square:
    """Deterministically map a (file, line) pair to a chess square (0-63)."""
    raw = f"{file_path}:{line_number}".encode('utf-8')
    digest = hashlib.sha256(raw).hexdigest()
    square = int(digest[:8], 16) % HASH_SQUARE_MOD
    return chess.Square(square)


@dataclass
class MoveRecord:
    """Represents a single chess move derived from a git diff hunk."""
    piece_type: chess.PieceType
    from_square: chess.Square
    to_square: chess.Square
    is_capture: bool
    file_path: str
    line_number: int
    commit_hash: str
    author: str
    message: str

    def to_chess_move(self, board: chess.Board) -> Optional[chess.Move]:
        """Try to create a legal chess move from this record on the given board.
        Returns None if no legal move matches."""
        # Attempt to find a piece of the given type on from_square moving to to_square.
        # This is a simplified approach; real logic would need to handle promotions etc.
        piece = board.piece_at(self.from_square)
        if piece is None or piece.piece_type != self.piece_type:
            return None
        # Build candidate move
        candidate = chess.Move(self.from_square, self.to_square)
        if candidate in board.legal_moves:
            return candidate
        # If not legal, perhaps the piece is on a different square — we'll just return None
        return None


@dataclass
class CommitState:
    """Represents a commit as a board state (FEN) with metadata."""
    commit_hash: str
    author: str
    message: str
    fen: str
    parent_hashes: List[str]
    moves: List[MoveRecord] = field(default_factory=list)


@dataclass
class BranchDuel:
    """Represents a duel between two branches."""
    branch_a: str
    branch_b: str
    merge_base: str
    moves_a: List[MoveRecord]
    moves_b: List[MoveRecord]
    conflict_moves: List[Tuple[MoveRecord, MoveRecord]]  # conflicting moves from both sides

    @property
    def total_moves(self) -> int:
        return len(self.moves_a) + len(self.moves_b) + len(self.conflict_moves)
