from game.relics.relic_registry import register_effect


@register_effect("banner")
class BannerEffect:
    def __init__(self, owned, definition) -> None:
        self.owned = owned
        self.definition = definition

    def on_acquired(self, context) -> None:
        if self.owned.state.get("applied"):
            return
        steps = int(self.definition.parameters.get("capacity", 1))
        for _step in range(steps):
            context.run.army.increase_capacity()
        self.owned.state["applied"] = True

    def register(self, dispatcher, context) -> None:
        return None
