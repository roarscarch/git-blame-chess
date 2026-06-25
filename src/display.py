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
    highlighted_squares: set[chess.Square] | None = None,
) -> str:
    """Render a chess board with colored squares and Unicode pieces.

    Args:
        board: The chess board to render.
        last_move: The last move played, to highlight from/to squares.
        legal_moves: Set of squares that are legal moves for the current player.
        highlighted_squares: Additional squares to highlight.

    Returns:
        A string representation of the board with ANSI color codes.
    """
    lines = []
    # Column labels
    header = '  ' + ' '.join(chr(ord('a') + col) for col in range(8))
    lines.append(f'{COLOR_COORD_LABEL}{header}{COLOR_RESET}')

    for rank in range(7, -1, -1):
        row = f'{COLOR_COORD_LABEL}{rank + 1}{COLOR_RESET} '
        for file in range(8):
            square = rank * 8 + file
            piece = board.piece_at(square)
            is_light = square_color(square)

            # Determine background color
            bg = COLOR_WHITE_SQUARE if is_light else COLOR_BLACK_SQUARE
            if last_move and (square == last_move.from_square or square == last_move.to_square):
                bg = COLOR_LAST_MOVE
            elif legal_moves and square in legal_moves:
                bg = COLOR_LEGAL_MOVE
            elif highlighted_squares and square in highlighted_squares:
                bg = COLOR_HIGHLIGHT

            if piece:
                symbol = get_piece_symbol(piece)
                fg = COLOR_WHITE_PIECE if piece.color == chess.WHITE else COLOR_BLACK_PIECE
                cell = f'{bg}{fg} {symbol} {COLOR_RESET}'
            else:
                cell = f'{bg}   {COLOR_RESET}'
            row += cell
        row += f'{COLOR_COORD_LABEL}{rank + 1}{COLOR_RESET}'
        lines.append(row)

    lines.append(f'{COLOR_COORD_LABEL}{header}{COLOR_RESET}')
    return '\
'.join(lines)


def render_move(move: chess.Move) -> str:
    """Render a chess move in algebraic notation."""
    return board.san(move) if 'board' in locals() else str(move)


def render_board_plain(board: chess.Board) -> str:
    """Render a chess board without colors (for logging or non-ANSI output)."""
    lines = []
    for rank in range(7, -1, -1):
        row = f'{rank + 1} '
        for file in range(8):
            square = rank * 8 + file
            piece = board.piece_at(square)
            if piece:
                symbol = PIECE_SYMBOLS[piece.piece_type][piece.color]
                row += f'{symbol}