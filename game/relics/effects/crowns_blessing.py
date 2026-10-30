from game.relics.events import BATTLE_START, visual_trigger
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

    def _bless(self, _event) -> None:
        if self.context is None:
            return
        board = self.context.board
        if board is None:
            return
        king = board.king("white")
        if king is None or king.col is None or king.row is None:
            return
        piece = board.piece_at(king.col, king.row + 1)
        if piece is None or piece.color != "white":
            return
        traits = self.definition.parameters.get("traits") or ("golden", "wanted", "explosive", "wooden")
        trait_id = self.context.rng.choice(tuple(traits))
        if not self.context.run.traits.assign_trait(piece.id, trait_id, overwrite=True):
            return
        self.context.flash(piece.col, piece.row, (230, 190, 70))
        visual_trigger(self.context.dispatcher, self.owned.instance_id, "Crown's Blessing")
