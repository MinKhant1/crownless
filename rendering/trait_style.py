from config.settings import TRAIT_HIGH_READABILITY


class TraitStyle:
    def __init__(self) -> None:
        self.strong = TRAIT_HIGH_READABILITY

    def toggle(self) -> None:
        self.strong = not self.strong


trait_style = TraitStyle()
