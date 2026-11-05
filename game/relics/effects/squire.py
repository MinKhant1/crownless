from game.board import in_bounds
from game.relics.events import CAPTURE_RESOLVED, visual_trigger
from game.relics.relic_context import copy_index
from game.relics.relic_registry import register_effect


@register_effect("squire")
class SquireEffect:
    def __init__(self, owned, definition) -> None:
        self.owned = owned
        self.definition = definition
        self.context = None

    def on_acquired(self, context) -> None:
        return None

    def register(self, dispatcher, context) -> None:
        self.context = context
        dispatcher.subscribe(CAPTURE_RESOLVED, self._on_capture, priority=24)

    def _on_capture(self, event) -> None:
        if self.context is None:
            return
        payload = event.payload
        if payload.get("capturing_color") != "white" or payload.get("capturing_kind") != "knight":
            return
        if payload.get("captured_piece_color") != "black":
            return
        col, row = payload["destination_square"]
        # the first Squire fills the square directly behind the knight; each extra copy adds a pawn
        # on the next free square behind it, diagonally left then right
        if copy_index(event, "squire") == 0:
            candidates = [(col, row - 1)]
        else:
            candidates = [(col - 1, row - 1), (col + 1, row - 1)]
        for square in candidates:
            if not in_bounds(*square):
                continue
            spawned = self.context.spawn_ally("pawn", square[0], square[1], None)
            if spawned is None:
                continue
            self.context.flash(square[0], square[1], (220, 196, 120))
            visual_trigger(self.context.dispatcher, self.owned.instance_id, "Squire")
            return
