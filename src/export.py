from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import chess
import chess.pgn

from .game import Game, CommitMove
from .duel import DuelState, BranchDuel
from .models import EXTENSION_PIECE_MAP, DEFAULT_PIECE, get_piece_for_path, path_to_square


def _get_piece_type_from_extension(file_path: str) -> int:
    """Get chess piece type from file extension."""
    ext = Path(file_path).suffix.lower()
    return EXTENSION_PIECE_MAP.get(ext, DEFAULT_PIECE)


def _get_piece_color_from_commit(commit_hex: str) -> bool:
    """Determine piece color (True=white, False=black) from commit hash."""
    # Use first hex digit of commit hash to determine color
    val = int(commit_hex[0], 16)
    return val < 8  # approximately 50/50 split


def _get_move_from_diff(diff: dict, commit_hex: str, board: chess.Board) -> Optional[chess.Move]:
    """Convert a file diff into a chess move."""
    file_path = diff.get('file_path', '')
    lines_added = diff.get('lines_added', 0)
    lines_deleted = diff.get('lines_deleted', 0)
    
    if not file_path:
        return None
    
    from_square = path_to_square(file_path)
    if from_square is None:
        return None
    
    # Determine piece type from extension
    piece_type = _get_piece_type_from_extension(file_path)
    
    # Determine color from commit hash
    color = _get_piece_color_from_commit(commit_hex)
    
    # Calculate target square based on lines changed
    # Simple hash: combine lines_added and lines_deleted
    combined = lines_added * 1000 + lines_deleted
    # Offset from source square (1-63)
    offset = (combined % 63) + 1
    to_square = (from_square + offset) % 64
    
    # Ensure we don't stay on same square
    if to_square == from_square:
        to_square = (to_square + 1) % 64
    
    move = chess.Move(from_square, to_square)
    
    # Check if move is legal (considering piece type)
    if board.piece_at(from_square) is not None:
        piece = board.piece_at(from_square)
        if piece.piece_type == piece_type and piece.color == color:
            # Check if move is pseudo-legal
            if move in board.legal_moves:
                return move
    
    # Try to find an alternative legal move for this piece
    for legal_move in board.legal_moves:
        if legal_move.from_square == from_square:
            return legal_move
    
    return None


def _make_move_from_commit(commit: CommitMove, board: chess.Board) -> Optional[chess.Move]:
    """Convert a CommitMove into a chess move."""
    if commit.move is not None:
        # If we already have a chess move, use it directly
        if isinstance(commit.move, chess.Move):
            if commit.move in board.legal_moves:
                return commit.move
            return None
        # If we have a dict representing diff
        if isinstance(commit.move, dict):
            return _get_move_from_diff(commit.move, commit.commit_hex, board)
    return None


def export_game_to_pgn(game: Game, output_path: Optional[Path] = None) -> str:
    """Export a Game object to PGN format.
    
    Args:
        game: The game to export.
        output_path: Optional path to write the PGN file.
    
    Returns:
        The PGN string.
    """
    # Create a new chess game
    chess_game = chess.pgn.Game()
    chess_game.headers["Event"] = "Git Blame Chess"
    chess_game.headers["Site"] = str(game.repo_path)
    chess_game.headers["Date"] = "????.??.??"
    chess_game.headers["Round"] = "1"
    chess_game.headers["White"] = "Commit History"
    chess_game.headers["Black"] = "Commit History"
    chess_game.headers["Result"] = "*"
    
    # Add repository info
    if game.branch:
        chess_game.headers["Branch"] = game.branch
    chess_game.headers["Variant"] = "Git Blame Chess"
    
    board = chess.Board()
    node = chess_game
    move_number = 1
    
    for commit in game.commit_moves:
        move = _make_move_from_commit(commit, board)
        if move is None:
            break
        
        # Determine if it's white or black's turn
        if board.turn == chess.WHITE:
            pass  # white's turn
        else:
            pass  # black's turn
        
        # Push the move to the PGN game
        node = node.add_main_variation(move)
        board.push(move)
        move_number += 1
    
    
    # Add PGN comments with commit info
    node = chess_game
    for commit in game.commit_moves:
        if node is None:
            break
        if commit.commit_hex:
            node.comment = f"Commit: {commit.commit_hex}"
        node = node.next()
    
    
    pgn_string = str(chess_game)
    
    if output_path:
        output_path.write_text(pgn_string)
    
    return pgn_string


def export_duel_to_pgn(duel: BranchDuel, output_path: Optional[Path] = None) -> str:
    """Export a BranchDuel game to PGN format.
    
    Args:
        duel: The duel to export.
        output_path: Optional path to write the PGN file.
    
    Returns:
        The PGN string.
    """
    if duel.state is None:
        duel.initialize()
    
    state = duel.state
    
    chess_game = chess.pgn.Game()
    chess_game.headers["Event"] = "Git Blame Chess - Branch Duel"
    chess_game.headers["Site"] = str(duel.repo.working_dir)
    chess_game.headers["Date"] = "????.??.??"
    chess_game.headers["Round"] = "1"
    chess_game.headers["White"] = f"Branch: {duel.left_branch}"
    chess_game.headers["Black"] = f"Branch: {duel.right_branch}"
    chess_game.headers["Result"] = "*"
    chess_game.headers["Variant"] = "Git Blame Chess - Duel"
    
    board = chess.Board()
    node = chess_game
    move_number = 1
    
    # Get all moves from both branches interleaved
    left_moves = list(state.left_game.commit_moves)
    right_moves = list(state.right_game.commit_moves)
    
    # Determine max length
    max_len = max(len(left_moves), len(right_moves))
    
    for i in range(max_len):
        # Left branch move (white)
        if i < len(left_moves):
            commit = left_moves[i]
            move = _make_move_from_commit(commit, board)
            if move is not None:
                node = node.add_main_variation(move)
                board.push(move)
                if commit.commit_hex:
                    node.comment = f"Left commit: {commit.commit_hex}