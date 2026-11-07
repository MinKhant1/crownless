import random
import unittest
from pathlib import Path

import pygame

from ai.trait_definitions import AI_TRAITS
from game.relics.relic_data import shop_relic_ids
from game.run_state import RunState
from game.traits import TRAITS
from rendering.asset_manager import AssetManager
from scenes.collection import CARD_MIN_HEIGHT, CollectionScreen, _frame, relic_card_size, relic_rects, tab_rects, tile_rects
from scenes.how_to_play import _relic_blocks
from scenes.main_menu import MainMenuScreen, _layout

ROOT = Path(__file__).resolve().parents[1]
SIZES = ((1280, 720), (1440, 900))


class CollectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((64, 64), pygame.HIDDEN)
        cls.assets = AssetManager(ROOT / "assets")

    def test_the_menu_lists_collection_and_options_between_how_to_play_and_exit(self):
        menu = MainMenuScreen(random.Random(2))
        keys = [key for key, _label in menu.buttons]
        self.assertEqual(keys, ["start", "guide", "collection", "options", "exit"])
        for size in SIZES:
            places = _layout(size)
            self.assertLess(places["guide"].bottom, places["collection"].top)
            self.assertLess(places["collection"].bottom, places["options"].top)
            self.assertLess(places["options"].bottom, places["exit"].top)
            self.assertLessEqual(places["exit"].bottom, size[1])
            self.assertEqual(self._click(menu, places["collection"].center, size), "collection")
            self.assertEqual(self._click(menu, places["options"].center, size), "options")

    def test_every_shop_relic_has_a_readable_card_that_scrolls_into_view(self):
        ids = list(shop_relic_ids())
        self.assertEqual(len(ids), 18)
        for size in SIZES:
            content = _frame(size)["content"]
            card_w, card_h = relic_card_size(content)
            self.assertGreaterEqual(card_h, CARD_MIN_HEIGHT)
            # the card's effect text is set at 2.7% of the card height
            self.assertGreaterEqual(int(card_h * 0.027), 11)
            placed = relic_rects(content, 0)
            self.assertEqual([relic_id for relic_id, _rect in placed], ids)
            for _relic_id, rect in placed:
                self.assertGreaterEqual(rect.left, content.left)
                self.assertLessEqual(rect.right, content.right)
            for first, (_id, rect) in enumerate(placed):
                for _other, other in placed[first + 1 :]:
                    self.assertFalse(rect.colliderect(other))
            page = CollectionScreen()
            page.open()
            for _ in range(40):
                page.on_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_PAGEDOWN}), size)
            last = relic_rects(content, page.scroll)[-1][1]
            self.assertTrue(content.contains(last))

    def test_special_pieces_and_personalities_fit_on_one_page(self):
        for size in SIZES:
            content = _frame(size)["content"]
            for count in (len(TRAITS), len(AI_TRAITS)):
                tiles = tile_rects(content, count)
                self.assertEqual(len(tiles), count)
                for index, tile in enumerate(tiles):
                    self.assertTrue(content.contains(tile))
                    self.assertGreaterEqual(tile.h, 180)
                    for other in tiles[index + 1 :]:
                        self.assertFalse(tile.colliderect(other))
            frame = _frame(size)
            for tab in tab_rects(frame["tabs"]):
                self.assertTrue(frame["panel"].contains(tab))
            self.assertFalse(frame["content"].colliderect(frame["back"]))

    def test_browsing_every_tab_never_touches_a_run(self):
        run = RunState.new(seed=12)
        before = (run.gold, run.relics.owned_ids(), [piece.id for piece in run.army.pieces], run.phase)
        size = (1280, 720)
        screen = pygame.Surface(size)
        page = CollectionScreen()
        page.open()
        for key, _label in CollectionScreen.TABS:
            tab = tab_rects(_frame(size)["tabs"])[[name for name, _ in CollectionScreen.TABS].index(key)]
            page.draw(screen, self.assets)
            self._press(page, tab.center, size)
            self.assertEqual(page.tab, key)
            page.update(1 / 60, size)
            page.draw(screen, self.assets)
        page.tab = "relics"
        page.draw(screen, self.assets)
        first = relic_rects(_frame(size)["content"], page.scroll)[0][1]
        self._press(page, first.center, size)
        reveal = page.flips[shop_relic_ids()[0]]
        self.assertLess(reveal.progress, 1.0)
        for _ in range(60):
            page.update(1 / 60, size)
        self.assertTrue(reveal.face_up)
        after = (run.gold, run.relics.owned_ids(), [piece.id for piece in run.army.pieces], run.phase)
        self.assertEqual(before, after)
        escape = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE})
        self.assertEqual(page.on_event(escape, size), "back")
        page.draw(screen, self.assets)
        self.assertEqual(self._press(page, _frame(size)["back"].center, size), "back")

    def test_how_to_play_points_to_collection_instead_of_listing_relics(self):
        text = " ".join(str(payload) for kind, _height, payload in _relic_blocks(900) if kind == "text")
        self.assertIn("Collection", text)
        self.assertNotIn("Sacrifice a piece", text)

    def _click(self, menu: MainMenuScreen, pos: tuple[int, int], window: tuple[int, int]) -> str | None:
        menu.on_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": pos}), window)
        return menu.on_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": pos}), window)

    def _press(self, page: CollectionScreen, pos: tuple[int, int], window: tuple[int, int]) -> str | None:
        page.on_event(pygame.event.Event(pygame.MOUSEMOTION, {"pos": pos, "rel": (0, 0), "buttons": (0, 0, 0)}), window)
        page.on_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": pos}), window)
        return page.on_event(pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": pos}), window)


if __name__ == "__main__":
    unittest.main()
