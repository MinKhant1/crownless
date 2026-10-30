from game.traits.trait_registry import TRAIT_IDS


class TraitManager:
    def __init__(self, run) -> None:
        self.run = run

    def assign_trait(self, piece_id: int, trait_id: str, overwrite: bool = False) -> bool:
        if trait_id not in TRAIT_IDS:
            return False
        matches = self._matches(piece_id)
        if not matches:
            return False
        current = next((piece.trait for piece in matches if piece.trait), None)
        if current and current != trait_id and not overwrite:
            return False
        for piece in matches:
            piece.trait = trait_id
        return True

    def remove_trait(self, piece_id: int) -> bool:
        matches = self._matches(piece_id)
        if not matches:
            return False
        for piece in matches:
            piece.trait = None
        return True

    def get_trait(self, piece_id: int) -> str | None:
        matches = self._matches(piece_id)
        if not matches:
            return None
        battle = self.run.battle
        if battle is not None:
            live = {id(piece) for piece in battle.game.board.pieces}
            for piece in matches:
                if id(piece) in live:
                    return piece.trait
        return matches[0].trait

    def _matches(self, piece_id: int) -> list:
        found = []
        seen: set[int] = set()
        pools = [self.run.army.pieces, self.run.enemies]
        battle = self.run.battle
        if battle is not None:
            pools.append(battle.game.board.pieces)
        visual = getattr(self.run, "visual_pieces", None)
        if visual:
            pools.append(visual)
        for pool in pools:
            for piece in pool:
                if piece.id != piece_id or id(piece) in seen:
                    continue
                seen.add(id(piece))
                found.append(piece)
        return found
