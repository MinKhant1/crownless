from config.settings import ENEMY_FORMATIONS, ENEMY_ID_START, parse_square
from game.piece import Piece


def spawn_enemies(level: int) -> list[Piece]:
    pieces: list[Piece] = []
    for index, (kind, square) in enumerate(ENEMY_FORMATIONS[level]):
        col, row = parse_square(square)
        pieces.append(Piece(ENEMY_ID_START + index, kind, "black", col, row))
    return pieces


def formation_counts(level: int) -> dict[str, int]:
    counts: dict[str, int] = {}
    for kind, _square in ENEMY_FORMATIONS[level]:
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def describe_counts(counts: dict[str, int]) -> str:
    parts: list[str] = []
    for kind in ("king", "queen", "rook", "bishop", "knight", "pawn"):
        count = counts.get(kind, 0)
        if count <= 0:
            continue
        name = kind.capitalize()
        if count != 1:
            name += "s"
        parts.append(f"{count} {name}")
    return ", ".join(parts)
