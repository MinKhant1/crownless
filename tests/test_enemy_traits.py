import random
import unittest

import pygame

from ai.enemy_ai import EnemyAI
from ai.trait_assignment import assign_personalities, assign_spawned, battle_personality, coming_battle, living_trait_counts
from ai.trait_definitions import AI_TRAITS
from game.battle_rules import BattleRules
from game.board import Board, CaptureRecord
from game.piece import Piece
from game.run_state import RunState
from rendering.enemy_tags import personality_layout, sidebar_anchors
from rendering.layout import build_layout


def piece(piece_id, kind, color, col, row, ai_trait=None):
    return Piece(piece_id, kind, color, col, row, ai_trait=ai_trait)


def board(*pieces):
    return Board(list(pieces), capture_kings=True, enforce_check=False)


class AssignmentTests(unittest.TestCase):
    def test_each_enemy_receives_one_trait_from_the_seed(self):
        first = RunState.new(seed=11)
        second = RunState.new(seed=11)
        self.assertGreaterEqual(len(first.enemies), 1)
        self.assertTrue(all(enemy.ai_trait == first.enemy_trait for enemy in first.enemies))
        self.assertEqual(first.enemy_trait, battle_personality(first.seed, first.level))
        self.assertEqual(first.enemy_trait, second.enemy_trait)
        self.assertTrue(all(piece.ai_trait is None for piece in first.army.pieces))
        kept = first.enemies[0].ai_trait
        first.enemies[0].ai_trait = "guardian"
        assign_personalities(first.enemies, first.seed, first.level)
        self.assertEqual(first.enemies[0].ai_trait, "guardian")
        first.enemies[0].ai_trait = kept
        first.begin_deployment()
        self.assertTrue(first.start_battle())
        playing = [piece.ai_trait for piece in first.battle.game.board.pieces if piece.color == "black"]
        self.assertEqual(playing, [enemy.ai_trait for enemy in first.enemies])
        self.assertTrue(playing)
        self.assertTrue(all(trait == first.battle.enemy_trait for trait in playing))
        remembered = first.battle.enemy_trait
        first.phase = "deployment"
        first.battle = None
        self.assertTrue(first.start_battle())
        self.assertEqual(first.battle.enemy_trait, remembered)
        first.enemy_trait = "guardian"
        for enemy in first.enemies:
            enemy.ai_trait = "aggressive"
        first.phase = "deployment"
        first.battle = None
        self.assertTrue(first.start_battle())
        self.assertEqual(first.battle.enemy_trait, "guardian")
        restored = [piece.ai_trait for piece in first.battle.game.board.pieces if piece.color == "black"]
        self.assertTrue(restored)
        self.assertTrue(all(trait == "guardian" for trait in restored))

    def test_a_new_enemy_is_tagged_and_a_player_piece_is_not(self):
        enemy = Piece(50, "knight", "black", 0, 6)
        ally = Piece(3, "pawn", "white", 0, 1)
        self.assertIn(assign_spawned(enemy, 4, 2), AI_TRAITS)
        self.assertIsNone(assign_spawned(ally, 4, 2))
        self.assertEqual(assign_spawned(enemy, 9, 2), enemy.ai_trait)

    def test_the_trait_stays_on_the_piece_after_a_move_and_a_copy(self):
        from ai.move_evaluator import allowed_moves

        pawn = piece(1, "pawn", "black", 2, 4, "hunter")
        field = board(pawn, piece(2, "king", "white", 0, 1))
        field.apply_move(allowed_moves(field, None, "black")[0])
        self.assertEqual(field.piece_by_id(1).ai_trait, "hunter")
        self.assertEqual(field.piece_by_id(1).copy().ai_trait, "hunter")


