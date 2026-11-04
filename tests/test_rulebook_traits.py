import random
import unittest

from ai.enemy_ai import EnemyAI
from ai.move_evaluator import allowed_moves
from game.board import Board
from game.move_generator import attacks_of, pseudo_moves_for
from game.move_validator import legal_moves
from game.piece import Piece
from game.run_state import RunState


def board(*pieces):
    return Board(list(pieces), capture_kings=True, enforce_check=False)


def place(run, piece, col, row):
    assert run.deployment.place(piece, col, row, run.blocked_squares(), run.army.capacity, run.army)


def army_piece(run, kind):
    return next(piece for piece in run.army.pieces if piece.kind == kind)


def targets(moves, col, row):
    return {(move.to_col, move.to_row) for move in moves if (move.from_col, move.from_row) == (col, row)}


class WantedTests(unittest.TestCase):
    def _field(self, personality):
        return board(
            Piece(1, "knight", "black", 2, 4, ai_trait=personality),
            Piece(2, "queen", "white", 3, 6),
            Piece(3, "pawn", "white", 4, 3, trait="wanted"),
        )

    def test_a_hunter_goes_for_the_wanted_piece(self):
        # without the trait a Hunter takes the queen here (test_enemy_traits)
        decision = EnemyAI().choose(self._field("hunter"), None, random.Random(3), "hard")
        self.assertEqual((decision.move.to_col, decision.move.to_row), (4, 3))
        self.assertEqual(decision.target, "pawn")

    def test_an_aggressive_enemy_still_takes_a_free_queen(self):
        decision = EnemyAI().choose(self._field("aggressive"), None, random.Random(3), "hard")
        self.assertEqual((decision.move.to_col, decision.move.to_row), (3, 6))


class GhostTests(unittest.TestCase):
    def test_a_ghost_slides_through_its_own_pieces_but_not_onto_them(self):
        field = board(
            Piece(1, "rook", "white", 0, 1, trait="ghost"),
            Piece(2, "pawn", "white", 0, 2),
            Piece(3, "pawn", "black", 0, 4),
        )
        ghost = field.piece_at(0, 1)
        self.assertEqual(targets(pseudo_moves_for(field, ghost), 0, 1) - {(1, 1), (2, 1), (3, 1), (4, 1), (5, 1)}, {(0, 3), (0, 4)})
        self.assertIn((0, 4), attacks_of(field, ghost))

    def test_a_normal_rook_is_still_blocked(self):
        field = board(Piece(1, "rook", "white", 0, 1), Piece(2, "pawn", "white", 0, 2))
        self.assertNotIn((0, 3), targets(pseudo_moves_for(field, field.piece_at(0, 1)), 0, 1))


class ExplosiveTests(unittest.TestCase):
    def test_the_enemy_that_captures_an_explosive_piece_dies_too(self):
        run = RunState.new(seed=35)
        king, pawn = army_piece(run, "king"), army_piece(run, "pawn")
        run.traits.assign_trait(pawn.id, "explosive")
        rook = Piece(10001, "rook", "black", 0, 4)
        walker = Piece(10002, "pawn", "black", 5, 5)
        run.enemies = [rook, walker]
        place(run, king, 2, 1)
        place(run, pawn, 0, 2)
        self.assertTrue(run.start_battle())
        session = run.battle
        session.click(2, 1)
        session.click(3, 1)
        session.click(0, 4)
        session.click(0, 2)
        board_now = session.game.board
        self.assertIsNone(board_now.piece_by_id(pawn.id))
        self.assertIsNone(board_now.piece_by_id(rook.id))
        self.assertIsNone(board_now.piece_at(0, 2))
        self.assertIsNone(session.outcome)
        self.assertEqual(session.game.turns.current, "white")

    def test_blowing_up_the_last_enemy_wins_the_battle(self):
        run = RunState.new(seed=36)
        king, pawn = army_piece(run, "king"), army_piece(run, "pawn")
        run.traits.assign_trait(pawn.id, "explosive")
        rook = Piece(10001, "rook", "black", 0, 4)
        run.enemies = [rook]
        place(run, king, 2, 1)
        place(run, pawn, 0, 2)
        self.assertTrue(run.start_battle())
        session = run.battle
        session.click(2, 1)
        session.click(3, 1)
        session.click(0, 4)
        session.click(0, 2)
        self.assertEqual(session.outcome, "victory")


class MagnetTests(unittest.TestCase):
    def test_enemies_next_to_a_magnet_cannot_move_backward(self):
        run = RunState.new(seed=37)
        king, knight = army_piece(run, "king"), army_piece(run, "knight")
        run.traits.assign_trait(knight.id, "magnet")
        stuck = Piece(10001, "rook", "black", 2, 3)
        free = Piece(10002, "rook", "black", 5, 3)
        run.enemies = [stuck, free]
        place(run, king, 0, 1)
        place(run, knight, 2, 2)
        self.assertTrue(run.start_battle())
        session = run.battle
        field = session.game.board
        for moves in (session.rules.filter_moves(field, legal_moves(field, "black")), allowed_moves(field, session.rules, "black")):
            stuck_to = targets(moves, 2, 3)
            self.assertFalse(any(row > 3 for _col, row in stuck_to))
            self.assertIn((2, 2), stuck_to)
            self.assertIn((3, 3), stuck_to)
            self.assertIn((5, 4), targets(moves, 5, 3))


if __name__ == "__main__":
    unittest.main()
