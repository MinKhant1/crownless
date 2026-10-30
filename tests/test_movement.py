import unittest

from config.settings import square_name
from game.board import Board, in_bounds
from game.move_generator import attacked_squares, pseudo_legal_moves
from game.move_validator import in_check, legal_moves
from game.piece import Piece

FILES = "ABCDEF"


def sq(name: str) -> tuple[int, int]:
    return FILES.index(name[0]), int(name[1])


def make_board(*placements: tuple) -> Board:
    pieces = []
    for index, placement in enumerate(placements, start=1):
        kind, color, square = placement[:3]
        moved = placement[3] if len(placement) > 3 else False
        trait = placement[4] if len(placement) > 4 else None
        col, row = sq(square)
        pieces.append(Piece(index, kind, color, col, row, moved, trait))
    return Board(pieces)


def destinations(board: Board, color: str, square: str, legal: bool = True) -> set[str]:
    origin = sq(square)
    moves = legal_moves(board, color) if legal else pseudo_legal_moves(board, color)
    found = set()
    for move in moves:
        if (move.from_col, move.from_row) == origin:
            found.add(square_name(move.to_col, move.to_row))
    return found


class MovementTests(unittest.TestCase):
    def test_white_pawn_forward_and_double_step(self):
        board = make_board(("pawn", "white", "F1"), ("king", "white", "C1"), ("king", "black", "C6"))
        self.assertEqual(destinations(board, "white", "F1"), {"F2", "F3"})

    def test_black_pawn_moves_toward_rank_one(self):
        board = make_board(("pawn", "black", "A6"), ("king", "black", "C6"), ("king", "white", "C1"))
        self.assertEqual(destinations(board, "black", "A6"), {"A5", "A4"})

    def test_pawn_blocked_by_piece(self):
        board = make_board(
            ("pawn", "white", "F1"),
            ("knight", "black", "F2"),
            ("king", "white", "C1"),
            ("king", "black", "C6"),
        )
        self.assertEqual(destinations(board, "white", "F1"), set())

    def test_pawn_double_step_blocked_on_second_square(self):
        board = make_board(
            ("pawn", "white", "B1"),
            ("rook", "black", "B3"),
            ("king", "white", "D1"),
            ("king", "black", "D6"),
        )
        self.assertEqual(destinations(board, "white", "B1"), {"B2"})

    def test_pawn_cannot_double_step_after_moving(self):
        board = make_board(
            ("pawn", "white", "B2", True),
            ("king", "white", "D1"),
            ("king", "black", "D6"),
        )
        self.assertEqual(destinations(board, "white", "B2"), {"B3"})

    def test_pawn_captures_diagonally_only(self):
        board = make_board(
            ("pawn", "white", "D3"),
            ("rook", "black", "C4"),
            ("knight", "black", "E4"),
            ("pawn", "black", "D4"),
            ("pawn", "white", "C2"),
            ("king", "white", "A1"),
            ("king", "black", "F6"),
        )
        self.assertEqual(destinations(board, "white", "D3"), {"C4", "E4"})

    def test_black_pawn_captures_toward_white(self):
        board = make_board(
            ("pawn", "black", "D4"),
            ("rook", "white", "C3"),
            ("knight", "white", "E3"),
            ("bishop", "white", "D3"),
            ("king", "white", "A1"),
            ("king", "black", "F6"),
        )
        self.assertEqual(destinations(board, "black", "D4"), {"C3", "E3"})

    def test_pawn_does_not_capture_friendly_pieces(self):
        board = make_board(
            ("pawn", "white", "D3"),
            ("rook", "white", "C4"),
            ("king", "white", "A1"),
            ("king", "black", "F6"),
        )
        self.assertEqual(destinations(board, "white", "D3"), {"D4", "D5"})

    def test_white_pawn_promotes_on_final_rank(self):
        board = make_board(("pawn", "white", "A5"), ("king", "white", "C1"), ("king", "black", "F6"))
        moves = [move for move in legal_moves(board, "white") if move.from_col == 0 and move.to_row == 6]
        self.assertEqual(len(moves), 1)
        self.assertEqual(moves[0].promotion, "queen")
        board.apply_move(moves[0])
        queen = board.piece_at(0, 6)
        self.assertIsNotNone(queen)
        self.assertEqual(queen.kind, "queen")
        self.assertEqual(queen.color, "white")
        self.assertTrue(queen.has_moved)
        self.assertIn("A4", destinations(board, "white", "A6"))

    def test_black_pawn_promotes_on_rank_one(self):
        board = make_board(("pawn", "black", "C2"), ("king", "black", "F6"), ("king", "white", "A4"))
        moves = [move for move in legal_moves(board, "black") if (move.from_col, move.from_row) == sq("C2")]
        promotion = [move for move in moves if move.to_row == 1]
        self.assertEqual(len(promotion), 1)
        self.assertEqual(promotion[0].promotion, "queen")
        board.apply_move(promotion[0])
        self.assertEqual(board.piece_at(*sq("C1")).kind, "queen")
        self.assertEqual(board.piece_at(*sq("C1")).color, "black")

    def test_capture_promotion_removes_enemy_and_records_it(self):
        board = make_board(
            ("pawn", "white", "B5", False, "golden"),
            ("rook", "black", "C6"),
            ("king", "white", "A1"),
            ("king", "black", "F4"),
        )
        move = next(move for move in legal_moves(board, "white") if (move.to_col, move.to_row) == sq("C6"))
        self.assertEqual(move.promotion, "queen")
        captured = board.apply_move(move)
        self.assertIsNotNone(captured)
        self.assertEqual(captured.piece.kind, "rook")
        self.assertEqual(len(board.capture_log), 1)
        self.assertIsNone(board.piece_by_id(captured.piece.id))
        promoted = board.piece_at(*sq("C6"))
        self.assertEqual(promoted.kind, "queen")
        self.assertEqual(promoted.trait, "golden")

    def test_rook_slides_and_stops(self):
        board = make_board(("rook", "white", "A1"), ("king", "white", "F1"), ("king", "black", "F6"))
        self.assertEqual(destinations(board, "white", "A1"), {"A2", "A3", "A4", "A5", "A6", "B1", "C1", "D1", "E1"})

    def test_rook_cannot_pass_friendly_or_land_on_it(self):
        board = make_board(
            ("rook", "white", "A1"),
            ("knight", "white", "A3"),
            ("bishop", "white", "C1"),
            ("king", "black", "F6"),
        )
        self.assertEqual(destinations(board, "white", "A1"), {"A2", "B1"})

    def test_rook_captures_and_cannot_jump(self):
        board = make_board(
            ("rook", "white", "A1"),
            ("pawn", "black", "A4"),
            ("king", "white", "F1"),
            ("king", "black", "F6"),
        )
        self.assertEqual(destinations(board, "white", "A1"), {"A2", "A3", "A4", "B1", "C1", "D1", "E1"})
        move = next(move for move in legal_moves(board, "white") if (move.to_col, move.to_row) == sq("A4"))
        captured = board.apply_move(move)
        self.assertEqual(captured.piece.kind, "pawn")
        self.assertEqual(board.piece_at(*sq("A4")).kind, "rook")
        self.assertIsNone(board.piece_at(*sq("A1")))
        self.assertEqual(len(board.pieces), 3)

    def test_knight_jumps_and_uses_every_l_shape(self):
        board = make_board(
            ("knight", "white", "C3"),
            ("pawn", "white", "C4"),
            ("pawn", "white", "B3"),
            ("pawn", "black", "D5"),
            ("king", "white", "A1"),
            ("king", "black", "F6"),
        )
        self.assertEqual(
            destinations(board, "white", "C3"),
            {"A2", "A4", "B1", "B5", "D1", "D5", "E2", "E4"},
        )

    def test_knight_on_corner_has_two_squares(self):
        board = make_board(("knight", "white", "A1"), ("king", "white", "C1"), ("king", "black", "C6"))
        self.assertEqual(destinations(board, "white", "A1"), {"B3", "C2"})

    def test_knight_on_opposite_corner(self):
        board = make_board(("knight", "black", "F6"), ("king", "black", "D6"), ("king", "white", "D1"))
        self.assertEqual(destinations(board, "black", "F6"), {"D5", "E4"})

    def test_bishop_diagonals_and_blockers(self):
        board = make_board(("bishop", "white", "C3"), ("king", "white", "B1"), ("king", "black", "F5"))
        self.assertEqual(
            destinations(board, "white", "C3"),
            {"A1", "A5", "B2", "B4", "D2", "D4", "E1", "E5", "F6"},
        )
        blocked = make_board(
            ("bishop", "white", "C3"),
            ("pawn", "white", "D4"),
            ("king", "white", "B1"),
            ("king", "black", "F5"),
        )
        self.assertEqual(
            destinations(blocked, "white", "C3"),
            {"A1", "A5", "B2", "B4", "D2", "E1"},
        )

    def test_queen_combines_rook_and_bishop(self):
        rook_board = make_board(("rook", "white", "C3"), ("king", "white", "A1"), ("king", "black", "F6"))
        bishop_board = make_board(("bishop", "white", "C3"), ("king", "white", "A1"), ("king", "black", "F6"))
        queen_board = make_board(("queen", "white", "C3"), ("king", "white", "A1"), ("king", "black", "F6"))
        self.assertEqual(
            destinations(queen_board, "white", "C3"),
            destinations(rook_board, "white", "C3") | destinations(bishop_board, "white", "C3"),
        )

    def test_king_moves_one_square(self):
        board = make_board(("king", "white", "C3"), ("king", "black", "F6"))
        self.assertEqual(
            destinations(board, "white", "C3"),
            {"B2", "B3", "B4", "C2", "C4", "D2", "D3", "D4"},
        )

    def test_king_cannot_step_off_the_board(self):
        board = make_board(("king", "white", "A1"), ("king", "black", "F6"))
        self.assertEqual(destinations(board, "white", "A1"), {"A2", "B1", "B2"})

    def test_edge_pieces_never_leave_the_board(self):
        kinds = ("pawn", "rook", "knight", "bishop", "queen", "king")
        for kind in kinds:
            for col in range(6):
                for row in range(1, 7):
                    board = Board([Piece(1, kind, "white", col, row)])
                    for move in pseudo_legal_moves(board, "white"):
                        self.assertTrue(in_bounds(move.to_col, move.to_row))

    def test_friendly_collision_for_every_stepper(self):
        board = make_board(
            ("queen", "white", "D4"),
            ("pawn", "white", "D5"),
            ("pawn", "white", "E4"),
            ("pawn", "white", "E5"),
            ("king", "black", "A1"),
        )
        found = destinations(board, "white", "D4")
        self.assertNotIn("D5", found)
        self.assertNotIn("E4", found)
        self.assertNotIn("E5", found)
        self.assertNotIn("D6", found)
        self.assertIn("D3", found)
        self.assertIn("C3", found)

    def test_copy_does_not_share_piece_state(self):
        board = make_board(("rook", "white", "A1", False, "wooden"), ("king", "black", "F6"))
        clone = board.copy()
        move = next(move for move in pseudo_legal_moves(clone, "white") if (move.to_col, move.to_row) == sq("A4"))
        clone.apply_move(move)
        self.assertEqual(board.piece_at(*sq("A1")).kind, "rook")
        self.assertIsNone(board.piece_at(*sq("A4")))
        self.assertEqual(clone.piece_at(*sq("A4")).trait, "wooden")


