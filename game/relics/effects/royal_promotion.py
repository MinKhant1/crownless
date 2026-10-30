from game.relics.events import BATTLE_END, visual_trigger
from game.relics.relic_registry import register_effect


@register_effect("royal_promotion")
class RoyalPromotionEffect:
    def __init__(self, owned, definition) -> None:
        self.owned = owned
        self.definition = definition
        self.context = None

    def on_acquired(self, context) -> None:
        return None

    def register(self, dispatcher, context) -> None:
        self.context = context
        dispatcher.subscribe(BATTLE_END, self._promote, priority=25)

    def _promote(self, event) -> None:
        if event.payload.get("outcome") != "victory" or self.context is None:
            return
        board = self.context.board
        if board is None:
            return
        pawns = [
            piece
            for piece in board.pieces
            if piece.color == "white" and piece.kind == "pawn" and piece.trait != "ghost"
        ]
        if not pawns:
            return
        pawn = self.context.rng.choice(pawns)
        traits = self.definition.parameters.get("traits") or ("golden", "wanted", "explosive", "wooden")
        trait_id = self.context.rng.choice(tuple(traits))
        if not self.context.run.traits.assign_trait(pawn.id, trait_id, overwrite=True):
            return
        if pawn.col is not None and pawn.row is not None:
            self.context.flash(pawn.col, pawn.row, (230, 180, 60))
        visual_trigger(self.context.dispatcher, self.owned.instance_id, "Royal Promotion")
