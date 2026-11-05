from game.board import in_bounds
from game.relics.events import BATTLE_START, visual_trigger
from game.relics.relic_registry import register_effect


def protected_squares(board, depth: int = 1) -> set[tuple[int, int]]:
    """Allied pieces behind a rook. One Castle Wall shields the first piece down the rook's file;
    each extra copy shields one more piece further back (depth = number of copies)."""
    found: set[tuple[int, int]] = set()
    if board is None:
        return found
    for piece in board.pieces:
        if piece.color != "white" or piece.kind != "rook" or piece.row is None or piece.col is None:
            continue
        row = piece.row - 1
        shielded = 0
        while row >= 1 and in_bounds(piece.col, row) and shielded < depth:
            occupant = board.piece_at(piece.col, row)
            if occupant is None:
                row -= 1
                continue
            if occupant.color != "white":
                break
            found.add((occupant.col, occupant.row))
            shielded += 1
            row -= 1
    return found


def _blocks(board, move) -> bool:
    return (move.to_col, move.to_row) in protected_squares(board)


@register_effect("castle_wall")
class CastleWallEffect:
    def __init__(self, owned, definition) -> None:
        self.owned = owned
        self.definition = definition
        self.context = None

    def on_acquired(self, context) -> None:
        return None

    def register(self, dispatcher, context) -> None:
        self.context = context
        dispatcher.subscribe(BATTLE_START, self._arm, priority=8)

    def _blocks(self, board, move) -> bool:
        depth = 1 if self.context is None else max(1, self.context.run.relics.count("castle_wall"))
        return (move.to_col, move.to_row) in protected_squares(board, depth)

    def _arm(self, _event) -> None:
        rules = None if self.context is None else self.context.rules
        if rules is None:
            return
        if not any(isinstance(getattr(block, "__self__", None), CastleWallEffect) for block in rules.capture_blocks):
            rules.capture_blocks.append(self._blocks)  # one wall check for all copies; copies deepen it
        visual_trigger(self.context.dispatcher, self.owned.instance_id, "Castle Wall")
