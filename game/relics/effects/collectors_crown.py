from game.relics.events import BATTLE_END, visual_trigger
from game.relics.relic_registry import register_effect


@register_effect("collectors_crown")
class CollectorsCrownEffect:
    def __init__(self, owned, definition) -> None:
        self.owned = owned
        self.definition = definition
        self.context = None

    def on_acquired(self, context) -> None:
        return None

    def register(self, dispatcher, context) -> None:
        self.context = context
        dispatcher.subscribe(BATTLE_END, self._on_end, priority=35)

    def _on_end(self, event) -> None:
        if event.payload.get("outcome") != "victory" or self.context is None:
            return
        board = self.context.board
        if board is None:
            return
        kinds = {piece.kind for piece in board.pieces if piece.color == "white"}
        if not kinds:
            return
        self.context.run.shop_rerolls += len(kinds)
        visual_trigger(self.context.dispatcher, self.owned.instance_id, f"Collector's Crown +{len(kinds)}")
