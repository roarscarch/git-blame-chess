from __future__ import annotations

import chess
import chess.pgn
import io
from pathlib import Path
from typing import Optional

from .game import Game, CommitMove
from .models import path_to_square


def game_to_pgn(game: Game, output_path: Optional[Path] = None) -> str:
    """Convert a Game into a PGN string, optionally writing to file."""
    pgn_game = chess.pgn.Game()
    pgn_game.headers["Event"] = "Git Blame Chess"
    pgn_game.headers["Site"] = str(game.repo_path.resolve())
    pgn_game.headers["Date"] = game.start_date.strftime("%Y.%m.%d") if game.start_date else "????.??.??"
    pgn_game.headers["Round"] = "1"
    pgn_game.headers["White"] = game.branch or "initial"
    pgn_game.headers["Black"] = "development"
    pgn_game.headers["Result"] = "*"
    pgn_game.headers["Variant"] = "Standard"
    pgn_game.headers["GitRepo"] = str(game.repo_path.resolve())
    pgn_game.headers["GitBranch"] = game.branch or "HEAD"
    pgn_game.headers["CommitCount"] = str(len(game.moves))
    pgn_game.headers["InitialFEN"] = chess.STARTING_FEN
    pgn_game.setup(chess.Board())

    node = pgn_game
    for i, move in enumerate(game.moves):
        comment_lines = [
            f"Commit: {move.commit_hash[:8] if move.commit_hash else '?'}",
            f"Author: {move.author}",
            f"Date: {move.datetime.strftime('%Y-%m-%d %H:%M:%S') if move.datetime else '?'}",
            f"Message: {move.message}",
            f"Files changed: {len(move.files_changed)}",
            f"Lines added: {move.lines_added}",
            f"Lines deleted: {move.lines_deleted}",
        ]
        if move.captures:
            comment_lines.append(f"Captures: {', '.join(str(c) for c in move.captures)}")
        comment = "\n".join(comment_lines)

        # Convert our internal move to a chess.Move
        chess_move = chess.Move(from_square=move.from_square, to_square=move.to_square, promotion=move.promotion)
        if not game.board.is_legal(chess_move):
            # Try to find a legal move that matches the intent
            legal_moves = list(game.board.legal_moves)
            found = False
            for lm in legal_moves:
                if lm.from_square == move.from_square and lm.to_square == move.to_square:
                    chess_move = lm
                    found = True
                    break
            if not found:
                # Skip illegal move in PGN export
                continue

        node = node.add_variation(chess_move)
        node.comment = comment
        game.board.push(chess_move)

    # Reset board after generation
    game.board.reset()
    for m in game.moves:
        chess_move = chess.Move(from_square=m.from_square, to_square=m.to_square, promotion=m.promotion)
        if game.board.is_legal(chess_move):
            game.board.push(chess_move)

    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
    pgn_str = pgn_game.accept(exporter)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(pgn_str)

    return pgn_str


def export_game(game: Game, output: Optional[Path] = None) -> str:
    """Export game to PGN. If output is None, return as string."""
    return game_to_pgn(game, output_path=output)
