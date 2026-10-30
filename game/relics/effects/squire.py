from game.board import in_bounds
from game.relics.events import CAPTURE_RESOLVED, visual_trigger
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
        behind = (col, row - 1)
        if not in_bounds(*behind):
            return
        spawned = self.context.spawn_ally("pawn", behind[0], behind[1], None)
        if spawned is None:
            return
        self.context.flash(behind[0], behind[1], (220, 196, 120))
        visual_trigger(self.context.dispatcher, self.owned.instance_id, "Squire")
