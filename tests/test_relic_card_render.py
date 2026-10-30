import unittest
from pathlib import Path

import pygame

from game.relics.relic_data import front_key, relic_by_id, shop_relic_ids
from rendering.asset_manager import AssetManager
from rendering.relic_art import ART_CROPS, artwork
from rendering.relic_card import CARD_RATIO, RelicCardRenderer


ROOT = Path(__file__).resolve().parents[1]


class RelicCardRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((64, 64), pygame.HIDDEN)
        cls.assets = AssetManager(ROOT / "assets")

    def test_background_is_not_loaded_as_relic_art(self):
        self.assertTrue(self.assets.has("relic_card"))
        self.assertTrue(self.assets.has("relic_back"))
        self.assertFalse(self.assets.has("relic_front_card_background"))
        self.assertFalse(self.assets.has("relic_front_back_card"))

    def test_shop_relics_trim_to_visible_artwork(self):
        for relic_id in shop_relic_ids():
            self.assertIn(relic_id, ART_CROPS)
            relic = relic_by_id(relic_id)
            self.assertIsNotNone(relic)
            image = artwork.image(self.assets, relic)
            source = self.assets.get(front_key(relic))
            self.assertIsNotNone(image)
            self.assertLessEqual(image.get_width(), source.get_width())
            self.assertLessEqual(image.get_height(), source.get_height())
            self.assertGreater(image.get_width(), 8)

    def test_banner_face_keeps_the_parchment_corner_and_the_card_ratio(self):
        renderer = RelicCardRenderer()
        relic = relic_by_id("banner")
        width, height = 280, 420
        self.assertAlmostEqual(width / height, CARD_RATIO, places=2)
        screen = pygame.Surface((width, height), pygame.SRCALPHA)
        renderer.draw(screen, self.assets, relic, screen.get_rect())
        background = self.assets.scaled("relic_card", (width, height))
        self.assertEqual(screen.get_at((2, 2)), background.get_at((2, 2)))
        self.assertEqual(screen.get_at((width - 3, height - 3)), background.get_at((width - 3, height - 3)))
        again = pygame.Surface((width, height), pygame.SRCALPHA)
        renderer.draw(again, self.assets, relic, again.get_rect())
        self.assertEqual(pygame.image.tobytes(screen, "RGBA"), pygame.image.tobytes(again, "RGBA"))
        back = pygame.Surface((width, height), pygame.SRCALPHA)
        renderer.draw(back, self.assets, relic, back.get_rect(), face_down=True)
        self.assertNotEqual(pygame.image.tobytes(screen, "RGBA"), pygame.image.tobytes(back, "RGBA"))
