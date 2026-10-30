import unittest
from pathlib import Path

import pygame

from game.battle_rules import BattleRules
from game.board import Board
from game.game import Game
from game.move_validator import legal_moves
from game.piece import Piece
from game.run_state import RunState
from game.traits import TRAIT_IDS
from rendering.asset_manager import AssetManager
from rendering.layout import build_layout
from rendering.overlay_renderer import draw_crosshair, trait_tooltip_lines
from rendering.piece_renderer import draw_pieces
from rendering.special_piece_renderer import special_pieces


ROOT = Path(__file__).resolve().parents[1]


def place(run: RunState, piece: Piece, col: int, row: int) -> None:
    assert run.deployment.place(piece, col, row, run.blocked_squares(), run.army.capacity, run.army)


def _opaque(surface: pygame.Surface) -> tuple[int, int] | None:
    width, height = surface.get_size()
    for y in range(0, height, 2):
        for x in range(0, width, 2):
            if surface.get_at((x, y)).a > 200:
                return x, y
    return None


class TraitAssignmentTests(unittest.TestCase):
    def test_assign_rejects_invalid_and_keeps_the_first_trait(self):
        run = RunState.new(seed=3)
        piece = next(item for item in run.army.pieces if item.kind == "knight")
        self.assertFalse(run.traits.assign_trait(piece.id, "mythic"))
        self.assertIsNone(piece.trait)
        self.assertIsNone(run.traits.get_trait(piece.id))
        self.assertFalse(run.traits.assign_trait(99999, "golden"))
        self.assertTrue(run.traits.assign_trait(piece.id, "golden"))
        self.assertEqual(run.traits.get_trait(piece.id), "golden")
        self.assertFalse(run.traits.assign_trait(piece.id, "ghost"))
        self.assertEqual(piece.trait, "golden")
        self.assertTrue(run.traits.assign_trait(piece.id, "wanted", overwrite=True))
        self.assertEqual(run.traits.get_trait(piece.id), "wanted")
        self.assertTrue(run.traits.remove_trait(piece.id))
        self.assertIsNone(piece.trait)
        self.assertIsNone(run.traits.get_trait(piece.id))
        self.assertFalse(run.traits.remove_trait(99999))

    def test_assignment_updates_the_battle_copy(self):
        run = RunState.new(seed=4)
        king = run.army.king()
        knight = next(item for item in run.army.pieces if item.kind == "knight")
        run.enemies = []
        place(run, king, 0, 1)
        place(run, knight, 1, 1)
        self.assertTrue(run.traits.assign_trait(knight.id, "explosive"))
        self.assertTrue(run.start_battle())
        live = run.battle.game.board.piece_by_id(knight.id)
        self.assertEqual(live.trait, "explosive")
        self.assertTrue(run.traits.assign_trait(knight.id, "golden", overwrite=True))
        self.assertEqual(live.trait, "golden")
        self.assertEqual(run.army.piece_by_id(knight.id).trait, "golden")
        self.assertEqual(run.traits.get_trait(knight.id), "golden")


class TraitRewardTests(unittest.TestCase):
    def _win(self, seed: int, traits: list[str | None]) -> tuple[RunState, list[Piece]]:
        run = RunState.new(seed=seed)
        king = run.army.king()
        others = [piece for piece in run.army.pieces if piece.kind != "king"]
        chosen = others[: len(traits)]
        run.enemies = []
        place(run, king, 0, 1)
        for index, (piece, trait) in enumerate(zip(chosen, traits)):
            if trait:
                self.assertTrue(run.traits.assign_trait(piece.id, trait))
            place(run, piece, index + 1, 1)
        self.assertTrue(run.start_battle())
        run.battle.evaluate()
        run.finish_victory()
        return run, chosen

    def test_two_golden_pieces_pay_once(self):
        run, chosen = self._win(31, ["golden", "golden"])
        self.assertEqual(run.golden_reward, 4)
        self.assertEqual(run.gold, 5 + 4 + 3)
        paid = run.gold
        run.finish_victory()
        self.assertEqual(run.gold, paid)
        self.assertEqual(run.golden_reward, 4)
        self.assertTrue(all(run.army.piece_by_id(piece.id).trait == "golden" for piece in chosen))

    def test_removed_golden_piece_is_not_paid(self):
        run = RunState.new(seed=32)
        king = run.army.king()
        pawn = next(piece for piece in run.army.pieces if piece.kind == "pawn")
        run.traits.assign_trait(pawn.id, "golden")
        run.enemies = []
        place(run, king, 0, 1)
        place(run, pawn, 1, 1)
        self.assertTrue(run.start_battle())
        live = run.battle.game.board.piece_by_id(pawn.id)
        run.battle.game.board.dismiss(live)
        run.battle.evaluate()
        run.finish_victory()
        self.assertEqual(run.golden_reward, 0)
        self.assertEqual(run.gold, 5 + 3)
        self.assertIsNone(run.army.piece_by_id(pawn.id))

    def test_ghost_cleanup_leaves_permanent_pieces(self):
        run, chosen = self._win(33, ["ghost", "golden"])
        ghost, golden = chosen
        self.assertIsNone(run.army.piece_by_id(ghost.id))
        self.assertEqual(run.army.piece_by_id(golden.id).trait, "golden")
        self.assertEqual(run.golden_reward, 2)
        self.assertFalse(any(piece.trait == "ghost" for piece in run.battle.game.board.pieces))

    def test_trait_persists_between_battles(self):
        run, chosen = self._win(34, ["wooden"])
        pawn = chosen[0]
        self.assertEqual(run.army.piece_by_id(pawn.id).trait, "wooden")
        run.continue_from_victory()
        run.leave_shop()
        self.assertEqual(run.army.piece_by_id(pawn.id).trait, "wooden")
        king = run.army.king()
        place(run, king, 0, 1)
        place(run, pawn, 1, 1)
        self.assertTrue(run.start_battle())
        self.assertEqual(run.battle.game.board.piece_by_id(pawn.id).trait, "wooden")


