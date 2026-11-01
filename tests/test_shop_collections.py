import unittest

import pygame

from config.settings import PIECE_COLLECTION_PRICE, RELIC_COLLECTION_PRICE, REROLL_PRICE
from game.run_state import RunState
from rendering.shop_layout import build_shop_layout
from rendering.shop_offers import ShopOffers


class CollectionShopTests(unittest.TestCase):
    def test_relic_chest_keeps_three_choices_through_reroll_and_close(self):
        run = RunState.new(seed=8)
        run.gold = 40
        notice = run.buy_relic_collection()
        self.assertIsNone(notice)
        self.assertEqual(run.gold, 40 - RELIC_COLLECTION_PRICE)
        choices = list(run.shop.relic_choices)
        self.assertEqual(len(choices), 3)
        self.assertEqual(len(set(choices)), 3)
        self.assertEqual(run.shop.collection_open, "relic")
        run.shop.collection_open = None
        self.assertIsNone(run.reroll_shop())
        self.assertEqual(run.gold, 40 - RELIC_COLLECTION_PRICE - REROLL_PRICE)
        self.assertEqual(run.shop.relic_choices, choices)
        self.assertTrue(run.shop.reopen_collection("relic"))
        self.assertEqual(run.buy_relic_collection(), "Sold out")
        self.assertEqual(run.gold, 40 - RELIC_COLLECTION_PRICE - REROLL_PRICE)
        run.shop.collection_pick = 1
        self.assertIsNone(run.confirm_collection())
        self.assertTrue(run.relics.owns(choices[1]))
        self.assertFalse(run.relics.owns(choices[0]))
        self.assertFalse(run.relics.owns(choices[2]))
        self.assertIsNone(run.shop.collection_open)
        self.assertTrue(run.shop.relic_collection_claimed)

    def test_piece_chest_adds_one_piece_and_rejects_a_second_buy(self):
        run = RunState.new(seed=9)
        run.gold = PIECE_COLLECTION_PRICE - 1
        self.assertEqual(run.buy_piece_collection(), "Not enough gold")
        self.assertEqual(run.gold, PIECE_COLLECTION_PRICE - 1)
        self.assertIsNone(run.shop.piece_choices)
        run.gold = PIECE_COLLECTION_PRICE
        before = len(run.army.pieces)
        self.assertIsNone(run.buy_piece_collection())
        self.assertEqual(run.gold, 0)
        choices = list(run.shop.piece_choices)
        self.assertEqual(len(choices), 3)
        run.shop.collection_pick = 0
        self.assertIsNone(run.confirm_collection())
        self.assertEqual(len(run.army.pieces), before + 1)
        self.assertEqual(run.army.pieces[-1].kind, choices[0])
        run.gold = 30
        self.assertEqual(run.buy_piece_collection(), "Sold out")
        self.assertEqual(run.gold, 30)

    def test_army_upgrade_buy_appears_only_after_the_card_is_selected(self):
        pygame.font.init()
        run = RunState.new(seed=12)
        run.gold = 40
        layout = build_shop_layout(1280, 900)
        offers = ShopOffers()
        offers.update(0, run, layout)
        rect = offers.art_rect(layout, "army_size")
        self.assertIsNone(offers.buy_rect(run, layout, "army_size"))
        offers.on_motion(run, rect.center, layout)
        self.assertEqual(offers.hovered, "army_size")
        self.assertIsNone(offers.buy_rect(run, layout, "army_size"))
        offers.on_left_down(rect.center, run, layout)
        offers.on_left_up(rect.center, run, layout)
        self.assertEqual(offers.selected, "army_size")
        button = offers.buy_rect(run, layout, "army_size")
        self.assertIsNotNone(button)
        offers.on_left_down(button.center, run, layout)
        offers.on_left_up(button.center, run, layout)
        self.assertEqual(run.army.capacity, 6)
        self.assertTrue(run.shop.army_sold)
        self.assertIsNone(offers.selected)
