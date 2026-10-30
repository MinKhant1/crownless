import unittest
from pathlib import Path

import pygame

from config.settings import STARTING_GOLD
from game.run_state import RunState
from game.visual_test import VisualTest
from rendering.asset_manager import AssetManager
from rendering.layout import build_layout
from rendering.piece_animation_controller import piece_motion
from rendering.piece_renderer import draw_pieces


ROOT = Path(__file__).resolve().parents[1]


class VisualTestTests(unittest.TestCase):
    def test_traits_are_assigned_only_on_the_temporary_board(self):
        run = RunState(4)
        army = [(piece.id, piece.trait, piece.kind) for piece in run.army.pieces]
        gold = run.gold
        phase = run.phase
        test = VisualTest()
        test.open(run)
        self.assertTrue(test.active)
        self.assertIsNone(run.battle)
        self.assertEqual(run.phase, phase)
        self.assertEqual(run.gold, gold)
        self.assertEqual(STARTING_GOLD, gold)
        white = {piece.kind: piece.trait for piece in test.game.board.pieces if piece.color == "white"}
        self.assertEqual(
            white,
            {
                "pawn": "golden",
                "knight": "wanted",
                "bishop": "explosive",
                "rook": "ghost",
                "queen": "wooden",
                "king": None,
            },
        )
        for piece in test.game.board.pieces:
            if piece.color == "black":
                self.assertIsNone(piece.trait)
            self.assertGreaterEqual(piece.id, 80001)
        self.assertEqual([(piece.id, piece.trait, piece.kind) for piece in run.army.pieces], army)
        pawn = next(piece for piece in test.game.board.pieces if piece.color == "white" and piece.kind == "pawn")
        self.assertTrue(run.traits.assign_trait(pawn.id, "wanted", overwrite=True))
        self.assertEqual(pawn.trait, "wanted")
        self.assertTrue(all(piece.trait is None for piece in run.army.pieces))
        test.close(run)
        self.assertFalse(test.active)
        self.assertIsNone(run.visual_pieces)
        self.assertIsNone(test.game)
        self.assertTrue(all(piece.trait is None for piece in run.army.pieces))

    def test_moves_keep_the_trait_and_ignore_the_army(self):
        run = RunState(4)
        test = VisualTest()
        test.open(run)
        game = test.game
        pawn = next(piece for piece in game.board.pieces if piece.color == "white" and piece.kind == "pawn")
        game.on_board_click(pawn.col, pawn.row)
        game.on_board_click(pawn.col, pawn.row + 1)
        self.assertEqual(pawn.row, 2)
        self.assertEqual(pawn.trait, "golden")
        self.assertEqual(run.gold, STARTING_GOLD)
        self.assertTrue(all(piece.trait is None for piece in run.army.pieces))
        self.assertIsNone(run.battle)


class VisualDrawTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((64, 64), pygame.HIDDEN)
        cls.assets = AssetManager(ROOT / "assets")

    def test_wanted_crosshair_rises_with_the_piece(self):
        run = RunState(4)
        test = VisualTest()
        test.open(run)
        game = test.game
        knight = next(piece for piece in game.board.pieces if piece.color == "white" and piece.kind == "knight")
        game._select(knight)
        layout = build_layout(1280, 900)
        square = layout.square_rect(knight.col, knight.row)
        grounded = pygame.Surface((1280, 900), pygame.SRCALPHA)
        draw_pieces(grounded, self.assets, game, layout)
        piece_motion.motions[knight.id].height = 18
        piece_motion._last_ms = pygame.time.get_ticks()
        lifted = pygame.Surface((1280, 900), pygame.SRCALPHA)
        draw_pieces(lifted, self.assets, game, layout)
        grounded_top = _crosshair_top(grounded, square)
        lifted_top = _crosshair_top(lifted, square)
        self.assertIsNotNone(grounded_top)
        self.assertIsNotNone(lifted_top)
        self.assertLess(lifted_top, grounded_top - 8)
        test.close(run)


def _crosshair_top(screen: pygame.Surface, square: pygame.Rect) -> int | None:
    left = max(0, square.left - 8)
    right = min(screen.get_width(), square.right + 8)
    top = max(0, square.top - 40)
    bottom = min(screen.get_height(), square.bottom)
    for y in range(top, bottom):
        for x in range(left, right):
            pixel = screen.get_at((x, y))
            if pixel.r > 150 and pixel.g < 100 and pixel.b < 100 and pixel.a > 160:
                return y
    return None
