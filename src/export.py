from __future__ import annotations

import chess
import chess.pgn
from datetime import datetime
from pathlib import Path
from typing import Optional

from .game import Game, CommitMove


def export_pgn(game: Game, output_path: Optional[Path] = None) -> str:
    """
    Export the game as a PGN string and optionally write to a file.

    Args:
        game: The Game object containing moves and metadata.
        output_path: Optional path to write the PGN file.

    Returns:
        The PGN string.
    """
    pgn_game = chess.pgn.Game()
    pgn_game.headers["Event"] = f"Git Blame Chess - {game.branch}"
    pgn_game.headers["Site"] = str(game.repo_path.resolve())
    pgn_game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
    pgn_game.headers["Round"] = "1"
    pgn_game.headers["White"] = "Git History"
    pgn_game.headers["Black"] = "Git History"
    pgn_game.headers["Result"] = "*"

    if game.moves:
        first_move = game.moves[0]
        pgn_game.headers["White"] = first_move.author
        pgn_game.headers["Black"] = first_move.author

    node = pgn_game
    for i, cm in enumerate(game.moves):
        # Determine the side to move based on the board state before the move
        # In standard chess, white moves first, then black, etc.
        # But here we treat each commit as a move regardless of side.
        # We'll annotate with the commit info.
        move_uci = cm.move.uci()
        san = cm.board_before.san(cm.move)

        # Add comment with commit details
        comment = f"Commit: {cm.commit_hash[:7]} | {cm.author} | {cm.message}"
        comment += f"\nFiles changed: {len(cm.files_changed)}, Lines: +{cm.lines_added}/-{cm.lines_deleted}"

        # Create the move in the PGN tree
        # We need to apply the move to a board to get SAN
        # But we already have the SAN from the game object
        # Use the SAN directly
        try:
            # Parse the SAN move on the current board
            move_obj = node.board().parse_san(san)
            node = node.add_variation(move_obj, comment=comment)
        except (ValueError, chess.InvalidMoveError):
            # Fallback: use UCI if SAN fails
            try:
                move_obj = chess.Move.from_uci(move_uci)
                if move_obj in node.board().legal_moves:
                    node = node.add_variation(move_obj, comment=comment)
                else:
                    # Skip illegal moves in PGN context
                    continue
            except (ValueError, chess.InvalidMoveError):
                continue

    # Set result based on game outcome if available
    if game.moves:
        final_board = game.moves[-1].board_after
        if final_board.is_checkmate():
            # Determine winner based on who made the last move
            # In our model, commits alternate? Not necessarily.
            # We'll just mark as checkmate.
            pgn_game.headers["Result"] = "1-0" if len(game.moves) % 2 == 1 else "0-1"
        elif final_board.is_stalemate():
            pgn_game.headers["Result"] = "1/2-1/2"
        elif final_board.is_insufficient_material():
            pgn_game.headers["Result"] = "1/2-1/2"
        else:
            pgn_game.headers["Result"] = "*"

    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
    pgn_str = pgn_game.accept(exporter)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(pgn_str, encoding="utf-8")

    return pgn_str
