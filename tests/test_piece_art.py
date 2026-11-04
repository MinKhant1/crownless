import unittest
from pathlib import Path

import pygame

PIECES = Path(__file__).resolve().parents[1] / "assets" / "pieces" / "normal"


class PieceArtTests(unittest.TestCase):
    def test_piece_images_hold_one_figure_without_sheet_leftovers(self):
        for path in sorted(PIECES.glob("*.png")):
            with self.subTest(piece=path.stem):
                image = pygame.image.load(str(path))
                parts = [part for part in pygame.mask.from_surface(image, 1).connected_components() if part.count() > 50]
                self.assertEqual(len(parts), 1, f"{path.name} has {len(parts)} separate shapes")


if __name__ == "__main__":
    unittest.main()
