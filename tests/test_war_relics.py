import unittest

from game.battle_summary import extra_reward_rows
from game.piece import Piece
from game.relics.events import BATTLE_START, BATTLE_END, CAPTURE_RESOLVED, PIECE_REMOVED, GameEvent
from game.run_state import RunState
from tests.test_relics import place


class WarRelicTests(unittest.TestCase):
    def start(self, *relics):
        run = RunState.new(seed=9)
        for relic in relics:
            self.assertIsNotNone(run.relics.acquire(relic))
        place(run, run.army.king(), 0, 1)
        place(run, next(p for p in run.army.pieces if p.kind == "rook"), 2, 1)
        run.enemies = [Piece(10001, "rook", "black", 2, 3), Piece(10002, "king", "black", 5, 6)]
        self.assertTrue(run.start_battle())
        return run

    def emit(self, run, kind, **payload):
        run.relics.dispatcher.publish(GameEvent(kind, payload))

    def capture(self, run, kind="rook", color="black", capturing="white", trait=None, target=10001, killer=2):
        self.emit(run, CAPTURE_RESOLVED, captured_piece_type=kind, captured_piece_color=color,
                  capturing_color=capturing, captured_trait=trait, captured_piece_id=target,
                  capturing_piece_id=killer)

    def test_war_tax_rounds_down_and_counts_only_allies(self):
        run = self.start("war_tax")
        board = run.battle.game.board
        for i in range(3):
            board.add_piece(Piece(50 + i, "pawn", "white", i + 1, 2))
        before = run.gold
        run.finish_victory()
        self.assertEqual(run.gold, before + 3 + 2)
        row = next(r for r in run.battle_summary.rows if "War Tax" in r.label)
        self.assertEqual(row.amount, 2)
        self.assertEqual(run.battle_summary.total_gold, 5)
        self.assertEqual(run.gold_earned, 5)

    def test_war_tax_at_defeat(self):
        run = self.start("war_tax")
        before = run.gold
        run.finish_defeat()
        self.assertEqual(run.gold, before + 1)
        self.assertEqual(run.gold_earned, 1)

    def test_spoils_immediate_capture_rewards_and_summary_do_not_double_pay(self):
        run = self.start("spoils_of_war")
        before = run.gold
        run.battle.click(2, 1)
        run.battle.click(2, 3)
        self.assertEqual(run.gold, before + 2)
        self.assertEqual(run.gold_earned, 2)
        run.finish_victory()
        self.assertEqual(run.gold, before + 5)
        self.assertEqual(run.gold_earned, 5)
        row = next(r for r in run.battle_summary.rows if "Spoils" in r.label)
        self.assertEqual(row.amount, 2)
        self.assertFalse(row.counts_toward_gold)
        self.assertEqual(run.battle_summary.total_gold, 3)

    def test_spoils_filters(self):
        run = self.start("spoils_of_war")
        before = run.gold
        for kind in ("pawn", "knight", "bishop", "king"):
            self.capture(run, kind=kind)
        self.capture(run, color="white", capturing="black")
        self.assertEqual(run.gold, before)
        self.capture(run, kind="queen")
        self.assertEqual(run.gold, before + 2)

    def test_veteran_cumulative_progress_and_once_per_run(self):
        run = self.start("veterans_banner")
        owned = run.relics.find("veterans_banner")
        capacity = run.army.capacity
        for i in range(7):
            self.emit(run, BATTLE_START)
            self.emit(run, BATTLE_END, outcome="victory")
            self.assertEqual(owned.state["progress"], min(i + 1, 5))
            self.assertEqual(run.army.capacity, capacity + (1 if i >= 4 else 0))
        self.assertTrue(owned.state["completed"])
        self.assertIsNone(run.relics.acquire("veterans_banner"))
        self.assertFalse(RunState.new(seed=9).relics.owns("veterans_banner"))

    def test_veteran_losses_and_defeat_preserve_progress(self):
        run = self.start("veterans_banner")
        owned = run.relics.find("veterans_banner")
        self.emit(run, BATTLE_END, outcome="victory")
        for loss in ("captured", "removed", "exploded", "defeat"):
            self.emit(run, BATTLE_START)
            if loss == "captured":
                self.capture(run, color="white", capturing="black")
            elif loss == "removed":
                self.emit(run, PIECE_REMOVED, color="white")
            elif loss == "exploded":
                self.capture(run, trait="explosive")
            self.emit(run, BATTLE_END, outcome="defeat" if loss == "defeat" else "victory")
            self.assertEqual(owned.state["progress"], 1)

    def test_vengeance_multiple_marks_one_bounty_per_enemy(self):
        run = self.start("golden_vengeance")
        board = run.battle.game.board
        before = run.gold
        for killer in (10001, 10002, 10001):
            self.capture(run, color="white", capturing="black", trait="golden", killer=killer)
        self.assertEqual(board.vengeance_marks, {10001, 10002})
        self.assertEqual(board.copy().vengeance_marks, board.vengeance_marks)
        self.capture(run, target=10001)
        self.assertEqual(board.vengeance_marks, {10002})
        self.assertEqual(run.gold, before + 3)
        self.capture(run, target=10001)
        self.assertEqual(run.gold, before + 3)
        self.capture(run, target=10002)
        self.assertEqual(run.gold, before + 6)
        self.assertEqual(run.gold_earned, 6)
        self.assertFalse(extra_reward_rows(run)[0].counts_toward_gold)

    def test_vengeance_only_golden_allies_and_battle_cleanup(self):
        run = self.start("golden_vengeance")
        board = run.battle.game.board
        for color, capturing, trait in (("white", "black", None), ("black", "white", "golden")):
            self.capture(run, color=color, capturing=capturing, trait=trait)
        self.assertFalse(board.vengeance_marks)
        self.capture(run, color="white", capturing="black", trait="golden", killer=10001)
        self.assertEqual(board.vengeance_marks, {10001})
        self.emit(run, BATTLE_END, outcome="defeat")
        self.assertFalse(board.vengeance_marks)
        self.assertFalse(run.relics.find("golden_vengeance").state["marked"])

    def test_vengeance_combines_with_spoils(self):
        run = self.start("golden_vengeance", "spoils_of_war")
        before = run.gold
        self.capture(run, color="white", capturing="black", trait="golden", killer=10001)
        self.capture(run, target=10001)
        self.assertEqual(run.gold, before + 5)
        self.assertFalse(run.battle.game.board.vengeance_marks)

    def test_vengeance_real_captures_mark_and_pay(self):
        run = self.start("golden_vengeance", "spoils_of_war")
        game = run.battle.game
        game.board.add_piece(Piece(99, "pawn", "white", 2, 2, trait="golden"))
        game.turns.current = "black"
        before = run.gold
        run.battle.click(2, 3)
        run.battle.click(2, 2)
        self.assertEqual(game.board.vengeance_marks, {10001})
        self.assertEqual(game.board.piece_by_id(10001).trait, None)
        self.assertEqual(game.turns.current, "white")
        run.battle.click(2, 1)
        run.battle.click(2, 2)
        self.assertEqual(run.gold, before + 5)
        self.assertFalse(game.board.vengeance_marks)
