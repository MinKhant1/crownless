import unittest
from pathlib import Path

import pygame

from game.relics.relic_data import shop_relic_ids
from game.run_state import RunState
from rendering.asset_manager import AssetManager
from rendering.win_screen import BUTTONS_IN, WinScreen, finished_at, shown_values, stat_values, win_layout
from scenes.result_scene import handle_result_click
from rendering.win_screen import win_screen

ROOT = Path(__file__).resolve().parents[1]
SIZES = ((1280, 720), (1440, 900), (960, 720))


def _win_battle(run: RunState, lose: str | None = None) -> None:
    run.begin_deployment()
    if lose is not None:
        piece = next(piece for piece in run.army.pieces if piece.kind == lose and piece.id in run.deployment.placed)
    run.start_battle()
    if lose is not None:
        board_piece = run.battle.game.board.piece_by_id(piece.id)
        run.battle.game.board.pieces.remove(board_piece)
    run.battle.force("victory")
    run.finish_victory()


class WinScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((64, 64), pygame.HIDDEN)
        cls.assets = AssetManager(ROOT / "assets")

    def test_the_run_keeps_totals_for_the_win_screen(self):
        run = RunState.new(seed=5)
        self.assertEqual((run.battles_won, run.gold_earned, run.pieces_lost), (0, 0, 0))
        before = run.gold
        _win_battle(run, lose="pawn")
        first_gain = run.gold - before
        self.assertEqual(run.battles_won, 1)
        self.assertEqual(run.gold_earned, first_gain)
        self.assertEqual(run.gold_earned, run.battle_summary.total_gold)
        self.assertEqual(run.pieces_lost, 1)
        run.continue_from_victory()
        run.gold += 40
        run.buy_relic()
        run.leave_shop()
        before = run.gold
        _win_battle(run)
        self.assertEqual(run.battles_won, 2)
        self.assertEqual(run.gold_earned, first_gain + run.gold - before)
        self.assertEqual(run.pieces_lost, 1)
        values = stat_values(run)
        self.assertEqual(values, {"battles": 2, "gold": run.gold_earned, "relics": len(run.relics.owned), "lost": 1})

    def test_the_panel_crown_and_buttons_fit_at_every_size(self):
        for size in SIZES:
            places = win_layout(size)
            window = pygame.Rect(0, 0, *size)
            self.assertTrue(window.contains(places.crown), size)
            self.assertTrue(window.contains(places.panel), size)
            self.assertLess(places.crown.top, places.panel.top)
            self.assertGreater(places.crown.bottom, places.panel.top)
            parts = [places.plinth, places.ledger, places.relics]
            for part in parts + [places.new_run, places.menu]:
                self.assertTrue(places.panel.contains(part), (size, part))
            for upper, lower in zip(parts, parts[1:]):
                self.assertLessEqual(upper.bottom, lower.top)
            self.assertLessEqual(places.relics.bottom, places.new_run.top)
            self.assertFalse(places.new_run.colliderect(places.menu))
            self.assertGreater(places.rule_y, places.title_y)
            self.assertLess(places.rule_y, places.plinth.top)

    def test_new_run_and_main_menu_answer_once_the_buttons_show(self):
        run = RunState.new(seed=9)
        run.phase = "complete"
        size = (1280, 720)
        win_screen.update(0.0, run)
        win_screen.elapsed = 0.0
        new_run, menu = win_screen.buttons(size)
        self.assertIsNone(handle_result_click(run, new_run.center, size))
        win_screen.update(BUTTONS_IN + 0.1, run)
        self.assertEqual(handle_result_click(run, new_run.center, size), "restart")
        self.assertEqual(handle_result_click(run, menu.center, size), "menu")
        self.assertIsNone(handle_result_click(run, (4, 4), size))

    def test_stats_count_up_to_the_real_totals(self):
        run = RunState.new(seed=11)
        run.battles_won, run.gold_earned, run.pieces_lost = 5, 23, 2
        self.assertEqual(shown_values(run, 0.0), {"battles": 0, "gold": 0, "relics": 0, "lost": 0})
        self.assertEqual(shown_values(run, finished_at(run)), stat_values(run))

    def test_a_crowded_run_draws_through_the_whole_animation(self):
        run = RunState.new(seed=13)
        for relic_id in shop_relic_ids():
            run.relics.acquire(relic_id)
        for kind in ("pawn", "knight", "bishop", "rook", "queen") * 2:
            run.army.create(kind).trait = "golden"
        run.battles_won, run.gold_earned = 5, 40
        run.phase = "complete"
        screen = WinScreen()
        for size in SIZES:
            surface = pygame.Surface(size)
            screen.elapsed = 0.0
            step = 0.0
            while step <= finished_at(run):
                screen.update(0.1, run)
                screen.draw(surface, self.assets, run)
                step += 0.1


if __name__ == "__main__":
    unittest.main()
