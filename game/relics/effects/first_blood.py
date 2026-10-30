from game.relics.events import BATTLE_START, CAPTURE_RESOLVED, visual_trigger
from game.relics.relic_registry import register_effect


@register_effect("first_blood")
class FirstBloodEffect:
    def __init__(self, owned, definition) -> None:
        self.owned = owned
        self.definition = definition
        self.context = None

    def on_acquired(self, context) -> None:
        self.owned.state.setdefault("used_this_battle", False)

    def register(self, dispatcher, context) -> None:
        self.context = context
        dispatcher.subscribe(BATTLE_START, self._reset, priority=12)
        dispatcher.subscribe(CAPTURE_RESOLVED, self._on_capture, priority=8)

    def _reset(self, _event) -> None:
        self.owned.state["used_this_battle"] = False

    def _on_capture(self, event) -> None:
        if self.owned.state.get("used_this_battle") or self.context is None:
            return
        payload = event.payload
        if payload.get("capturing_color") != "white" or payload.get("captured_piece_color") != "black":
            return
        game = self.context.game
        if game is None:
            return
        self.owned.state["used_this_battle"] = True
        game.hold_turn = True
        game.bonus_piece_id = payload.get("capturing_piece_id")
        square = payload.get("destination_square")
        if square is not None:
            self.context.flash(square[0], square[1], (196, 48, 42))
        visual_trigger(self.context.dispatcher, self.owned.instance_id, "First Blood")
