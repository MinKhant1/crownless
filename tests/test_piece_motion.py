import unittest
from pathlib import Path

import pygame

from game.game import Game
from game.piece import Piece
from rendering.asset_manager import AssetManager
from rendering.layout import build_layout
from rendering.piece_animation_controller import PieceAnimationController
from rendering.piece_renderer import draw_pieces
from rendering.piece_visual_effects import draw_contact_shadow, figurines, shadow_center
from rendering.special_piece_renderer import special_pieces


ROOT = Path(__file__).resolve().parents[1]


def _interior(surface: pygame.Surface) -> tuple[int, int] | None:
    width, height = surface.get_size()
    best: tuple[int, int] | None = None
    best_alpha = 0
    for y in range(height // 3, height * 2 // 3, 2):
        for x in range(width // 3, width * 2 // 3, 2):
            alpha = surface.get_at((x, y)).a
            if alpha > best_alpha:
                best_alpha = alpha
                best = (x, y)
    return best


class PieceMotionTests(unittest.TestCase):
    def test_selected_piece_rises_then_settles(self):
        piece = Piece(1, "knight", "white", 0, 1)
        motion = PieceAnimationController()
        motion.update([piece], piece.id, 70, now_ms=0)
        clock = 0
        while clock < 200:
            clock += 40
            motion.update([piece], piece.id, 70, now_ms=clock)
        self.assertGreater(motion.motions[piece.id].height, 8)
        lift, scale, tilt, ratio = motion.offset(piece.id)
        self.assertGreater(lift, 6)
        self.assertGreater(scale, 1.04)
        self.assertGreater(tilt, 1)
        self.assertGreater(ratio, 0.5)
        sprite_y = 200 - lift
        ground_y = shadow_center((100, 200), 70)[1]
        self.assertLess(sprite_y, 194)
        self.assertGreater(ground_y, 200)
        while clock < 1200:
            clock += 40
            motion.update([piece], None, 70, now_ms=clock)
        settled, scale, tilt, ratio = motion.offset(piece.id)
        self.assertLess(settled, 1.5)
        self.assertLess(scale, 1.02)
        self.assertLess(abs(tilt), 0.4)
        self.assertLess(ratio, 0.15)

    def test_one_move_travels_and_a_crowd_snaps(self):
        knight = Piece(1, "knight", "white", 0, 1)
        pawn = Piece(2, "pawn", "white", 1, 1)
        motion = PieceAnimationController()
        motion.update([knight], knight.id, 70, now_ms=0)
        motion.update([knight], knight.id, 70, now_ms=160)
        knight.col = 2
        motion.update([knight], None, 70, now_ms=176)
        self.assertEqual(motion.motions[1].travel_from, (0, 1))
        self.assertLess(motion.motions[1].travel_t, 1)
        motion.update([knight, pawn], None, 70, now_ms=200)
        knight.col = 4
        pawn.col = 3
        motion.update([knight, pawn], None, 70, now_ms=220)
        self.assertIsNone(motion.motions[1].travel_from)
        self.assertIsNone(motion.motions[2].travel_from)
        self.assertEqual(motion.motions[1].anchor, (4, 1))

    def test_idle_piece_stays_down(self):
        piece = Piece(3, "rook", "black", 0, 6)
        motion = PieceAnimationController()
        motion.update([piece], None, 70, now_ms=0)
        motion.update([piece], None, 70, now_ms=500)
        lift, scale, tilt, ratio = motion.offset(piece.id)
        self.assertEqual(lift, 0)
        self.assertEqual(scale, 1)
        self.assertEqual(tilt, 0)
        self.assertEqual(ratio, 0)


class FigurineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((64, 64), pygame.HIDDEN)
        cls.assets = AssetManager(ROOT / "assets")

    def setUp(self):
        figurines.clear()

    def test_dressing_does_not_change_the_source_art(self):
        raw = self.assets._raw["white_knight"]
        before_raw = pygame.image.tobytes(raw, "RGBA")
        fitted = self.assets.fitted("white_knight", 72, 72)
        before_fitted = pygame.image.tobytes(fitted, "RGBA")
        piece = Piece(1, "knight", "white", 0, 1)
        dressed = figurines.image(self.assets, piece, 72)
        again = figurines.image(self.assets, piece, 72)
        self.assertIs(dressed, again)
        self.assertEqual(dressed.get_width(), fitted.get_width() + 2)
        self.assertEqual(pygame.image.tobytes(raw, "RGBA"), before_raw)
        self.assertEqual(pygame.image.tobytes(fitted, "RGBA"), before_fitted)
        self.assertIs(special_pieces.image(self.assets, "white", "knight", None, 72), fitted)

    def test_ghost_stays_paler_than_the_solid_figure(self):
        solid = figurines.image(self.assets, Piece(1, "knight", "white", 0, 1), 80)
        ghost_source = special_pieces.image(self.assets, "white", "knight", "ghost", 80)
        ghost = figurines.image(self.assets, Piece(2, "knight", "white", 0, 1, trait="ghost"), 80)
        spot = _interior(ghost_source)
        self.assertIsNotNone(spot)
        assert spot is not None
        faded = ghost.get_at((spot[0] + 1, spot[1] + 1))
        plain = solid.get_at((spot[0] + 1, spot[1] + 1))
        self.assertLess(faded.a, int(plain.a * 0.85))
        self.assertGreater(faded.a, 20)

    def test_shadow_is_darker_toward_the_center(self):
        screen = pygame.Surface((120, 60), pygame.SRCALPHA)
        draw_contact_shadow(screen, (60, 30), 70, 0)
        self.assertGreater(screen.get_at((60, 30)).a, screen.get_at((8, 8)).a)
        lifted = pygame.Surface((160, 80), pygame.SRCALPHA)
        grounded = draw_contact_shadow(screen, (60, 30), 70, 0)
        spread = draw_contact_shadow(lifted, (80, 40), 70, 1)
        self.assertGreater(spread.width, grounded.width)

    def test_board_draw_keeps_move_dots_and_the_artwork(self):
        raw = self.assets._raw["white_pawn"]
        before = pygame.image.tobytes(raw, "RGBA")
        game = Game()
        pawn = game.board.piece_at(5, 1)
        self.assertIsNotNone(pawn)
        assert pawn is not None
        game._select(pawn)
        self.assertTrue(game.legal)
        layout = build_layout(1280, 900)
        screen = pygame.Surface((1280, 900), pygame.SRCALPHA)
        draw_pieces(screen, self.assets, game, layout)
        found = False
        for move in game.legal:
            if game.board.piece_at(move.to_col, move.to_row) is not None:
                continue
            pixel = screen.get_at(layout.square_rect(move.to_col, move.to_row).center)
            if pixel.g > pixel.r and pixel.g > 100:
                found = True
        self.assertTrue(found)
        self.assertEqual(pygame.image.tobytes(raw, "RGBA"), before)
        self.assertEqual(game.selected_id, pawn.id)
