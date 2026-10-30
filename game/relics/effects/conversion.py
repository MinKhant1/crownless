from game.relics.events import BATTLE_START, CAPTURE_RESOLVED
from game.relics.relic_registry import register_effect


@register_effect("conversion")
class ConversionEffect:
    def __init__(self, owned, definition) -> None:
        self.owned = owned
        self.definition = definition
        self.context = None

    def on_acquired(self, context) -> None:
        self.owned.state.setdefault("used_this_battle", False)

    def register(self, dispatcher, context) -> None:
        self.context = context
        dispatcher.subscribe(BATTLE_START, self._on_battle_start, priority=20)
        dispatcher.subscribe(CAPTURE_RESOLVED, self._on_capture, priority=20)

    def _on_battle_start(self, _event) -> None:
        self.owned.state["used_this_battle"] = False

    def _on_capture(self, event) -> None:
        if self.owned.state.get("used_this_battle"):
            return
        payload = event.payload
        if payload.get("capturing_color") != "white" or payload.get("capturing_kind") != "bishop":
            return
        if payload.get("captured_piece_color") != "black":
            return
        self.owned.state["used_this_battle"] = True
        if self.context is None:
            return
        destination = payload["destination_square"]
        options = self.context.empty_neighbors(destination[0], destination[1])
        if not options:
            return
        col, row = self.context.rng.choice(options)
        self.context.spawn_ally(payload["captured_piece_type"], col, row, "ghost")
