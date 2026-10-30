from game.relics.events import BATTLE_END, BATTLE_START, CAPTURE_RESOLVED, visual_trigger
from game.relics.relic_registry import register_effect


@register_effect("flawless_victory")
class FlawlessVictoryEffect:
    def __init__(self, owned, definition) -> None:
        self.owned = owned
        self.definition = definition
        self.context = None

    def on_acquired(self, context) -> None:
        self.owned.state.setdefault("lost_piece", False)

    def register(self, dispatcher, context) -> None:
        self.context = context
        dispatcher.subscribe(BATTLE_START, self._reset, priority=12)
        dispatcher.subscribe(CAPTURE_RESOLVED, self._on_capture, priority=50)
        dispatcher.subscribe(BATTLE_END, self._on_end, priority=30)

    def _reset(self, _event) -> None:
        self.owned.state["lost_piece"] = False

    def _on_capture(self, event) -> None:
        if event.payload.get("captured_piece_color") == "white":
            self.owned.state["lost_piece"] = True

    def _on_end(self, event) -> None:
        if event.payload.get("outcome") != "victory" or self.context is None:
            return
        if self.owned.state.get("lost_piece"):
            return
        bonus = int(self.definition.parameters.get("gold", 3))
        self.context.run.gold += bonus
        visual_trigger(self.context.dispatcher, self.owned.instance_id, f"Flawless Victory +{bonus}")
