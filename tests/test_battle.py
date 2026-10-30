import unittest

from config.settings import ARMY_CAPACITY, ARMY_SIZE, CURRENT_LEVEL, INITIAL_SETUP, parse_square
from game.game import Game
from rendering.hud_renderer import army_text, level_text, turn_text
from tests.test_movement import destinations, make_board, sq


class BattleFlowTests(unittest.TestCase):
    def test_initial_setup_and_hud_state(self):
        game = Game()
        self.assertEqual(game.turns.current, "white")
        self.assertEqual(game.turns.move_count, 0)
        self.assertEqual(game.turns.battle_state, "ongoing")
        self.assertFalse(game.turns.finished)
        self.assertEqual(len(game.board.pieces), 12)
        self.assertEqual(game.current_level, CURRENT_LEVEL)
        self.assertEqual(game.army_size, ARMY_SIZE)
        self.assertEqual(game.army_capacity, ARMY_CAPACITY)
        self.assertEqual(level_text(game.current_level), "Lvl: 1")
        self.assertEqual(army_text(game.army_size, game.army_capacity), "6 / 6")
        self.assertEqual(turn_text(game.turns), "White's Turn")
        placed = {(piece.kind, piece.color, piece.col, piece.row) for piece in game.board.pieces}
        expected = set()
        for kind, color, square in INITIAL_SETUP:
            col, row = parse_square(square)
            expected.add((kind, color, col, row))
        self.assertEqual(placed, expected)
        for piece in game.board.pieces:
            self.assertFalse(piece.has_moved)
            self.assertIsNone(piece.trait)
        ids = [piece.id for piece in game.board.pieces]
        self.assertEqual(len(ids), len(set(ids)))

    def test_opening_king_cannot_step_onto_the_attacked_file(self):
        game = Game()
        self.assertNotIn("D2", destinations(game.board, "white", "E1"))
        self.assertIn("E2", destinations(game.board, "white", "E1"))
        self.assertIn("F2", destinations(game.board, "white", "E1"))

    def test_selection_move_and_turn_swap(self):
        board = make_board(
            ("rook", "white", "A1"),
            ("king", "white", "C1"),
            ("rook", "black", "F6"),
            ("king", "black", "D6"),
        )
        game = Game(board)
        game.on_board_click(*sq("F6"))
        self.assertIsNone(game.selected_piece())
        game.on_board_click(*sq("A1"))
        self.assertEqual(game.selected_piece().kind, "rook")
        game.on_board_click(*sq("A1"))
        self.assertIsNone(game.selected_piece())
        game.on_board_click(*sq("A1"))
        game.on_board_click(*sq("B2"))
        self.assertEqual((game.board.piece_at(*sq("A1")).kind), "rook")
        self.assertEqual(game.turns.current, "white")
        game.on_board_click(*sq("A2"))
        self.assertEqual(game.board.piece_at(*sq("A2")).color, "white")
        self.assertIsNone(game.selected_piece())
        self.assertEqual(game.turns.current, "black")
        self.assertEqual(game.turns.move_count, 1)
        self.assertEqual(turn_text(game.turns), "Black's Turn")
        game.on_board_click(*sq("A2"))
        self.assertEqual(game.turns.current, "black")
        game.on_board_click(*sq("F6"))
        game.on_board_click(*sq("F5"))
        self.assertEqual(game.turns.current, "white")
        self.assertEqual(game.turns.move_count, 2)

    def test_clicking_another_friendly_piece_changes_selection(self):
        board = make_board(
            ("rook", "white", "A1"),
            ("knight", "white", "B1"),
            ("king", "white", "D1"),
            ("king", "black", "D6"),
        )
        game = Game(board)
        game.on_board_click(*sq("A1"))
        game.on_board_click(*sq("B1"))
        self.assertEqual(game.selected_piece().kind, "knight")
        self.assertIn("A3", {sq_name for sq_name in _names(game)})

    def test_capture_updates_board_and_log(self):
        board = make_board(
            ("rook", "white", "A1"),
            ("pawn", "black", "A4"),
            ("king", "white", "C1"),
            ("king", "black", "F6"),
        )
        game = Game(board)
        pawn_id = game.board.piece_at(*sq("A4")).id
        game.on_board_click(*sq("A1"))
        game.on_board_click(*sq("A4"))
        self.assertEqual(game.board.piece_at(*sq("A4")).kind, "rook")
        self.assertIsNone(game.board.piece_by_id(pawn_id))
        self.assertEqual(game.last_capture_id, pawn_id)
        self.assertEqual(game.board.capture_log[0].piece.kind, "pawn")
        self.assertEqual(game.board.capture_log[0].col, sq("A4")[0])
        self.assertEqual(game.turns.current, "black")
        self.assertEqual(game.army_size, ARMY_SIZE)

    def test_pinned_click_does_not_move(self):
        board = make_board(
            ("king", "white", "A1"),
            ("rook", "white", "A4"),
            ("rook", "black", "A6"),
            ("king", "black", "F6"),
        )
        game = Game(board)
        game.on_board_click(*sq("A4"))
        game.on_board_click(*sq("B4"))
        self.assertEqual(game.board.piece_at(*sq("A4")).kind, "rook")
        self.assertEqual(game.turns.current, "white")
        self.assertEqual(game.turns.move_count, 0)
        game.on_board_click(*sq("A5"))
        self.assertEqual(game.board.piece_at(*sq("A5")).kind, "rook")
        self.assertEqual(game.turns.current, "black")

    def test_check_is_reported_after_a_move(self):
        board = make_board(
            ("rook", "white", "A4"),
            ("king", "white", "C1"),
            ("king", "black", "E6"),
        )
        game = Game(board)
        game.on_board_click(*sq("A4"))
        game.on_board_click(*sq("E4"))
        self.assertTrue(game.turns.in_check)
        self.assertEqual(game.turns.battle_state, "check")
        self.assertFalse(game.turns.finished)
        self.assertEqual(game.turns.current, "black")
        self.assertEqual(turn_text(game.turns), "Black's Turn")

    def test_checkmate_ends_the_battle(self):
        board = make_board(("king", "black", "A1"), ("queen", "white", "B4"), ("king", "white", "C2"))
        game = Game(board)
        game.on_board_click(*sq("B4"))
        game.on_board_click(*sq("B2"))
        self.assertEqual(game.turns.battle_state, "checkmate")
        self.assertTrue(game.turns.finished)
        self.assertEqual(game.turns.winner, "white")
        self.assertEqual(turn_text(game.turns), "Checkmate - White wins")
        before = {(piece.id, piece.col, piece.row) for piece in game.board.pieces}
        game.on_board_click(*sq("C2"))
        game.on_board_click(*sq("C3"))
        after = {(piece.id, piece.col, piece.row) for piece in game.board.pieces}
        self.assertEqual(before, after)

    def test_checkmate_on_the_side_to_move(self):
        board = make_board(
            ("king", "white", "A1"),
            ("queen", "black", "B2"),
            ("rook", "black", "C2"),
            ("king", "black", "F6"),
        )
        game = Game(board)
        self.assertEqual(game.turns.battle_state, "checkmate")
        self.assertEqual(game.turns.winner, "black")
        game.on_board_click(*sq("A1"))
        self.assertIsNone(game.selected_piece())

    def test_stalemate_on_the_side_to_move(self):
        board = make_board(("king", "white", "A1"), ("queen", "black", "C2"), ("king", "black", "F6"))
        game = Game(board)
        self.assertEqual(game.turns.battle_state, "stalemate")
        self.assertIsNone(game.turns.winner)
        self.assertEqual(turn_text(game.turns), "Stalemate")

    def test_promotion_through_a_click(self):
        board = make_board(("pawn", "white", "A5"), ("king", "white", "C1"), ("king", "black", "F6"))
        game = Game(board)
        game.on_board_click(*sq("A5"))
        game.on_board_click(*sq("A6"))
        queen = game.board.piece_at(*sq("A6"))
        self.assertEqual(queen.kind, "queen")
        self.assertEqual(queen.color, "white")
        self.assertEqual(game.turns.current, "black")

    def test_hud_labels_follow_game_state(self):
        game = Game()
        game.current_level = 4
        game.army_size = 3
        game.army_capacity = 8
        self.assertEqual(level_text(game.current_level), "Lvl: 4")
        self.assertEqual(army_text(game.army_size, game.army_capacity), "3 / 8")


def _names(game: Game) -> set[str]:
    from config.settings import square_name

    return {square_name(move.to_col, move.to_row) for move in game.legal}


if __name__ == "__main__":
    unittest.main()
