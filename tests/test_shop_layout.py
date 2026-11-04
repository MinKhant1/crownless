import itertools
import unittest

from rendering.layout import build_layout
from rendering.shop_layout import build_shop_layout

SIZES = ((1280, 720), (1366, 768), (1440, 900), (1600, 900), (1920, 1080))
OFFERS = ("piece", "relic", "army_size")
CHESTS = ("relic_collection", "piece_collection")


def shop_at(size):
    left = build_layout(*size).left.right + 12
    return left, build_shop_layout(*size, left)


class ShopLayoutTests(unittest.TestCase):
    def test_continue_is_bottom_right_and_reroll_bottom_left(self):
        for size in SIZES:
            with self.subTest(size=size):
                left, layout = shop_at(size)
                width, height = size
                button, reroll = layout.continue_button, layout.reroll
                self.assertGreater(button.centerx, (left + width) // 2)
                self.assertLess(reroll.centerx, (left + width) // 2)
                for rect in (button, reroll):
                    self.assertGreater(rect.centery, height * 0.8)
                    self.assertTrue(rect.top >= 0 and rect.bottom <= height and rect.left >= left and rect.right <= width)

    def test_three_offer_cards_share_one_row_with_a_price_above_each(self):
        for size in SIZES:
            with self.subTest(size=size):
                _left, layout = shop_at(size)
                frames = [layout.slots[key] for key in OFFERS]
                self.assertEqual({frame.size for frame in frames}, {frames[0].size})
                self.assertEqual({frame.y for frame in frames}, {frames[0].y})
                for frame, tag in zip(frames, layout.tags):
                    self.assertLessEqual(tag.bottom, frame.top + 4)
                    self.assertEqual(tag.centerx, frame.centerx)

    def test_nothing_on_the_shop_overlaps_or_leaves_the_screen(self):
        for size in SIZES:
            with self.subTest(size=size):
                left, layout = shop_at(size)
                parts = {key: layout.slots[key] for key in OFFERS + CHESTS}
                parts.update({f"{key} price": tag for key, tag in zip(OFFERS + CHESTS, layout.tags)})
                parts["continue"] = layout.continue_button
                parts["reroll"] = layout.reroll
                for name, rect in parts.items():
                    self.assertTrue(rect.left >= left and rect.right <= size[0] and rect.top >= 0 and rect.bottom <= size[1], name)
                for (a, first), (b, second) in itertools.combinations(parts.items(), 2):
                    self.assertFalse(first.colliderect(second), f"{a} overlaps {b}")


if __name__ == "__main__":
    unittest.main()
