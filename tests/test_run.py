import unittest

from config.settings import (
    ENEMY_FORMATIONS,
    STARTER_KINDS,
    STARTING_GOLD,
    STARTING_NON_KING_CAPACITY,
    parse_square,
)
from game.board import Board
from game.level_manager import formation_counts, spawn_enemies
from game.move import Move
from game.piece import Piece
from game.run_state import RunState
from game.shop_manager import ShopManager
from tests.test_movement import make_board


class ScriptedRandom:
    def __init__(self, kinds: list[str]) -> None:
        self.kinds = list(kinds)

    def choice(self, options: tuple[str, ...] | list[str]) -> str:
        kind = self.kinds.pop(0)
        if kind not in options:
            raise AssertionError(kind)
        return kind


class RunTests(unittest.TestCase):
    def test_starting_army_and_gold(self):
        run = RunState.new(seed=7)
        self.assertEqual(run.gold, STARTING_GOLD)
        self.assertEqual(run.gold, 5)
        self.assertEqual(len(run.relics.owned), 0)
        self.assertEqual(run.level, 1)
        self.assertEqual(run.phase, "preview")
        self.assertEqual(run.army.capacity, STARTING_NON_KING_CAPACITY)
        self.assertEqual(sorted(piece.kind for piece in run.army.pieces), sorted(STARTER_KINDS))
        self.assertEqual(len({piece.id for piece in run.army.pieces}), 6)
        for piece in run.army.pieces:
            self.assertIsNone(piece.trait)
            self.assertIsNone(piece.col)
            self.assertEqual(piece.color, "white")
        self.assertIsNotNone(run.army.king())

    def test_enemy_formations_for_the_first_five_levels(self):
        self.assertEqual(formation_counts(1), {"pawn": 3, "knight": 1})
        self.assertEqual(formation_counts(2), {"pawn": 3, "bishop": 1, "knight": 1})
        self.assertEqual(formation_counts(3), {"pawn": 2, "bishop": 1, "knight": 1, "rook": 1})
        self.assertEqual(formation_counts(4), {"pawn": 3, "bishop": 1, "knight": 1, "rook": 1})
        self.assertEqual(formation_counts(5), {"king": 1, "pawn": 2, "knight": 1, "bishop": 1, "rook": 1})
        for level in range(1, 6):
            squares = []
            for _kind, square in ENEMY_FORMATIONS[level]:
                col, row = parse_square(square)
                self.assertGreaterEqual(row, 4)
                squares.append((col, row))
            self.assertEqual(len(squares), len(set(squares)))
            enemies = spawn_enemies(level)
            self.assertEqual(len(enemies), len(squares))
            self.assertTrue(all(piece.color == "black" for piece in enemies))

    def test_buying_a_piece_adds_it_to_the_collection(self):
        run = RunState.new(seed=3)
        kind = run.shop.piece_kind
        before = len(run.army.pieces)
        self.assertIsNone(run.buy_piece())
        self.assertEqual(run.gold, 0)
        self.assertEqual(len(run.army.pieces), before + 1)
        bought = run.army.pieces[-1]
        self.assertEqual(bought.kind, kind)
        self.assertIsNone(bought.col)
        self.assertTrue(run.shop.piece_sold)
        self.assertNotIn(bought.id, run.deployment.placed)

    def test_insufficient_gold(self):
        run = RunState.new(seed=3)
        run.gold = 4
        run.shop.piece_sold = False
        owned = len(run.army.pieces)
        self.assertEqual(run.buy_piece(), "Not enough gold")
        self.assertEqual(run.gold, 4)
        self.assertEqual(len(run.army.pieces), owned)
        run.gold = 11
        self.assertEqual(run.buy_army(), "Not enough gold")
        self.assertEqual(run.army.capacity, 5)
        self.assertEqual(run.gold, 11)
        run.gold = 1
        self.assertEqual(run.reroll_shop(), "Not enough gold")
        self.assertEqual(run.gold, 1)

    def test_relic_offer_requires_gold(self):
        run = RunState.new(seed=3)
        run.gold = 0
        self.assertIsNotNone(run.shop.relic_id)
        self.assertTrue(run.shop.relic_enabled)
        self.assertEqual(run.buy_relic(), "Not enough gold")
        self.assertEqual(run.gold, 0)
        self.assertEqual(len(run.relics.owned), 0)

    def test_sold_out_and_reroll(self):
        shop = ShopManager(ScriptedRandom(["knight", "queen", "rook"]))
        from game.army_manager import ArmyManager

        army = ArmyManager()
        self.assertEqual(shop.piece_kind, "knight")
        gold, notice = shop.buy_piece(10, army)
        self.assertIsNone(notice)
        self.assertEqual(gold, 5)
        self.assertEqual(army.pieces[-1].kind, "knight")
        gold, notice = shop.buy_piece(gold, army)
        self.assertEqual(notice, "Sold out")
        self.assertEqual(gold, 5)
        self.assertEqual(len(army.pieces), 1)
        gold, notice = shop.buy_army(gold, army)
        self.assertEqual(notice, "Not enough gold")
        gold = 12
        gold, notice = shop.buy_army(gold, army)
        self.assertIsNone(notice)
        self.assertEqual(army.capacity, 6)
        self.assertTrue(shop.army_sold)
        gold, notice = shop.buy_army(gold, army)
        self.assertEqual(notice, "Sold out")
        self.assertEqual(army.capacity, 6)
        gold, notice = shop.reroll(4)
        self.assertIsNone(notice)
        self.assertEqual(gold, 2)
        self.assertEqual(shop.piece_kind, "queen")
        self.assertFalse(shop.piece_sold)
        self.assertFalse(shop.army_sold)
        self.assertFalse(shop.relic_enabled)
        self.assertEqual(len(army.pieces), 1)
        self.assertEqual(army.capacity, 6)
        gold, notice = shop.reroll(gold)
        self.assertIsNone(notice)
        self.assertEqual(shop.piece_kind, "rook")

    def test_army_upgrade_persists_for_the_run(self):
        run = RunState.new(seed=4)
        run.gold = 30
        self.assertIsNone(run.buy_army())
        self.assertEqual(run.army.capacity, 6)
        self.assertEqual(run.gold, 18)
        self.assertIsNone(run.reroll_shop())
        self.assertEqual(run.gold, 16)
        self.assertFalse(run.shop.army_sold)
        self.assertIsNone(run.buy_army())
        self.assertEqual(run.army.capacity, 7)

    def test_deployment_capacity_and_mandatory_king(self):
        run = RunState.new(seed=5)
        blocked: set[tuple[int, int]] = set()
        king = run.army.king()
        others = [piece for piece in run.army.pieces if piece.kind != "king"]
        self.assertFalse(run.deployment.ready(run.army))
        self.assertFalse(run.start_battle())
        self.assertIsNone(run.battle)
        for index, piece in enumerate(others):
            self.assertTrue(run.deployment.place(piece, index, 2, blocked, run.army.capacity, run.army))
        self.assertFalse(run.deployment.ready(run.army))
        self.assertTrue(run.deployment.place(king, 4, 1, blocked, run.army.capacity, run.army))
        self.assertTrue(run.deployment.ready(run.army))
        self.assertEqual(run.deployment.non_king_count(run.army), 5)
        extra = run.army.create("rook")
        self.assertFalse(run.deployment.place(extra, 5, 1, blocked, run.army.capacity, run.army))
        self.assertFalse(run.deployment.can_place(extra, 0, 6, blocked, 99, run.army))
        self.assertFalse(run.deployment.can_place(extra, 0, 3, blocked, 99, run.army))
        run.army.increase_capacity()
        self.assertTrue(run.deployment.place(extra, 5, 1, blocked, run.army.capacity, run.army))
        run.deployment.remove(extra.id)
        self.assertIsNone(run.deployment.piece_id_at(5, 1))
        self.assertNotIn(extra.id, run.deployment.placed)

    def test_enemy_squares_block_deployment(self):
        run = RunState.new(seed=1)
        pawn = next(piece for piece in run.army.pieces if piece.kind == "pawn")
        enemy = run.enemies[0]
        self.assertFalse(
            run.deployment.can_place(
                pawn,
                enemy.col,
                1,
                {(enemy.col, 1)},
                run.army.capacity,
                run.army,
            )
        )

    def test_captured_piece_is_removed_and_reserves_survive(self):
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
        self.assertEqual(session.outcome, "victory")
        run.finish_victory()
        remaining = {piece.id: piece.kind for piece in run.army.pieces}
        self.assertNotIn(pawn.id, remaining)
        self.assertEqual(remaining[king.id], "king")
        self.assertEqual(remaining[rook.id], "rook")
        self.assertEqual(remaining[bishop.id], "bishop")
        self.assertEqual(run.gold, STARTING_GOLD + 3)
        self.assertTrue(all(piece.col is None for piece in run.army.pieces))

    def test_promoted_survivor_keeps_its_new_kind(self):
        run = RunState.new(seed=13)
        king = run.army.king()
        pawn = next(piece for piece in run.army.pieces if piece.kind == "pawn")
        run.enemies = []
        blocked: set[tuple[int, int]] = set()
        self.assertTrue(run.deployment.place(king, 0, 1, blocked, run.army.capacity, run.army))
        self.assertTrue(run.deployment.place(pawn, 1, 2, blocked, run.army.capacity, run.army))
        self.assertTrue(run.start_battle())
        run.battle.game.board.apply_move(Move(1, 2, 1, 6, "queen"))
        run.battle.evaluate()
        self.assertEqual(run.battle.outcome, "victory")
        run.finish_victory()
        self.assertEqual(run.army.piece_by_id(pawn.id).kind, "queen")
        self.assertIsNone(run.army.piece_by_id(pawn.id).col)

    def test_player_king_capture_ends_the_run(self):
        run = RunState.new(seed=9)
        king = run.army.king()
        pawn = next(piece for piece in run.army.pieces if piece.kind == "pawn")
        run.enemies = [Piece(10001, "rook", "black", 0, 2)]
        blocked = run.blocked_squares()
        self.assertTrue(run.deployment.place(king, 0, 1, blocked, run.army.capacity, run.army))
        self.assertTrue(run.deployment.place(pawn, 5, 2, blocked, run.army.capacity, run.army))
        self.assertTrue(run.start_battle())
        session = run.battle
        session.click(5, 2)
        session.click(5, 3)
        session.click(0, 2)
        session.click(0, 1)
        self.assertEqual(session.outcome, "defeat")
        run.finish_defeat()
        self.assertEqual(run.phase, "defeat")
        self.assertEqual(run.gold, STARTING_GOLD)

    def test_classic_rules_still_reject_king_captures(self):
        board = make_board(("king", "white", "A1"), ("rook", "black", "A2"), ("king", "black", "F6"))
        with self.assertRaises(ValueError):
            board.apply_move(Move(0, 2, 0, 1))
        crownless = Board(
            [piece.copy() for piece in board.pieces],
            capture_kings=True,
            enforce_check=False,
        )
        crownless.apply_move(Move(0, 2, 0, 1))
        self.assertIsNone(crownless.king("white"))

    def test_victory_reward_and_level_progression(self):
        run = RunState.new(seed=11)
        king = run.army.king()
        self.assertTrue(run.deployment.place(king, 0, 1, run.blocked_squares(), run.army.capacity, run.army))
        run.enemies = []
        self.assertTrue(run.start_battle())
        run.battle.evaluate()
        self.assertEqual(run.battle.outcome, "victory")
        run.finish_victory()
        self.assertEqual(run.phase, "victory")
        self.assertEqual(run.gold, 8)
        run.finish_victory()
        self.assertEqual(run.gold, 8)
        run.continue_from_victory()
        self.assertEqual(run.phase, "shop")
        run.leave_shop()
        self.assertEqual(run.level, 2)
        self.assertEqual(run.phase, "preview")
        self.assertEqual(len(run.enemies), 5)
        run.level = 5
        run.phase = "victory"
        run.continue_from_victory()
        self.assertEqual(run.phase, "complete")

    def test_restart_resets_the_run(self):
        run = RunState.new(seed=12)
        run.gold = 0
        run.level = 4
        run.army.capacity = 9
        run.army.create("queen")
        fresh = run.restart()
        self.assertEqual(fresh.gold, 5)
        self.assertEqual(fresh.level, 1)
        self.assertEqual(fresh.army.capacity, 5)
        self.assertEqual(len(fresh.army.pieces), 6)
        self.assertEqual(fresh.phase, "preview")
        self.assertEqual(len(fresh.relics.owned), 0)


if __name__ == "__main__":
    unittest.main()
