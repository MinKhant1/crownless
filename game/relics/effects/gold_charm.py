from game.relics.events import BATTLE_END, visual_trigger
from game.relics.relic_registry import register_effect


@register_effect("gold_charm")
class GoldCharmEffect:
    def __init__(self, owned, definition) -> None:
        self.owned = owned
        self.definition = definition
        self.context = None

    def on_acquired(self, context) -> None:
        return None

    def register(self, dispatcher, context) -> None:
        self.context = context
        dispatcher.subscribe(BATTLE_END, self._on_battle_end, priority=40)

    def _on_battle_end(self, event) -> None:
        if event.payload.get("outcome") != "victory" or self.context is None:
            return
        bonus = int(self.definition.parameters.get("gold", 1))
        self.context.run.gold += bonus
        visual_trigger(self.context.dispatcher, self.owned.instance_id)
