from config.settings import PROMOTION_KIND
from game.board import Board, in_bounds
from game.move import Move
from game.piece import Piece

KNIGHT_OFFSETS = (
    (1, 2),
    (2, 1),
    (2, -1),
    (1, -2),
    (-1, -2),
    (-2, -1),
    (-2, 1),
    (-1, 2),
)
KING_OFFSETS = (
    (1, 0),
    (-1, 0),
    (0, 1),
    (0, -1),
    (1, 1),
    (1, -1),
    (-1, 1),
    (-1, -1),
)
BISHOP_DIRS = ((1, 1), (1, -1), (-1, 1), (-1, -1))
ROOK_DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def pawn_direction(color: str) -> int:
    if color == "white":
        return 1
    return -1


def final_rank(color: str) -> int:
    if color == "white":
        return 6
    return 1


def _promotion(piece: Piece, row: int) -> str | None:
    if piece.kind == "pawn" and row == final_rank(piece.color):
        return PROMOTION_KIND
    return None


def _move(piece: Piece, col: int, row: int) -> Move:
    return Move(piece.col, piece.row, col, row, _promotion(piece, row))


def _can_capture(board: Board, occupant: Piece, color: str) -> bool:
    if occupant.color == color:
        return False
    if occupant.kind == "king" and not board.capture_kings:
        return False
    return True


def _ray(board: Board, col: int, row: int, directions: tuple[tuple[int, int], ...]) -> list[tuple[int, int]]:
    squares: list[tuple[int, int]] = []
    for delta_col, delta_row in directions:
        next_col = col + delta_col
        next_row = row + delta_row
        while in_bounds(next_col, next_row):
            squares.append((next_col, next_row))
            if board.piece_at(next_col, next_row) is not None:
                break
            next_col += delta_col
            next_row += delta_row
    return squares


def _offsets(col: int, row: int, offsets: tuple[tuple[int, int], ...]) -> list[tuple[int, int]]:
    squares: list[tuple[int, int]] = []
    for delta_col, delta_row in offsets:
        next_col = col + delta_col
        next_row = row + delta_row
        if in_bounds(next_col, next_row):
            squares.append((next_col, next_row))
    return squares


def pawn_attacks(piece: Piece) -> list[tuple[int, int]]:
    direction = pawn_direction(piece.color)
    squares: list[tuple[int, int]] = []
    for delta_col in (-1, 1):
        col = piece.col + delta_col
        row = piece.row + direction
        if in_bounds(col, row):
            squares.append((col, row))
    return squares


def attacks_of(board: Board, piece: Piece) -> list[tuple[int, int]]:
    if piece.kind == "pawn":
        return pawn_attacks(piece)
    if piece.kind == "knight":
        return _offsets(piece.col, piece.row, KNIGHT_OFFSETS)
    if piece.kind == "king":
        return _offsets(piece.col, piece.row, KING_OFFSETS)
    if piece.kind == "bishop":
        return _ray(board, piece.col, piece.row, BISHOP_DIRS)
    if piece.kind == "rook":
        return _ray(board, piece.col, piece.row, ROOK_DIRS)
    if piece.kind == "queen":
        return _ray(board, piece.col, piece.row, BISHOP_DIRS + ROOK_DIRS)
    return []


def attacked_squares(board: Board, color: str) -> set[tuple[int, int]]:
    squares: set[tuple[int, int]] = set()
    for piece in board.pieces:
        if piece.color == color:
            squares.update(attacks_of(board, piece))
    return squares


def _slide_moves(board: Board, piece: Piece, directions: tuple[tuple[int, int], ...]) -> list[Move]:
    moves: list[Move] = []
    for delta_col, delta_row in directions:
        col = piece.col + delta_col
        row = piece.row + delta_row
        while in_bounds(col, row):
            occupant = board.piece_at(col, row)
            if occupant is None:
                moves.append(_move(piece, col, row))
            else:
                if _can_capture(board, occupant, piece.color):
                    moves.append(_move(piece, col, row))
                break
            col += delta_col
            row += delta_row
    return moves


def _step_moves(board: Board, piece: Piece, offsets: tuple[tuple[int, int], ...]) -> list[Move]:
    moves: list[Move] = []
    for col, row in _offsets(piece.col, piece.row, offsets):
        occupant = board.piece_at(col, row)
        if occupant is None or _can_capture(board, occupant, piece.color):
            moves.append(_move(piece, col, row))
    return moves


def _pawn_moves(board: Board, piece: Piece) -> list[Move]:
    moves: list[Move] = []
    direction = pawn_direction(piece.color)
    forward_row = piece.row + direction
    if in_bounds(piece.col, forward_row) and board.piece_at(piece.col, forward_row) is None:
        moves.append(_move(piece, piece.col, forward_row))
        jump_row = piece.row + (2 * direction)
        if (
            not piece.has_moved
            and in_bounds(piece.col, jump_row)
            and board.piece_at(piece.col, jump_row) is None
        ):
            moves.append(_move(piece, piece.col, jump_row))
    for col, row in pawn_attacks(piece):
        occupant = board.piece_at(col, row)
        if occupant is not None and _can_capture(board, occupant, piece.color):
            moves.append(_move(piece, col, row))
    return moves


def pseudo_moves_for(board: Board, piece: Piece) -> list[Move]:
    if piece.kind == "pawn":
        return _pawn_moves(board, piece)
    if piece.kind == "knight":
        return _step_moves(board, piece, KNIGHT_OFFSETS)
    if piece.kind == "king":
        return _step_moves(board, piece, KING_OFFSETS)
    if piece.kind == "bishop":
        return _slide_moves(board, piece, BISHOP_DIRS)
    if piece.kind == "rook":
        return _slide_moves(board, piece, ROOK_DIRS)
    if piece.kind == "queen":
        return _slide_moves(board, piece, BISHOP_DIRS + ROOK_DIRS)
    return []


def pseudo_legal_moves(board: Board, color: str) -> list[Move]:
    moves: list[Move] = []
    for piece in board.pieces:
        if piece.color == color:
            moves.extend(pseudo_moves_for(board, piece))
    moves.sort(key=lambda move: (move.from_col, move.from_row, move.to_col, move.to_row, move.promotion or ""))
    return moves

