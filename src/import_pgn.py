from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import chess
import chess.pgn

from .game import Game, CommitMove
from .models import path_to_square, EXTENSION_PIECE_MAP, DEFAULT_PIECE


def parse_pgn(pgn_string: str) -> chess.Board:
    """Parse a PGN string and return the resulting board."""
    game = chess.pgn.read_game(pgn_string)
    if game is None:
        raise ValueError("Invalid PGN: could not parse")
    board = game.board()
    for move in game.mainline_moves():
        board.push(move)
    return board


def import_game_from_pgn(pgn_string: str, repo_path: Optional[str] = None) -> Game:
    """
    Import a chess game from a PGN string and convert it to a Game object.
    
    Each move in the PGN is mapped to a synthetic commit move with:
    - commit_hash: SHA256 of the move's UCI string (deterministic)
    - author: taken from PGN tags if available, else "PGN Import"
    - message: the SAN notation of the move
    - board_before: the board state before the move
    - board_after: the board state after the move
    
    The file-to-square mapping is preserved by assigning each move to a
    dummy file path derived from the move's algebraic notation.
    """
    pgn_game = chess.pgn.read_game(pgn_string)
    if pgn_game is None:
        raise ValueError("Invalid PGN: could not parse")
    
    board = chess.Board()
    moves: List[CommitMove] = []
    
    # Extract metadata from PGN tags
    white = pgn_game.headers.get("White", "White")
    black = pgn_game.headers.get("Black", "Black")
    date = pgn_game.headers.get("Date", "????.??.??")
    event = pgn_game.headers.get("Event", "PGN Import")
    
    for i, move in enumerate(pgn_game.mainline_moves()):
        board_before = board.copy()
        board.push(move)
        board_after = board.copy()
        
        # Generate a unique but deterministic commit hash
        commit_hash = hashlib.sha256(move.uci().encode()).hexdigest()[:12]
        
        # Determine author based on move parity (white = left, black = right)
        author = white if i % 2 == 0 else black
        
        # Create a synthetic file path from the move's algebraic notation
        san = board_before.san(move)
        # Use square names to create a path-like identifier
        from_sq = chess.SQUARE_NAMES[move.from_square]
        to_sq = chess.SQUARE_NAMES[move.to_square]
        file_path = f"pgn/{from_sq}-{to_sq}"
        
        # Determine piece type from the moved piece
        piece = board_before.piece_at(move.from_square)
        piece_type = piece.piece_type if piece else chess.PAWN
        
        # Map piece type to a file extension for consistency
        ext_to_piece = {v: k for k, v in EXTENSION_PIECE_MAP.items()}
        extension = ext_to_piece.get(piece_type, ".py")
        file_path_with_ext = file_path + extension
        
        # Compute the square from the file path (for model consistency)
        square = path_to_square(file_path_with_ext)
        
        # Determine number of lines changed (proxy for captures or complexity)
        lines_changed = 1
        if board.is_capture(move):
            lines_changed = 2  # capture = more change
        if move.promotion:
            lines_changed = 3  # promotion = significant change
        
        commit_move = CommitMove(
            commit_hash=commit_hash,
            author=author,
            timestamp=i * 60,  # synthetic timestamps (1 minute per move)
            message=san,
            files_changed=[file_path_with_ext],
            lines_added=1,
            lines_deleted=lines_changed - 1,
            piece_type=piece_type,
            from_square=move.from_square,
            to_square=move.to_square,
            promotion=move.promotion,
            capture=board.is_capture(move),
            board_before=board_before.fen(),
            board_after=board_after.fen(),
        )
        moves.append(commit_move)
    
    # Create the Game object with imported metadata
    return Game(
        repo_path=repo_path or ".",
        branch="imported",
        moves=moves,
        board=chess.Board(),
        start_board=chess.Board(),
        current_move_index=0,
        metadata={
            "Event": event,
            "Date": date,
            "White": white,
            "Black": black,
        },
    )


def validate_pgn(pgn_string: str) -> Tuple[bool, Optional[str]]:
    """Validate a PGN string. Returns (is_valid, error_message)."""
    try:
        game = chess.pgn.read_game(pgn_string)
        if game is None:
            return False, "Could not parse PGN (game object is None)"
        board = game.board()
        for move in game.mainline_moves():
            if move not in board.legal_moves:
                return False, f"Illegal move: {board.san(move)}"
            board.push(move)
        return True, None
    except Exception as e:
        return False, str(e)


def import_game_from_pgn_file(file_path: str, repo_path: Optional[str] = None) -> Game:
    """Import a game from a PGN file."""
    with open(file_path, "r") as f:
        pgn_content = f.read()
    return import_game_from_pgn(pgn_content, repo_path)