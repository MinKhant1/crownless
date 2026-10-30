from game.piece import Piece


KIND_ORDER = {"queen": 0, "rook": 1, "bishop": 2, "knight": 3, "pawn": 4}


class ArmyEntry:
    def __init__(self, piece: Piece, pieces: tuple[Piece, ...], status: str) -> None:
        self.piece = piece
        self.pieces = pieces
        self.status = status

    @property
    def count(self) -> int:
        return len(self.pieces)

    def ids(self) -> tuple[int, ...]:
        return tuple(piece.id for piece in self.pieces)


def piece_status(run, piece: Piece) -> str:
    if run.phase in ("battle", "victory", "defeat") and run.battle is not None:
        if any(item.id == piece.id for item in run.battle.game.board.pieces):
            return "Surviving"
        if piece.id in run.deployment.placed:
            return "Captured"
        return "Reserve"
    if piece.id in run.deployment.placed:
        return "Deployed"
    return "Reserve"


def listed_pieces(run) -> list[Piece]:
    pieces = list(run.army.pieces)
    if run.phase not in ("battle", "victory", "defeat") or run.battle is None:
        return pieces
    known = {piece.id for piece in pieces}
    for piece in run.battle.game.board.pieces:
        if piece.color == "white" and piece.id not in known:
            pieces.append(piece)
            known.add(piece.id)
    for piece_id, kind, trait in run.battle_roster:
        if piece_id in known:
            continue
        pieces.append(Piece(piece_id, kind, "white", trait=trait))
        known.add(piece_id)
    return pieces


def sorted_pieces(pieces: list[Piece]) -> list[Piece]:
    kings = sorted((piece for piece in pieces if piece.kind == "king"), key=lambda piece: piece.id)
    rest = [piece for piece in pieces if piece.kind != "king"]
    rest.sort(key=lambda piece: (KIND_ORDER.get(piece.kind, 9), piece.trait or "", piece.id))
    return kings + rest


def army_entries(run) -> list[ArmyEntry]:
    kings: list[ArmyEntry] = []
    groups: list[ArmyEntry] = []
    buckets: dict[tuple[str, str | None, str], ArmyEntry] = {}
    for piece in sorted_pieces(listed_pieces(run)):
        status = piece_status(run, piece)
        if piece.kind == "king":
            kings.append(ArmyEntry(piece, (piece,), status))
            continue
        key = (piece.kind, piece.trait, status)
        current = buckets.get(key)
        if current is None:
            entry = ArmyEntry(piece, (piece,), status)
            buckets[key] = entry
            groups.append(entry)
        else:
            current.pieces = current.pieces + (piece,)
    return kings + groups
