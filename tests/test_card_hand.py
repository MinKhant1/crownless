import unittest

import pygame

from config.settings import PIECE_PRICE, RELIC_PRICE
from game.run_state import RunState
from rendering.card_motion import preview_order
from rendering.layout import build_layout
from rendering.relic_bar_renderer import RelicBar
from rendering.relic_flip import shop_reveal
from rendering.relic_tooltip_renderer import draw_relic_tooltip
from rendering.shop_layout import build_shop_layout
from rendering.shop_piece_hand import ShopPieceHand
from rendering.shop_relic_hand import ShopRelicHand
from game.relics.relic_data import relic_by_id


class CardOrderTests(unittest.TestCase):
    def test_preview_inserts_the_dragged_card_between_neighbors(self):
        ids = ["banner", "squire", "recruitment", "conversion"]
        preview = preview_order(ids, "conversion", 50, [0, 100, 200, 300])
        self.assertEqual(preview, ["banner", "conversion", "squire", "recruitment"])

    def test_drag_reorders_display_without_touching_effects(self):
        run = RunState.new(seed=21)
        owned = [run.relics.acquire(relic_id) for relic_id in ("banner", "squire", "recruitment", "conversion")]
        self.assertEqual([item.relic_id for item in owned], ["banner", "squire", "recruitment", "conversion"])
        bar = RelicBar()
        layout = build_layout(1280, 900)
        bar.update(0, run, layout)
        slots = {slot.owned.relic_id: slot for slot in bar.placements(run, layout, 0)}
        squire_before = slots["squire"].drawn.centerx
        conversion = slots["conversion"]
        start = conversion.drawn.center
        bar.on_left_down(start, run, layout, now=0)
        bar.on_motion(run, (start[0] + 3, start[1]), layout, now=0, held=True)
        self.assertIsNone(bar.dragged_card_id)
        bar.on_motion(run, (start[0] + 16, start[1] - 4), layout, now=0, held=True)
        self.assertEqual(bar.dragged_card_id, conversion.owned.instance_id)
        between = (
            (slots["banner"].rest.centerx + slots["squire"].rest.centerx) // 2,
            slots["banner"].rest.centery,
        )
        bar.on_motion(run, between, layout, now=0, held=True)
        bar.update(0.04, run, layout)
        partial = next(slot.drawn.centerx for slot in bar.placements(run, layout, 0) if slot.owned.relic_id == "squire")
        bar.update(1, run, layout)
        settled = next(slot.drawn.centerx for slot in bar.placements(run, layout, 0) if slot.owned.relic_id == "squire")
        self.assertGreater(partial, squire_before)
        self.assertGreater(settled, partial)
        bar.on_left_up(run, between, layout, layout.window, now=0)
        self.assertIsNone(bar.dragged_card_id)
        self.assertIsNone(bar.selected_card_id)
        self.assertEqual(
            [item.relic_id for item in bar.ordered(run)],
            ["banner", "conversion", "squire", "recruitment"],
        )
        self.assertEqual(
            [item.relic_id for item in run.relics.owned],
            ["banner", "squire", "recruitment", "conversion"],
        )
        self.assertFalse(owned[3].state.get("used_this_battle", False))
        saved = list(run.relic_display_order)
        run.phase = "shop"
        run.phase = "battle"
        self.assertEqual(run.relic_display_order, saved)
        self.assertEqual([item.instance_id for item in bar.ordered(run)], saved)

    def test_dragged_card_stays_on_screen_and_captures_the_pointer(self):
        run = RunState.new(seed=22)
        run.relics.acquire("banner")
        bar = RelicBar()
        layout = build_layout(1280, 900)
        bar.update(0, run, layout)
        slot = bar.placements(run, layout, 0)[0]
        board = layout.square_rect(2, 2).center
        bar.on_left_down(slot.drawn.center, run, layout, now=0)
        self.assertTrue(bar.pointer_captured)
        bar.on_motion(run, board, layout, now=0, held=True)
        bar.update(1, run, layout)
        self.assertTrue(bar.dragging)
        self.assertTrue(bar.hits(board, run, layout, now=0))
        for card in bar.placements(run, layout, 0):
            self.assertGreaterEqual(card.drawn.left, 6)
            self.assertGreaterEqual(card.drawn.top, 6)
            self.assertLessEqual(card.drawn.right, layout.window[0] - 6)
            self.assertLessEqual(card.drawn.bottom, layout.window[1] - 6)
        bar.on_motion(run, (-400, -400), layout, now=0, held=True)
        bar.update(1, run, layout)
        for card in bar.placements(run, layout, 0):
            self.assertGreaterEqual(card.drawn.left, 6)
            self.assertGreaterEqual(card.drawn.top, 6)
        bar.on_left_up(run, board, layout, layout.window, now=0)
        self.assertIsNone(bar.selected_card_id)
        self.assertFalse(bar.pointer_captured)

    def test_overlapping_cards_give_the_pointer_to_the_top_card(self):
        run = RunState.new(seed=23)
        for relic_id in ("banner", "squire", "recruitment", "conversion", "first_blood"):
            run.relics.acquire(relic_id)
        bar = RelicBar()
        layout = build_layout(1280, 900)
        bar.update(0, run, layout)
        slots = bar.placements(run, layout, 0)
        point = (slots[1].rest.left + 1, slots[1].rest.centery)
        self.assertTrue(slots[0].rest.collidepoint(point))
        self.assertEqual(bar._slot_at(point, run, layout, 0).owned.instance_id, slots[1].owned.instance_id)
        bar.selected_card_id = slots[0].owned.instance_id
        bar.update(1, run, layout)
        slots = bar.placements(run, layout, 0)
        overlap = slots[0].drawn.clip(slots[1].drawn)
        if overlap.w > 2 and overlap.h > 2:
            self.assertEqual(bar._slot_at(overlap.center, run, layout, 0).owned.instance_id, slots[0].owned.instance_id)


