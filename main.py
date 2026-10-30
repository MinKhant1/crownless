from pathlib import Path

import pygame

from config.settings import FPS, MIN_WINDOW_HEIGHT, MIN_WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_WIDTH
from game.run_state import RunState
from rendering.asset_manager import AssetManager
from rendering.layout import build_layout, square_at
from rendering.relic_bar_renderer import RelicBar
from rendering.shop_layout import build_shop_layout
from rendering.shop_renderer import draw_shop
from rendering.piece_animation_controller import piece_motion
from rendering.piece_visual_effects import figurines
from rendering.special_piece_renderer import special_pieces
from scenes.battle_scene import draw_battle, handle_battle_click
from scenes.deployment_scene import DeploymentScene
from scenes.relic_overlay import RelicOverlay
from scenes.result_scene import draw_result, handle_result_click
from scenes.shop_scene import handle_shop_click
from scenes.trait_debug import TraitDebug

ROOT = Path(__file__).resolve().parent


def _trait_icons(deployment: DeploymentScene, run: RunState, window: tuple[int, int], layout) -> list:
    if run.phase != "deployment":
        return []
    _left, tray, _button = deployment.panels(window, layout)
    return deployment.icon_rects(tray, run)


def main() -> None:
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_caption("Crownless")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
    clock = pygame.time.Clock()
    assets = AssetManager(ROOT / "assets")
    run = RunState.new()
    deployment = DeploymentScene()
    relics = RelicOverlay()
    relic_bar = RelicBar()
    trait_debug = TraitDebug()
    running = True
    while running:
        window = screen.get_size()
        board_layout = build_layout(*window)
        shop_layout = build_shop_layout(*window)
        relic_bar.bind(run)
        if relics.open:
            relic_bar.close_detail()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                size = (max(MIN_WINDOW_WIDTH, event.w), max(MIN_WINDOW_HEIGHT, event.h))
                if screen.get_size() != size:
                    screen = pygame.display.set_mode(size, pygame.RESIZABLE)
                    assets.clear_scaled()
                    special_pieces.clear()
                    figurines.clear()
                    relic_bar.clear()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F3 and run.phase == "battle" and run.battle is not None:
                run.battle.game.toggle_debug()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F4:
                trait_debug.toggle()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F5:
                piece_motion.toggle_debug()
            elif event.type == pygame.MOUSEWHEEL and run.phase in ("preview", "deployment", "battle"):
                relic_bar.on_wheel(run, board_layout, event.pos, event.y)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                relic_bar.on_right_click()
            elif event.type == pygame.MOUSEMOTION:
                if run.phase in ("preview", "deployment", "battle"):
                    relic_bar.on_motion(run, event.pos, board_layout)
                else:
                    relic_bar.hover_id = None
                relics.on_motion(run, event.pos, window, shop_layout)
                if relics.open:
                    continue
                if run.phase in ("preview", "deployment"):
                    deployment.on_motion(event.pos)
                    deployment.hover = square_at(board_layout, event.pos)
                elif run.phase == "battle" and run.battle is not None:
                    run.battle.game.hover = square_at(board_layout, event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if run.phase in ("preview", "deployment", "battle") and relic_bar.on_left_down(event.pos, run, board_layout):
                    continue
                if trait_debug.hits(event.pos, board_layout, window, _trait_icons(deployment, run, window, board_layout)):
                    continue
                if relics.wants(event.pos, window):
                    relics.armed = True
                elif run.phase in ("preview", "deployment"):
                    deployment.on_press(run, event.pos, board_layout, window)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if run.phase in ("preview", "deployment", "battle") and (relic_bar.armed or relic_bar.detail_id is not None):
                    relic_bar.on_left_up(run, event.pos, board_layout, window)
                    continue
                if relics.armed or relics.open:
                    relics.on_click(run, event.pos, window)
                    relics.armed = False
                    continue
                icons = _trait_icons(deployment, run, window, board_layout)
                if trait_debug.hits(event.pos, board_layout, window, icons):
                    trait_debug.on_click(run, event.pos, board_layout, window, icons)
                    continue
                if run.phase == "shop":
                    handle_shop_click(run, event.pos, shop_layout)
                elif run.phase in ("preview", "deployment"):
                    deployment.on_release(run, event.pos, board_layout, window)
                elif run.phase == "battle":
                    handle_battle_click(run, event.pos, board_layout, window)
                elif run.phase in ("victory", "defeat", "complete"):
                    if handle_result_click(run, event.pos, window) == "restart":
                        run = run.restart()
                        trait_debug.target_id = None
                        piece_motion.clear()
        if run.phase == "shop":
            draw_shop(screen, assets, run, shop_layout)
        elif run.phase in ("preview", "deployment"):
            deployment.draw(screen, assets, run, board_layout, relic_bar)
        elif run.phase == "battle":
            draw_battle(screen, assets, run, board_layout, relic_bar)
        else:
            draw_result(screen, assets, run)
        trait_debug.draw(screen, run)
        relics.draw(screen, assets, run, shop_layout)
        if run.phase in ("preview", "deployment", "battle") and not relics.open:
            relic_bar.draw_overlay(screen, assets, run, board_layout)
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()


if __name__ == "__main__":
    main()
