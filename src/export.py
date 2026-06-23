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
        # Since we start with an empty board and each commit adds/removes pieces,
        # we assign moves alternately starting with white for the first commit.
        turn = chess.WHITE if i % 2 == 0 else chess.BLACK
        # The actual move UCI is stored in cm.uci
        # We need to parse it as a chess.Move and add to the PGN
        try:
            move = chess.Move.from_uci(cm.uci)
            # Verify the move is legal on the current board state
            # We simulate the board state up to this point
            board = chess.Board()
            for j in range(i):
                prev_move = chess.Move.from_uci(game.moves[j].uci)
                if prev_move in board.legal_moves:
                    board.push(prev_move)
                else:
                    # If the move is illegal, we ignore it (shouldn't happen in practice)
                    pass
            if move in board.legal_moves:
                node = node.add_variation(move)
            else:
                # Fallback: just add the move anyway (might produce unusual games)
                node = node.add_variation(move)
        except ValueError:
            # If the UCI is invalid, skip this move
            continue

    if output_path:
        with open(output_path, "w") as f:
            f.write(str(pgn_game))

    return str(pgn_game)
