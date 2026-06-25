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
    highlight_squares: set[chess.Square] | None = None,
) -> str:
    """Render the board as a colored string for terminal output.

    Args:
        board: The chess board to render.
        last_move: The last move played (to highlight from/to squares).
        legal_moves: Set of squares that are legal move destinations.
        highlight_squares: Additional squares to highlight (e.g., selected piece).

    Returns:
        A string with ANSI escape codes for colored terminal output.
    """
    if legal_moves is None:
        legal_moves = set()
    if highlight_squares is None:
        highlight_squares = set()

    lines: list[str] = []
    # Column labels
    col_labels = '  a  b  c  d  e  f  g  h'
    lines.append(col_labels)
    lines.append('  ' + '-' * 33)

    for rank in range(7, -1, -1):
        row = f'{rank + 1} |'
        for file in range(8):
            square = chess.square(file, rank)
            piece = board.piece_at(square)
            is_light = square_color(square)
            bg = COLOR_WHITE_SQUARE if is_light else COLOR_BLACK_SQUARE

            # Determine if this square should be highlighted
            if last_move:
                if square == last_move.from_square or square == last_move.to_square:
                    bg = COLOR_LAST_MOVE
            if square in legal_moves:
                bg = COLOR_LEGAL_MOVE
            if square in highlight_squares:
                bg = COLOR_HIGHLIGHT

            if piece:
                symbol = get_piece_symbol(piece)
                fg = COLOR_WHITE_PIECE if piece.color else COLOR_BLACK_PIECE
                row += f'{bg}{fg} {symbol} {COLOR_RESET}'
            else:
                if is_light:
                    row += f'{bg}   {COLOR_RESET}'
                else:
                    row += f'{bg}   {COLOR_RESET}'
        row += f'| {rank + 1}'
        lines.append(row)

    lines.append('  ' + '-' * 33)
    lines.append(col_labels)
    return '\n'.join(lines)


def render_move(move: chess.Move, board: chess.Board) -> str:
    """Render a move in algebraic notation with piece symbols.

    Args:
        move: The move to render.
        board: The board state before the move (for disambiguation).

    Returns:
        A string like '♘c3' or '♙e4'.
    """
    piece = board.piece_at(move.from_square)
    if piece:
        symbol = get_piece_symbol(piece)
        # Use UCI-like notation for simplicity
        uci = move.uci()
        return f'{symbol}{uci}'
    return move.uci()


def render_game_info(game_info: dict) -> str:
    """Render game metadata like players, date, result, etc."""
    lines: list[str] = []
    for key, value in game_info.items():
        lines.append(f'{key}: {value}')
    return '\n'.join(lines)


def render_promotion_choices() -> str:
    """Render a prompt for promotion piece selection."""
    return 'Promote to: [Q]ueen, [R]ook, [B]ishop, [K]night: '
