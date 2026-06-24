from __future__ import annotations

import chess
import chess.pgn
from pathlib import Path
from typing import List, Optional, Tuple

from .models import path_to_square, get_piece_for_path


def import_pgn_file(pgn_path: Path) -> chess.Board:
    """
    Import a PGN file and return the final board state.
    
    Args:
        pgn_path: Path to the PGN file.
        
    Returns:
        The chess.Board after all moves are applied.
        
    Raises:
        FileNotFoundError: If the PGN file does not exist.
        ValueError: If the PGN file is malformed or contains invalid moves.
    """
    if not pgn_path.exists():
        raise FileNotFoundError(f"PGN file not found: {pgn_path}")
    
    with open(pgn_path, 'r') as f:
        game = chess.pgn.read_game(f)
    
    if game is None:
        raise ValueError("Could not parse PGN file: file is empty or malformed")
    
    board = game.board()
    for move in game.mainline_moves():
        if move not in board.legal_moves:
            raise ValueError(f"Illegal move in PGN: {move.uci()}")
        board.push(move)
    
    return board


def import_pgn_with_headers(pgn_path: Path) -> Tuple[chess.Board, dict]:
    """
    Import a PGN file and return both the final board state and headers.
    
    Args:
        pgn_path: Path to the PGN file.
        
    Returns:
        A tuple of (board, headers_dict).
        
    Raises:
        FileNotFoundError: If the PGN file does not exist.
        ValueError: If the PGN file is malformed.
    """
    if not pgn_path.exists():
        raise FileNotFoundError(f"PGN file not found: {pgn_path}")
    
    with open(pgn_path, 'r') as f:
        game = chess.pgn.read_game(f)
    
    if game is None:
        raise ValueError("Could not parse PGN file: file is empty or malformed")
    
    headers = game.headers
    board = game.board()
    for move in game.mainline_moves():
        if move not in board.legal_moves:
            raise ValueError(f"Illegal move in PGN: {move.uci()}")
        board.push(move)
    
    return board, dict(headers)


def import_pgn_moves(pgn_path: Path) -> List[chess.Move]:
    """
    Import a PGN file and return the list of moves.
    
    Args:
        pgn_path: Path to the PGN file.
        
    Returns:
        A list of chess.Move objects in order.
        
    Raises:
        FileNotFoundError: If the PGN file does not exist.
        ValueError: If the PGN file is malformed or contains invalid moves.
    """
    if not pgn_path.exists():
        raise FileNotFoundError(f"PGN file not found: {pgn_path}")
    
    with open(pgn_path, 'r') as f:
        game = chess.pgn.read_game(f)
    
    if game is None:
        raise ValueError("Could not parse PGN file: file is empty or malformed")
    
    moves = []
    board = chess.Board()
    for move in game.mainline_moves():
        if move not in board.legal_moves:
            raise ValueError(f"Illegal move in PGN: {move.uci()}")
        moves.append(move)
        board.push(move)
    
    return moves


def pgn_to_game(pgn_path: Path, repo_path: Optional[Path] = None) -> 'Game':
    """
    Convert a PGN file into a Game object for interactive replay.
    
    Args:
        pgn_path: Path to the PGN file.
        repo_path: Optional path to the git repository (for metadata).
        
    Returns:
        A Game object initialized with the moves from the PGN.
        
    Raises:
        FileNotFoundError: If the PGN file does not exist.
        ValueError: If the PGN file is malformed or contains invalid moves.
    """
    from .game import Game
    from .models import CommitMove
    
    board, headers = import_pgn_with_headers(pgn_path)
    
    # Reconstruct moves list
    game = chess.pgn.read_game(open(pgn_path, 'r'))
    moves = list(game.mainline_moves())
    
    commit_moves = []
    for i, move in enumerate(moves):
        cm = CommitMove(
            commit_hash=headers.get("Site", f"pgn-move-{i}"),
            author=headers.get("White", "?") if i % 2 == 0 else headers.get("Black", "?"),
            message=headers.get("Event", "Imported from PGN"),
            move=move,
            timestamp=headers.get("Date", "?"),
        )
        commit_moves.append(cm)
    
    return Game(
        repo_path=repo_path or Path("."),
        branch="imported",
        moves=commit_moves,
        board=board,
    )