import unittest
from pathlib import Path

import pygame

from rendering.wood_swirl import FALLBACK, WoodSwirlBackground, _debug_layout


ROOT = Path(__file__).resolve().parents[1]
TEXTURE = ROOT / "assets" / "backgrounds" / "wood_swirl.png"


def _samples(surface: pygame.Surface) -> tuple:
    width, height = surface.get_size()
    points = []
    for y in range(8, height, 24):
        for x in range(8, width, 24):
            points.append(surface.get_at((x, y))[:3])
    return tuple(points)


class WoodSwirlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.display.set_mode((64, 64), pygame.HIDDEN)

    def test_missing_texture_fills_the_screen(self):
        background = WoodSwirlBackground(vignette_strength=0)
        background.ensure(ROOT / "assets" / "backgrounds" / "missing.png")
        screen = pygame.Surface((180, 120))
        screen.fill((255, 0, 255))
        background.draw(screen)
        self.assertEqual(screen.get_at((0, 0))[:3], FALLBACK)
        self.assertEqual(screen.get_at((179, 119))[:3], FALLBACK)
        self.assertEqual(screen.get_at((90, 60))[:3], FALLBACK)

    def test_shader_flows_the_grain_and_keeps_the_frame_fixed(self):
        background = WoodSwirlBackground(vignette_strength=0)
        background.ensure(TEXTURE)
        still = self._frame(background)
        background.distortion_strength = 0.0
        background.swirl_strength = 0.0
        background.elapsed = 0.0
        frozen = self._frame(background)
        background.update(6.0)
        later = self._frame(background)
        self.assertEqual(frozen, later)
        background.distortion_strength = 0.08
        background.swirl_strength = 0.06
        background.elapsed = 0.4
        bent = self._frame(background)
        background.elapsed = 5.0
        flowed = self._frame(background)
        self.assertNotEqual(bent, flowed)
        self.assertTrue(background.uses_shader)
        self.assertNotIn((255, 0, 255), bent)
        self.assertNotIn((255, 0, 255), flowed)
        self.assertNotEqual(still, bent)

    def test_pause_and_disabled_do_not_advance_time(self):
        background = WoodSwirlBackground(enabled=False, vignette_strength=0)
        background.ensure(TEXTURE)
        first = self._frame(background)
        background.update(30.0)
        background.resize()
        second = self._frame(background)
        self.assertEqual(background.elapsed, 0.0)
        self.assertEqual(first, second)
        background.enabled = True
        background.paused = True
        background.elapsed = 1.5
        background.update(10.0)
        self.assertEqual(background.elapsed, 1.5)

    def test_debug_sliders_change_only_the_named_amount(self):
        background = WoodSwirlBackground()
        background.debug_open = True
        before = background.distortion_strength
        _panel, rows, pause = _debug_layout()
        _name, _minus, plus = rows[1]
        self.assertTrue(background.debug_click(plus.center))
        self.assertGreater(background.distortion_strength, before)
        self.assertTrue(background.debug_click(pause.center))
        self.assertTrue(background.paused)

    def _frame(self, background: WoodSwirlBackground) -> tuple:
        screen = pygame.Surface((320, 200))
        screen.fill((255, 0, 255))
        background.draw(screen)
        for point in ((0, 0), (319, 0), (0, 199), (319, 199)):
            self.assertNotEqual(screen.get_at(point)[:3], (255, 0, 255))
        return _samples(screen)
