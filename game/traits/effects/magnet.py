from game.move_generator import pawn_direction
from game.relics.events import BATTLE_START
from game.relics.relic_context import NEIGHBORS


def register(dispatcher, context) -> None:
    dispatcher.subscribe(BATTLE_START, lambda event: on_battle_start(event, context), priority=90)


def on_battle_start(event, context) -> None:
    rules = context.rules
    if rules is not None and blocks_backward not in rules.capture_blocks:
        rules.capture_blocks.append(blocks_backward)


def blocks_backward(board, move) -> bool:
    piece = board.piece_at(move.from_col, move.from_row)
    if piece is None or (move.to_row - move.from_row) * pawn_direction(piece.color) >= 0:
        return False
    for delta_col, delta_row in NEIGHBORS:
        near = board.piece_at(move.from_col + delta_col, move.from_row + delta_row)
        if near is not None and near.trait == "magnet" and near.color != piece.color:
            return True
    return False
