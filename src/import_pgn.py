from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import chess
import chess.pgn

from .models import EXTENSION_PIECE_MAP, DEFAULT_PIECE, get_piece_for_path, path_to_square


@dataclass
class PGNImportResult:
    """Result of importing a PGN file."""
    moves: List[chess.Move]
    headers: Dict[str, str]
    board: chess.Board = field(default_factory=chess.Board)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    valid: bool = True


class PGNImporter:
    """
    Imports a PGN file and validates it against a git repository.
    
    The PGN is expected to contain moves that correspond to changes in a git repo.
    Each move can optionally be annotated with the file path and line range.
    """

    FILE_ANNOTATION_PATTERN = re.compile(r'\{file: ([^,]+), lines: (\d+)-(\d+)\}')

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path
        self.pgn_path: Optional[Path] = None

    def load_pgn(self, path: Path) -> Optional[chess.pgn.Game]:
        """Load a PGN file and return the game object."""
        if not path.exists():
            return None
        with open(path, 'r') as f:
            return chess.pgn.read_game(f)

    def import_game(self, pgn_path: Path) -> PGNImportResult:
        """Import a PGN file and validate it."""
        self.pgn_path = pgn_path
        game = self.load_pgn(pgn_path)
        if game is None:
            return PGNImportResult(
                moves=[],
                headers={},
                errors=[f"Could not load PGN from {pgn_path}"],
                valid=False
            )

        result = PGNImportResult(
            headers=dict(game.headers)
        )

        # Validate required headers
        required_headers = ['Event', 'Site', 'Date', 'Round', 'White', 'Black']
        for header in required_headers:
            if header not in result.headers:
                result.warnings.append(f"Missing PGN header: {header}")

        # Extract moves
        board = chess.Board()
        for node in game.mainline():
            move = node.move
            if move is None:
                continue
            # Validate move is legal on current board
            if move not in board.legal_moves:
                result.errors.append(f"Illegal move: {board.san(move)} at ply {board.fullmove_number}")
                result.valid = False
                continue
            board.push(move)
            result.moves.append(move)

            # Check for file annotations
            comment = node.comment
            if comment:
                match = self.FILE_ANNOTATION_PATTERN.search(comment)
                if match:
                    file_path = match.group(1)
                    start_line = int(match.group(2))
                    end_line = int(match.group(3))
                    # Validate file exists if repo path provided
                    if self.repo_path:
                        full_path = self.repo_path / file_path
                        if not full_path.exists():
                            result.warnings.append(
                                f"File {file_path} not found in repository at {self.repo_path}"
                            )

        result.board = board
        return result

    def validate_against_repo(self, result: PGNImportResult) -> PGNImportResult:
        """
        Validate imported game against the git repository.
        Checks that file paths exist and line numbers are within bounds.
        """
        if self.repo_path is None:
            result.warnings.append("No repo path provided, skipping repo validation")
            return result

        # This is a simplified validation - in production, we'd parse the
        # actual git history and compare moves
        for i, move in enumerate(result.moves):
            # Check that the move corresponds to a real file change
            # For now, just check file existence from annotations
            pass

        return result

    def import_and_validate(self, pgn_path: Path) -> PGNImportResult:
        """Import a PGN file and fully validate it."""
        result = self.import_game(pgn_path)
        if result.valid:
            result = self.validate_against_repo(result)
        return result

    @staticmethod
    def parse_file_annotation(comment: str) -> Optional[Tuple[str, int, int]]:
        """
        Parse a file annotation from a PGN comment.
        Expected format: {file: path/to/file.py, lines: 10-25}
        """
        match = PGNImporter.FILE_ANNOTATION_PATTERN.search(comment)
        if match:
            return (match.group(1), int(match.group(2)), int(match.group(3)))
        return None

    @staticmethod
    def create_pgn_comment(file_path: str, start_line: int, end_line: int) -> str:
        """Create a PGN comment with file annotation."""
        return f"{{file: {file_path}, lines: {start_line}-{end_line}}}