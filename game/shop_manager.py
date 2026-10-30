import random

from config.settings import (
    ARMY_UPGRADE_PRICE,
    PIECE_PRICE,
    RELIC_PRICE,
    REROLL_PRICE,
    SHOP_PIECE_KINDS,
)
from game.army_manager import ArmyManager


class ShopManager:
    def __init__(self, rng: random.Random, catalog: tuple[str, ...] = ()) -> None:
        self.rng = rng
        self.catalog = tuple(catalog)
        self.piece_kind = SHOP_PIECE_KINDS[0]
        self.piece_sold = False
        self.army_sold = False
        self.relic_id: str | None = None
        self.relic_sold = False
        self.relic_enabled = False
        self.offer_serial = 0
        self.roll()

    def roll(self, owned_ids: set[str] | None = None) -> None:
        self.offer_serial = getattr(self, "offer_serial", 0) + 1
        self.piece_kind = self.rng.choice(SHOP_PIECE_KINDS)
        self.piece_sold = False
        self.army_sold = False
        owned = owned_ids or set()
        choices = [relic_id for relic_id in self.catalog if relic_id not in owned]
        if choices:
            self.relic_id = self.rng.choice(choices)
            self.relic_sold = False
            self.relic_enabled = True
        else:
            self.relic_id = None
            self.relic_sold = True
            self.relic_enabled = False

    def begin_visit(self, owned_ids: set[str] | None = None) -> None:
        self.roll(owned_ids)

    def buy_piece(self, gold: int, army: ArmyManager) -> tuple[int, str | None]:
        if self.piece_sold:
            return gold, "Sold out"
        if gold < PIECE_PRICE:
            return gold, "Not enough gold"
        army.create(self.piece_kind)
        self.piece_sold = True
        return gold - PIECE_PRICE, None

    def buy_relic(self, gold: int) -> tuple[int, str | None]:
        if self.relic_id is None or self.relic_sold:
            return gold, "Sold out"
        if gold < RELIC_PRICE:
            return gold, "Not enough gold"
        self.relic_sold = True
        return gold - RELIC_PRICE, None

    def buy_army(self, gold: int, army: ArmyManager) -> tuple[int, str | None]:
        if self.army_sold:
            return gold, "Sold out"
        if gold < ARMY_UPGRADE_PRICE:
            return gold, "Not enough gold"
        army.increase_capacity()
        self.army_sold = True
        return gold - ARMY_UPGRADE_PRICE, None

    def reroll(self, gold: int, owned_ids: set[str] | None = None) -> tuple[int, str | None]:
        if gold < REROLL_PRICE:
            return gold, "Not enough gold"
        self.roll(owned_ids)
        return gold - REROLL_PRICE, None
