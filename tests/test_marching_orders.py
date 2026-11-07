import unittest

from game.board import Board
from game.move import Move
from game.move_generator import attacks_of, pseudo_moves_for
from game.move_validator import legal_moves
from game.piece import Piece
from game.relics.relic_data import relic_by_id, shop_relic_ids
from game.run_state import RunState
from tests.test_relics import place


class MarchingOrdersTests(unittest.TestCase):
    def board(self, *blockers, enabled=True, trait=None):
        pawn = Piece(1, "pawn", "white", 2, 3, has_moved=True, trait=trait)
        return Board([pawn, *blockers], enforce_check=False, marching_orders=enabled), pawn

    def destinations(self, board, pawn):
        return {(m.to_col, m.to_row) for m in pseudo_moves_for(board, pawn)}

    def test_repeated_two_square_moves_and_board_copy(self):
        board, pawn = self.board()
        board.apply_move(Move(2, 3, 2, 4))
        self.assertIn((2, 6), self.destinations(board, pawn))
        move = next(m for m in legal_moves(board, "white") if m.to_row == 6)
        self.assertIsNotNone(move.promotion)
        clone = board.copy()
        self.assertTrue(clone.marching_orders)
        self.assertEqual(legal_moves(board, "white"), legal_moves(clone, "white"))

    def test_requires_relic_and_does_not_buff_enemies(self):
        board, pawn = self.board(enabled=False)
        self.assertNotIn((2, 5), self.destinations(board, pawn))
        board.marching_orders = True
        pawn.color = "black"
        self.assertEqual(self.destinations(board, pawn), {(2, 2)})

    def test_clear_path_required_even_for_ghosts(self):
        for color in ("white", "black"):
            for trait in (None, "ghost"):
                with self.subTest(color=color, trait=trait):
                    board, pawn = self.board(Piece(2, "rook", color, 2, 4), trait=trait)
                    self.assertEqual(self.destinations(board, pawn), set())
                    board, pawn = self.board(Piece(2, "rook", color, 2, 5), trait=trait)
                    self.assertEqual(self.destinations(board, pawn), {(2, 4)})

    def test_diagonal_captures_and_attacks_unchanged(self):
        board, pawn = self.board(Piece(2, "rook", "black", 3, 4), Piece(3, "rook", "black", 1, 5))
        self.assertEqual(self.destinations(board, pawn), {(2, 4), (2, 5), (3, 4)})
        self.assertEqual(set(attacks_of(board, pawn)), {(1, 4), (3, 4)})

    def test_registered_available_and_applied_at_battle_start(self):
        self.assertIn("marching_orders", shop_relic_ids())
        self.assertEqual(relic_by_id("marching_orders").art, "marching_order.png")
        run = RunState.new(seed=4)
        self.assertIsNotNone(run.relics.acquire("marching_orders"))
        self.assertIsNone(run.relics.acquire("marching_orders"))
        king = run.army.king()
        pawn = next(p for p in run.army.pieces if p.kind == "pawn")
        place(run, king, 0, 1)
        place(run, pawn, 2, 2)
        self.assertTrue(run.start_battle())
        board = run.battle.game.board
        self.assertTrue(board.marching_orders)
        deployed = board.piece_by_id(pawn.id)
        deployed.has_moved = True
        self.assertIn((2, 4), self.destinations(board, deployed))
