from game.relics.relic_data import RelicDef


EFFECT_TYPES: dict[str, type] = {}


def register_effect(effect_id: str):
    def wrap(cls):
        EFFECT_TYPES[effect_id] = cls
        return cls

    return wrap


def build_effect(definition: RelicDef, owned):
    cls = EFFECT_TYPES.get(definition.effect_id)
    if cls is None:
        return None
    return cls(owned, definition)
