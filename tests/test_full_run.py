import unittest
from pathlib import Path

import pygame

import main
from ai.enemy_ai import EnemyTurn
from game.run_state import RunState
from game.scene_manager import SceneManager
from game.visual_test import VisualTest
from rendering.asset_manager import AssetManager
from rendering.collection_overlay import collection_overlay
from rendering.layout import build_layout
from rendering.relic_bar_renderer import RelicBar
from rendering.relic_flip import shop_reveal
from rendering.relic_preview import RelicPreviewModal
from rendering.shop_layout import build_shop_layout
from rendering.shop_offers import shop_offers
from rendering.shop_piece_hand import shop_piece
from rendering.shop_relic_hand import shop_hand
from rendering.wood_swirl import wood_swirl
from scenes.battle_scene import debug_buttons, handle_battle_click
from scenes.campaign_view import present, settle_finished_board
from scenes.deployment_scene import DeploymentScene
from scenes.relic_gallery import RelicGallery
from scenes.relic_overlay import RelicOverlay

DT = 1 / 60
ROOT = Path(__file__).resolve().parents[1]


class FullRunTests(unittest.TestCase):
    """Plays whole runs headless through the same per-frame calls main.py makes, drawing every frame."""

    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
        cls.screen = pygame.display.set_mode((1280, 720), pygame.HIDDEN)
        cls.assets = AssetManager(ROOT / "assets")

    def setUp(self):
        self.deployment, self.relics, self.relic_bar = DeploymentScene(), RelicOverlay(), RelicBar()
        self.gallery, self.preview, self.scene = RelicGallery(), RelicPreviewModal(), SceneManager()
        self.enemy_turn, self.visual = EnemyTurn(), VisualTest()

    def layouts(self):
        window = self.screen.get_size()
        board = build_layout(*window)
        return window, board, build_shop_layout(*window, board.left.right + 12)

    def frame(self, run):
        window, board, shop = self.layouts()
        self.relic_bar.bind(run)
        if run.phase == "shop":
            shop_reveal.update(DT, (run.shop.offer_serial, run.shop.relic_id))
            shop_piece.prepare(self.assets, run, shop)
        self.gallery.update(DT)
        wood_swirl.update(DT)
        self.preview.update(DT)
        self.scene.update(DT)
        main._advance_enemy(run, self.scene, self.enemy_turn, DT, self.visual)
        if run.phase == "preview":
            run.begin_deployment()
        if run.phase in ("preview", "deployment", "battle", "victory", "defeat"):
            self.relic_bar.update(DT, run, board)
        if run.phase == "shop":
            shop_piece.update(DT, run, shop, window)
            shop_hand.update(DT, run, shop, window)
            shop_offers.update(DT, run, shop)
            collection_overlay.update(DT, run)
        present(self.screen, self.assets, run, self.deployment, self.relic_bar, self.scene, board, shop)
        if not self.scene.motion.active:
            self.relics.draw(self.screen, self.assets, run, shop)
            if run.phase in ("preview", "deployment", "battle"):
                self.relic_bar.draw_overlay(self.screen, self.assets, run, board)
        self.gallery.draw(self.screen, self.assets, run)
        self.preview.draw(self.screen, self.assets)

    def frames(self, run, count):
        for _ in range(count):
            self.frame(run)

    def settle(self, run):
        for _ in range(900):
            self.frame(run)
            if not self.scene.motion.active and not self.scene.blocks_pointer():
                return
        self.fail(f"scene never settled in phase {run.phase}")

    def end_battle(self, run, won):
        window, board, _shop = self.layouts()
        run.start_battle()
        self.frames(run, 20)
        win, loss = debug_buttons(window, board)
        handle_battle_click(run, (win if won else loss).center, board, window)
        settle_finished_board(run)
        self.scene.begin_banner("level_complete" if won else "game_over")
        for _ in range(600):
            self.frame(run)
            if self.scene.result_ready():
                return
        self.fail(f"result never showed in phase {run.phase}")

    def test_a_run_with_every_shop_bought_out_reaches_the_end(self):
        for seed in (3, 21):
            with self.subTest(seed=seed):
                run = RunState.new(seed)
                self.scene.reset()
                for level in range(1, 6):
                    self.settle(run)
                    self.assertEqual(run.level, level)
                    self.end_battle(run, won=True)
                    self.assertEqual(run.phase, "victory")
                    main._continue_victory(self.scene, run, self.relic_bar)
                    self.settle(run)
                    if level == 5:
                        break
                    self.assertEqual(run.phase, "shop")
                    run.gold = 60
                    for buy in (run.buy_piece, run.buy_relic, run.buy_army, run.reroll_shop, run.buy_relic):
                        buy()
                        self.frames(run, 10)
                    main._leave_shop(self.scene, run, self.relic_bar)
                self.assertEqual(run.phase, "complete")

    def test_losing_the_king_ends_the_run(self):
        run = RunState.new(4)
        self.scene.reset()
        self.settle(run)
        self.end_battle(run, won=False)
        self.assertEqual(run.phase, "defeat")