class ImmobilizeTests(unittest.TestCase):
    def test_owner_turns_advance_the_lock(self):
        piece = Piece(7, "rook", "black", 0, 3)
        board = Board([piece], capture_kings=True, enforce_check=False)
        rules = BattleRules()
        rules.bind(lambda: board)
        rules.lock(piece.id, 2)
        self.assertEqual(rules.statuses[piece.id].status_id, "immobilized")
        self.assertEqual(rules.statuses[piece.id].remaining_owner_turns, 2)
        self.assertEqual(rules.statuses[piece.id].source_trait, "wooden")
        rules.spend("white")
        self.assertEqual(rules.locks[piece.id], 2)
        rules.spend("black")
        self.assertEqual(rules.locks[piece.id], 2)
        self.assertEqual(rules.statuses[piece.id].remaining_owner_turns, 2)
        rules.spend("black")
        self.assertEqual(rules.locks[piece.id], 1)
        rules.spend("white")
        self.assertEqual(rules.locks[piece.id], 1)
        rules.spend("black")
        self.assertEqual(rules.locks[piece.id], 0)
        self.assertNotIn(piece.id, rules.statuses)
        self.assertTrue(rules.filter_moves(board, legal_moves(board, "black")))

    def test_missing_piece_drops_its_status(self):
        piece = Piece(7, "rook", "black", 0, 3)
        board = Board([piece], capture_kings=True, enforce_check=False)
        rules = BattleRules()
        rules.bind(lambda: board)
        rules.lock(piece.id, 2)
        board.dismiss(piece)
        rules.spend("black")
        self.assertNotIn(piece.id, rules.statuses)
        self.assertNotIn(piece.id, rules.locks)

    def test_immobilized_piece_cannot_move_but_can_be_captured(self):
        run = RunState.new(seed=35)
        king = run.army.king()
        queen = next(piece for piece in run.army.pieces if piece.kind == "queen")
        pawn = next(piece for piece in run.army.pieces if piece.kind == "pawn")
        run.traits.assign_trait(pawn.id, "wooden")
        rook = Piece(10001, "rook", "black", 0, 3)
        walker = Piece(10002, "pawn", "black", 5, 5)
        run.enemies = [rook, walker]
        place(run, king, 2, 1)
        place(run, queen, 1, 2)
        place(run, pawn, 0, 2)
        self.assertTrue(run.start_battle())
        session = run.battle
        session.click(1, 2)
        session.click(1, 3)
        session.click(0, 3)
        session.click(0, 2)
        self.assertEqual(session.rules.locks.get(rook.id), 2)
        self.assertEqual(session.rules.statuses[rook.id].remaining_owner_turns, 2)
        session.click(2, 1)
        session.click(3, 1)
        session.click(0, 2)
        self.assertIsNone(session.game.selected_id)
        rook_moves = [
            move
            for move in legal_moves(session.game.board, "black")
            if (move.from_col, move.from_row) == (0, 2)
        ]
        self.assertEqual(session.rules.filter_moves(session.game.board, rook_moves), [])
        session.click(5, 5)
        session.click(5, 4)
        self.assertEqual((session.game.board.piece_by_id(walker.id).col, session.game.board.piece_by_id(walker.id).row), (5, 4))
        self.assertEqual(session.rules.locks.get(rook.id), 1)
        session.click(1, 3)
        self.assertEqual(session.game.selected_id, queen.id)
        session.click(0, 2)
        self.assertIsNone(session.game.board.piece_by_id(rook.id))
        self.assertNotIn(rook.id, session.rules.statuses)
        self.assertNotIn(rook.id, session.rules.locks)


