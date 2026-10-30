class TraitContext:
    def __init__(self, relic_context) -> None:
        self._context = relic_context

    @property
    def run(self):
        return self._context.run

    @property
    def board(self):
        return self._context.board

    @property
    def rules(self):
        return self._context.rules
