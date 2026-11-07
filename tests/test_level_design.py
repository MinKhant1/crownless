import unittest

from config.settings import ENEMY_FORMATIONS, ENEMY_TRAITS, MAX_LEVEL, VICTORY_GOLD, WANTED_BOUNTY, parse_square
from game.level_manager import formation_counts, spawn_enemies
from game.piece import Piece
from game.relics.effects.castle_wall import protected_squares
from game.run_state import RunState
from game.traits import TRAIT_IDS
from tests.test_relics import place


def _kind(run, kind):
    return next(piece for piece in run.army.pieces if piece.kind == kind)


def _board(level):
    return {square: (kind, ENEMY_TRAITS.get(level, {}).get(square)) for kind, square in ENEMY_FORMATIONS[level]}


class StageDesignTests(unittest.TestCase):
    def test_the_run_has_thirty_stages_on_the_enemy_ranks(self):
        self.assertEqual(MAX_LEVEL, 30)
        self.assertEqual(sorted(ENEMY_FORMATIONS), list(range(1, 31)))
        for level in range(1, MAX_LEVEL + 1):
            squares = [square for _kind, square in ENEMY_FORMATIONS[level]]
            self.assertEqual(len(squares), len(set(squares)), level)
            for square in squares:
                self.assertIn(parse_square(square)[1], (5, 6), (level, square))
            for square, trait in ENEMY_TRAITS.get(level, {}).items():
                self.assertIn(square, squares, f"stage {level}: no piece on {square} to carry {trait}")
                self.assertIn(trait, TRAIT_IDS)

    def test_milestones_follow_the_design_sheet(self):
        sheet = {
            5: ({"queen": 1, "pawn": 2, "knight": 1, "bishop": 1, "rook": 1}, {}),
            10: ({"knight": 3, "pawn": 4}, {"wooden knight": 1}),
            15: ({"bishop": 3, "knight": 3, "pawn": 3}, {"wanted knight": 1, "wooden bishop": 1}),
            20: ({"knight": 5, "pawn": 5}, {"wooden knight": 1, "magnet knight": 1}),
            25: ({"queen": 1, "bishop": 2, "knight": 2, "pawn": 6}, {"magnet knight": 2}),
            30: ({"queen": 2, "rook": 1, "bishop": 1, "knight": 1, "pawn": 6},
                 {"explosive queen": 1, "wanted pawn": 1, "wooden bishop": 1}),
        }
        for level, (counts, specials) in sheet.items():
            self.assertEqual(formation_counts(level), counts, level)
            found: dict[str, int] = {}
            for piece in spawn_enemies(level):
                if piece.trait:
                    key = f"{piece.trait} {piece.kind}"
                    found[key] = found.get(key, 0) + 1
            self.assertEqual(found, specials, level)

    def test_sketched_stages_put_every_piece_where_it_was_drawn(self):
        # stage 5's two pawns cover the queen and the rook (the sheet's pieces, re-ordered by the shield rule)
        self.assertEqual(_board(5), {"B6": ("rook", None), "C6": ("queen", None), "D6": ("bishop", None),
                                     "E6": ("knight", None), "B5": ("pawn", None), "C5": ("pawn", None)})
        self.assertEqual(_board(10), {"C6": ("knight", None), "D6": ("knight", "wooden"), "E6": ("knight", None),
                                      "B5": ("pawn", None), "C5": ("pawn", None), "D5": ("pawn", None), "E5": ("pawn", None)})
        self.assertEqual(_board(15), {"A6": ("bishop", "wooden"), "B6": ("knight", "wanted"), "C6": ("bishop", None),
                                      "D6": ("knight", None), "E6": ("bishop", None), "F6": ("knight", None),
                                      "A5": ("pawn", None), "C5": ("pawn", None), "E5": ("pawn", None)})

    def test_every_piece_starts_behind_a_pawn_and_the_most_valuable_go_first(self):
        value = {"queen": 9, "rook": 5, "bishop": 3, "knight": 3}
        for level in range(1, MAX_LEVEL + 1):
            pawns = {parse_square(square)[0] for kind, square in ENEMY_FORMATIONS[level] if kind == "pawn"}
            pieces = [(kind, parse_square(square)) for kind, square in ENEMY_FORMATIONS[level] if kind != "pawn"]
            for kind, (_col, row) in pieces:
                self.assertEqual(row, 6, f"stage {level}: {kind} must stand on the back rank")
            shielded = [kind for kind, (col, _row) in pieces if col in pawns]
            open_ = [kind for kind, (col, _row) in pieces if col not in pawns]
            self.assertEqual(len(shielded), min(len(pieces), len(pawns)), f"stage {level}: a pawn is not covering a piece")
            if open_:
                self.assertLessEqual(max(value[kind] for kind in open_), min(value[kind] for kind in shielded),
                                     f"stage {level}: {open_} left open while a lesser piece is covered")
        exposed = {level for level in range(1, MAX_LEVEL + 1)
                   if sum(kind == "pawn" for kind, _ in ENEMY_FORMATIONS[level]) < sum(kind != "pawn" for kind, _ in ENEMY_FORMATIONS[level])}
        self.assertEqual(exposed, {5, 15})  # only the sheet's own stages are short of pawns

    def test_stages_never_get_smaller_from_one_milestone_to_the_next(self):
        sizes = [len(ENEMY_FORMATIONS[level]) for level in range(5, MAX_LEVEL + 1)]
        self.assertEqual(sizes, sorted(sizes))

    def test_the_preview_and_the_battle_both_carry_enemy_traits(self):
        run = RunState.new(seed=3)
        run.level = 15
        run.prepare_level()
        traits = {(piece.col, piece.row): piece.trait for piece in run.enemies if piece.trait}
        self.assertEqual(traits, {parse_square("A6"): "wooden", parse_square("B6"): "wanted"})


