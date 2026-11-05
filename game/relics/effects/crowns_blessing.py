from game.relics.events import BATTLE_START, visual_trigger
from game.relics.relic_context import copy_index
from game.relics.relic_registry import register_effect


@register_effect("crowns_blessing")
class CrownsBlessingEffect:
    def __init__(self, owned, definition) -> None:
        self.owned = owned
        self.definition = definition
        self.context = None

    def on_acquired(self, context) -> None:
        return None

    def register(self, dispatcher, context) -> None:
        self.context = context
        dispatcher.subscribe(BATTLE_START, self._bless, priority=30)

    def _bless(self, event) -> None:
        if self.context is None:
            return
        board = self.context.board
        if board is None:
            return
        king = board.king("white")
        if king is None or king.col is None or king.row is None:
            return
        # the first Blessing takes the piece in front of the King; each extra copy blesses another piece
        # beside it: front-left, front-right, then either side of the King
        col, row = king.col, king.row
        if copy_index(event, "crowns_blessing") == 0:
            squares = [(col, row + 1)]
        else:
            squares = [(col - 1, row + 1), (col + 1, row + 1), (col - 1, row), (col + 1, row)]
        blessed = event.payload.setdefault("_blessed", set())
        piece = None
        for square_col, square_row in squares:
            candidate = board.piece_at(square_col, square_row)
            if candidate is not None and candidate.color == "white" and candidate.id not in blessed and candidate.kind != "king":
                piece = candidate
                break
        if piece is None:
            return
        blessed.add(piece.id)
        traits = self.definition.parameters.get("traits") or ("golden", "wanted", "explosive", "wooden")
        trait_id = self.context.rng.choice(tuple(traits))
        if not self.context.run.traits.assign_trait(piece.id, trait_id, overwrite=True):
            return
        self.context.flash(piece.col, piece.row, (230, 190, 70))
        visual_trigger(self.context.dispatcher, self.owned.instance_id, "Crown's Blessing")
