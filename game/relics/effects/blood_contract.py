from dataclasses import dataclass

from game.relics.events import RELIC_ACTIVATED, GameEvent
from game.relics.relic_registry import register_effect
from game.traits import TRAIT_IDS


PREP_PHASES = ("preview", "deployment")


@dataclass
class ActivationResult:
    ok: bool
    message: str
    sacrificed_kind: str = ""
    sacrificed_id: int = 0
    target_kind: str = ""
    target_id: int = 0
    trait_id: str = ""


def _eligible(context) -> list:
    pieces = [piece for piece in context.run.army.pieces if piece.color == "white" and piece.kind != "king"]
    pieces.sort(key=lambda piece: piece.id)
    return pieces


@register_effect("blood_contract")
class BloodContractEffect:
    def __init__(self, owned, definition) -> None:
        self.owned = owned
        self.definition = definition

    def on_acquired(self, context) -> None:
        self.owned.state.setdefault("spent", False)

    def register(self, dispatcher, context) -> None:
        return None

    def can_activate(self, context) -> tuple[bool, str]:
        if self.owned.state.get("spent"):
            return False, "Already used"
        if context.run.phase not in PREP_PHASES:
            return False, "Only before battle"
        if len(_eligible(context)) < 2:
            return False, "Need two pieces besides the King"
        return True, ""

    def activate(self, context, piece_id: int | None = None) -> ActivationResult:
        allowed, message = self.can_activate(context)
        if not allowed:
            return ActivationResult(False, message)
        eligible = _eligible(context)
        sacrifice = next((piece for piece in eligible if piece.id == piece_id), None)
        if sacrifice is None:
            if piece_id is not None and context.run.army.king() is not None and context.run.army.king().id == piece_id:
                return ActivationResult(False, "The King cannot be sacrificed")
            return ActivationResult(False, "Choose a piece")
        pool = [piece for piece in eligible if piece.id != sacrifice.id]
        target = context.rng.choice(pool)
        trait_id = context.rng.choice(TRAIT_IDS)
        removed = context.remove_owned(sacrifice.id)
        if removed is None:
            return ActivationResult(False, "Choose a piece")
        if not context.run.traits.assign_trait(target.id, trait_id, overwrite=True):
            return ActivationResult(False, "Choose a piece")
        self.owned.state["spent"] = True
        context.dispatcher.publish(
            GameEvent(RELIC_ACTIVATED, {"relic_id": self.definition.id, "instance_id": self.owned.instance_id})
        )
        return ActivationResult(
            True,
            "The contract is signed.",
            sacrificed_kind=removed.kind,
            sacrificed_id=removed.id,
            target_kind=target.kind,
            target_id=target.id,
            trait_id=trait_id,
        )
