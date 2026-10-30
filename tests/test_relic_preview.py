import unittest

import pygame

from rendering.relic_card import CARD_RATIO
from rendering.relic_preview import RelicPreviewModal, preview_card_rect


class RelicPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((64, 64), pygame.HIDDEN)

    def test_card_fits_each_window_without_leaving_the_padding(self):
        for window in ((1440, 900), (960, 720), (1280, 800)):
            rect = preview_card_rect(window)
            pad_x = int(window[0] * 0.08)
            pad_y = int(window[1] * 0.08)
            self.assertGreaterEqual(rect.left, pad_x - 1)
            self.assertGreaterEqual(rect.top, pad_y - 1)
            self.assertLessEqual(rect.right, window[0] - pad_x + 1)
            self.assertLessEqual(rect.bottom, window[1] - pad_y + 1)
            self.assertLessEqual(rect.w, window[0] * 0.55 + 1)
            self.assertLessEqual(rect.h, window[1] * 0.82 + 1)
            self.assertAlmostEqual(rect.w / rect.h, CARD_RATIO, places=2)

    def test_click_opens_and_escape_or_outside_closes(self):
        modal = RelicPreviewModal()
        origin = pygame.Rect(30, 40, 70, 105)
        modal.show("banner", origin, "owned-1")
        modal.update(0.05)
        self.assertTrue(modal.blocks)
        self.assertGreater(modal.shown, 0.0)
        self.assertLess(modal.blend, 1.0)
        modal.update(1.0)
        self.assertEqual(modal.shown, 1.0)
        self.assertTrue(modal.on_escape())
        self.assertTrue(modal.closing)
        modal.update(1.0)
        self.assertFalse(modal.blocks)
        modal.show("banner", origin, "owned-1")
        modal.update(1.0)
        window = (1280, 900)
        modal.on_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(8, 8)), window)
        modal.on_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(8, 8)), window)
        self.assertTrue(modal.closing)

    def test_activate_is_only_offered_for_an_owned_activated_relic(self):
        modal = RelicPreviewModal()
        modal.show("blood_contract", pygame.Rect(10, 10, 70, 105), "owned-2")
        modal.update(1.0)
        modal._place((1280, 900))
        self.assertIsNotNone(modal.activate_rect)
        modal.show("banner", pygame.Rect(10, 10, 70, 105), "owned-3")
        modal.update(1.0)
        modal._place((1280, 900))
        self.assertIsNone(modal.activate_rect)
