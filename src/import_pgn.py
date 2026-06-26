from __future__ import annotations

import chess
import chess.pgn
from pathlib import Path
from typing import Optional, Tuple, List
from dataclasses import dataclass
from .models import EXTENSION_PIECE_MAP, get_piece_for_path, path_to_square
from .game import Game, CommitMove


@dataclass
class ImportedGame:
    """Represents a PGN game imported for replay."""
    headers: dict[str, str]
    moves: List[chess.Move]
    final_board: chess.Board


def parse_pgn_file(pgn_path: Path) -> Optional[ImportedGame]:
    """Parse a PGN file and return an ImportedGame object."""
    if not pgn_path.exists():
        return None
    try:
        with open(pgn_path, 'r', encoding='utf-8') as f:
            game = chess.pgn.read_game(f)
        if game is None:
            return None
        headers = dict(game.headers)
        moves: List[chess.Move] = []
        node = game
        while node.variations:
            node = node.variations[0]
            moves.append(node.move)
        final_board = game.end().board()
        return ImportedGame(headers=headers, moves=moves, final_board=final_board)
    except (ValueError, OSError) as e:
        print(f"Error parsing PGN file: {e}")
        return None


def validate_pgn_game(imported: ImportedGame) -> bool:
    """Validate that the imported game follows expected structure."""
    # Check that the game has at least one move
    if not imported.moves:
        print("PGN game has no moves.")
        return False
    # Validate that the final board is consistent with the move list
    board = chess.Board()
    for move in imported.moves:
        if move not in board.legal_moves:
            print(f"Move {move} is not legal in position: {board.fen()}")
            return False
        board.push(move)
    return True


def load_pgn_into_game(pgn_path: Path, repo_path: Path = Path('.'), branch: Optional[str] = None) -> Optional[Game]:
    """
    Load a PGN file and convert it into a Game object for replay.
    Uses dummy commit hashes based on move index.
    """
    imported = parse_pgn_file(pgn_path)
    if imported is None:
        print(f"Could not parse PGN file: {pgn_path}")
        return None
    
    if not validate_pgn_game(imported):
        print("PGN validation failed.")
        return None
    
    # Build a Game from the moves
    game = Game(repo_path=repo_path, branch=branch or "pgn_import")
    game.board = chess.Board()
    game.moves = []
    game.commit_moves = []
    
    board = chess.Board()
    for i, move in enumerate(imported.moves):
        # Generate a fake commit hash
        fake_sha = f"pgn-import-{i:08d}"
        # Determine piece type from the moved piece
        piece = board.piece_at(move.from_square)
        if piece is None:
            print(f"No piece at source square {move.from_square} for move {i}")
            return None
        piece_type = piece.piece_type
        # Build a CommitMove with dummy diff info
        commit_move = CommitMove(
            commit_sha=fake_sha,
            author="PGN Import",
            message=f"PGN move {i+1}: {move.uci()}",
            piece_type=piece_type,
            from_square=move.from_square,
            to_square=move.to_square,
            capture=board.is_capture(move),
            promotion=move.promotion,
        )
        game.commit_moves.append(commit_move)
        game.moves.append(move)
        board.push(move)
    
    game.board = board
    game.current_index = len(game.moves) - 1
    return game
