import unittest

from config.settings import (
    BATTLE_START_TIME,
    ENEMY_FORMATIONS,
    STARTING_GOLD,
    VICTORY_BANNER_TIME,
    VICTORY_GOLD,
    VICTORY_REWARD_TIME,
    parse_square,
)
from game.level_manager import formation_counts, spawn_enemies
from game.piece import Piece
from game.run_state import RunState
from game.scene_manager import SceneManager
from game.transitions.easing import ease_in_out_cubic, ease_out_cubic
from game.transitions.transition_manager import TransitionManager


def _win(run: RunState) -> None:
    king = run.army.king()
    assert king is not None
    run.enemies = []
    run.deployment.place(king, 0, 1, run.blocked_squares(), run.army.capacity, run.army)
    run.start_battle()
    run.battle.evaluate()
    run.finish_victory()


class CampaignTests(unittest.TestCase):
    def test_level_formations_stay_on_the_upper_rows(self):
        first = RunState.new(seed=4)
        second = RunState.new(seed=4)
        self.assertEqual(
            [(piece.kind, piece.col, piece.row) for piece in first.enemies],
            [(piece.kind, piece.col, piece.row) for piece in second.enemies],
        )
        expected = {
            1: {"pawn": 3, "knight": 1},
            2: {"pawn": 3, "bishop": 1, "knight": 1},
            3: {"pawn": 2, "bishop": 1, "knight": 1, "rook": 1},
            4: {"pawn": 3, "bishop": 1, "knight": 1, "rook": 1},
            5: {"king": 1, "pawn": 2, "knight": 1, "bishop": 1, "rook": 1},
        }
        for level in range(1, 6):
            self.assertEqual(formation_counts(level), expected[level])
            seen = []
            for _kind, square in ENEMY_FORMATIONS[level]:
                col, row = parse_square(square)
                self.assertGreaterEqual(row, 5)
                self.assertLessEqual(row, 6)
                self.assertGreaterEqual(col, 0)
                self.assertLessEqual(col, 5)
                seen.append((col, row))
            self.assertEqual(len(seen), len(set(seen)))
            enemies = spawn_enemies(level)
            self.assertEqual([(piece.kind, piece.col, piece.row) for piece in enemies], [(piece.kind, piece.col, piece.row) for piece in spawn_enemies(level)])
            self.assertTrue(all(piece.color == "black" for piece in enemies))

    def test_levels_advance_one_at_a_time_and_pay_once(self):
        run = RunState.new(seed=21)
        for level in range(1, 6):
            self.assertEqual(run.level, level)
            self.assertEqual(run.phase, "preview")
            before = run.gold
            _win(run)
            self.assertEqual(run.phase, "victory")
            self.assertEqual(run.gold, before + VICTORY_GOLD)
            run.finish_victory()
            self.assertEqual(run.gold, before + VICTORY_GOLD)
            if level < 5:
                run.continue_from_victory()
                self.assertEqual(run.phase, "shop")
                run.continue_from_victory()
                self.assertEqual(run.phase, "shop")
                run.leave_shop()
                self.assertEqual(run.level, level + 1)
                self.assertEqual(run.phase, "preview")
                run.leave_shop()
                self.assertEqual(run.level, level + 1)
            else:
                run.continue_from_victory()
                self.assertEqual(run.phase, "complete")
                self.assertEqual(run.level, 5)
                run.continue_from_victory()
                self.assertEqual(run.phase, "complete")
                self.assertEqual(run.gold, STARTING_GOLD + VICTORY_GOLD * 5)

    def test_shop_purchases_survive_the_next_level(self):
        run = RunState.new(seed=6)
        _win(run)
        run.continue_from_victory()
        run.gold = 40
        self.assertIsNone(run.buy_army())
        self.assertIsNone(run.buy_piece())
        owned = len(run.army.pieces)
        capacity = run.army.capacity
        self.assertIsNone(run.reroll_shop())
        gold = run.gold
        run.leave_shop()
        self.assertEqual(run.level, 2)
        self.assertEqual(run.army.capacity, capacity)
        self.assertEqual(len(run.army.pieces), owned)
        self.assertEqual(run.gold, gold)
        self.assertEqual(run.army.capacity, 6)

    def test_captured_piece_is_gone_and_the_reserve_stays(self):
        run = RunState.new(seed=8)
        king = run.army.king()
        rook = next(piece for piece in run.army.pieces if piece.kind == "rook")
        pawn = next(piece for piece in run.army.pieces if piece.kind == "pawn")
        bishop = next(piece for piece in run.army.pieces if piece.kind == "bishop")
        run.enemies = [Piece(10001, "rook", "black", 0, 4)]
        blocked = run.blocked_squares()
        self.assertTrue(run.deployment.place(king, 5, 1, blocked, run.army.capacity, run.army))
        self.assertTrue(run.deployment.place(rook, 1, 1, blocked, run.army.capacity, run.army))
        self.assertTrue(run.deployment.place(pawn, 0, 2, blocked, run.army.capacity, run.army))
        self.assertTrue(run.start_battle())
        session = run.battle
        session.click(1, 1)
        session.click(1, 2)
        session.click(0, 4)
        session.click(0, 2)
        session.click(1, 2)
        session.click(0, 2)
        run.finish_victory()
        remaining = {piece.id for piece in run.army.pieces}
        self.assertNotIn(pawn.id, remaining)
        self.assertIn(king.id, remaining)
        self.assertIn(rook.id, remaining)
        self.assertIn(bishop.id, remaining)

    def test_restart_returns_to_the_opening_run(self):
        run = RunState.new(seed=12)
        run.gold = 0
        run.level = 5
        run.phase = "complete"
        run.army.capacity = 9
        fresh = run.restart()
        self.assertEqual(fresh.gold, STARTING_GOLD)
        self.assertEqual(fresh.level, 1)
        self.assertEqual(fresh.phase, "preview")
        self.assertEqual(fresh.army.capacity, 5)
        self.assertEqual(len(fresh.relics.owned), 0)

    def test_easing_endpoints(self):
        self.assertEqual(ease_out_cubic(0), 0)
        self.assertEqual(ease_out_cubic(1), 1)
        self.assertEqual(ease_in_out_cubic(0), 0)
        self.assertEqual(ease_in_out_cubic(1), 1)
        self.assertEqual(ease_in_out_cubic(0.5), 0.5)
        self.assertGreater(ease_out_cubic(0.5), 0.5)

    def test_slide_tracks_the_window_and_blocks_input(self):
        motion = TransitionManager()
        self.assertTrue(motion.start("slide_left", 1.0))
        self.assertFalse(motion.start("fade", 1.0))
        opened = motion.placement(200)
        self.assertEqual((opened.out_x, opened.in_x), (0, 200))
        motion.update(0.5)
        narrow = motion.placement(100)
        wide = motion.placement(300)
        self.assertEqual(narrow.out_x * 3, wide.out_x)
        self.assertEqual(narrow.in_x * 3, wide.in_x)
        self.assertLess(narrow.out_x, 0)
        self.assertGreater(narrow.in_x, 0)
        motion.update(0.5)
        self.assertFalse(motion.active)

    def test_transition_blocks_shop_until_it_settles(self):
        run = RunState.new(seed=9)
        run.phase = "victory"
        scene = SceneManager()
        self.assertTrue(scene.begin(run, run.continue_from_victory, "slide_left", 0.75))
        self.assertEqual(run.phase, "shop")
        self.assertEqual(scene.outgoing, "victory")
        self.assertEqual(scene.incoming, "shop")
        self.assertTrue(scene.blocks_pointer())
        self.assertFalse(scene.shop_interactive(run))
        self.assertFalse(scene.transition_to("preview", source="shop"))
        self.assertFalse(scene.begin(run, run.leave_shop, "slide_left", 0.65))
        self.assertEqual(run.level, 1)
        self.assertEqual(run.phase, "shop")
        scene.update(0.75)
        self.assertFalse(scene.blocks_pointer())
        self.assertTrue(scene.shop_interactive(run))
        self.assertIsNone(scene.outgoing)

    def test_battle_banner_blocks_then_the_result_banner_opens(self):
        scene = SceneManager()
        scene.begin_banner("battle_start")
        self.assertTrue(scene.blocks_pointer())
        scene.update(BATTLE_START_TIME - 0.01)
        self.assertTrue(scene.blocks_pointer())
        scene.update(0.02)
        self.assertFalse(scene.blocks_pointer())
        scene.begin_banner("level_complete")
        self.assertFalse(scene.result_ready())
        scene.update(VICTORY_BANNER_TIME + VICTORY_REWARD_TIME - 0.01)
        self.assertFalse(scene.result_ready())
        scene.update(0.02)
        self.assertTrue(scene.result_ready())

    def test_level_five_fades_to_the_run_complete_screen(self):
        run = RunState.new(seed=15)
        run.level = 5
        run.phase = "victory"
        scene = SceneManager()
        self.assertTrue(scene.begin(run, run.continue_from_victory, "fade", 0.7))
        self.assertEqual(run.phase, "complete")
        self.assertEqual(scene.motion.kind, "fade")
        self.assertTrue(scene.blocks_pointer())
        scene.update(0.7)
        self.assertEqual(run.phase, "complete")
        self.assertFalse(scene.blocks_pointer())


if __name__ == "__main__":
    unittest.main()