class RelicTraitTests(unittest.TestCase):
    def test_blood_contract_overwrites_with_the_manager(self):
        run = RunState.new(seed=11)
        run.relics.acquire("blood_contract")
        for piece in run.army.pieces:
            if piece.kind != "king":
                run.traits.assign_trait(piece.id, "wooden")
        pawn = next(piece for piece in run.army.pieces if piece.kind == "pawn")
        result = run.relics.effect_for("blood_contract").activate(run.relics.context, pawn.id)
        self.assertTrue(result.ok)
        self.assertIn(result.trait_id, TRAIT_IDS)
        self.assertEqual(run.traits.get_trait(result.target_id), result.trait_id)
        self.assertNotEqual(run.army.piece_by_id(result.target_id).kind, "king")

    def test_recruitment_spawn_has_no_trait_and_conversion_ghost_is_removed(self):
        run = RunState.new(seed=36)
        king = run.army.king()
        run.enemies = []
        place(run, king, 0, 1)
        self.assertTrue(run.start_battle())
        recruit = run.relics.context.spawn_ally("rook", 2, 2, None)
        ghost = run.relics.context.spawn_ally("bishop", 3, 3, "ghost")
        self.assertIsNotNone(recruit)
        self.assertIsNone(recruit.trait)
        self.assertIsNone(run.traits.get_trait(recruit.id))
        self.assertEqual(ghost.trait, "ghost")
        self.assertEqual(run.traits.get_trait(ghost.id), "ghost")
        run.battle.evaluate()
        run.finish_victory()
        self.assertIsNone(run.battle.game.board.piece_by_id(ghost.id))
        self.assertIsNone(run.army.piece_by_id(ghost.id))
        self.assertIsNotNone(run.army.piece_by_id(recruit.id))
        self.assertIsNone(run.army.piece_by_id(recruit.id).trait)


class OverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((64, 64), pygame.HIDDEN)
        cls.assets = AssetManager(ROOT / "assets")

    def test_tints_do_not_change_the_source_art(self):
        raw = self.assets._raw["white_bishop"]
        before_raw = pygame.image.tobytes(raw, "RGBA")
        fitted = self.assets.fitted("white_bishop", 80, 80)
        before_fitted = pygame.image.tobytes(fitted, "RGBA")
        for trait in ("golden", "wanted", "explosive", "ghost", "wooden"):
            first = special_pieces.image(self.assets, "white", "bishop", trait, 80)
            second = special_pieces.image(self.assets, "white", "bishop", trait, 80)
            self.assertIs(first, second)
        self.assertEqual(pygame.image.tobytes(raw, "RGBA"), before_raw)
        self.assertEqual(pygame.image.tobytes(fitted, "RGBA"), before_fitted)
        board = Board(
            [
                Piece(1, "king", "white", 4, 1),
                Piece(2, "king", "black", 4, 6),
                Piece(3, "bishop", "white", 0, 1, trait="golden"),
                Piece(4, "knight", "black", 0, 6, trait="ghost"),
            ]
        )
        screen = pygame.Surface((1280, 900), pygame.SRCALPHA)
        draw_pieces(screen, self.assets, Game(board), build_layout(1280, 900))
        self.assertEqual(pygame.image.tobytes(raw, "RGBA"), before_raw)
        self.assertEqual(pygame.image.tobytes(self.assets.fitted("white_bishop", 80, 80), "RGBA"), before_fitted)

    def test_white_and_black_overlays_are_distinct(self):
        for color in ("white", "black"):
            fitted = self.assets.fitted(f"{color}_knight", 96, 96)
            spot = _opaque(fitted)
            self.assertIsNotNone(spot)
            golden = special_pieces.image(self.assets, color, "knight", "golden", 96)
            ghost = special_pieces.image(self.assets, color, "knight", "ghost", 96)
            self.assertEqual(golden.get_width(), fitted.get_width() + 2)
            base = fitted.get_at(spot)
            faded = ghost.get_at(spot)
            self.assertLess(faded.a, int(base.a * 0.72))
            self.assertGreater(faded.a, int(base.a * 0.48))
            warmed = golden.get_at((spot[0] + 1, spot[1] + 1))
            self.assertNotEqual((warmed.r, warmed.g, warmed.b), (base.r, base.g, base.b))
        screen = pygame.Surface((140, 140), pygame.SRCALPHA)
        draw_crosshair(screen, pygame.Rect(10, 10, 100, 100))
        self.assertTrue(any(screen.get_at((x, 32)).a > 0 for x in range(20, 120)))

    def test_tooltip_copy(self):
        samples = {
            "golden": ("Golden Knight", "Earn +2 Gold if this piece survives the battle."),
            "ghost": ("Ghost Bishop", "Temporary piece. Disappears after battle."),
            "wooden": ("Wooden Rook", "A piece that captures this cannot move for 2 turns."),
            "wanted": ("Wanted Queen", "Effect coming soon."),
            "explosive": ("Explosive Pawn", "Effect coming soon."),
        }
        kinds = {
            "golden": "knight",
            "ghost": "bishop",
            "wooden": "rook",
            "wanted": "queen",
            "explosive": "pawn",
        }
        for trait, expected in samples.items():
            lines = trait_tooltip_lines(Piece(1, kinds[trait], "black", trait=trait))
            self.assertEqual(lines, expected)
        self.assertIsNone(trait_tooltip_lines(Piece(2, "king", "white")))


if __name__ == "__main__":
    unittest.main()
