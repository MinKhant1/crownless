import unittest

from game.board import in_bounds
from game.move import Move
from game.move_validator import legal_moves
from game.piece import Piece
from game.relics.events import CAPTURE_RESOLVED, GameEvent
from game.relics.relic_context import NEIGHBORS
from game.relics.relic_data import shop_relic_ids
from game.run_state import RunState
from game.traits import TRAIT_IDS


def place(run: RunState, piece: Piece, col: int, row: int) -> None:
    blocked = run.blocked_squares()
    assert run.deployment.place(piece, col, row, blocked, run.army.capacity, run.army)


class RelicTests(unittest.TestCase):
    def test_acquisition_and_duplicate_prevention(self):
        run = RunState.new(seed=1)
        owned = run.relics.acquire("recruitment")
        self.assertIsNotNone(owned)
        self.assertEqual(owned.relic_id, "recruitment")
        self.assertEqual(owned.instance_id, "relic_001")
        self.assertEqual(owned.acquisition_order, 1)
        self.assertIsNone(run.relics.acquire("recruitment"))
        self.assertEqual(len(run.relics.owned), 1)
        self.assertTrue(run.relics.owns("recruitment"))

    def test_capture_effect_registers_once(self):
        run = RunState.new(seed=2)
        before = run.relics.dispatcher.count(CAPTURE_RESOLVED)
        run.relics.acquire("recruitment")
        run.relics.acquire("conversion")
        self.assertEqual(run.relics.dispatcher.count(CAPTURE_RESOLVED), before + 2)

    def test_event_chain_stops(self):
        run = RunState.new(seed=2)
        calls = {"n": 0}

        def loop(event):
            calls["n"] += 1
            run.relics.dispatcher.publish(event)

        run.relics.dispatcher.subscribe("loop_test", loop, priority=0)
        run.relics.dispatcher.publish(GameEvent("loop_test", {}))
        self.assertEqual(calls["n"], run.relics.dispatcher.limit)

    def test_blood_contract_sacrifices_and_assigns_a_trait(self):
        first = self._sacrifice(11)
        second = self._sacrifice(11)
        self.assertEqual(first, second)
        self.assertIn(first[1], TRAIT_IDS)
        self.assertNotEqual(first[0], 0)

    def _sacrifice(self, seed: int):
        run = RunState.new(seed=seed)
        run.relics.acquire("blood_contract")
        pawn = next(piece for piece in run.army.pieces if piece.kind == "pawn")
        result = run.relics.effect_for("blood_contract").activate(run.relics.context, pawn.id)
        self.assertTrue(result.ok)
        self.assertIsNone(run.army.piece_by_id(pawn.id))
        target = run.army.piece_by_id(result.target_id)
        self.assertIsNotNone(target)
        self.assertEqual(target.trait, result.trait_id)
        self.assertNotEqual(target.kind, "king")
        self.assertTrue(run.relics.find("blood_contract").state["spent"])
        again = run.relics.effect_for("blood_contract").activate(run.relics.context, result.target_id)
        self.assertFalse(again.ok)
        self.assertEqual(again.message, "Already used")
        return result.target_id, result.trait_id

    def test_blood_contract_protects_the_king(self):
        run = RunState.new(seed=4)
        run.relics.acquire("blood_contract")
        king = run.army.king()
        result = run.relics.effect_for("blood_contract").activate(run.relics.context, king.id)
        self.assertFalse(result.ok)
        self.assertIn("King", result.message)
        self.assertIsNotNone(run.army.king())
        self.assertIsNone(run.army.king().trait)
        run.phase = "battle"
        pawn = next(piece for piece in run.army.pieces if piece.kind == "pawn")
        blocked = run.relics.effect_for("blood_contract").activate(run.relics.context, pawn.id)
        self.assertFalse(blocked.ok)
        self.assertEqual(blocked.message, "Only before battle")

    def test_blood_contract_needs_two_pieces(self):
        run = RunState.new(seed=5)
        run.relics.acquire("blood_contract")
        king = run.army.king()
        pawn = next(piece for piece in run.army.pieces if piece.kind == "pawn")
        for piece in list(run.army.pieces):
            if piece.id not in (king.id, pawn.id):
                run.army.remove(piece.id)
        result = run.relics.effect_for("blood_contract").activate(run.relics.context, pawn.id)
        self.assertFalse(result.ok)
        self.assertIn(pawn.id, {piece.id for piece in run.army.pieces})

    def test_recruitment_spawns_on_the_original_square(self):
        run = RunState.new(seed=6)
        run.relics.acquire("recruitment")
        king = run.army.king()
        rook = next(piece for piece in run.army.pieces if piece.kind == "rook")
        run.enemies = [Piece(10001, "pawn", "black", 1, 3)]
        place(run, king, 0, 1)
        place(run, rook, 1, 2)
        self.assertTrue(run.start_battle())
        run.battle.click(1, 2)
        run.battle.click(1, 3)
        board = run.battle.game.board
        recruit = board.piece_at(1, 2)
        self.assertIsNotNone(recruit)
        self.assertEqual(recruit.color, "white")
        self.assertEqual(recruit.kind, "pawn")
        self.assertIsNone(recruit.trait)
        self.assertEqual(board.piece_at(1, 3).kind, "rook")
        self.assertGreater(
            sum(1 for piece in board.pieces if piece.color == "white" and piece.kind != "king"),
            1,
        )

    def test_recruitment_skips_an_occupied_origin(self):
        run = RunState.new(seed=6)
        run.relics.acquire("recruitment")
        king = run.army.king()
        place(run, king, 0, 1)
        run.enemies = []
        self.assertTrue(run.start_battle())
        board = run.battle.game.board
        board.add_piece(Piece(50, "pawn", "white", 1, 1))
        before = len(board.pieces)
        run.relics.dispatcher.publish(
            GameEvent(
                CAPTURE_RESOLVED,
                {
                    "capturing_piece_id": king.id,
                    "capturing_kind": "king",
                    "capturing_color": "white",
                    "captured_piece_id": 9,
                    "captured_piece_type": "knight",
                    "captured_piece_color": "black",
                    "captured_trait": None,
                    "origin_square": (1, 1),
                    "destination_square": (2, 1),
                },
            )
        )
        self.assertEqual(len(board.pieces), before)
        self.assertEqual(board.piece_at(1, 1).id, 50)

    def test_recruitment_can_exceed_capacity_during_battle(self):
        run = RunState.new(seed=8)
        run.relics.acquire("recruitment")
        king = run.army.king()
        others = [piece for piece in run.army.pieces if piece.kind != "king"]
        run.enemies = [Piece(10001, "pawn", "black", 3, 3)]
        place(run, king, 5, 1)
        for index, piece in enumerate(others):
            place(run, piece, index, 2)
        self.assertTrue(run.start_battle())
        run.battle.click(3, 2)
        run.battle.click(3, 3)
        board = run.battle.game.board
        non_kings = [piece for piece in board.pieces if piece.color == "white" and piece.kind != "king"]
        self.assertGreater(len(non_kings), run.army.capacity)
        self.assertEqual(run.battle.outcome, "victory")
        run.finish_victory()
        owned = [piece for piece in run.army.pieces if piece.kind != "king"]
        self.assertEqual(len(owned), 6)
        self.assertEqual(run.army.capacity, 5)
        self.assertTrue(any(piece.kind == "pawn" and piece.id not in {item.id for item in others} for piece in owned))

    def test_conversion_only_the_first_bishop_capture_and_only_adjacent(self):
        run = RunState.new(seed=9)
        run.relics.acquire("conversion")
        king = run.army.king()
        bishop = next(piece for piece in run.army.pieces if piece.kind == "bishop")
        place(run, king, 0, 1)
        place(run, bishop, 2, 2)
        run.enemies = []
        self.assertTrue(run.start_battle())
        board = run.battle.game.board
        bishop_piece = board.piece_by_id(bishop.id)
        bishop_piece.col, bishop_piece.row = 3, 4
        board._grid.clear()
        for piece in board.pieces:
            board._grid[(piece.col, piece.row)] = piece
        destination = (3, 4)
        blocked = [(destination[0] + dc, destination[1] + dr) for dc, dr in NEIGHBORS]
        open_square = (4, 4)
        blocked.remove(open_square)
        for index, square in enumerate(blocked):
            if in_bounds(*square) and board.piece_at(*square) is None:
                board.add_piece(Piece(800 + index, "pawn", "black", square[0], square[1]))
        self._capture(run, bishop.id, "bishop", "knight", (2, 3), destination)
        ghost = board.piece_at(*open_square)
        self.assertIsNotNone(ghost)
        self.assertEqual(ghost.trait, "ghost")
        self.assertEqual(ghost.kind, "knight")
        self.assertEqual(ghost.color, "white")
        self.assertTrue(run.relics.find("conversion").state["used_this_battle"])
        before = sum(1 for piece in board.pieces if piece.trait == "ghost")
        self._capture(run, bishop.id, "bishop", "pawn", (4, 5), (4, 5))
        self.assertEqual(sum(1 for piece in board.pieces if piece.trait == "ghost"), before)
        knight = next(piece for piece in run.army.pieces if piece.kind == "knight")
        self._capture(run, knight.id, "knight", "rook", (1, 1), (2, 3))
        self.assertEqual(sum(1 for piece in board.pieces if piece.trait == "ghost"), before)

    def test_conversion_spawns_nothing_when_boxed_in(self):
        run = RunState.new(seed=10)
        run.relics.acquire("conversion")
        king = run.army.king()
        place(run, king, 0, 1)
        run.enemies = []
        self.assertTrue(run.start_battle())
        board = run.battle.game.board
        destination = (3, 3)
        for index, (delta_col, delta_row) in enumerate(NEIGHBORS):
            square = (destination[0] + delta_col, destination[1] + delta_row)
            if in_bounds(*square):
                board.add_piece(Piece(900 + index, "pawn", "black", square[0], square[1]))
        self._capture(run, king.id, "bishop", "queen", (2, 2), destination)
        self.assertFalse(any(piece.trait == "ghost" for piece in board.pieces))
        self.assertTrue(run.relics.find("conversion").state["used_this_battle"])

    def test_recruitment_resolves_before_conversion(self):
        run = RunState.new(seed=12)
        run.relics.acquire("recruitment")
        run.relics.acquire("conversion")
        king = run.army.king()
        bishop = next(piece for piece in run.army.pieces if piece.kind == "bishop")
        run.enemies = [Piece(10001, "knight", "black", 3, 3)]
        place(run, king, 0, 1)
        place(run, bishop, 2, 2)
        self.assertTrue(run.start_battle())
        run.battle.click(2, 2)
        run.battle.click(3, 3)
        board = run.battle.game.board
        recruited = board.piece_at(2, 2)
        self.assertIsNotNone(recruited)
        self.assertEqual(recruited.kind, "knight")
        self.assertIsNone(recruited.trait)
        ghosts = [piece for piece in board.pieces if piece.trait == "ghost"]
        self.assertEqual(len(ghosts), 1)
        self.assertNotEqual((ghosts[0].col, ghosts[0].row), (2, 2))
        self.assertIn((ghosts[0].col, ghosts[0].row), self._around(3, 3))
        run.finish_victory()
        self.assertFalse(any(piece.trait == "ghost" for piece in run.army.pieces))
        self.assertTrue(any(piece.id == recruited.id for piece in run.army.pieces))

    def test_golden_reward_and_ghost_removal(self):
        run = RunState.new(seed=13)
        king = run.army.king()
        pawn = next(piece for piece in run.army.pieces if piece.kind == "pawn")
        rook = next(piece for piece in run.army.pieces if piece.kind == "rook")
        pawn.trait = "golden"
        rook.trait = "ghost"
        run.enemies = []
        place(run, king, 0, 1)
        place(run, pawn, 1, 1)
        place(run, rook, 2, 1)
        self.assertTrue(run.start_battle())
        run.battle.evaluate()
        run.finish_victory()
        self.assertEqual(run.gold, 5 + 2 + 3)
        self.assertIsNotNone(run.army.piece_by_id(pawn.id))
        self.assertEqual(run.army.piece_by_id(pawn.id).trait, "golden")
        self.assertIsNone(run.army.piece_by_id(rook.id))

    def test_wooden_immobilizes_the_capturer_for_two_turns(self):
        run = RunState.new(seed=14)
        king = run.army.king()
        pawn = next(piece for piece in run.army.pieces if piece.kind == "pawn")
        pawn.trait = "wooden"
        rook = Piece(10001, "rook", "black", 0, 3)
        walker = Piece(10002, "pawn", "black", 5, 5)
        run.enemies = [rook, walker]
        place(run, king, 5, 1)
        place(run, pawn, 0, 2)
        self.assertTrue(run.start_battle())
        session = run.battle
        session.click(5, 1)
        session.click(4, 1)
        session.click(0, 3)
        session.click(0, 2)
        self.assertEqual(session.rules.locks.get(10001), 2)
        rook_moves = [
            move
            for move in legal_moves(session.game.board, "black")
            if (move.from_col, move.from_row) == (0, 2)
        ]
        self.assertEqual(session.rules.filter_moves(session.game.board, rook_moves), [])
        session.click(4, 1)
        session.click(3, 1)
        session.click(5, 5)
        session.click(5, 4)
        self.assertEqual(session.rules.locks.get(10001), 1)
        session.click(3, 1)
        session.click(2, 1)
        session.click(5, 4)
        session.click(5, 3)
        self.assertEqual(session.rules.locks.get(10001), 0)
        opened = [
            move
            for move in legal_moves(session.game.board, "black")
            if (move.from_col, move.from_row) == (0, 2)
        ]
        self.assertTrue(session.rules.filter_moves(session.game.board, opened))

    def test_conversion_resets_on_the_next_battle(self):
        run = RunState.new(seed=15)
        owned = run.relics.acquire("conversion")
        king = run.army.king()
        place(run, king, 0, 1)
        run.enemies = []
        self.assertTrue(run.start_battle())
        owned.state["used_this_battle"] = True
        run.phase = "deployment"
        run.battle = None
        self.assertTrue(run.start_battle())
        self.assertFalse(owned.state["used_this_battle"])

    def test_shop_purchase_and_reroll_exclude_owned_relics(self):
        run = RunState.new(seed=16)
        run.gold = 7
        offered = run.shop.relic_id
        self.assertIn(offered, shop_relic_ids())
        self.assertNotIn("gold_charm", shop_relic_ids())
        self.assertIsNone(run.buy_relic())
        self.assertEqual(run.gold, 0)
        self.assertTrue(run.relics.owns(offered))
        self.assertTrue(run.shop.relic_sold)
        self.assertEqual(run.buy_relic(), "Sold out")
        run.gold = 9
        self.assertIsNone(run.reroll_shop())
        self.assertEqual(run.gold, 7)
        self.assertNotEqual(run.shop.relic_id, offered)
        self.assertFalse(run.relics.owns(run.shop.relic_id))
        charm = run.relics.acquire("gold_charm")
        self.assertIsNotNone(charm)
        run.gold = 4
        king = run.army.king()
        place(run, king, 0, 1)
        run.enemies = []
        run.phase = "deployment"
        self.assertTrue(run.start_battle())
        run.battle.evaluate()
        run.finish_victory()
        bonus = 3 if run.relics.owns("flawless_victory") else 0
        self.assertEqual(run.gold, 4 + 1 + 3 + bonus)

    def _capture(self, run, capturer_id, kind, captured_kind, origin, destination) -> None:
        run.relics.dispatcher.publish(
            GameEvent(
                CAPTURE_RESOLVED,
                {
                    "capturing_piece_id": capturer_id,
                    "capturing_kind": kind,
                    "capturing_color": "white",
                    "captured_piece_id": 4242,
                    "captured_piece_type": captured_kind,
                    "captured_piece_color": "black",
                    "captured_trait": None,
                    "origin_square": origin,
                    "destination_square": destination,
                },
            )
        )

    def _around(self, col: int, row: int):
        return [(col + dc, row + dr) for dc, dr in NEIGHBORS]


if __name__ == "__main__":
    unittest.main()