class ShopHandTests(unittest.TestCase):
    def setUp(self):
        pygame.font.init()
        shop_reveal.progress = 1.0
        shop_reveal.key = None

    def test_buy_stays_hidden_until_the_card_is_clicked(self):
        run = RunState.new(seed=31)
        run.gold = 20
        offered = run.shop.relic_id
        hand = ShopRelicHand()
        layout = build_shop_layout(1280, 900)
        window = (1280, 900)
        hand.update(0, run, layout, window)
        self.assertIsNone(hand.buy_rect(run, layout, window))
        slot = hand.slots(run, layout, window)[0]
        hand.on_motion(run, slot.rest.center, layout, window, held=False)
        self.assertEqual(hand.hovered_card_id, offered)
        self.assertIsNone(hand.selected_card_id)
        self.assertIsNone(hand.buy_rect(run, layout, window))
        hand.on_left_down(slot.rest.center, run, layout, window)
        hand.on_left_up(slot.rest.center, run, layout, window)
        self.assertEqual(hand.selected_card_id, offered)
        self.assertIsNotNone(hand.buy_rect(run, layout, window))
        self.assertEqual(run.gold, 20)
        self.assertFalse(run.relics.owns(offered))

    def test_buy_purchases_once_and_insufficient_gold_does_not(self):
        run = RunState.new(seed=32)
        run.gold = 20
        offered = run.shop.relic_id
        hand = ShopRelicHand()
        layout = build_shop_layout(1280, 900)
        window = (1280, 900)
        hand.update(0, run, layout, window)
        slot = hand.slots(run, layout, window)[0]
        hand.on_left_down(slot.rest.center, run, layout, window)
        hand.on_left_up(slot.rest.center, run, layout, window)
        button = hand.buy_rect(run, layout, window)
        hand.on_left_down(button.center, run, layout, window)
        hand.on_left_up(button.center, run, layout, window)
        self.assertEqual(run.gold, 20 - RELIC_PRICE)
        self.assertTrue(run.relics.owns(offered))
        self.assertIsNone(hand.selected_card_id)
        self.assertIsNone(hand.buy_rect(run, layout, window))
        hand.on_left_down(button.center, run, layout, window)
        hand.on_left_up(button.center, run, layout, window)
        self.assertEqual(run.gold, 20 - RELIC_PRICE)

        poor = RunState.new(seed=33)
        poor.gold = 6
        poor_offer = poor.shop.relic_id
        poor_hand = ShopRelicHand()
        poor_hand.update(0, poor, layout, window)
        poor_slot = poor_hand.slots(poor, layout, window)[0]
        poor_hand.on_left_down(poor_slot.rest.center, poor, layout, window)
        poor_hand.on_left_up(poor_slot.rest.center, poor, layout, window)
        label, enabled = poor_hand.buy_caption(poor)
        self.assertEqual(label, "Not enough Gold")
        self.assertFalse(enabled)
        poor_button = poor_hand.buy_rect(poor, layout, window)
        poor_hand.on_left_down(poor_button.center, poor, layout, window)
        poor_hand.on_left_up(poor_button.center, poor, layout, window)
        self.assertEqual(poor.gold, 6)
        self.assertFalse(poor.relics.owns(poor_offer))

    def test_dragging_a_shop_card_does_not_purchase_it(self):
        run = RunState.new(seed=34)
        run.gold = 20
        offered = run.shop.relic_id
        hand = ShopRelicHand()
        layout = build_shop_layout(1280, 900)
        window = (1280, 900)
        hand.update(0, run, layout, window)
        slot = hand.slots(run, layout, window)[0]
        start = slot.drawn.center
        hand.on_left_down(start, run, layout, window)
        hand.on_motion(run, (start[0] + 40, start[1]), layout, window, held=True)
        self.assertEqual(hand.dragged_card_id, offered)
        outside = (8, 8)
        hand.on_left_up(outside, run, layout, window)
        self.assertEqual(run.gold, 20)
        self.assertFalse(run.relics.owns(offered))
        self.assertEqual(run.shop.relic_id, offered)
        self.assertIsNone(hand.selected_card_id)
        hand.update(1, run, layout, window)
        returned = hand.slots(run, layout, window)[0]
        self.assertAlmostEqual(returned.drawn.centerx, returned.rest.centerx, delta=2)


