import unittest

import pygame

from game.army_roster import army_entries
from game.run_state import RunState
from game.scene_manager import SceneManager
from rendering.army_panel import ArmyPanel
from rendering.layout import build_layout, square_at
from scenes.battle_scene import handle_battle_click
from scenes.deployment_scene import DeploymentScene


class ArmySortTests(unittest.TestCase):
    def test_king_leads_and_the_rest_follow_piece_value(self):
        run = RunState.new(seed=1)
        run.army.pieces.reverse()
        kinds = [entry.piece.kind for entry in army_entries(run)]
        self.assertEqual(kinds, ["king", "queen", "rook", "bishop", "knight", "pawn"])

    def test_different_traits_or_statuses_stay_separate(self):
        run = RunState.new(seed=2)
        golden = run.army.create("pawn")
        golden.trait = "golden"
        first = run.army.create("pawn")
        second = run.army.create("pawn")
        run.begin_deployment()
        entries = [entry for entry in army_entries(run) if entry.piece.kind == "pawn"]
        self.assertGreaterEqual(len(entries), 2)
        self.assertTrue(any(entry.piece.trait == "golden" and entry.count == 1 for entry in entries))
        reserve = [entry for entry in entries if entry.status == "Reserve" and entry.piece.trait is None]
        self.assertEqual(len(reserve), 1)
        self.assertEqual(reserve[0].count, 2)
        self.assertIn(first.id, reserve[0].ids())
        self.assertIn(second.id, reserve[0].ids())
        self.assertNotIn(golden.id, reserve[0].ids())


class BattleLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((64, 64), pygame.HIDDEN)

    def test_columns_align_the_square_board_at_each_size(self):
        for size in ((1440, 900), (1280, 720), (1280, 900), (960, 720)):
            layout = build_layout(*size)
            window = pygame.Rect(0, 0, *size)
            self.assertTrue(window.contains(layout.left))
            self.assertTrue(window.contains(layout.right))
            self.assertTrue(window.contains(layout.frame))
            self.assertTrue(window.contains(layout.board))
            self.assertTrue(window.contains(layout.start))
            self.assertTrue(window.contains(layout.menu))
            self.assertTrue(window.contains(layout.options))
            self.assertAlmostEqual(layout.left.w / size[0], 0.25, delta=0.05)
            self.assertAlmostEqual(layout.right.w / size[0], 0.25, delta=0.05)
            self.assertGreater(layout.center.w / size[0], 0.42)
            self.assertEqual(layout.board.w, layout.board.h)
            self.assertEqual(layout.board.w, layout.square * 6)
            self.assertGreater(layout.square, 36)
            self.assertFalse(layout.left.colliderect(layout.board))
            self.assertFalse(layout.right.colliderect(layout.board))
            self.assertFalse(layout.relics.colliderect(layout.board))
            self.assertLessEqual(layout.relics.bottom, layout.frame.top)
            self.assertLess(layout.frame.bottom, layout.start.top)
            self.assertGreater(layout.menu.y, layout.left.centery)
            self.assertLess(layout.menu.bottom, layout.options.top)
            self.assertLessEqual(layout.turn.bottom, size[1])
            self.assertTrue(layout.left.contains(layout.menu))
            self.assertTrue(layout.left.contains(layout.options))
            for col in range(6):
                for row in range(1, 7):
                    point = layout.square_rect(col, row).center
                    self.assertEqual(square_at(layout, point), (col, row))
            self.assertIsNone(square_at(layout, layout.left.center))
            self.assertIsNone(square_at(layout, layout.right.center))

    def test_resizing_keeps_the_board_square_and_inside_the_center(self):
        wide = build_layout(1440, 900)
        short = build_layout(1280, 720)
        self.assertNotEqual(wide.board.size, short.board.size)
        for layout in (wide, short):
            self.assertTrue(layout.center.contains(layout.board))
            self.assertEqual(layout.board.w, layout.board.h)
            self.assertLess(layout.left.right, layout.frame.left)
            self.assertGreater(layout.right.left, layout.frame.right)

    def test_army_rows_live_in_the_right_panel(self):
        run = RunState.new(seed=3)
        reserve = run.army.create("pawn")
        run.begin_deployment()
        layout = build_layout(1440, 900)
        panel = ArmyPanel()
        rows = panel.rows(run, layout)
        shown = {entry.piece.id for entry, _rect in rows}
        self.assertIn(reserve.id, shown)
        self.assertNotIn(run.army.king().id, shown)
        for piece in run.army.pieces:
            if piece.id in run.deployment.placed:
                self.assertNotIn(piece.id, shown)
        for _entry, rect in rows:
            self.assertTrue(layout.right.contains(rect))
            self.assertFalse(rect.colliderect(layout.board))
            self.assertIsNone(square_at(layout, rect.center))

    def test_panel_selection_swaps_a_reserve_piece(self):
        run = RunState.new(seed=4)
        extra = run.army.create("pawn")
        extra.trait = "wooden"
        run.begin_deployment()
        self.assertNotIn(extra.id, run.deployment.placed)
        scene = DeploymentScene()
        layout = build_layout(1440, 900)
        window = layout.window
        queen = next(piece for piece in run.army.pieces if piece.kind == "queen")
        knight = next(piece for piece in run.army.pieces if piece.kind == "knight")
        self._click(scene, run, layout.square_rect(*run.deployment.placed[queen.id]).center, layout, window)
        self.assertEqual(run.selected_piece_id, queen.id)
        knight_square = run.deployment.placed[knight.id]
        self._click(scene, run, self._row(scene, run, layout, extra.id), layout, window)
        self.assertEqual(run.selected_piece_id, extra.id)
        self._click(scene, run, layout.square_rect(*knight_square).center, layout, window)
        self.assertEqual(run.deployment.placed[extra.id], knight_square)
        self.assertNotIn(knight.id, run.deployment.placed)
        self.assertIn(knight.id, {piece.id for piece in run.army.pieces})

    def test_battle_locks_the_army_panel(self):
        run = RunState.new(seed=6)
        run.begin_deployment()
        pawn = next(piece for piece in run.army.pieces if piece.kind == "pawn")
        square = run.deployment.placed[pawn.id]
        self.assertTrue(run.start_battle())
        board_piece = run.battle.game.board.piece_at(*square)
        run.battle.game.board.pieces.remove(board_piece)
        captured = next(entry for entry in army_entries(run) if pawn.id in entry.ids())
        self.assertEqual(captured.status, "Captured")
        scene = DeploymentScene()
        layout = build_layout(1280, 720)
        before = dict(run.deployment.placed)
        count = len(run.battle.game.board.pieces)
        row = self._row(scene, run, layout, pawn.id)
        scene.on_press(run, row, layout, layout.window)
        scene.on_release(run, row, layout, layout.window)
        handle_battle_click(run, row, layout, layout.window)
        self.assertEqual(run.deployment.placed, before)
        self.assertIsNone(run.selected_piece_id)
        self.assertEqual(len(run.battle.game.board.pieces), count)
        self.assertFalse(scene.army.accepts(run))

    def test_long_armies_scroll_inside_the_panel(self):
        run = RunState.new(seed=7)
        for index in range(14):
            piece = run.army.create("pawn")
            piece.trait = f"mark-{index}"
        layout = build_layout(1280, 720)
        panel = ArmyPanel()
        panel.rows(run, layout)
        panel.on_wheel(run, layout, layout.right.center, -1)
        self.assertGreater(panel.scroll, 0)
        held = panel.scroll
        self.assertFalse(panel.on_wheel(run, layout, layout.board.center, -3))
        self.assertEqual(panel.scroll, held)
        scrolled = panel.scroll
        panel.on_wheel(run, layout, layout.right.center, 1)
        self.assertLess(panel.scroll, scrolled)

    def test_columns_slide_with_the_battle_scene(self):
        run = RunState.new(seed=8)
        run.begin_deployment()
        layout = build_layout(1440, 900)
        window = pygame.Rect(0, 0, *layout.window)
        for rect in (layout.left, layout.center, layout.right, layout.frame, layout.relics, layout.start):
            self.assertTrue(window.contains(rect))
        scene = SceneManager()
        self.assertTrue(scene.begin(run, run.start_battle, "slide_left", 0.78))
        self.assertEqual(scene.outgoing, "deployment")
        self.assertEqual(scene.incoming, "battle")
        self.assertTrue(scene.blocks_pointer())
        self.assertEqual(run.phase, "battle")
        scene.update(0.78)
        self.assertFalse(scene.motion.active)
        self.assertFalse(scene.blocks_pointer())

    def _row(self, scene: DeploymentScene, run: RunState, layout, piece_id: int) -> tuple[int, int]:
        for entry, rect in scene.army.rows(run, layout):
            if piece_id in entry.ids():
                return rect.center
        self.fail(f"missing row {piece_id}")

    def _click(self, scene: DeploymentScene, run: RunState, pos, layout, window) -> None:
        scene.on_press(run, pos, layout, window)
        scene.on_release(run, pos, layout, window)
