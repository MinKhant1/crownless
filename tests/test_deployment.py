import unittest

import pygame

from game.piece import Piece
from game.run_state import RunState
from rendering.layout import build_layout
from scenes.deployment_scene import DeploymentScene


class DeploymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.display.set_mode((64, 64), pygame.HIDDEN)

    def test_first_level_deploys_the_whole_starting_army(self):
        first = RunState.new(seed=4)
        second = RunState.new(seed=4)
        first.begin_deployment()
        second.begin_deployment()
        self.assertEqual(first.deployment.placed, second.deployment.placed)
        self.assertEqual(len(first.deployment.placed), 6)
        self.assertEqual(first.deployment.non_king_count(first.army), 5)
        king = first.army.king()
        self.assertIsNotNone(king)
        self.assertIn(king.id, first.deployment.placed)
        squares = list(first.deployment.placed.values())
        self.assertEqual(len(squares), len(set(squares)))
        self.assertTrue(all(row in (1, 2) and 0 <= col <= 5 for col, row in squares))
        self.assertTrue(first.validate_deployment())
        ids = set(first.deployment.placed)
        self.assertEqual(ids, {piece.id for piece in first.army.pieces})

    def test_reposition_swap_reserve_and_reset(self):
        run = RunState.new(seed=6)
        gold = run.gold
        relics = len(run.relics.owned)
        capacity = run.army.capacity
        run.begin_deployment()
        snapshot = dict(run.deployment.placed)
        knight = next(piece for piece in run.army.pieces if piece.kind == "knight")
        queen = next(piece for piece in run.army.pieces if piece.kind == "queen")
        knight.trait = "wanted"
        used = set(snapshot.values())
        target = next((col, row) for row in (1, 2) for col in range(6) if (col, row) not in used)
        self.assertTrue(run.reposition_piece(knight.id, target))
        self.assertEqual(run.deployment.placed[knight.id], target)
        queen_square = run.deployment.placed[queen.id]
        self.assertTrue(run.swap_deployed_pieces(knight.id, queen.id))
        self.assertEqual(run.deployment.placed[knight.id], queen_square)
        self.assertEqual(run.deployment.placed[queen.id], target)
        extra = run.army.create("pawn")
        extra.trait = "golden"
        self.assertNotIn(extra.id, run.deployment.placed)
        self.assertFalse(run.deployment.place(extra, 5, 2, run.blocked_squares(), run.army.capacity, run.army))
        self.assertTrue(run.replace_with_reserve(extra.id, knight.id))
        self.assertEqual(run.deployment.placed[extra.id], queen_square)
        self.assertNotIn(knight.id, run.deployment.placed)
        self.assertIn(extra, run.army.pieces)
        self.assertIn(knight, run.army.pieces)
        self.assertEqual(extra.trait, "golden")
        self.assertEqual(knight.trait, "wanted")
        king = run.army.king()
        self.assertFalse(run.replace_with_reserve(knight.id, king.id))
        self.assertIn(king.id, run.deployment.placed)
        self.assertEqual(run.notice, "King stays")
        run.reset_formation()
        self.assertEqual(run.deployment.placed, snapshot)
        self.assertEqual(run.gold, gold)
        self.assertEqual(len(run.relics.owned), relics)
        self.assertEqual(run.army.capacity, capacity)
        self.assertEqual(run.level, 1)
        self.assertEqual(knight.trait, "wanted")

    def test_start_battle_keeps_the_arranged_squares(self):
        run = RunState.new(seed=8)
        run.begin_deployment()
        rook = next(piece for piece in run.army.pieces if piece.kind == "rook")
        rook.trait = "wooden"
        used = set(run.deployment.placed.values())
        target = next((col, row) for row in (1, 2) for col in range(6) if (col, row) not in used)
        self.assertTrue(run.reposition_piece(rook.id, target))
        arranged = dict(run.deployment.placed)
        run.enemies = []
        self.assertTrue(run.start_battle())
        self.assertEqual(run.phase, "battle")
        self.assertEqual(run.deployment.placed, arranged)
        whites = [piece for piece in run.battle.game.board.pieces if piece.color == "white"]
        self.assertEqual(len(whites), len(arranged))
        for piece in whites:
            self.assertEqual((piece.col, piece.row), arranged[piece.id])
        found = next(piece for piece in whites if piece.id == rook.id)
        self.assertEqual(found.trait, "wooden")
        self.assertEqual(run.battle.game.turns.current, "white")

    def test_survivors_keep_squares_and_captured_pieces_stay_gone(self):
        run = RunState.new(seed=11)
        run.begin_deployment()
        king = run.army.king()
        rook = next(piece for piece in run.army.pieces if piece.kind == "rook")
        pawn = next(piece for piece in run.army.pieces if piece.kind == "pawn")
        bishop = next(piece for piece in run.army.pieces if piece.kind == "bishop")
        run.deployment.clear()
        blocked = run.blocked_squares()
        self.assertTrue(run.deployment.place(king, 5, 1, blocked, run.army.capacity, run.army))
        self.assertTrue(run.deployment.place(rook, 1, 1, blocked, run.army.capacity, run.army))
        self.assertTrue(run.deployment.place(pawn, 0, 2, blocked, run.army.capacity, run.army))
        self.assertTrue(run.deployment.place(bishop, 2, 1, blocked, run.army.capacity, run.army))
        remembered = {king.id: (5, 1), rook.id: (1, 1), bishop.id: (2, 1)}
        run.enemies = [Piece(10001, "rook", "black", 0, 4)]
        self.assertTrue(run.start_battle())
        session = run.battle
        session.click(1, 1)
        session.click(1, 2)
        session.click(0, 4)
        session.click(0, 2)
        session.click(1, 2)
        session.click(0, 2)
        run.finish_victory()
        self.assertNotIn(pawn.id, {piece.id for piece in run.army.pieces})
        run.continue_from_victory()
        run.leave_shop()
        self.assertEqual(run.level, 2)
        run.begin_deployment()
        self.assertNotIn(pawn.id, run.deployment.placed)
        for piece_id, square in remembered.items():
            self.assertEqual(run.deployment.placed[piece_id], square)
        self.assertLessEqual(run.deployment.non_king_count(run.army), run.army.capacity)

    def test_every_level_gets_a_valid_formation(self):
        run = RunState.new(seed=15)
        for level in range(1, 6):
            self.assertEqual(run.level, level)
            self.assertEqual(run.phase, "preview")
            run.begin_deployment()
            self.assertTrue(run.validate_deployment())
            squares = list(run.deployment.placed.values())
            self.assertEqual(len(squares), len(set(squares)))
            self.assertTrue(all(row in (1, 2) for _col, row in squares))
            self.assertIn(run.army.king().id, run.deployment.placed)
            self.assertLessEqual(run.deployment.non_king_count(run.army), run.army.capacity)
            self.assertGreater(run.deployment.non_king_count(run.army), 0)
            run.enemies = []
            arranged = dict(run.deployment.placed)
            self.assertTrue(run.start_battle())
            self.assertEqual(run.deployment.placed, arranged)
            run.battle.evaluate()
            run.finish_victory()
            if level < 5:
                run.continue_from_victory()
                run.leave_shop()

    def test_clicks_reposition_and_do_not_remove_the_king(self):
        run = RunState.new(seed=2)
        run.begin_deployment()
        scene = DeploymentScene()
        layout = build_layout(1280, 900)
        window = (1280, 900)
        king = run.army.king()
        knight = next(piece for piece in run.army.pieces if piece.kind == "knight")
        king_at = layout.square_rect(*run.deployment.placed[king.id]).center
        knight_at = layout.square_rect(*run.deployment.placed[knight.id]).center
        self._click(scene, run, king_at, layout, window)
        self.assertEqual(run.selected_piece_id, king.id)
        self._click(scene, run, king_at, layout, window)
        self.assertIsNone(run.selected_piece_id)
        self.assertIn(king.id, run.deployment.placed)
        knight_square = run.deployment.placed[knight.id]
        king_square = run.deployment.placed[king.id]
        self._click(scene, run, knight_at, layout, window)
        self._click(scene, run, king_at, layout, window)
        self.assertEqual(run.deployment.placed[knight.id], king_square)
        self.assertEqual(run.deployment.placed[king.id], knight_square)
        tray = scene.panels(window, layout)[1]
        scene.press_id = king.id
        scene.press_pos = king_at
        scene.dragging = True
        scene._drop(run, tray.center, layout, tray)
        self.assertEqual(run.notice, "King stays")
        self.assertIn(king.id, run.deployment.placed)
        _reset, start = scene.command_buttons(layout)
        self.assertLessEqual(start.bottom, window[1])
        self.assertLessEqual(start.right, window[0])
        arranged = dict(run.deployment.placed)
        self._click(scene, run, start.center, layout, window)
        self.assertEqual(run.phase, "battle")
        self.assertEqual(run.deployment.placed, arranged)

    def _click(self, scene: DeploymentScene, run: RunState, pos: tuple[int, int], layout, window) -> None:
        scene.on_press(run, pos, layout, window)
        scene.on_release(run, pos, layout, window)


if __name__ == "__main__":
    unittest.main()