class PersonalityTests(unittest.TestCase):
    def setUp(self):
        self.ai = EnemyAI()
        self.rng = random.Random(3)

    def test_hunter_takes_the_queen_when_the_capture_is_safe(self):
        field = board(
            piece(1, "knight", "black", 2, 4, "hunter"),
            piece(2, "queen", "white", 3, 6),
            piece(3, "pawn", "white", 4, 3),
        )
        decision = self.ai.choose(field, None, self.rng, "hard")
        self.assertEqual((decision.move.to_col, decision.move.to_row), (3, 6))

    def test_guardian_blocks_an_attack_on_the_queen(self):
        queen = piece(2, "queen", "black", 3, 4, "guardian")
        knight = piece(1, "knight", "black", 3, 6, "guardian")
        field = board(knight, queen, piece(3, "rook", "white", 0, 4))
        rules = BattleRules()
        rules.lock(queen.id, 2)
        decision = self.ai.choose(field, rules, self.rng, "hard")
        self.assertEqual((decision.move.from_col, decision.move.from_row), (3, 6))
        self.assertEqual((decision.move.to_col, decision.move.to_row), (2, 4))

    def test_vengeful_chases_the_latest_surviving_captor(self):
        killer = piece(8, "knight", "white", 0, 4)
        field = board(
            piece(1, "rook", "black", 0, 2, "vengeful"),
            killer,
            piece(3, "pawn", "white", 3, 2),
        )
        fallen = piece(4, "pawn", "black", None, None)
        field.capture_log.append(CaptureRecord(fallen, killer.id, 1, 3))
        decision = self.ai.choose(field, None, self.rng, "hard")
        self.assertEqual((decision.move.to_col, decision.move.to_row), (0, 4))

    def test_berserker_accepts_the_trade_aggressive_refuses(self):
        pieces = [
            piece(1, "bishop", "black", 2, 2),
            piece(2, "pawn", "white", 4, 4),
            piece(3, "rook", "white", 4, 6),
            piece(4, "pawn", "black", 1, 3),
        ]
        reckless = board(*(item.copy() for item in pieces))
        reckless.piece_by_id(1).ai_trait = "berserker"
        cautious = board(*(item.copy() for item in pieces))
        cautious.piece_by_id(1).ai_trait = "aggressive"
        rules = BattleRules()
        rules.lock(4, 2)
        taken = EnemyAI().choose(reckless, rules, self.rng, "hard")
        refused = EnemyAI().choose(cautious, rules, self.rng, "hard")
        self.assertEqual((taken.move.to_col, taken.move.to_row), (4, 4))
        self.assertNotEqual((refused.move.to_col, refused.move.to_row), (4, 4))

    def test_a_battle_trait_scores_every_enemy_move(self):
        field = board(
            piece(1, "pawn", "black", 0, 4, "aggressive"),
            piece(2, "knight", "black", 1, 4, "guardian"),
            piece(3, "king", "white", 0, 1),
        )
        decision = EnemyAI().choose(field, None, self.rng, "hard", trait="hunter")
        self.assertTrue(decision.scored)
        self.assertTrue(all(item.personality == "hunter" for item in decision.scored))

    def test_the_next_battle_rolls_its_own_personality(self):
        run = RunState.new(seed=21)
        first = run.enemy_trait
        run.enemies = []
        king = run.army.king()
        run.deployment.place(king, 0, 1, run.blocked_squares(), run.army.capacity, run.army)
        self.assertTrue(run.start_battle())
        run.battle.evaluate()
        run.finish_victory()
        run.continue_from_victory()
        run.leave_shop()
        self.assertEqual(run.level, 2)
        self.assertEqual(run.enemy_trait, battle_personality(run.seed, 2))
        self.assertTrue(all(enemy.ai_trait == run.enemy_trait for enemy in run.enemies))
        self.assertIn(first, AI_TRAITS)

    def test_living_tags_follow_captures_and_ignore_player_pieces(self):
        run = RunState.new(seed=8)
        for enemy in run.enemies:
            enemy.ai_trait = "guardian"
        run.enemies[0].ai_trait = "hunter"
        run.enemies[1].ai_trait = "hunter"
        run.enemies[0].col = None
        counts = dict(living_trait_counts(run))
        self.assertEqual(counts.get("hunter"), 1)
        self.assertEqual(counts.get("guardian"), len(run.enemies) - 2)
        self.assertNotIn(None, counts)
        run.enemies.append(piece(90, "pawn", "black", 1, 6, "berserker"))
        self.assertEqual(dict(living_trait_counts(run)).get("berserker"), 1)


class TagLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((64, 64), pygame.HIDDEN)

    def test_the_battle_number_stays_above_one_centered_tag(self):
        run = RunState.new(seed=2)
        king = run.army.king()
        run.deployment.place(king, 0, 1, run.blocked_squares(), run.army.capacity, run.army)
        self.assertTrue(run.start_battle())
        game = run.battle.game
        enemies = [piece for piece in game.board.pieces if piece.color == "black" and piece.ai_trait]
        self.assertGreaterEqual(len(enemies), 2)
        first, second = enemies[0], enemies[1]
        second.ai_trait = "hunter" if run.enemy_trait != "hunter" else "guardian"
        aspects = {trait: (640, 180) for trait in ("aggressive", "guardian", "hunter", "vengeful", "berserker")}
        layout = build_layout(1440, 900)
        game.hover = None
        game.selected_id = None
        self.assertEqual([row.trait for row in personality_layout(layout, run, aspects, game).rows], [run.battle.enemy_trait])
        game.hover = (first.col, first.row)
        for size in ((1440, 900), (960, 720)):
            layout = build_layout(*size)
            placed = personality_layout(layout, run, aspects, game)
            window = pygame.Rect(0, 0, *size)
            self.assertTrue(window.contains(placed.title))
            self.assertLess(placed.title.centery, layout.left.centery)
            self.assertTrue(layout.left.contains(placed.title))
            self.assertEqual([row.trait for row in placed.rows], [run.battle.enemy_trait])
            row = placed.rows[0]
            self.assertEqual(row.rect.centerx, layout.left.centerx)
            self.assertGreater(row.rect.y, placed.title.bottom)
            tag_bottom, gold_y = sidebar_anchors(run, layout)
            self.assertTrue(layout.left.contains(row.rect))
            self.assertFalse(row.rect.colliderect(layout.board))
            self.assertFalse(row.rect.colliderect(layout.menu))
            self.assertLessEqual(row.rect.bottom, tag_bottom + 1)
            self.assertLess(row.rect.bottom, gold_y)
            self.assertAlmostEqual(row.rect.w / row.rect.h, 640 / 180, places=1)
        game.hover = (second.col, second.row)
        switched = personality_layout(layout, run, aspects, game)
        self.assertEqual([row.trait for row in switched.rows], [run.battle.enemy_trait])
        game.hover = None
        game.selected_id = None
        self.assertEqual([row.trait for row in personality_layout(layout, run, aspects, game).rows], [run.battle.enemy_trait])


class ShopPreviewTests(unittest.TestCase):
    def test_shop_preview_matches_the_next_battle_without_changing_this_one(self):
        from config.settings import ENEMY_FORMATIONS, parse_square
        from game.level_manager import spawn_enemies

        run = RunState.new(seed=21)
        run.phase = "shop"
        saved_trait = run.enemy_trait
        saved_level = run.level
        preview = coming_battle(run)
        self.assertIsNotNone(preview)
        trait, enemies = preview
        self.assertEqual(trait, battle_personality(run.seed, saved_level + 1))
        self.assertEqual(run.enemy_trait, saved_trait)
        self.assertEqual(run.level, saved_level)
        expected = spawn_enemies(saved_level + 1)
        self.assertEqual(
            [(piece.kind, piece.col, piece.row) for piece in enemies],
            [(piece.kind, piece.col, piece.row) for piece in expected],
        )
        self.assertEqual(
            {(piece.kind, (piece.col, piece.row)) for piece in enemies},
            {(kind, parse_square(square)) for kind, square in ENEMY_FORMATIONS[saved_level + 1]},
        )
        self.assertTrue(all(piece.ai_trait == trait for piece in enemies))
        self.assertTrue(all(piece.ai_trait == saved_trait for piece in run.enemies))
