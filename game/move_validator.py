from config.settings import opposite
from game.board import Board
from game.move import Move
from game.move_generator import attacked_squares, pseudo_legal_moves


def in_check(board: Board, color: str) -> bool:
    king = board.king(color)
    if king is None:
        return False
    return (king.col, king.row) in attacked_squares(board, opposite(color))


def is_legal_move(board: Board, move: Move, color: str) -> bool:
    clone = board.copy()
    clone.apply_move(move)
    return not in_check(clone, color)


def legal_moves(board: Board, color: str) -> list[Move]:
    moves = pseudo_legal_moves(board, color)
    if not board.enforce_check:
        return moves
    return [move for move in moves if is_legal_move(board, move, color)]
