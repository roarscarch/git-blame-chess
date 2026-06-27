from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import chess
import chess.pgn

from .game import Game, CommitMove
from .models import EXTENSION_PIECE_MAP, DEFAULT_PIECE, get_piece_for_path, path_to_square


def parse_pgn(pgn_string: str) -> Optional[Game]:
    """
    Parse a PGN string into a Game object.
    Returns None if parsing fails.
    """
    try:
        game = chess.pgn.read_game(pgn_string)
        if game is None:
            return None
        return _pgn_to_game(game)
    except Exception:
        return None


def parse_pgn_file(filepath: str) -> Optional[Game]:
    """
    Parse a PGN file into a Game object.
    Returns None if parsing fails.
    """
    try:
        with open(filepath, 'r') as f:
            pgn_string = f.read()
        return parse_pgn(pgn_string)
    except Exception:
        return None


def _pgn_to_game(pgn_game: chess.pgn.GameNode) -> Game:
    """
    Convert a chess.pgn.Game object into a Game instance.
    This uses the PGN headers and moves to reconstruct the commit history.
    """
    from datetime import datetime, timezone
    
    headers = pgn_game.headers
    
    # Extract metadata from PGN headers
    event = headers.get("Event", "Imported PGN Game")
    site = headers.get("Site", "")
    date_str = headers.get("Date", "")
    round_str = headers.get("Round", "")
    white = headers.get("White", "White")
    black = headers.get("Black", "Black")
    result = headers.get("Result", "*")
    
    # Parse date if available
    commit_date = None
    if date_str:
        try:
            import datetime
            parsed_date = datetime.datetime.strptime(date_str, "%Y.%m.%d")
            commit_date = parsed_date.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    
    if commit_date is None:
        commit_date = datetime.now(timezone.utc)
    
    # Build commit moves from the game moves
    board = chess.Board()
    commit_moves: List[CommitMove] = []
    
    for move_node in pgn_game.mainline():
        move = move_node.move
        if move is None:
            continue
        
        # Create a deterministic commit hash based on move
        import hashlib
        commit_hash = hashlib.sha256(str(move).encode()).hexdigest()[:8]
        
        # Create a commit message from the move
        commit_message = f"Chess move: {board.san(move)}"
        
        # Determine piece type from move
        piece = board.piece_at(move.from_square)
        piece_type = piece.piece_type if piece else chess.PAWN
        
        # Map piece type to extension (reverse of get_piece_for_path)
        ext_to_piece = {v: k for k, v in EXTENSION_PIECE_MAP.items()}
        file_ext = ext_to_piece.get(piece_type, ".txt")
        
        # Create a pseudo file path
        from_sq_name = chess.SQUARE_NAMES[move.from_square]
        to_sq_name = chess.SQUARE_NAMES[move.to_square]
        file_path = f"src/{from_sq_name}_{to_sq_name}{file_ext}"
        
        # Compute line number from square index
        line_number = move.from_square + 1
        
        commit_move = CommitMove(
            commit_hash=commit_hash,
            author=white if len(commit_moves) % 2 == 0 else black,
            commit_date=commit_date,
            commit_message=commit_message,
            file_path=file_path,
            lines_changed=1,
            piece_type=piece_type,
            from_square=move.from_square,
            to_square=move.to_square,
            board_fen=board.fen(),
        )
        commit_moves.append(commit_move)
        
        # Apply the move to the board for next iteration
        board.push(move)
    
    # Create Game object with the constructed moves
    game = Game(
        repo_path="",
        branch="imported",
        commit_moves=commit_moves,
        current_index=-1,
        board=chess.Board(),
        total_moves=len(commit_moves),
    )
    
    return game


def validate_pgn(pgn_string: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a PGN string.
    Returns (is_valid, error_message).
    """
    try:
        game = chess.pgn.read_game(pgn_string)
        if game is None:
            return False, "Failed to parse PGN: empty or invalid format"
        
        # Validate that the game has at least one move
        has_moves = False
        for _ in game.mainline():
            has_moves = True
            break
        
        if not has_moves:
            return False, "PGN game has no moves"
        
        # Validate that the game is legal
        board = chess.Board()
        for move_node in game.mainline():
            move = move_node.move
            if move is None:
                continue
            if move not in board.legal_moves:
                san = board.san(move)
                return False, f"Illegal move {san} at board position"
            board.push(move)
        
        return True, None
    except Exception as e:
        return False, f"Error validating PGN: {str(e)}"


def validate_pgn_file(filepath: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a PGN file.
    Returns (is_valid, error_message).
    """
    try:
        with open(filepath, 'r') as f:
            pgn_string = f.read()
        return validate_pgn(pgn_string)
    except FileNotFoundError:
        return False, f"File not found: {filepath}"
    except Exception as e:
        return False, f"Error reading file: {str(e)}