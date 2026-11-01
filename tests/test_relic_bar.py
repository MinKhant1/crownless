import unittest
from pathlib import Path

import pygame

from game.piece import Piece
from game.relics.relic_data import relic_by_id
from game.relics.relic_manager import OwnedRelic
from game.run_state import RunState
from rendering.asset_manager import AssetManager
from rendering.layout import build_layout, square_at
from rendering.relic_bar_renderer import RelicBar, _detail_geometry, card_state, rest_rects
from rendering.relic_tooltip_renderer import tooltip_lines


ROOT = Path(__file__).resolve().parents[1]


def place(run: RunState, piece: Piece, col: int, row: int) -> None:
    assert run.deployment.place(piece, col, row, run.blocked_squares(), run.army.capacity, run.army)


class RelicBarTests(unittest.TestCase):
    def test_empty_inventory_has_no_cards(self):
        run = RunState.new(seed=1)
        bar = RelicBar()
        self.assertEqual(bar.visible(run), [])
        self.assertEqual(bar.ordered(run), [])

    def test_relics_follow_acquisition_order(self):
        run = RunState.new(seed=2)
        bar = RelicBar()
        run.relics.acquire("conversion")
        run.relics.acquire("blood_contract")
        run.relics.acquire("recruitment")
        self.assertEqual(
            [item.relic_id for item in bar.visible(run)],
            ["conversion", "blood_contract", "recruitment"],
        )

    def test_more_than_five_relics_scroll_without_dropping_any(self):
        run = RunState.new(seed=3)
        for relic_id in ("blood_contract", "recruitment", "conversion", "gold_charm"):
            run.relics.acquire(relic_id)
        run.relics.owned.append(OwnedRelic("recruitment", "relic_extra_a", 50))
        run.relics.owned.append(OwnedRelic("conversion", "relic_extra_b", 51))
        bar = RelicBar()
        layout = build_layout(1280, 900)
        self.assertEqual(len(run.relics.owned), 6)
        self.assertEqual(len(bar.visible(run)), 5)
        self.assertEqual(bar.visible(run)[-1].instance_id, "relic_extra_a")
        self.assertTrue(bar.on_wheel(run, layout, layout.relics.center, -1))
        self.assertEqual(bar.visible(run)[0].relic_id, "recruitment")
        self.assertEqual(bar.visible(run)[-1].instance_id, "relic_extra_b")
        self.assertTrue(bar.on_wheel(run, layout, layout.relics.center, 1))
        self.assertEqual(bar.scroll, 0)
        left, right = bar.arrow_rects(layout, len(run.relics.owned))
        self.assertIsNotNone(left)
        self.assertIsNotNone(right)
        bar.scroll = 1
        bar.on_left_down(left.center, run, layout, now=0)
        bar.on_left_up(run, left.center, layout, (1280, 900), now=0)
        self.assertEqual(bar.scroll, 0)
        self.assertEqual(len(run.relics.owned), 6)

    def test_hover_lifts_the_card_and_click_toggles_selection(self):
        run = RunState.new(seed=4)
        owned = run.relics.acquire("recruitment")
        bar = RelicBar()
        layout = build_layout(1280, 900)
        bar.update(0, run, layout)
        slot = bar.placements(run, layout, 0)[0]
        bar.on_motion(run, slot.rest.center, layout, now=0)
        self.assertEqual(bar.hover_id, owned.instance_id)
        self.assertIsNone(bar.selected_card_id)
        bar.update(1, run, layout)
        lifted = bar.placements(run, layout, 0)[0]
        self.assertLessEqual(lifted.drawn.bottom, slot.rest.bottom - 8)
        self.assertGreater(lifted.drawn.h, slot.rest.h)
        bar.on_left_down(slot.rest.center, run, layout, now=0)
        bar.on_left_up(run, slot.rest.center, layout, (1280, 900), now=0)
        self.assertEqual(bar.selected_card_id, owned.instance_id)
        self.assertIsNone(bar.consume_click())
        self.assertIsNone(bar.detail_id)
        bar.on_left_down(slot.rest.center, run, layout, now=0)
        bar.on_left_up(run, slot.rest.center, layout, (1280, 900), now=0)
        self.assertIsNone(bar.selected_card_id)
        self.assertFalse(bar.on_right_click())
        self.assertIsNone(square_at(layout, slot.rest.center))
        board_point = layout.square_rect(0, 1).center
        self.assertIsNotNone(square_at(layout, board_point))
        self.assertFalse(bar.hits(board_point, run, layout, now=0))

    def test_tooltip_uses_the_relic_text(self):
        relic = relic_by_id("blood_contract")
        lines = [text for text, _strong in tooltip_lines(relic)]
        self.assertEqual(lines[0], "Blood Contract")
        self.assertEqual(lines[1], '"Signed in red. Paid in kind."')
        self.assertEqual(lines[2], "Sacrifice a piece. One random piece becomes a random Special Piece.")
        priced = [text for text, _strong in tooltip_lines(relic, price=7)]
        self.assertEqual(priced[-1], "7 Gold")

    def test_used_and_disabled_states_follow_the_relic(self):
        run = RunState.new(seed=5)
        blood = run.relics.acquire("blood_contract")
        self.assertEqual(card_state(run, blood), "active")
        run.phase = "battle"
        self.assertEqual(card_state(run, blood), "disabled")
        blood.state["spent"] = True
        self.assertEqual(card_state(run, blood), "used")
        conversion = run.relics.acquire("conversion")
        king = run.army.king()
        place(run, king, 0, 1)
        run.enemies = []
        self.assertTrue(run.start_battle())
        self.assertEqual(card_state(run, conversion), "active")
        conversion.state["used_this_battle"] = True
        self.assertEqual(card_state(run, conversion), "used")

    def test_detail_activate_goes_through_the_manager(self):
        run = RunState.new(seed=11)
        run.phase = "deployment"
        owned = run.relics.acquire("blood_contract")
        bar = RelicBar()
        bar.detail_id = owned.instance_id
        pawn = next(piece for piece in run.army.pieces if piece.kind == "pawn")
        _panel, _card, pieces, button, _close = _detail_geometry(run, (1280, 900))
        piece_rect = next(rect for piece, rect in pieces if piece.id == pawn.id)
        layout = build_layout(1280, 900)
        bar.on_left_up(run, piece_rect.center, layout, (1280, 900))
        self.assertEqual(bar.detail_piece, pawn.id)
        bar.on_left_up(run, button.center, layout, (1280, 900))
        self.assertTrue(owned.state.get("spent"))
        self.assertIsNone(bar.detail_id)
        target = next(piece for piece in run.army.pieces if piece.trait)
        self.assertIsNotNone(target)

    def test_trigger_flashes_the_relic_not_a_trait(self):
        run = RunState.new(seed=7)
        charm = run.relics.acquire("gold_charm")
        recruited = run.relics.acquire("recruitment")
        bar = RelicBar()
        bar.bind(run)
        king = run.army.king()
        rook = next(piece for piece in run.army.pieces if piece.kind == "rook")
        pawn = next(piece for piece in run.army.pieces if piece.kind == "pawn")
        pawn.trait = "golden"
        run.enemies = [Piece(10001, "pawn", "black", 1, 3)]
        place(run, king, 0, 1)
        place(run, rook, 1, 2)
        place(run, pawn, 2, 1)
        self.assertTrue(run.start_battle())
        run.battle.click(1, 2)
        run.battle.click(1, 3)
        self.assertIn(recruited.instance_id, bar.flashes)
        self.assertNotIn(charm.instance_id, bar.flashes)
        run.battle.evaluate()
        run.finish_victory()
        self.assertIn(charm.instance_id, bar.flashes)
        self.assertEqual(run.gold, 5 + 2 + 3 + 1)
        self.assertEqual(
            [item.instance_id for item in run.relics.owned],
            [charm.instance_id, recruited.instance_id],
        )

    def test_row_stays_above_the_board_when_the_window_changes(self):
        wide = build_layout(1280, 900)
        narrow = build_layout(960, 700)
        for layout in (wide, narrow):
            self.assertLessEqual(layout.relics.bottom, layout.frame.top)
            self.assertFalse(layout.relics.colliderect(layout.board))
            self.assertEqual(layout.board.w, layout.board.h)
            self.assertGreater(layout.square, 36)
            self.assertLessEqual(layout.turn.bottom, layout.window[1])
            cards = rest_rects(layout.relics, 5, False)
            self.assertEqual(len(cards), 5)
            for card in cards:
                self.assertFalse(card.colliderect(layout.board))
                self.assertGreaterEqual(card.left, layout.relics.left)
                self.assertLessEqual(card.right, layout.relics.right)
        self.assertGreaterEqual(rest_rects(wide.relics, 1, False)[0].w, 70)
        self.assertGreaterEqual(rest_rects(wide.relics, 1, False)[0].h, 98)
        left, right = RelicBar().arrow_rects(wide, 6)
        for card in rest_rects(wide.relics, 5, True):
            self.assertFalse(card.colliderect(left))
            self.assertFalse(card.colliderect(right))


class RelicBarDrawTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((64, 64), pygame.HIDDEN)
        cls.assets = AssetManager(ROOT / "assets")

    def test_draw_empty_one_and_many(self):
        layout = build_layout(1280, 900)
        screen = pygame.Surface((1280, 900), pygame.SRCALPHA)
        empty = RunState.new(seed=8)
        bar = RelicBar()
        bar.draw_cards(screen, self.assets, empty, layout, now=0)
        bar.draw_overlay(screen, self.assets, empty, layout, now=0)
        one = RunState.new(seed=9)
        owned = one.relics.acquire("blood_contract")
        bar.draw_cards(screen, self.assets, one, layout, now=0)
        bar.hover_id = owned.instance_id
        bar.draw_overlay(screen, self.assets, one, layout, now=0)
        bar.detail_id = owned.instance_id
        bar.draw_overlay(screen, self.assets, one, layout, now=0)
        for index in range(4):
            one.relics.owned.append(OwnedRelic("gold_charm", f"extra_{index}", 20 + index))
        bar.scroll = 2
        bar.flashes[owned.instance_id] = 0
        bar.draw_cards(screen, self.assets, one, layout, now=200)
        self.assertGreater(bar.pulse(owned.instance_id, 200), 0)
        self.assertEqual(bar.pulse(owned.instance_id, 5000), 0)

    def test_dragged_card_is_painted_above_the_board(self):
        layout = build_layout(1280, 900)
        screen = pygame.Surface((1280, 900))
        screen.fill((10, 20, 30))
        run = RunState.new(seed=11)
        run.relics.acquire("banner")
        bar = RelicBar()
        bar.update(0, run, layout)
        slot = bar.placements(run, layout, 0)[0]
        board = layout.board.center
        bar.on_left_down(slot.drawn.center, run, layout, now=0)
        bar.on_motion(run, board, layout, now=0, held=True)
        bar.update(1, run, layout)
        self.assertTrue(bar.dragging)
        before = screen.get_at(board)
        bar.draw_cards(screen, self.assets, run, layout, now=0)
        self.assertEqual(screen.get_at(board), before)
        bar.draw_overlay(screen, self.assets, run, layout, now=0)
        self.assertNotEqual(screen.get_at(board), before)


if __name__ == "__main__":
    unittest.main()
