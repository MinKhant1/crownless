from game.relics.events import BATTLE_START, CAPTURE_RESOLVED, visual_trigger
from game.relics.relic_registry import register_effect


@register_effect("recruitment")
class RecruitmentEffect:
    def __init__(self, owned, definition) -> None:
        self.owned = owned
        self.definition = definition
        self.context = None

    def on_acquired(self, context) -> None:
        self.owned.state.setdefault("used_this_battle", False)

    def register(self, dispatcher, context) -> None:
        self.context = context
        dispatcher.subscribe(BATTLE_START, self._reset, priority=20)
        dispatcher.subscribe(CAPTURE_RESOLVED, self._on_capture, priority=10)

    def _reset(self, _event) -> None:
        self.owned.state["used_this_battle"] = False

    def _on_capture(self, event) -> None:
        if self.owned.state.get("used_this_battle") or self.context is None:
            return
        payload = event.payload
        if payload.get("capturing_color") != "white" or payload.get("captured_piece_color") != "black":
            return
        self.owned.state["used_this_battle"] = True
        origin = payload["origin_square"]
        spawned = self.context.spawn_ally(payload["captured_piece_type"], origin[0], origin[1], None)
        if spawned is not None:
            self.context.flash(origin[0], origin[1], (90, 150, 210))
            visual_trigger(self.context.dispatcher, self.owned.instance_id, "Recruitment")
