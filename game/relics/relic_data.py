from dataclasses import dataclass, field
from pathlib import Path


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
        parameters={"once": True},
    ),
    RelicDef(
        id="castle_wall",
        name="Castle Wall",
        art="castle_wall.png",
        flavor_text="Stone does not bargain.",
        description="Allied pieces behind a Rook cannot be captured.",
        effect_id="castle_wall",
        trigger="passive",
    ),
    RelicDef(
        id="chain_fuse",
        name="Chain Fuse",
        art="chain_fuse.png",
        flavor_text="One spark, and the whole line remembers fire.",
        description="When an Explosive piece dies, adjacent Explosive pieces also explode.",
        effect_id="chain_fuse",
        trigger="on_death",
    ),
    RelicDef(
        id="collectors_crown",
        name="Collector's Crown",
        art="collector_crown.png",
        flavor_text="He who holds a little of all may choose once more.",
        description="At battle's end, gain 1 Shop Reroll for each different piece type on the board.",
        effect_id="collectors_crown",
        trigger="on_battle_end",
    ),
    RelicDef(
        id="conversion",
        name="Conversion",
        art="conversion.png",
        flavor_text="Absolved, it rises to walk beside you.",
        description="The first piece your Bishop captures joins the battle as a Ghost.",
        effect_id="conversion",
        trigger="on_capture",
        parameters={"once_per_battle": True, "trait": "ghost"},
    ),
    RelicDef(
        id="crowns_blessing",
        name="Crown's Blessing",
        art="crowns_blessing.png",
        flavor_text="Even uncrowned, a king's shadow blesses.",
        description="At battle's start, one piece in front of the King becomes a random Special Piece.",
        effect_id="crowns_blessing",
        trigger="on_battle_start",
        parameters={"traits": ("golden", "wanted", "explosive", "wooden")},
    ),
    RelicDef(
        id="first_blood",
        name="First Blood",
        art="first_blood.png",
        flavor_text="Fortune favours the first blade drawn.",
        description="The piece that makes the first capture may move one additional turn.",
        effect_id="first_blood",
        trigger="on_capture",
        parameters={"once_per_battle": True},
    ),
    RelicDef(
        id="flawless_victory",
        name="Flawless Victory",
        art="flawless_victory.png",
        flavor_text="No grave dug. No coin spared.",
        description="Gain 3 Gold if you win without losing a piece.",
        effect_id="flawless_victory",
        trigger="on_battle_end",
        parameters={"gold": 3},
    ),
    RelicDef(
        id="graveyard",
        name="Graveyard",
        art="graveyard.png",
        flavor_text="The earth returns what it cannot keep, though less than it took.",
        description="The first Special Piece you lose returns as a Normal Piece.",
        effect_id="graveyard",
        trigger="on_death",
        parameters={"once_per_battle": True},
    ),
    RelicDef(
        id="recruitment",
        name="Recruitment",
        art="recruitment.png",
        flavor_text="Kneel, and serve a truer king.",
        description="The first enemy you capture becomes yours.",
        effect_id="recruitment",
        trigger="on_capture",
        parameters={"once_per_battle": True},
    ),
    RelicDef(
        id="royal_promotion",
        name="Royal Promotion",
        art="royal_promotion.png",
        flavor_text="The humblest who endure are first remembered.",
        description="One random surviving Pawn becomes a Special Piece.",
        effect_id="royal_promotion",
        trigger="on_battle_end",
        parameters={"traits": ("golden", "wanted", "explosive", "wooden")},
    ),
    RelicDef(
        id="squire",
        name="Squire",
        art="squire.png",
        flavor_text="Where the knight rides, the boy follows.",
        description="When a Knight captures, a Pawn appears directly behind it.",
        effect_id="squire",
        trigger="on_capture",
    ),
    RelicDef(
        id="banner",
        name="Banner",
        art="banner.png",
        flavor_text="Raise it high, and more shall come.",
        description="+1 Army Size.",
        effect_id="banner",
        trigger="on_acquire",
        parameters={"capacity": 1},
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


def front_key(relic: RelicDef) -> str:
    return f"relic_front_{Path(relic.art).stem}"
