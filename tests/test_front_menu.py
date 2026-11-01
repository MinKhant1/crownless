import random
import unittest

import pygame

from game.traits import TRAIT_IDS, TRAITS
from scenes.how_to_play import HowToPlayScreen
from scenes.main_menu import MainMenuScreen, _layout
from scenes.menu_piece import MenuPiece


class FrontMenuTests(unittest.TestCase):
    def test_the_menu_king_keeps_one_special_trait(self):
        menu = MainMenuScreen(random.Random(3))
        first = menu.king.trait
        self.assertIn(first, TRAIT_IDS)
        menu.update(0.2, (1440, 900))
        self.assertEqual(menu.king.trait, first)
        menu.enter()
        self.assertIn(menu.king.trait, TRAIT_IDS)

    def test_start_how_to_play_and_exit_are_the_menu_actions(self):
        menu = MainMenuScreen(random.Random(1))
        window = (1440, 900)
        places = _layout(window)
        self.assertEqual(self._click(menu, places["start"].center, window), "start")
        self.assertEqual(self._click(menu, places["guide"].center, window), "guide")
        self.assertEqual(self._click(menu, places["exit"].center, window), "exit")
        self.assertIsNone(self._click(menu, (4, 4), window))

    def test_the_king_can_be_dragged_and_released_without_a_run(self):
        piece = MenuPiece("king", "golden")
        rest = pygame.Rect(200, 180, 96, 96)
        window = (1440, 900)
        self.assertTrue(piece.on_press(rest.center, rest, window))
        piece.on_motion((rest.centerx + 40, rest.centery - 10), rest, window, True)
        self.assertTrue(piece.dragging)
        piece.on_release()
        self.assertFalse(piece.dragging)
        piece.update(0.4, rest, window)
        self.assertFalse(piece.dragging)

    def test_how_to_play_samples_a_preview_and_switches_tabs(self):
        guide = HowToPlayScreen(random.Random(5))
        guide.open()
        self.assertEqual(len(guide._relic_offer), 3)
        self.assertEqual(len(guide._piece_offer), 3)
        guide._hits = [("tab:enemies", pygame.Rect(0, 0, 20, 20))]
        event = pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": (10, 10)})
        self.assertIsNone(guide.on_event(event, (1440, 900)))
        self.assertEqual(guide.tab, "enemies")
        guide._step_pawn(1)
        self.assertEqual(guide.pawn.trait, TRAITS[1].id)

    def _click(self, menu: MainMenuScreen, pos: tuple[int, int], window: tuple[int, int]) -> str | None:
        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": pos})
        up = pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": pos})
        menu.on_event(down, window)
        return menu.on_event(up, window)


if __name__ == "__main__":
    unittest.main()
