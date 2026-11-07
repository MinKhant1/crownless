from game.relics.effects.base_effect import RelicEffect
from game.relics.events import BATTLE_START, visual_trigger
from game.relics.relic_registry import register_effect


@register_effect("marching_orders")
class MarchingOrdersEffect(RelicEffect):
    def on_acquired(self, context) -> None:
        if context.board is not None:
            context.board.marching_orders = True

    def register(self, dispatcher, context) -> None:
        self.context = context
        dispatcher.subscribe(BATTLE_START, self._arm, priority=8)

    def _arm(self, _event) -> None:
        if self.context.board is not None:
            self.context.board.marching_orders = True
            visual_trigger(self.context.dispatcher, self.owned.instance_id, "Marching Orders")
