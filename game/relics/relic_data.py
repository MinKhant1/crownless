from dataclasses import dataclass, field


@dataclass(frozen=True)
class RelicDef:
    id: str
    name: str
    art: str
    flavor_text: str
    description: str
    effect_id: str
    trigger: str
    parameters: dict = field(default_factory=dict)
    rarity: str = "common"
    in_shop: bool = True


RELICS: tuple[RelicDef, ...] = (
    RelicDef(
        id="blood_contract",
        name="Blood Contract",
        art="blood_contract.png",
        flavor_text="Signed in red. Paid in kind.",
        description="Sacrifice a piece. One random piece becomes a random Special Piece.",
        effect_id="blood_contract",
        trigger="on_activate",
        parameters={},
        rarity="common",
    ),
    RelicDef(
        id="recruitment",
        name="Recruitment",
        art="recruitment.png",
        flavor_text="The fallen take our colors.",
        description="When your piece captures an enemy piece, the captured piece joins your side.",
        effect_id="recruitment",
        trigger="on_capture",
        parameters={},
        rarity="common",
    ),
    RelicDef(
        id="conversion",
        name="Conversion",
        art="conversion.png",
        flavor_text="One soul, and the bishop is satisfied.",
        description="The first enemy piece your Bishop captures each battle joins as a Ghost.",
        effect_id="conversion",
        trigger="on_capture",
        parameters={},
        rarity="common",
    ),
    RelicDef(
        id="gold_charm",
        name="Gold Charm",
        art="gold_charm.png",
        flavor_text="Victory leaves a coin in the cup.",
        description="After a victory, gain 1 gold.",
        effect_id="gold_charm",
        trigger="on_battle_end",
        parameters={"gold": 1},
        rarity="common",
        in_shop=False,
    ),
)


def relic_by_id(relic_id: str) -> RelicDef | None:
    for relic in RELICS:
        if relic.id == relic_id:
            return relic
    return None


def shop_relic_ids() -> tuple[str, ...]:
    return tuple(relic.id for relic in RELICS if relic.in_shop)