class ShopPieceHandTests(unittest.TestCase):
    def setUp(self):
        pygame.font.init()

    def _hand(self, seed: int, gold: int):
        run = RunState.new(seed=seed)
        run.gold = gold
        hand = ShopPieceHand()
        layout = build_shop_layout(1280, 900)
        window = (1280, 900)
        hand.update(0, run, layout, window)
        return run, hand, layout, window

    def test_hover_lifts_the_piece_without_showing_buy(self):
        run, hand, layout, window = self._hand(41, 20)
        card = layout.cards[0]
        piece = hand.rest_rect(run, layout)
        self.assertLess(piece.w, card.w)
        self.assertLess(piece.h, card.h)
        self.assertFalse(piece.collidepoint(card.midbottom))
        self.assertIsNone(hand.buy_rect(run, layout, window))
        self.assertFalse(hand.on_left_down(card.midbottom, run, layout, window))
        rest_bottom = hand.drawn_rect(run, layout, window).bottom
        hand.on_motion(run, piece.center, layout, window, held=False)
        hand.update(0.05, run, layout, window)
        rising = hand.drawn_rect(run, layout, window)
        hand.update(1, run, layout, window)
        settled = hand.drawn_rect(run, layout, window)
        self.assertLess(rising.bottom, rest_bottom)
        self.assertLess(settled.bottom, rising.bottom)
        self.assertLess(settled.w, card.w)
        self.assertFalse(hand.selected)
        self.assertIsNone(hand.buy_rect(run, layout, window))
        self.assertFalse(run.shop.piece_sold)
        self.assertEqual(run.gold, 20)

    def test_click_selects_the_piece_and_buy_click_purchases_once(self):
        run, hand, layout, window = self._hand(42, 20)
        piece = hand.rest_rect(run, layout)
        before = len(run.army.pieces)
        self.assertIsNone(hand.buy_rect(run, layout, window))
        self.assertFalse(hand.on_left_down(layout.buys[0].center, run, layout, window))
        self.assertEqual(run.gold, 20)
        hand.on_left_down(piece.center, run, layout, window)
        hand.on_left_up(piece.center, run, layout, window)
        self.assertTrue(hand.selected)
        self.assertIsNotNone(hand.buy_rect(run, layout, window))
        self.assertEqual(len(run.army.pieces), before)
        button = hand.buy_rect(run, layout, window)
        clear = (piece.centerx, piece.bottom - 6)
        self.assertLess(button.centery, piece.centery)
        self.assertTrue(piece.collidepoint(clear))
        self.assertFalse(button.collidepoint(clear))
        hand.on_left_down(clear, run, layout, window)
        hand.on_left_up(clear, run, layout, window)
        self.assertFalse(hand.selected)
        self.assertIsNone(hand.buy_rect(run, layout, window))
        hand.on_left_down(piece.center, run, layout, window)
        hand.on_left_up(piece.center, run, layout, window)
        buy = hand.buy_rect(run, layout, window).center
        hand.on_left_down(buy, run, layout, window)
        hand.on_left_up(buy, run, layout, window)
        self.assertTrue(run.shop.piece_sold)
        self.assertEqual(run.gold, 20 - PIECE_PRICE)
        self.assertEqual(len(run.army.pieces), before + 1)
        self.assertFalse(hand.on_left_down(buy, run, layout, window))
        self.assertEqual(run.gold, 20 - PIECE_PRICE)

    def test_drag_holds_the_piece_without_buying_it(self):
        run, hand, layout, window = self._hand(43, 20)
        piece = hand.rest_rect(run, layout)
        start = piece.center
        before = len(run.army.pieces)
        hand.on_left_down(start, run, layout, window)
        hand.on_motion(run, (start[0] + 4, start[1]), layout, window, held=True)
        self.assertFalse(hand.dragging)
        hand.on_motion(run, (start[0] + 70, start[1] - 30), layout, window, held=True)
        self.assertTrue(hand.dragging)
        self.assertIsNone(hand.buy_rect(run, layout, window))
        hand.update(1, run, layout, window)
        held = hand.drawn_rect(run, layout, window)
        self.assertGreater(abs(held.centerx - piece.centerx), 40)
        self.assertLess(held.w, layout.cards[0].w)
        hand.on_left_up((start[0] + 70, start[1] - 30), run, layout, window)
        self.assertFalse(hand.dragging)
        self.assertFalse(hand.selected)
        self.assertFalse(run.shop.piece_sold)
        self.assertEqual(len(run.army.pieces), before)
        self.assertEqual(run.gold, 20)
        hand.update(1, run, layout, window)
        home = hand.drawn_rect(run, layout, window)
        self.assertAlmostEqual(home.centerx, piece.centerx, delta=2)

    def test_insufficient_gold_does_not_buy_the_held_piece(self):
        run, hand, layout, window = self._hand(44, PIECE_PRICE - 1)
        piece = hand.rest_rect(run, layout)
        hand.on_left_down(piece.center, run, layout, window)
        hand.on_left_up(piece.center, run, layout, window)
        label, enabled = hand.buy_caption(run)
        self.assertEqual(label, "Not enough Gold")
        self.assertFalse(enabled)
        buy = hand.buy_rect(run, layout, window)
        self.assertIsNotNone(buy)
        hand.on_left_down(buy.center, run, layout, window)
        hand.on_left_up(buy.center, run, layout, window)
        self.assertEqual(run.gold, PIECE_PRICE - 1)
        self.assertFalse(run.shop.piece_sold)


class TooltipDrawTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((64, 64), pygame.HIDDEN)

    def test_tooltip_stays_on_screen_beside_the_card(self):
        screen = pygame.Surface((1280, 900))
        relic = relic_by_id("blood_contract")
        card = pygame.Rect(40, 80, 70, 105)
        panel = draw_relic_tooltip(screen, relic, card, price=7)
        self.assertTrue(screen.get_rect().contains(panel))
        self.assertFalse(panel.collidepoint(card.center))
        self.assertGreater(panel.w, 80)
        self.assertGreater(panel.h, 40)


if __name__ == "__main__":
    unittest.main()
