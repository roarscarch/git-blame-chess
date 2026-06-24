from __future__ import annotations

import chess

# Unicode chess piece symbols
PIECE_SYMBOLS = {
    chess.PAWN: {True: '♙', False: '♟'},
    chess.KNIGHT: {True: '♘', False: '♞'},
    chess.BISHOP: {True: '♗', False: '♝'},
    chess.ROOK: {True: '♖', False: '♜'},
    chess.QUEEN: {True: '♕', False: '♛'},
    chess.KING: {True: '♔', False: '♚'},
}

# ANSI color codes for terminal output
COLOR_RESET = '\033[0m'
COLOR_WHITE_SQUARE = '\033[48;5;250m'
COLOR_BLACK_SQUARE = '\033[48;5;240m'
COLOR_WHITE_PIECE = '\033[38;5;15m'
COLOR_BLACK_PIECE = '\033[38;5;0m'
COLOR_COORD_LABEL = '\033[38;5;8m'
COLOR_HIGHLIGHT = '\033[48;5;226m'  # yellow background
COLOR_LAST_MOVE = '\033[48;5;46m'   # green background
COLOR_LEGAL_MOVE = '\033[48;5;214m' # orange background


def get_piece_symbol(piece: chess.Piece) -> str:
    """Get the Unicode symbol for a chess piece."""
    return PIECE_SYMBOLS[piece.piece_type][piece.color]


def square_color(square: chess.Square) -> bool:
    """Return True if square is light, False if dark."""
    return (square // 8 + square % 8) % 2 == 0


def render_board(
    board: chess.Board,
    last_move: chess.Move | None = None,
    legal_moves: set[chess.Square] | None = None,
    selected_square: chess.Square | None = None,
    flipped: bool = False,
) -> str:
    """
    Render the chess board as a colored string for terminal output.

    Args:
        board: The chess board to render.
        last_move: The last move made, to highlight from/to squares.
        legal_moves: Set of squares that are legal moves from the selected square.
        selected_square: The currently selected square (for highlighting).
        flipped: If True, flip the board so black is at the bottom.

    Returns:
        A string with ANSI color codes for terminal display.
    """
    lines: list[str] = []
    ranks = range(7, -1, -1) if not flipped else range(0, 8)
    files = range(0, 8) if not flipped else range(7, -1, -1)

    # Top coordinate label
    coord_line = '  '
    for f in files:
        coord_line += f'{COLOR_COORD_LABEL} {chess.FILE_NAMES[f]} {COLOR_RESET}'
    lines.append(coord_line)

    for r in ranks:
        row: list[str] = []
        # Rank label on the left
        row.append(f'{COLOR_COORD_LABEL}{chess.RANK_NAMES[r]}{COLOR_RESET} ')
        for f in files:
            square = chess.square(f, r)
            piece = board.piece_at(square)
            is_light_square = square_color(square)

            # Determine background color
            if selected_square is not None and square == selected_square:
                bg = COLOR_HIGHLIGHT
            elif last_move is not None and square in (last_move.from_square, last_move.to_square):
                bg = COLOR_LAST_MOVE
            elif legal_moves is not None and square in legal_moves:
                bg = COLOR_LEGAL_MOVE
            else:
                bg = COLOR_WHITE_SQUARE if is_light_square else COLOR_BLACK_SQUARE

            if piece is None:
                # Empty square
                row.append(f'{bg}   {COLOR_RESET}')
            else:
                symbol = get_piece_symbol(piece)
                fg = COLOR_WHITE_PIECE if piece.color == chess.WHITE else COLOR_BLACK_PIECE
                row.append(f'{bg}{fg} {symbol} {COLOR_RESET}')
        lines.append(''.join(row))
        # Rank label on the right
        lines[-1] += f' {COLOR_COORD_LABEL}{chess.RANK_NAMES[r]}{COLOR_RESET}'

    # Bottom coordinate label
    coord_line = '  '
    for f in files:
        coord_line += f'{COLOR_COORD_LABEL} {chess.FILE_NAMES[f]} {COLOR_RESET}'
    lines.append(coord_line)

    return '\n'.join(lines)


def render_move_history(moves: list[chess.Move], board: chess.Board | None = None) -> str:
    """
    Render a list of moves in algebraic notation.

    Args:
        moves: List of chess moves.
        board: Optional board to use for disambiguation (if None, creates a new board).

    Returns:
        A string with move numbers and algebraic notation.
    """
    if board is None:
        board = chess.Board()
    lines: list[str] = []
    for i, move in enumerate(moves):
        san = board.san(move)
        board.push(move)
        if i % 2 == 0:
            move_number = i // 2 + 1
            lines.append(f'{move_number}. {san}')
        else:
            lines[-1] += f' {san}'
    return ' '.join(lines)


def render_game_status(board: chess.Board) -> str:
    """
    Render the game status (checkmate, stalemate, etc.) as a string.

    Args:
        board: The chess board to evaluate.

    Returns:
        A string describing the game status.
    """
    if board.is_checkmate():
        winner = 'White' if board.turn == chess.BLACK else 'Black'
        return f'Checkmate! {winner} wins.'
    elif board.is_stalemate():
        return 'Stalemate! The game is a draw.'
    elif board.is_insufficient_material():
        return 'Draw due to insufficient material.'
    elif board.is_check():
        return 'Check!'
    else:
        turn = 'White' if board.turn == chess.WHITE else 'Black'
        return f'{turn} to move.'


def render_full_display(
    board: chess.Board,
    moves: list[chess.Move],
    last_move: chess.Move | None = None,
    legal_moves: set[chess.Square] | None = None,
    selected_square: chess.Square | None = None,
    flipped: bool = False,
) -> str:
    """
    Render the full display including board, move history, and game status.

    Args:
        board: The chess board to render.
        moves: List of moves played so far.
        last_move: The last move made.
        legal_moves: Set of legal move target squares.
        selected_square: The currently selected square.
        flipped: If True, flip the board.

    Returns:
        A string with the complete display.
    """
    lines: list[str] = []
    lines.append('=== Git Blame Chess ===')
    lines.append('')
    lines.append(render_board(board, last_move, legal_moves, selected_square, flipped))
    lines.append('')
    lines.append('Move History:')
    lines.append(render_move_history(moves))
    lines.append('')
    lines.append(render_game_status(board))
    return '\n'.join(lines)