import unittest
from pathlib import Path
import tempfile
import os

from git import Repo
import chess

from src.game import Game, CommitMove
from src.models import path_to_square, get_piece_for_path


class TestGame(unittest.TestCase):
    """Tests for the Game class."""

    def setUp(self):
        """Create a temporary git repository with some commits."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.temp_dir.name) / "test_repo"
        self.repo_path.mkdir(parents=True)
        self.repo = Repo.init(self.repo_path)
        # Create initial commit
        readme = self.repo_path / "README.md"
        readme.write_text("# Test Repo")
        self.repo.index.add(["README.md"])
        self.repo.index.commit("Initial commit")
        # Create second commit
        main_file = self.repo_path / "main.py"
        main_file.write_text("print('hello')")
        self.repo.index.add(["main.py"])
        self.repo.index.commit("Add main.py")
        # Create third commit
        main_file.write_text("print('hello world')\nprint('goodbye')")
        self.repo.index.add(["main.py"])
        self.repo.index.commit("Update main.py")

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_from_repo_initialization(self):
        """Test that Game.from_repo creates a valid game with correct number of moves."""
        game = Game.from_repo(self.repo_path)
        self.assertIsNotNone(game)
        self.assertEqual(len(game.moves), 3)  # 3 commits
        self.assertEqual(game.repo_path, self.repo_path)

    def test_from_repo_branch(self):
        """Test that Game.from_repo with explicit branch works."""
        game = Game.from_repo(self.repo_path, branch="master")
        self.assertIsNotNone(game)
        self.assertEqual(len(game.moves), 3)

    def test_from_repo_invalid_path(self):
        """Test that Game.from_repo raises FileNotFoundError for invalid path."""
        with self.assertRaises(FileNotFoundError):
            Game.from_repo(Path("/nonexistent/path"))

    def test_from_repo_no_commits(self):
        """Test that Game.from_repo returns empty game for repo with no commits."""
        empty_repo = Path(self.temp_dir.name) / "empty_repo"
        empty_repo.mkdir(parents=True)
        Repo.init(empty_repo)
        # No commits yet
        game = Game.from_repo(empty_repo)
        self.assertIsNotNone(game)
        self.assertEqual(len(game.moves), 0)

    def test_commit_move_creation(self):
        """Test that CommitMove objects are created correctly."""
        game = Game.from_repo(self.repo_path)
        move = game.moves[0]
        self.assertIsInstance(move, CommitMove)
        self.assertEqual(move.commit.message.strip(), "Initial commit")
        self.assertEqual(move.commit.hexsha, self.repo.head.commit.hexsha)

    def test_commit_move_chess_move(self):
        """Test that commit moves generate valid chess moves."""
        game = Game.from_repo(self.repo_path)
        for move in game.moves:
            self.assertIsNotNone(move.chess_move)
            self.assertIsInstance(move.chess_move, chess.Move)
            self.assertIn(move.chess_move.from_square, chess.SQUARES)
            self.assertIn(move.chess_move.to_square, chess.SQUARES)

    def test_board_after_moves(self):
        """Test that applying moves results in a valid board state."""
        game = Game.from_repo(self.repo_path)
        board = chess.Board()
        for move in game.moves:
            self.assertTrue(move.chess_move in board.legal_moves,
                            f"Move {move.chess_move} is not legal on board:\n{board}")
            board.push(move.chess_move)
        self.assertFalse(board.is_game_over())
        self.assertIsNotNone(board.fen())

    def test_path_to_square_deterministic(self):
        """Test that path_to_square produces consistent results."""
        path1 = "src/main.py"
        path2 = "src/main.py"
        square1 = path_to_square(path1)
        square2 = path_to_square(path2)
        self.assertEqual(square1, square2)

    def test_path_to_square_unique(self):
        """Test that different paths produce different squares (likely)."""
        path1 = "a.py"
        path2 = "b.py"
        square1 = path_to_square(path1)
        square2 = path_to_square(path2)
        self.assertNotEqual(square1, square2)

    def test_get_piece_for_path_known_extension(self):
        """Test that known extensions return correct piece type."""
        self.assertEqual(get_piece_for_path("main.py"), chess.KNIGHT)
        self.assertEqual(get_piece_for_path("test.js"), chess.KNIGHT)
        self.assertEqual(get_piece_for_path("styles.css"), chess.ROOK)
        self.assertEqual(get_piece_for_path("readme.md"), chess.PAWN)
        self.assertEqual(get_piece_for_path("data.json"), chess.BISHOP)
        self.assertEqual(get_piece_for_path("template.html"), chess.ROOK)

    def test_get_piece_for_path_unknown_extension(self):
        """Test that unknown extensions return default piece."""
        from src.models import DEFAULT_PIECE
        self.assertEqual(get_piece_for_path("unknown.xyz"), DEFAULT_PIECE)

    def test_commit_move_square_mapping(self):
        """Test that commit moves map to squares based on file paths."""
        game = Game.from_repo(self.repo_path)
        for move in game.moves:
            # For each file changed, the move should be from a square derived from the file
            for file_path in move.files_changed:
                square = path_to_square(file_path)
                self.assertIn(square, chess.SQUARES)


if __name__ == "__main__":
    unittest.main()