import unittest

import pygame

from config.settings import GOLDEN_BONUS, VICTORY_GOLD
from game.battle_summary import FallenGroup, RewardRow, build_battle_summary
from game.piece import Piece
from game.run_state import RunState
from rendering.victory_summary import continue_rect, summary_frames, summary_for
from tests.test_relics import place


def _kind(run: RunState, kind: str) -> Piece:
    return next(piece for piece in run.army.pieces if piece.kind == kind)


class SummaryDataTests(unittest.TestCase):
    def test_duplicate_losses_group_and_ghosts_stay_temporary(self):
        run = RunState.new(seed=3)
        first = _kind(run, "pawn")
        second = run.army.create("pawn")
        ghost = run.army.create("pawn")
        ghost.trait = "ghost"
        run.deployment.placed[first.id] = (0, 1)
        run.deployment.placed[second.id] = (1, 1)
        run.deployment.placed[ghost.id] = (2, 1)
        run.battle_roster = tuple((piece.id, piece.kind, piece.trait) for piece in run.army.pieces)
        run.army.pieces = [piece for piece in run.army.pieces if piece.kind != "pawn"]
        summary = build_battle_summary(run, run.gold, 0, 0, [(80, "bishop", "ghost")])
        names = {(group.name, group.count, group.category) for group in summary.fallen}
        self.assertIn(("Pawn", 2, "permanent"), names)
        self.assertIn(("Ghost Pawn", 1, "temporary"), names)
        self.assertIn(("Ghost Bishop", 1, "temporary"), names)
        self.assertFalse(summary.flawless)
        self.assertEqual(summary.permanent_losses, 2)

    def test_flawless_relic_row_matches_the_gold_paid(self):
        run = RunState.new(seed=4)
        run.relics.acquire("flawless_victory")
        place(run, _kind(run, "king"), 0, 1)
        rook = _kind(run, "rook")
        rook.trait = "golden"
        place(run, rook, 2, 1)
        run.enemies = [Piece(10001, "pawn", "black", 2, 3)]
        self.assertTrue(run.start_battle())
        run.battle.click(2, 1)
        run.battle.click(2, 3)
        before = run.gold
        run.finish_victory()
        summary = run.battle_summary
        labels = [row.label for row in summary.rows]
        self.assertIn("Battle Win", labels)
        self.assertIn("Relic: Flawless Victory", labels)
        self.assertIn("Golden Piece", labels)
        self.assertNotIn("Interest", labels)
        self.assertEqual(summary.total_gold, VICTORY_GOLD + 3 + GOLDEN_BONUS)
        self.assertEqual(summary.gold_after - summary.gold_before, summary.total_gold)
        self.assertEqual(run.gold, before + summary.total_gold)
        self.assertTrue(summary.flawless)
        self.assertEqual(summary.fallen, ())

    def test_a_lost_pawn_is_listed_and_flawless_gold_is_withheld(self):
        run = RunState.new(seed=5)
        run.relics.acquire("flawless_victory")
        place(run, _kind(run, "king"), 0, 1)
        place(run, _kind(run, "rook"), 1, 1)
        place(run, _kind(run, "pawn"), 1, 2)
        run.enemies = [Piece(10001, "pawn", "black", 2, 3)]
        self.assertTrue(run.start_battle())
        run.battle.click(0, 1)
        run.battle.click(0, 2)
        run.battle.click(2, 3)
        run.battle.click(1, 2)
        run.battle.click(1, 1)
        run.battle.click(1, 2)
        self.assertEqual(run.battle.outcome, "victory")
        run.finish_victory()
        summary = run.battle_summary
        self.assertNotIn("Relic: Flawless Victory", [row.label for row in summary.rows])
        self.assertEqual(summary.fallen, (FallenGroup("pawn", 1),))
        self.assertEqual(summary.fallen[0].name, "Pawn")
        self.assertFalse(summary.flawless)

    def test_collector_rerolls_are_shown_apart_from_gold(self):
        run = RunState.new(seed=6)
        run.relics.acquire("collectors_crown")
        place(run, _kind(run, "king"), 0, 1)
        place(run, _kind(run, "rook"), 2, 1)
        place(run, _kind(run, "pawn"), 3, 1)
        run.enemies = [Piece(10001, "pawn", "black", 2, 3)]
        self.assertTrue(run.start_battle())
        run.battle.click(2, 1)
        run.battle.click(2, 3)
        before = run.gold
        run.finish_victory()
        summary = run.battle_summary
        crown = next(row for row in summary.rows if row.label == "Relic: Collector's Crown")
        self.assertGreater(crown.amount, 0)
        self.assertFalse(crown.counts_toward_gold)
        self.assertEqual(crown.source, "Shop Rerolls")
        self.assertEqual(summary.total_gold, VICTORY_GOLD)
        self.assertEqual(run.gold, before + VICTORY_GOLD)

    def test_future_rows_keep_the_same_shape(self):
        row = RewardRow("Relic: Example", 4, "relic", source="Future")
        self.assertEqual(row.amount, 4)
        self.assertTrue(row.counts_toward_gold)


class SummaryLayoutTests(unittest.TestCase):
    def test_panels_and_continue_stay_on_screen(self):
        run = RunState.new(seed=7)
        run.phase = "victory"
        for size in ((1440, 900), (960, 720)):
            frames = summary_frames(size, summary_for(run))
            window = pygame.Rect(0, 0, *size)
            self.assertTrue(window.contains(frames.left))
            self.assertTrue(window.contains(frames.center))
            self.assertTrue(window.contains(frames.right))
            self.assertTrue(frames.center.contains(frames.button))
            self.assertEqual(continue_rect(size, run), frames.button)
            self.assertLess(frames.left.right, frames.center.left)
            self.assertLess(frames.center.right, frames.right.left)
