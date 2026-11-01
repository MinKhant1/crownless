from dataclasses import dataclass, replace


@dataclass
class Piece:
    id: int
    kind: str
    color: str
    col: int | None = None
    row: int | None = None
    has_moved: bool = False
    trait: str | None = None
    ai_trait: str | None = None

    def copy(self) -> "Piece":
        return replace(self)