class SafetyTests(unittest.TestCase):
    def test_rook_check_is_detected_and_blocked_by_a_piece(self):
        checked = make_board(("king", "white", "E1"), ("rook", "black", "E6"), ("king", "black", "A6"))
        self.assertTrue(in_check(checked, "white"))
        self.assertIn(sq("E1"), attacked_squares(checked, "black"))
        blocked = make_board(
            ("king", "white", "E1"),
            ("pawn", "white", "E3"),
            ("rook", "black", "E6"),
            ("king", "black", "A6"),
        )
        self.assertFalse(in_check(blocked, "white"))

    def test_king_cannot_move_into_check(self):
        board = make_board(("king", "white", "E1"), ("rook", "black", "E6"), ("king", "black", "A6"))
        self.assertEqual(destinations(board, "white", "E1"), {"D1", "D2", "F1", "F2"})

    def test_king_cannot_capture_a_protected_piece(self):
        board = make_board(("king", "white", "A1"), ("queen", "black", "B2"), ("rook", "black", "C2"), ("king", "black", "F6"))
        self.assertNotIn("B2", destinations(board, "white", "A1"))

    def test_pinned_piece_cannot_leave_the_line(self):
        board = make_board(("king", "white", "A1"), ("bishop", "white", "B2"), ("queen", "black", "C3"), ("king", "black", "F6"))
        pseudo = destinations(board, "white", "B2", legal=False)
        legal = destinations(board, "white", "B2", legal=True)
        self.assertIn("A3", pseudo)
        self.assertIn("C1", pseudo)
        self.assertEqual(legal, {"C3"})

    def test_pinned_knight_has_no_legal_move(self):
        board = make_board(("king", "white", "E1"), ("knight", "white", "E2"), ("rook", "black", "E6"), ("king", "black", "A6"))
        self.assertFalse(in_check(board, "white"))
        self.assertEqual(destinations(board, "white", "E2"), set())
        self.assertTrue(destinations(board, "white", "E2", legal=False))

    def test_king_is_never_a_capture_destination(self):
        board = make_board(("king", "white", "A1"), ("rook", "black", "A2"), ("king", "black", "F6"))
        moves = pseudo_legal_moves(board, "black")
        targets = {(move.to_col, move.to_row) for move in moves}
        self.assertNotIn(sq("A1"), targets)
        from game.move import Move

        with self.assertRaises(ValueError):
            board.apply_move(Move(0, 2, 0, 1))

    def test_checkmate_corner(self):
        board = make_board(
            ("king", "white", "A1"),
            ("queen", "black", "B2"),
            ("rook", "black", "C2"),
            ("king", "black", "F6"),
        )
        from game.turn_manager import TurnManager

        turns = TurnManager("white")
        turns.refresh(board)
        self.assertTrue(in_check(board, "white"))
        self.assertEqual(legal_moves(board, "white"), [])
        self.assertEqual(turns.battle_state, "checkmate")
        self.assertTrue(turns.finished)
        self.assertEqual(turns.winner, "black")

    def test_stalemate_corner(self):
        board = make_board(("king", "white", "A1"), ("queen", "black", "C2"), ("king", "black", "F6"))
        from game.turn_manager import TurnManager

        turns = TurnManager("white")
        turns.refresh(board)
        self.assertFalse(in_check(board, "white"))
        self.assertEqual(legal_moves(board, "white"), [])
        self.assertEqual(turns.battle_state, "stalemate")
        self.assertTrue(turns.finished)
        self.assertIsNone(turns.winner)

    def test_rules_do_not_depend_on_the_test_formation(self):
        board = make_board(("rook", "white", "D4"), ("bishop", "black", "B5"), ("knight", "white", "F2"))
        self.assertIn("D6", destinations(board, "white", "D4", legal=False))
        self.assertIn("A6", destinations(board, "black", "B5", legal=False))
        self.assertIn("D3", destinations(board, "white", "F2", legal=False))
        self.assertNotIn("D5", destinations(board, "white", "F2", legal=False))


if __name__ == "__main__":
    unittest.main()