class GameOverTests(unittest.TestCase):
    def test_game_over_names_the_stage_you_fell_on(self):
        from scenes.result_scene import defeat_buttons, fell_at, _banner_panel

        run = RunState.new(seed=5)
        run.level = 12
        self.assertEqual(fell_at(run), "Fell at Stage 12 of 30")
        panel = _banner_panel((1440, 900), run, "defeat", 1.0)
        restart, menu = defeat_buttons((1440, 900), run)
        self.assertGreater(restart.top, panel.top + 150)  # the stage line (y=138) sits clear of the buttons
        self.assertTrue(panel.contains(restart) and panel.contains(menu))


class EnemyTraitTests(unittest.TestCase):
    def _battle(self, enemies, *, rook=(0, 2)):
        run = RunState.new(seed=9)
        place(run, _kind(run, "king"), 3, 1)
        place(run, _kind(run, "rook"), *rook)
        run.enemies = enemies
        self.assertTrue(run.start_battle())
        return run

    def test_capturing_an_enemy_wanted_piece_pays_a_bounty_on_victory(self):
        run = self._battle([Piece(10001, "knight", "black", 0, 5, trait="wanted")])
        gold = run.gold
        run.battle.click(0, 2)
        run.battle.click(0, 5)
        self.assertEqual(run.battle.outcome, "victory")
        run.finish_victory()
        self.assertEqual(run.gold, gold + VICTORY_GOLD + WANTED_BOUNTY)
        labels = [row.label for row in run.battle_summary.rows]
        self.assertIn("Wanted Bounty", labels)

    def test_an_enemy_wooden_piece_pins_the_piece_that_takes_it(self):
        run = self._battle([Piece(10001, "pawn", "black", 0, 5, trait="wooden"), Piece(10002, "pawn", "black", 5, 6)])
        run.battle.click(0, 2)
        run.battle.click(0, 5)
        rook = run.battle.game.board.piece_at(0, 5)
        self.assertGreater(run.battle.rules.locks.get(rook.id, 0), 0)

    def test_an_enemy_explosive_piece_takes_the_capturer_with_it(self):
        run = self._battle([Piece(10001, "queen", "black", 0, 5, trait="explosive"), Piece(10002, "pawn", "black", 5, 6)])
        run.battle.click(0, 2)
        run.battle.click(0, 5)
        board = run.battle.game.board
        self.assertIsNone(board.piece_at(0, 5))
        self.assertFalse(any(piece.kind == "rook" and piece.color == "white" for piece in board.pieces))


