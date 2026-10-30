class RelicEffect:
    def __init__(self, owned, definition) -> None:
        self.owned = owned
        self.definition = definition

    def on_acquired(self, context) -> None:
        return None

    def register(self, dispatcher, context) -> None:
        return None

    def can_activate(self, context) -> tuple[bool, str]:
        return False, "This relic has no activation."

    def activate(self, context, piece_id: int | None = None):
        return None
