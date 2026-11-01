import random
import unittest

from ai.ai_config import set_difficulty
from ai.enemy_ai import EnemyAI, EnemyTurn
from ai.move_evaluator import allowed_moves
from game.battle_rules import BattleRules
from game.battle_session import BattleSession
from game.board import Board
from game.game import Game
from game.piece import Piece
from game.relics.effects.castle_wall import _blocks


def piece(piece_id, kind, color, col, row, trait=None):
    return Piece(piece_id, kind, color, col, row, trait=trait)


def battle_board(pieces):
    return Board(pieces, capture_kings=True, enforce_check=False)


class ChoiceTests(unittest.TestCase):
    def setUp(self):
        set_difficulty("hard")
        self.ai = EnemyAI()
        self.rng = random.Random(7)
    def tearDown(self):
        set_difficulty("normal")

    def test_queen_capture_beats_a_safe_pawn_capture(self):
        board = battle_board([
            piece(1, "knight", "black", 2, 4),
            piece(2, "queen", "white", 3, 6),
            piece(3, "pawn", "white", 4, 3),
        ])
        decision = self.ai.choose(board, None, self.rng, "hard")
        self.assertEqual((decision.move.to_col, decision.move.to_row), (3, 6))
        self.assertIn("Queen", decision.report)
        self.assertIn("Score:", decision.report)

    def test_queen_is_not_traded_for_a_pawn(self):
        board = battle_board([
            piece(1, "queen", "black", 3, 3),
            piece(2, "pawn", "white", 3, 4),
            piece(3, "rook", "white", 0, 4),
        ])
        decision = self.ai.choose(board, None, self.rng, "hard")
        self.assertNotEqual((decision.move.to_col, decision.move.to_row), (3, 4))
        self.assertIn(decision.move, allowed_moves(board, None, "black"))

    def test_candidates_are_legal_on_the_small_board(self):
        board = battle_board([
            piece(1, "queen", "black", 0, 1),
            piece(2, "pawn", "white", 5, 6),
        ])
        decision = self.ai.choose(board, None, self.rng, "hard")
        legal = allowed_moves(board, None, "black")
        self.assertIn(decision.move, legal)
        for item in decision.scored:
            self.assertIn(item.move, legal)
            self.assertGreaterEqual(item.move.to_col, 0)
            self.assertLess(item.move.to_col, 6)
            self.assertGreaterEqual(item.move.to_row, 1)
            self.assertLessEqual(item.move.to_row, 6)

    def test_no_legal_move_is_reported_without_a_choice(self):
        board = battle_board([piece(1, "king", "white", 0, 1)])
        decision = self.ai.choose(board, None, self.rng, "hard")
        self.assertIsNone(decision.move)
        self.assertEqual(decision.scored, [])
        self.assertIn("No legal move", decision.report)

    def test_castle_wall_and_wooden_locks_are_respected(self):
        rules = BattleRules()
        rules.capture_blocks.append(_blocks)
        board = battle_board([
            piece(1, "knight", "black", 2, 4),
            piece(2, "rook", "white", 4, 6),
            piece(3, "pawn", "white", 4, 5),
            piece(4, "pawn", "white", 0, 5),
        ])
        destinations = {(move.to_col, move.to_row) for move in allowed_moves(board, rules, "black")}
        self.assertNotIn((4, 5), destinations)
        self.assertIn((0, 5), destinations)
        decision = self.ai.choose(board, rules, self.rng, "hard")
        self.assertEqual((decision.move.to_col, decision.move.to_row), (0, 5))
        locked = BattleRules()
        locked.lock(1, 2)
        stuck = battle_board([
            piece(1, "knight", "black", 2, 4),
            piece(5, "pawn", "black", 4, 4),
            piece(2, "queen", "white", 3, 6),
        ])
        decision = EnemyAI().choose(stuck, locked, self.rng, "hard")
        self.assertEqual((decision.move.from_col, decision.move.from_row), (4, 4))

    def test_reachable_rook_beats_an_unreachable_queen(self):
        board = battle_board([
            piece(1, "knight", "black", 2, 4),
            piece(2, "rook", "white", 3, 6),
            piece(3, "queen", "white", 0, 1),
        ])
        decision = self.ai.choose(board, None, self.rng, "hard")
        self.assertEqual((decision.move.to_col, decision.move.to_row), (3, 6))

    def test_king_capture_is_worth_a_hanging_queen(self):
        board = battle_board([
            piece(1, "queen", "black", 3, 3),
            piece(2, "king", "white", 3, 2),
            piece(3, "rook", "white", 0, 2),
            piece(4, "pawn", "white", 4, 4),
        ])
        decision = self.ai.choose(board, None, self.rng, "hard")
        self.assertEqual((decision.move.to_col, decision.move.to_row), (3, 2))
        self.assertIn("King", decision.report)

    def test_tied_scores_follow_the_seed(self):
        board = battle_board([
            piece(1, "pawn", "black", 1, 4),
            piece(2, "pawn", "black", 3, 4),
            piece(3, "king", "white", 2, 1),
        ])
        first = EnemyAI().choose(board, None, random.Random(4), "hard")
        second = EnemyAI().choose(board, None, random.Random(4), "hard")
        self.assertEqual(first.move, second.move)
        best = max(item.score for item in first.scored)
        tied = [item for item in first.scored if item.score == best]
        self.assertGreaterEqual(len(tied), 2)
        self.assertIn(first.move, [item.move for item in tied])


class TurnTests(unittest.TestCase):
    def test_one_enemy_turn_plays_a_single_move(self):
        rules = BattleRules()
        session = _session([
            piece(1, "pawn", "black", 2, 4),
            piece(2, "king", "white", 0, 1),
        ], rules)
        turn = EnemyTurn()
        turn.update(session, 1.0, random.Random(1))
        self.assertEqual(session.game.turns.current, "black")
        self.assertEqual(session.game.board.piece_by_id(1).row, 4)
        turn.update(session, 1.0, random.Random(1))
        self.assertEqual(session.game.turns.current, "white")
        self.assertLess(session.game.board.piece_by_id(1).row, 4)
        row = session.game.board.piece_by_id(1).row
        turn.update(session, 1.0, random.Random(1))
        self.assertEqual(session.game.board.piece_by_id(1).row, row)
        self.assertEqual(session.game.turns.current, "white")


def _session(pieces, rules):
    game = Game(
        battle_board(pieces),
        starting="black",
        mode="crownless",
        move_filter=rules.filter_moves,
        on_turn_end=rules.spend,
    )

    class Session:
        def __init__(self):
            self.game = game
            self.rules = rules
            self.outcome = None

        def click(self, col, row):
            BattleSession.click(self, col, row)

        def evaluate(self):
            BattleSession.evaluate(self)

    return Session()
