from __future__ import annotations

import chess
import chess.pgn
from typing import List, Optional
from io import StringIO
from dataclasses import dataclass, field

from .game import Game, CommitMove
from .models import piece_type_from_extension


@dataclass
class ExportOptions:
    """Options for PGN export."""
    include_annotations: bool = True
    include_comments: bool = True
    include_clock: bool = False
    event_name: str = "Git Blame Chess"
    site: str = "local"
    date: str = "????.??.??"
    round: str = "-"


class GameExporter:
    """Export a game to PGN format."""

    def __init__(self, game: Game, options: Optional[ExportOptions] = None) -> None:
        self.game = game
        self.options = options or ExportOptions()

    def to_pgn_string(self) -> str:
        """Export the game as a PGN string."""
        game_node = self._build_game_node()
        exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
        return game_node.accept(exporter)

    def to_file(self, path: str) -> None:
        """Export the game to a PGN file."""
        pgn_str = self.to_pgn_string()
        with open(path, 'w', encoding='utf-8') as f:
            f.write(pgn_str)

    def _build_game_node(self) -> chess.pgn.Game:
        """Build a PGN game tree from the game's move list."""
        game = chess.pgn.Game()
        game.headers["Event"] = self.options.event_name
        game.headers["Site"] = self.options.site
        game.headers["Date"] = self.options.date
        game.headers["Round"] = self.options.round
        game.headers["White"] = self._get_player_name(chess.WHITE)
        game.headers["Black"] = self._get_player_name(chess.BLACK)
        game.headers["Result"] = self._get_result()

        # Add repository info as a custom header
        repo_path = str(self.game.repo_path.resolve()) if hasattr(self.game, 'repo_path') else "unknown"
        game.headers["Site"] = repo_path

        # Build move tree
        node = game
        board = chess.Board()

        for i, move in enumerate(self.game.moves):
            if move.move is None:
                continue

            # Create a new node for this move
            node = node.add_variation(move.move)

            if self.options.include_comments:
                comment = self._build_comment(move, i)
                if comment:
                    node.comment = comment

            # Apply move to board for validation
            try:
                board.push(move.move)
            except ValueError:
                # If the move is illegal in the current board state, skip it
                continue

        return game

    def _get_player_name(self, color: chess.Color) -> str:
        """Get the player name for a given color."""
        if hasattr(self.game, 'branch_name'):
            branch = self.game.branch_name
            return f"{branch} ({'White' if color == chess.WHITE else 'Black'})"
        return f"Branch-{'White' if color == chess.WHITE else 'Black'}"

    def _get_result(self) -> str:
        """Get the game result string."""
        if not self.game.moves:
            return "*"
        board = self.game.current_board() if hasattr(self.game, 'current_board') else chess.Board()
        if board.is_checkmate():
            winner = "White" if board.turn == chess.BLACK else "Black"
            return f"1-0" if winner == "White" else "0-1"
        if board.is_stalemate() or board.is_insufficient_material():
            return "1/2-1/2"
        return "*"

    def _build_comment(self, move: CommitMove, index: int) -> str:
        """Build a comment string for a move."""
        parts = []

        if move.commit_hash:
            parts.append(f"commit: {move.commit_hash[:7]}")

        if move.files_changed:
            files_str = ", ".join(move.files_changed[:3])
            if len(move.files_changed) > 3:
                files_str += f" (+{len(move.files_changed) - 3} more)"
            parts.append(f"files: {files_str}")

        if move.author:
            parts.append(f"author: {move.author}")

        if move.message:
            # Truncate commit message for comment
            msg = move.message.strip().split('\n')[0]
            if len(msg) > 60:
                msg = msg[:57] + "..."
            parts.append(f"msg: {msg}")

        return " | ".join(parts)


def export_game(game: Game, path: str, options: Optional[ExportOptions] = None) -> None:
    """Convenience function to export a game to a PGN file."""
    exporter = GameExporter(game, options)
    exporter.to_file(path)


def export_game_to_string(game: Game, options: Optional[ExportOptions] = None) -> str:
    """Convenience function to export a game as a PGN string."""
    exporter = GameExporter(game, options)
    return exporter.to_pgn_string()
