from __future__ import annotations

import pytest
import chess
from pathlib import Path
from src.game import Game, CommitMove
from src.models import get_piece_for_path, path_to_square


class TestPathToSquare:
    """Tests for path_to_square mapping."""

    def test_deterministic_mapping(self) -> None:
        """Same path always maps to same square."""
        path = "src/main.py"
        square1 = path_to_square(path)
        square2 = path_to_square(path)
        assert square1 == square2

    def test_different_paths_different_squares(self) -> None:
        """Different paths likely produce different squares."""
        squares = {path_to_square(f"file_{i}.txt") for i in range(100)}
        assert len(squares) > 90  # Allow some collisions

    def test_square_in_range(self) -> None:
        """Square must be valid chess square (0-63)."""
        for i in range(50):
            square = path_to_square(f"test_{i}.py")
            assert 0 <= square < 64

    def test_different_extensions_same_name(self) -> None:
        """Files with same name but different extensions map differently."""
        square1 = path_to_square("file.py")
        square2 = path_to_square("file.txt")
        assert square1 != square2


class TestGetPieceForPath:
    """Tests for piece type mapping from file extension."""

    def test_python_file_is_pawn(self) -> None:
        """.py files map to pawn."""
        piece = get_piece_for_path("src/module.py")
        assert piece == chess.PAWN

    def test_java_file_is_knight(self) -> None:
        """.java files map to knight."""
        piece = get_piece_for_path("Main.java")
        assert piece == chess.KNIGHT

    def test_cpp_file_is_bishop(self) -> None:
        """.cpp files map to bishop."""
        piece = get_piece_for_path("utils.cpp")
        assert piece == chess.BISHOP

    def test_js_file_is_rook(self) -> None:
        """.js files map to rook."""
        piece = get_piece_for_path("app.js")
        assert piece == chess.ROOK

    def test_md_file_is_queen(self) -> None:
        """.md files map to queen."""
        piece = get_piece_for_path("README.md")
        assert piece == chess.QUEEN

    def test_unknown_extension_default(self) -> None:
        """Unknown extensions map to default piece (pawn)."""
        piece = get_piece_for_path("data.bin")
        assert piece == chess.PAWN

    def test_no_extension_default(self) -> None:
        """Files without extension map to default."""
        piece = get_piece_for_path("Makefile")
        assert piece == chess.PAWN


class TestCommitMove:
    """Tests for CommitMove creation and validation."""

    def test_create_valid_move(self) -> None:
        """Create a CommitMove with valid parameters."""
        move = CommitMove(
            commit_hash="abc123",
            author="test",
            message="test commit",
            timestamp=1000,
            file_changes={"src/main.py": 5},
            move=chess.Move.from_uci("e2e4"),
        )
        assert move.commit_hash == "abc123"
        assert move.move.uci() == "e2e4"

    def test_move_with_multiple_files(self) -> None:
        """Move can have multiple file changes."""
        move = CommitMove(
            commit_hash="def456",
            author="dev",
            message="multiple files",
            timestamp=2000,
            file_changes={"src/a.py": 3, "src/b.py": 7},
            move=chess.Move.from_uci("d2d4"),
        )
        assert len(move.file_changes) == 2


class TestGameInitialization:
    """Tests for Game class initialization."""

    def test_game_initial_board(self) -> None:
        """Game starts with standard starting position."""
        game = Game()
        assert game.board.fen() == chess.STARTING_FEN
        assert len(game.moves) == 0

    def test_game_with_initial_move(self) -> None:
        """Game can be initialized with a move."""
        move = chess.Move.from_uci("e2e4")
        game = Game(initial_move=move)
        assert len(game.moves) == 1
        assert game.moves[0].move == move

    def test_game_from_repo_nonexistent(self, tmp_path: Path) -> None:
        """Game.from_repo raises error for invalid path."""
        with pytest.raises(Exception):
            Game.from_repo(tmp_path / "nonexistent")


class TestGameMoveApplication:
    """Tests for applying moves to the game."""

    def test_apply_valid_move(self) -> None:
        """Applying a legal move updates the board."""
        game = Game()
        move = chess.Move.from_uci("e2e4")
        commit_move = CommitMove(
            commit_hash="abc",
            author="test",
            message="e4",
            timestamp=1,
            file_changes={"test.py": 1},
            move=move,
        )
        game.apply_move(commit_move)
        assert game.board.piece_at(chess.E4) is not None
        assert game.board.piece_at(chess.E2) is None

    def test_apply_illegal_move_raises(self) -> None:
        """Applying an illegal move raises ValueError."""
        game = Game()
        move = chess.Move.from_uci("e2e5")  # Invalid for pawn
        commit_move = CommitMove(
            commit_hash="abc",
            author="test",
            message="bad move",
            timestamp=1,
            file_changes={"test.py": 1},
            move=move,
        )
        with pytest.raises(ValueError):
            game.apply_move(commit_move)

    def test_undo_move(self) -> None:
        """Undoing a move restores previous board state."""
        game = Game()
        move = chess.Move.from_uci("e2e4")
        commit_move = CommitMove(
            commit_hash="abc",
            author="test",
            message="e4",
            timestamp=1,
            file_changes={"test.py": 1}