from dataclasses import dataclass


@dataclass(frozen=True)
class TraitDef:
    id: str
    name: str
    description: str


TRAITS: tuple[TraitDef, ...] = (
    TraitDef("golden", "Golden", "Earn +2 Gold if this piece survives the battle."),
    TraitDef("wanted", "Wanted", "Effect coming soon."),
    TraitDef("explosive", "Explosive", "Effect coming soon."),
    TraitDef("ghost", "Ghost", "Temporary piece. Disappears after battle."),
    TraitDef("wooden", "Wooden", "A piece that captures this cannot move for 2 turns."),
)

TRAIT_IDS: tuple[str, ...] = tuple(trait.id for trait in TRAITS)

TRAIT_SHORT = {
    "golden": "GLD",
    "wanted": "WNT",
    "explosive": "EXP",
    "ghost": "GHO",
    "wooden": "WDN",
}


def trait_by_id(trait_id: str | None) -> TraitDef | None:
    if trait_id is None:
        return None
    for trait in TRAITS:
        if trait.id == trait_id:
            return trait
    return None


def trait_name(trait_id: str | None) -> str:
    trait = trait_by_id(trait_id)
    if trait is None:
        return ""
    return trait.name
