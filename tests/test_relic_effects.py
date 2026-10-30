import unittest

from config.settings import VICTORY_GOLD
from game.move_validator import legal_moves
from game.piece import Piece
from game.relics.effects.castle_wall import protected_squares
from game.relics.relic_data import front_key, relic_by_id, shop_relic_ids
from game.run_state import RunState
from rendering.relic_flip import ShopReveal
from tests.test_relics import place


PERSISTENT = {"golden", "wanted", "explosive", "wooden"}


def _kind(run: RunState, kind: str) -> Piece:
    return next(piece for piece in run.army.pieces if piece.kind == kind)


class RelicEffectTests(unittest.TestCase):
    def test_catalog_maps_card_art_and_keeps_gold_charm_out_of_the_shop(self):
        self.assertEqual(len(shop_relic_ids()), 13)
        self.assertNotIn("gold_charm", shop_relic_ids())
        self.assertEqual(front_key(relic_by_id("collectors_crown")), "relic_front_collector_crown")

    def test_card_flip_shrinks_at_the_midpoint(self):
        reveal = ShopReveal()
        reveal.update(0.0, "offer")
        self.assertFalse(reveal.face_up)
        self.assertGreater(reveal.scale_x, 0.9)
        reveal.progress = 0.5
        self.assertTrue(reveal.face_up)
        self.assertLess(reveal.scale_x, 0.2)

    def test_recruitment_triggers_once(self):
        run = RunState.new(seed=6)
        run.relics.acquire("recruitment")
        place(run, _kind(run, "king"), 0, 1)
        place(run, _kind(run, "rook"), 1, 2)
        place(run, _kind(run, "knight"), 2, 2)
        run.enemies = [
            Piece(10001, "pawn", "black", 1, 3),
            Piece(10002, "pawn", "black", 3, 4),
            Piece(10003, "king", "black", 5, 6),
        ]
        self.assertTrue(run.start_battle())
        run.battle.click(1, 2)
        run.battle.click(1, 3)
        board = run.battle.game.board
        self.assertEqual(board.piece_at(1, 2).kind, "pawn")
        run.battle.click(5, 6)
        run.battle.click(5, 5)
        run.battle.click(2, 2)
        run.battle.click(3, 4)
        pawns = [piece for piece in board.pieces if piece.color == "white" and piece.kind == "pawn"]
        self.assertEqual(len(pawns), 1)
        self.assertIsNone(board.piece_at(2, 2))

    def test_castle_wall_blocks_the_square_behind_a_rook(self):
        run = RunState.new(seed=8)
        run.relics.acquire("castle_wall")
        place(run, _kind(run, "king"), 0, 1)
        place(run, _kind(run, "rook"), 1, 2)
        place(run, _kind(run, "pawn"), 1, 1)
        run.enemies = [Piece(10001, "knight", "black", 0, 3)]
        self.assertTrue(run.start_battle())
        board = run.battle.game.board
        moves = legal_moves(board, "black")
        filtered = run.battle.rules.filter_moves(board, moves)
        self.assertTrue(any(move.to_col == 1 and move.to_row == 1 for move in moves))
        self.assertFalse(any(move.to_col == 1 and move.to_row == 1 for move in filtered))
        rook = board.piece_at(1, 2)
        board.dismiss(rook)
        rook.col, rook.row = 1, 4
        board.add_piece(rook)
        board.add_piece(Piece(10002, "pawn", "black", 1, 3))
        self.assertNotIn((1, 1), protected_squares(board))

    def test_chain_fuse_detonates_each_explosive_once(self):
        run = RunState.new(seed=9)
        run.relics.acquire("chain_fuse")
        place(run, _kind(run, "king"), 0, 1)
        place(run, _kind(run, "rook"), 0, 2)
        run.enemies = [
            Piece(10001, "pawn", "black", 0, 3, trait="explosive"),
            Piece(10002, "pawn", "black", 1, 3, trait="explosive"),
            Piece(10003, "king", "black", 5, 6),
        ]
        self.assertTrue(run.start_battle())
        run.battle.click(0, 2)
        run.battle.click(0, 3)
        board = run.battle.game.board
        self.assertIsNone(board.piece_at(1, 3))
        self.assertEqual(board.piece_at(0, 3).kind, "rook")
        self.assertIsNotNone(board.piece_at(5, 6))

    def test_squire_spawns_behind_a_knight_and_skips_the_edge(self):
        run = RunState.new(seed=10)
        run.relics.acquire("squire")
        place(run, _kind(run, "king"), 5, 1)
        place(run, _kind(run, "knight"), 2, 2)
        run.enemies = [Piece(10001, "pawn", "black", 3, 4), Piece(10002, "king", "black", 0, 6)]
        self.assertTrue(run.start_battle())
        run.battle.click(2, 2)
        run.battle.click(3, 4)
        board = run.battle.game.board
        spawned = board.piece_at(3, 3)
        self.assertIsNotNone(spawned)
        self.assertEqual(spawned.color, "white")
        self.assertEqual(spawned.kind, "pawn")
        edge = RunState.new(seed=11)
        edge.relics.acquire("squire")
        place(edge, _kind(edge, "king"), 5, 1)
        place(edge, _kind(edge, "knight"), 2, 2)
        edge.enemies = [Piece(10011, "pawn", "black", 0, 1), Piece(10012, "king", "black", 5, 6)]
        self.assertTrue(edge.start_battle())
        edge.battle.click(2, 2)
        edge.battle.click(0, 1)
        self.assertIsNone(edge.battle.game.board.piece_at(0, 0))
        self.assertEqual(
            sum(1 for piece in edge.battle.game.board.pieces if piece.color == "white" and piece.kind == "pawn"),
            0,
        )

    def test_first_blood_grants_one_extra_white_move(self):
        run = RunState.new(seed=12)
        run.relics.acquire("first_blood")
        place(run, _kind(run, "king"), 0, 1)
        place(run, _kind(run, "rook"), 1, 2)
        run.enemies = [Piece(10001, "pawn", "black", 1, 3), Piece(10002, "king", "black", 5, 6)]
        self.assertTrue(run.start_battle())
        run.battle.click(1, 2)
        run.battle.click(1, 3)
        self.assertEqual(run.battle.game.turns.current, "white")
        run.battle.click(1, 3)
        run.battle.click(1, 4)
        self.assertEqual(run.battle.game.turns.current, "black")

    def test_crowns_blessing_traits_the_piece_in_front_of_the_king(self):
        run = RunState.new(seed=13)
        run.relics.acquire("crowns_blessing")
        king = _kind(run, "king")
        pawn = _kind(run, "pawn")
        place(run, king, 2, 1)
        place(run, pawn, 2, 2)
        run.enemies = [Piece(10001, "king", "black", 5, 6)]
        self.assertTrue(run.start_battle())
        blessed = run.battle.game.board.piece_at(2, 2)
        self.assertIn(blessed.trait, PERSISTENT)
        self.assertEqual(run.army.piece_by_id(pawn.id).trait, blessed.trait)

    def test_crowns_blessing_does_nothing_without_a_piece_in_front(self):
        run = RunState.new(seed=14)
        run.relics.acquire("crowns_blessing")
        place(run, _kind(run, "king"), 2, 1)
        run.enemies = [Piece(10001, "king", "black", 5, 6)]
        self.assertTrue(run.start_battle())
        self.assertTrue(all(piece.trait is None for piece in run.army.pieces))

    def test_flawless_victory_pays_only_without_a_loss(self):
        clean = RunState.new(seed=15)
        clean.relics.acquire("flawless_victory")
        place(clean, _kind(clean, "king"), 0, 1)
        place(clean, _kind(clean, "rook"), 2, 1)
        clean.enemies = [Piece(10001, "pawn", "black", 2, 3)]
        self.assertTrue(clean.start_battle())
        clean.battle.click(2, 1)
        clean.battle.click(2, 3)
        self.assertEqual(clean.battle.outcome, "victory")
        before = clean.gold
        clean.finish_victory()
        self.assertEqual(clean.gold, before + VICTORY_GOLD + 3)

        lost = RunState.new(seed=16)
        lost.relics.acquire("flawless_victory")
        place(lost, _kind(lost, "king"), 0, 1)
        place(lost, _kind(lost, "rook"), 1, 1)
        place(lost, _kind(lost, "pawn"), 1, 2)
        lost.enemies = [Piece(10001, "pawn", "black", 2, 3)]
        self.assertTrue(lost.start_battle())
        lost.battle.click(0, 1)
        lost.battle.click(0, 2)
        lost.battle.click(2, 3)
        lost.battle.click(1, 2)
        lost.battle.click(1, 1)
        lost.battle.click(1, 2)
        self.assertEqual(lost.battle.outcome, "victory")
        before = lost.gold
        lost.finish_victory()
        self.assertEqual(lost.gold, before + VICTORY_GOLD)

    def test_banner_raises_capacity_once(self):
        run = RunState.new(seed=17)
        before = run.army.capacity
        self.assertIsNotNone(run.relics.acquire("banner"))
        self.assertEqual(run.army.capacity, before + 1)
        self.assertIsNone(run.relics.acquire("banner"))
        self.assertEqual(run.army.capacity, before + 1)

    def test_graveyard_restores_the_first_special_piece_as_normal(self):
        run = RunState.new(seed=18)
        run.relics.acquire("graveyard")
        pawn = _kind(run, "pawn")
        pawn.trait = "golden"
        place(run, _kind(run, "king"), 0, 1)
        place(run, pawn, 1, 2)
        run.enemies = [Piece(10001, "rook", "black", 1, 5)]
        self.assertTrue(run.start_battle())
        run.battle.click(0, 1)
        run.battle.click(0, 2)
        run.battle.click(1, 5)
        run.battle.click(1, 2)
        restored = [
            piece
            for piece in run.battle.game.board.pieces
            if piece.color == "white" and piece.kind == "pawn" and piece.trait is None
        ]
        self.assertEqual(len(restored), 1)
        self.assertNotEqual(restored[0].id, pawn.id)

    def test_royal_promotion_upgrades_a_surviving_pawn(self):
        run = RunState.new(seed=19)
        run.relics.acquire("royal_promotion")
        pawn = _kind(run, "pawn")
        place(run, _kind(run, "king"), 0, 1)
        place(run, pawn, 2, 2)
        place(run, _kind(run, "rook"), 3, 1)
        run.enemies = [Piece(10001, "pawn", "black", 3, 4)]
        self.assertTrue(run.start_battle())
        run.battle.click(3, 1)
        run.battle.click(3, 4)
        self.assertEqual(run.battle.outcome, "victory")
        run.finish_victory()
        self.assertIn(run.army.piece_by_id(pawn.id).trait, PERSISTENT)

    def test_collectors_crown_adds_free_rerolls_for_distinct_kinds(self):
        run = RunState.new(seed=20)
        run.relics.acquire("collectors_crown")
        place(run, _kind(run, "king"), 0, 1)
        place(run, _kind(run, "rook"), 2, 1)
        place(run, _kind(run, "pawn"), 3, 2)
        run.enemies = [Piece(10001, "pawn", "black", 2, 4)]
        self.assertTrue(run.start_battle())
        run.battle.game.board.piece_at(3, 2).trait = "golden"
        run.battle.click(2, 1)
        run.battle.click(2, 4)
        run.finish_victory()
        self.assertEqual(run.shop_rerolls, 3)
        gold = run.gold
        self.assertIsNone(run.reroll_shop())
        self.assertEqual(run.shop_rerolls, 2)
        self.assertEqual(run.gold, gold)
