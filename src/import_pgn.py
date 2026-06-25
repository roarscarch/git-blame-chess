from __future__ import annotations

import chess
import chess.pgn
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import EXTENSION_PIECE_MAP, DEFAULT_PIECE, get_piece_for_path, path_to_square
from .game import Game, CommitMove


def parse_pgn_file(pgn_path: Path) -> Optional[chess.pgn.Game]:
    """Parse a PGN file and return the chess.pgn.Game object."""
    try:
        with open(pgn_path, 'r') as f:
            game = chess.pgn.read_game(f)
        return game
    except Exception as e:
        print(f"Error reading PGN file: {e}")
        return None


def pgn_to_commit_moves(pgn_game: chess.pgn.Game) -> List[CommitMove]:
    """Convert a chess.pgn.Game to a list of CommitMove objects."""
    commit_moves: List[CommitMove] = []
    board = pgn_game.board()
    node = pgn_game
    move_number = 0
    while node.variations:
        node = node.variations[0]
        move = node.move
        if move is None:
            continue
        # Generate a fake commit hash based on move and position
        hash_input = f"{move.uci()}{node.comment if node.comment else ''}{move_number}"
        commit_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:10]
        # Determine piece type from the moving piece
        piece = board.piece_at(move.from_square)
        piece_type_char = piece.symbol().upper() if piece else '?'
        # Generate a fake author
        author = f"player_{'w' if board.turn == chess.WHITE else 'b'}"
        # Generate fake message
        message = f"{piece_type_char} {chess.SQUARE_NAMES[move.from_square]} -> {chess.SQUARE_NAMES[move.to_square]}"
        if board.is_capture(move):
            message += " (capture)"
        # Create CommitMove
        commit_move = CommitMove(
            commit_hash=commit_hash,
            author=author,
            message=message,
            move=move,
            fen_before=board.fen(),
            fen_after=board.fen(),  # Will be updated after the move
            timestamp=move_number,
            files_changed=[],
            lines_added=0,
            lines_removed=0,
        )
        commit_moves.append(commit_move)
        board.push(move)
        move_number += 1
    # Update fen_after for each move
    board.reset()
    for i, cm in enumerate(commit_moves):
        board.push(cm.move)
        commit_moves[i] = cm._replace(fen_after=board.fen())
    return commit_moves


def pgn_to_game(pgn_path: Path, repo_path: Optional[Path] = None) -> Optional[Game]:
    """Convert a PGN file to a Game object."""
    pgn_game = parse_pgn_file(pgn_path)
    if pgn_game is None:
        return None
    commit_moves = pgn_to_commit_moves(pgn_game)
    if not commit_moves:
        return None
    # Extract headers as game metadata
    headers = pgn_game.headers
    branch = headers.get("Branch", "imported")
    author = headers.get("White", "unknown")
    # Create Game object
    game = Game(
        repo_path=repo_path or Path.cwd(),
        branch=branch,
        commit_moves=commit_moves,
        start_fen=chess.STARTING_FEN,
        current_index=-1,
        board=chess.Board(),
        authors={author}