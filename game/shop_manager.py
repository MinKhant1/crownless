import random

from config.settings import (
    ARMY_UPGRADE_PRICE,
    PIECE_COLLECTION_PRICE,
    PIECE_PRICE,
    RELIC_COLLECTION_PRICE,
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
        self.relic_collection_sold = False
        self.piece_collection_sold = False
        self.relic_collection_claimed = False
        self.piece_collection_claimed = False
        self.relic_choices: list[str] | None = None
        self.piece_choices: list[str] | None = None
        self.collection_open: str | None = None
        self.collection_pick: int | None = None
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
        self.relic_collection_sold = False
        self.piece_collection_sold = False
        self.relic_collection_claimed = False
        self.piece_collection_claimed = False
        self.relic_choices = None
        self.piece_choices = None
        self.collection_open = None
        self.collection_pick = None
        self.roll(owned_ids)

    def unclaimed_collection(self) -> str | None:
        if self.relic_choices and not self.relic_collection_claimed:
            return "relic"
        if self.piece_choices and not self.piece_collection_claimed:
            return "piece"
        return None

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

    def buy_relic_collection(self, gold: int, catalog: tuple[str, ...], owned_ids: set[str] | None = None) -> tuple[int, str | None]:
        if self.relic_collection_sold or self.relic_choices:
            return gold, "Sold out"
        if gold < RELIC_COLLECTION_PRICE:
            return gold, "Not enough gold"
        blocked = set(owned_ids or ())
        if self.relic_id and not self.relic_sold:
            blocked.add(self.relic_id)
        pool = [relic_id for relic_id in catalog if relic_id not in blocked]
        if not pool:
            return gold, "Sold out"
        self.relic_choices = self.rng.sample(pool, min(3, len(pool)))
        self.relic_collection_sold = True
        self.relic_collection_claimed = False
        self.collection_open = "relic"
        self.collection_pick = None
        return gold - RELIC_COLLECTION_PRICE, None

    def buy_piece_collection(self, gold: int) -> tuple[int, str | None]:
        if self.piece_collection_sold or self.piece_choices:
            return gold, "Sold out"
        if gold < PIECE_COLLECTION_PRICE:
            return gold, "Not enough gold"
        kinds = list(SHOP_PIECE_KINDS)
        self.piece_choices = self.rng.sample(kinds, min(3, len(kinds)))
        self.piece_collection_sold = True
        self.piece_collection_claimed = False
        self.collection_open = "piece"
        self.collection_pick = None
        return gold - PIECE_COLLECTION_PRICE, None

    def reopen_collection(self, kind: str) -> bool:
        if kind == "relic" and self.relic_choices and not self.relic_collection_claimed:
            self.collection_open = "relic"
            return True
        if kind == "piece" and self.piece_choices and not self.piece_collection_claimed:
            self.collection_open = "piece"
            return True
        return False

    def take_relic_choice(self) -> str | None:
        if self.collection_open != "relic" or not self.relic_choices or self.relic_collection_claimed:
            return None
        if self.collection_pick is None or not 0 <= self.collection_pick < len(self.relic_choices):
            return None
        relic_id = self.relic_choices[self.collection_pick]
        self.relic_collection_claimed = True
        self.collection_open = None
        self.collection_pick = None
        return relic_id

    def take_piece_choice(self) -> str | None:
        if self.collection_open != "piece" or not self.piece_choices or self.piece_collection_claimed:
            return None
        if self.collection_pick is None or not 0 <= self.collection_pick < len(self.piece_choices):
            return None
        kind = self.piece_choices[self.collection_pick]
        self.piece_collection_claimed = True
        self.collection_open = None
        self.collection_pick = None
        return kind
