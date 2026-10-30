from game.traits.trait_manager import TraitManager
from game.traits.trait_registry import TRAIT_IDS, TRAIT_SHORT, TRAITS, TraitDef, trait_by_id, trait_name


def register_trait_handlers(dispatcher, context) -> None:
    from game.traits.effects import explosive, ghost, golden, wanted, wooden
    from game.traits.trait_context import TraitContext

    traits = TraitContext(context)
    golden.register(dispatcher, traits)
    wanted.register(dispatcher, traits)
    explosive.register(dispatcher, traits)
    ghost.register(dispatcher, traits)
    wooden.register(dispatcher, traits)


__all__ = [
    "TRAIT_IDS",
    "TRAIT_SHORT",
    "TRAITS",
    "TraitDef",
    "TraitManager",
    "register_trait_handlers",
    "trait_by_id",
    "trait_name",
]
