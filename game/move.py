from dataclasses import dataclass


@dataclass(frozen=True)
class Move:
    from_col: int
    from_row: int
    to_col: int
    to_row: int
    promotion: str | None = None
