from game.relics.events import CAPTURE_RESOLVED
from game.relics.relic_registry import register_effect


@register_effect("recruitment")
class RecruitmentEffect:
    def __init__(self, owned, definition) -> None:
        self.owned = owned
        self.definition = definition
        self.context = None

    def on_acquired(self, context) -> None:
        return None

    def register(self, dispatcher, context) -> None:
        self.context = context
        dispatcher.subscribe(CAPTURE_RESOLVED, self._on_capture, priority=10)

    def _on_capture(self, event) -> None:
        payload = event.payload
        if payload.get("capturing_color") != "white" or payload.get("captured_piece_color") != "black":
            return
        if self.context is None:
            return
        origin = payload["origin_square"]
        self.context.spawn_ally(payload["captured_piece_type"], origin[0], origin[1], None)