class UniqueRelicTests(unittest.TestCase):
    def test_shop_sells_out_when_all_relics_are_owned(self):
        run = RunState.new(seed=4)
        for relic_id in run.shop.catalog:
            if relic_id != "chain_fuse":
                run.relics.acquire(relic_id)
        run.relics.acquire("chain_fuse")
        seen = set()
        for _ in range(60):
            run.shop.roll(run.relics.unavailable_ids())
            seen.add(run.shop.relic_id)
        self.assertEqual(seen, {None})
        self.assertTrue(run.shop.relic_sold)
        self.assertFalse(run.shop.relic_enabled)

    def test_buying_a_relic_you_own_is_rejected_without_charging(self):
        run = RunState.new(seed=4)
        run.relics.acquire("squire")
        run.gold = 20
        run.shop.relic_id = "squire"
        run.shop.relic_sold = False
        self.assertEqual(run.buy_relic(), "Already owned")
        self.assertEqual(run.gold, 20)
        self.assertEqual(run.relics.count("squire"), 1)

    def test_duplicate_recruitment_does_not_recruit_twice(self):
        run = RunState.new(seed=6)
        run.relics.acquire("recruitment")
        run.relics.acquire("recruitment")
        place(run, _kind(run, "king"), 0, 1)
        place(run, _kind(run, "rook"), 1, 2)
        place(run, _kind(run, "knight"), 2, 2)
        run.enemies = [Piece(10001, "pawn", "black", 1, 3), Piece(10002, "pawn", "black", 3, 4), Piece(10003, "king", "black", 5, 6)]
        self.assertTrue(run.start_battle())
        board = run.battle.game.board
        run.battle.click(1, 2)
        run.battle.click(1, 3)
        run.battle.click(5, 6)
        run.battle.click(5, 5)
        run.battle.click(2, 2)
        run.battle.click(3, 4)
        recruits = [piece for piece in board.pieces if piece.color == "white" and piece.kind == "pawn"]
        self.assertEqual(len(recruits), 1)

    def test_duplicate_squire_does_not_spawn_extra_pawns(self):
        run = RunState.new(seed=6)
        run.relics.acquire("squire")
        run.relics.acquire("squire")
        place(run, _kind(run, "king"), 0, 1)
        place(run, _kind(run, "knight"), 2, 2)
        run.enemies = [Piece(10001, "pawn", "black", 3, 4), Piece(10002, "king", "black", 5, 6)]
        self.assertTrue(run.start_battle())
        run.battle.click(2, 2)
        run.battle.click(3, 4)
        pawns = {(piece.col, piece.row) for piece in run.battle.game.board.pieces if piece.color == "white" and piece.kind == "pawn"}
        self.assertEqual(len(pawns), 1)
        self.assertIn((3, 3), pawns)

    def test_duplicate_blessing_does_not_bless_extra_pieces(self):
        run = RunState.new(seed=6)
        run.relics.acquire("crowns_blessing")
        run.relics.acquire("crowns_blessing")
        place(run, _kind(run, "king"), 2, 1)
        place(run, _kind(run, "pawn"), 2, 2)
        place(run, _kind(run, "knight"), 1, 2)
        run.enemies = [Piece(10001, "king", "black", 5, 6)]
        self.assertTrue(run.start_battle())
        blessed = [piece for piece in run.battle.game.board.pieces if piece.color == "white" and piece.trait]
        self.assertEqual({(piece.col, piece.row) for piece in blessed}, {(2, 2)})

    def test_castle_wall_copies_shield_deeper_down_the_file(self):
        run = RunState.new(seed=6)
        run.relics.acquire("castle_wall")
        place(run, _kind(run, "rook"), 0, 2)
        place(run, _kind(run, "king"), 0, 1)
        run.enemies = [Piece(10001, "king", "black", 5, 6)]
        self.assertTrue(run.start_battle())
        board = run.battle.game.board
        self.assertEqual(protected_squares(board, 1), {(0, 1)})
        board.add_piece(Piece(500, "pawn", "white", 1, 1))
        rook = next(piece for piece in board.pieces if piece.kind == "rook")
        board.add_piece(Piece(501, "rook", "white", 1, 3))
        board.add_piece(Piece(502, "pawn", "white", 1, 2))
        self.assertEqual(protected_squares(board, 1) - {(0, 1)}, {(1, 2)})
        self.assertEqual(protected_squares(board, 2) - {(0, 1)}, {(1, 2), (1, 1)})
        self.assertIsNotNone(rook)

    def test_spent_blood_contract_cannot_be_acquired_again(self):
        from rendering.relic_bar_renderer import card_state

        run = RunState.new(seed=12)
        first = run.relics.acquire("blood_contract")
        second = run.relics.acquire("blood_contract")
        victim = next(p for p in run.army.pieces if p.kind == "pawn")
        self.assertTrue(run.relics.activate(first.instance_id, victim.id).ok)
        self.assertEqual(card_state(run, first), "used")
        self.assertIsNone(second)
        self.assertIsNone(run.relics.acquire("blood_contract"))
        self.assertEqual(run.relics.count("blood_contract"), 1)

    def test_duplicate_gold_relic_does_not_pay_twice(self):
        run = RunState.new(seed=11)
        run.relics.acquire("flawless_victory")
        run.relics.acquire("flawless_victory")
        place(run, run.army.king(), 0, 1)
        run.enemies = []
        self.assertTrue(run.start_battle())
        run.battle.evaluate()
        gold = run.gold
        run.finish_victory()
        self.assertEqual(run.gold, gold + VICTORY_GOLD + 3)
        row = next(row for row in run.battle_summary.rows if "Flawless" in row.label)
        self.assertEqual((row.label, row.amount), ("Relic: Flawless Victory", 3))


if __name__ == "__main__":
    unittest.main()
