import unittest
from pathlib import Path

import pygame

from config.settings import RELIC_CARD_HEIGHT, RELIC_CARD_WIDTH
from game.relics.relic_data import RELICS
from game.run_state import RunState
from rendering import style
from rendering.army_panel import ArmyPanel
from rendering.asset_manager import AssetManager
from rendering.board_renderer import _CACHE, clear_board_cache, draw_board
from rendering.layout import build_layout
from rendering.relic_card import MINI_NAME_SIZES, mini_name

ROOT = Path(__file__).resolve().parents[1]


class RestyleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((64, 64), pygame.HIDDEN)
        cls.assets = AssetManager(ROOT / "assets")

    def test_board_squares_are_flat_textures_joined_by_inlay_lines(self):
        clear_board_cache()
        layout = build_layout(1440, 900)
        screen = pygame.Surface(layout.window)
        draw_board(screen, self.assets, layout)
        light, dark = _CACHE.tiles(self.assets, layout.square)
        self.assertIs(light, self.assets.scaled("light", (layout.square, layout.square)))
        self.assertIs(dark, self.assets.scaled("dark", (layout.square, layout.square)))
        inlay = _CACHE.inlay_surface
        self.assertEqual(inlay.get_size(), layout.board.size)
        seam = layout.square - 1
        self.assertGreater(inlay.get_at((seam, layout.square // 2)).a, 150)
        self.assertLess(inlay.get_at((layout.square // 2, layout.square // 2)).a, 60)

    def test_every_relic_name_reads_on_a_mini_card(self):
        width = RELIC_CARD_WIDTH - 8
        readable = [style.title_font(size, bold=True) for size in MINI_NAME_SIZES if size >= 11]
        for relic in RELICS:
            lines, font = mini_name(relic.name, width)
            self.assertLessEqual(len(lines), 2, relic.name)
            self.assertIn(font, readable, relic.name)
            for line in lines:
                self.assertLessEqual(font.size(line)[0], width, relic.name)
        self.assertGreater(RELIC_CARD_WIDTH / RELIC_CARD_HEIGHT, 2 / 3)

    def test_the_army_panel_shows_the_board_when_the_reserve_is_empty(self):
        run = RunState.new(seed=14)
        run.begin_deployment()
        self.assertTrue(run.start_battle())
        layout = build_layout(1440, 900)
        panel = ArmyPanel()
        placed = panel._placed(run, layout)
        on_board = {entry.piece.id for key, entry, _rect in placed if key == "board"}
        self.assertEqual(on_board, set(run.deployment.placed))
        self.assertEqual(panel.rows(run, layout), [])
        for _key, _entry, rect in placed:
            self.assertTrue(layout.right.contains(rect))
        screen = pygame.Surface(layout.window)
        panel.draw(screen, self.assets, run, layout)

    def test_plaques_and_parchment_cache_by_size(self):
        first = style.plaque((200, 44), "idle")
        self.assertIs(first, style.plaque((200, 44), "idle"))
        self.assertIsNot(first, style.plaque((200, 44), "hover"))
        sheet = style.parchment(self.assets, (300, 200), seed=2)
        self.assertEqual(sheet.get_size(), (300, 200))
        self.assertEqual(sheet.get_at((0, 0)).a, 0)
        self.assertGreater(sheet.get_at((150, 100)).a, 240)


if __name__ == "__main__":
    unittest.main()
