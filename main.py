from pathlib import Path

import pygame

from config.settings import (
    FPS,
    MAX_LEVEL,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    SPECIAL_PIECE_VISUAL_TEST,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from game.run_state import RunState
from game.scene_manager import SceneManager, slide_duration
from game.visual_test import VisualTest
from rendering.asset_manager import AssetManager
from rendering.board_renderer import clear_board_cache
from rendering.battle_view import render_battle
from rendering.hud_renderer import _blit_text, get_font
from rendering.layout import build_layout, square_at
from rendering.overlay_renderer import draw_trait_tooltip
from rendering.relic_bar_renderer import RelicBar
from rendering.relic_flip import shop_reveal
from rendering.relic_preview import RelicPreviewModal
from rendering.shop_layout import build_shop_layout
from rendering.shop_piece_hand import shop_piece
from rendering.shop_relic_hand import shop_hand
from rendering.wood_swirl import wood_swirl
from scenes.relic_gallery import RelicGallery
from rendering.piece_animation_controller import piece_motion
from rendering.piece_visual_effects import figurines
from rendering.overlay_renderer import _RINGS
from rendering.special_piece_renderer import special_pieces
from rendering.trait_style import trait_style
from ai.enemy_ai import EnemyTurn
from scenes.battle_scene import handle_battle_click
from scenes.campaign_view import present, settle_finished_board
from scenes.deployment_scene import DeploymentScene
from scenes.relic_overlay import RelicOverlay
from rendering.victory_summary import continue_rect
from scenes.result_scene import handle_result_click
from scenes.screen_menu import ScreenMenu
from scenes.shop_scene import handle_shop_click
from scenes.trait_debug import TraitDebug

ROOT = Path(__file__).resolve().parent


def _trait_icons(deployment: DeploymentScene, run: RunState, window: tuple[int, int], layout) -> list:
    if run.phase != "deployment":
        return []
    return deployment.icon_rects(run, layout)


def _board_phase(run: RunState) -> bool:
    return run.phase in ("preview", "deployment", "battle", "victory", "defeat")


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
    visual_test = VisualTest()
    scene = SceneManager()
    screen_menu = ScreenMenu()
    gallery = RelicGallery()
    preview = RelicPreviewModal()
    enemy_turn = EnemyTurn()
    cursor = None
    dt = 0.0
    if SPECIAL_PIECE_VISUAL_TEST:
        visual_test.open(run)
    running = True
    while running:
        window = screen.get_size()
        board_layout = build_layout(*window)
        shop_layout = build_shop_layout(*window)
        relic_bar.bind(run)
        if relics.open:
            relic_bar.close_detail()
        if run.phase == "shop":
            shop_reveal.update(dt, (run.shop.offer_serial, run.shop.relic_id))
            shop_piece.prepare(assets, run, shop_layout)
        gallery.update(dt)
        wood_swirl.update(dt)
        preview.update(dt)
        scene.update(dt)
        _advance_enemy(run, scene, enemy_turn, dt, visual_test)
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
                    clear_board_cache()
                    _RINGS.clear()
                    relic_bar.clear()
                    preview.clear()
                    wood_swirl.resize()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F3 and run.phase == "battle" and run.battle is not None:
                run.battle.game.toggle_debug()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F4:
                trait_debug.toggle()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F5:
                piece_motion.toggle_debug()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F6:
                trait_style.toggle()
                special_pieces.clear()
                figurines.clear()
                _RINGS.clear()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F7:
                visual_test.toggle(run)
                trait_debug.target_id = None
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F8:
                gallery.toggle()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F9:
                wood_swirl.toggle_debug()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and wood_swirl.debug_hit(event.pos):
                continue
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and wood_swirl.debug_click(event.pos):
                continue
            elif (
                event.type == pygame.KEYDOWN
                and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER)
                and run.phase == "victory"
                and scene.result_ready()
                and not gallery.open
                and not preview.blocks
            ):
                _continue_victory(scene, run, relic_bar)
                continue
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and preview.on_escape():
                continue
            elif preview.blocks and event.type in (
                pygame.MOUSEMOTION,
                pygame.MOUSEBUTTONDOWN,
                pygame.MOUSEBUTTONUP,
                pygame.MOUSEWHEEL,
            ):
                preview.on_event(event, window)
                if preview.pending_activate:
                    relic_bar.detail_id = preview.pending_activate
                    relic_bar.detail_piece = None
                    relic_bar.notice = ""
                    preview.pending_activate = None
                continue
            elif _pointer_blocked(scene, event):
                continue
            elif event.type == pygame.MOUSEWHEEL and run.phase in ("preview", "deployment", "battle"):
                if not deployment.army.on_wheel(run, board_layout, event.pos, event.y):
                    relic_bar.on_wheel(run, board_layout, event.pos, event.y)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                relic_bar.on_right_click()
            elif event.type == pygame.MOUSEMOTION:
                held = bool(event.buttons[0])
                if run.phase == "shop":
                    shop_piece.on_motion(run, event.pos, shop_layout, window, held=held)
                    shop_hand.on_motion(run, event.pos, shop_layout, window, held=held)
                    if shop_piece.claims(event.pos, run, shop_layout, window) and not shop_hand.dragging:
                        shop_hand.hovered_card_id = None
                else:
                    shop_hand.hovered_card_id = None
                    shop_piece.hovered = False
                if run.phase in ("preview", "deployment", "battle"):
                    relic_bar.on_motion(run, event.pos, board_layout, held=held)
                else:
                    relic_bar.hover_id = None
                if _board_phase(run):
                    deployment.army.hover_at(run, board_layout, event.pos)
                relics.on_motion(run, event.pos, window, shop_layout)
                if relics.open:
                    continue
                over_relic = relic_bar.pointer_captured or relic_bar.hovered_card_id is not None
                if over_relic:
                    if run.phase == "battle" and run.battle is not None:
                        run.battle.game.hover = None
                    elif run.phase in ("preview", "deployment"):
                        deployment.hover = None
                elif visual_test.active and visual_test.game is not None:
                    visual_test.game.hover = square_at(board_layout, event.pos)
                elif run.phase in ("preview", "deployment"):
                    deployment.on_motion(event.pos)
                    deployment.hover = square_at(board_layout, event.pos)
                elif run.phase == "battle" and run.battle is not None:
                    run.battle.game.hover = square_at(board_layout, event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if gallery.open:
                    continue
                if _board_phase(run) and screen_menu.on_press(board_layout, event.pos):
                    continue
                if run.phase in ("preview", "deployment", "battle") and relic_bar.on_left_down(event.pos, run, board_layout):
                    continue
                if run.phase == "shop" and shop_piece.on_left_down(event.pos, run, shop_layout, window):
                    continue
                if run.phase == "shop" and shop_hand.on_left_down(event.pos, run, shop_layout, window):
                    continue
                if trait_debug.hits(event.pos, board_layout, window, _trait_icons(deployment, run, window, board_layout)):
                    continue
                if relics.wants(event.pos, window):
                    relics.armed = True
                elif visual_test.active:
                    pass
                elif run.phase in ("preview", "deployment"):
                    deployment.on_press(run, event.pos, board_layout, window)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if gallery.open:
                    gallery.on_click(event.pos, run, window)
                    continue
                if _board_phase(run) and (screen_menu.press is not None or screen_menu.mode):
                    action = screen_menu.on_release(event.pos, window, board_layout)
                    if action == "restart":
                        if visual_test.active:
                            visual_test.close(run)
                        run = run.restart()
                        scene.reset()
                        trait_debug.target_id = None
                        piece_motion.clear()
                        relic_bar.clear()
                        preview.dismiss()
                    elif action == "readability":
                        special_pieces.clear()
                        figurines.clear()
                        _RINGS.clear()
                    continue
                if run.phase in ("preview", "deployment", "battle") and (
                    relic_bar.armed or relic_bar.dragging or relic_bar.detail_id is not None
                ):
                    relic_bar.on_left_up(run, event.pos, board_layout, window)
                    relic_bar.consume_click()
                    continue
                if relics.armed or relics.open:
                    relics.on_click(run, event.pos, window)
                    relics.armed = False
                    continue
                icons = _trait_icons(deployment, run, window, board_layout)
                if trait_debug.hits(event.pos, board_layout, window, icons):
                    trait_debug.on_click(run, event.pos, board_layout, window, icons)
                    continue
                if visual_test.active and visual_test.game is not None:
                    square = square_at(board_layout, event.pos)
                    if square is not None:
                        visual_test.game.on_board_click(*square)
                elif run.phase == "shop":
                    if shop_piece.on_left_up(event.pos, run, shop_layout, window):
                        continue
                    if shop_hand.on_left_up(event.pos, run, shop_layout, window):
                        continue
                    if handle_shop_click(run, event.pos, shop_layout) == "leave":
                        preview.dismiss()
                        shop_hand.clear()
                        shop_piece.clear()
                        _leave_shop(scene, run, relic_bar)
                elif run.phase in ("preview", "deployment"):
                    before = run.phase
                    deployment.on_release(run, event.pos, board_layout, window)
                    if before != "battle" and run.phase == "battle":
                        scene.begin_banner("battle_start")
                elif run.phase == "battle":
                    handle_battle_click(run, event.pos, board_layout, window, enemy_turn.busy())
                    if run.phase == "victory":
                        settle_finished_board(run)
                        scene.begin_banner("level_complete")
                    elif run.phase == "defeat":
                        settle_finished_board(run)
                        scene.begin_banner("game_over")
                elif run.phase in ("victory", "defeat") and not scene.result_ready():
                    pass
                elif run.phase in ("victory", "defeat", "complete"):
                    action = handle_result_click(run, event.pos, window)
                    if action == "restart":
                        run = run.restart()
                        scene.reset()
                        trait_debug.target_id = None
                        piece_motion.clear()
                        preview.dismiss()
                    elif action == "continue":
                        _continue_victory(scene, run, relic_bar)
        if not visual_test.active and run.phase == "preview":
            run.begin_deployment()
        if run.phase in ("preview", "deployment", "battle", "victory", "defeat"):
            relic_bar.update(dt, run, board_layout)
        elif relic_bar.dragging or relic_bar.armed:
            relic_bar.cancel_pointer()
        if run.phase == "shop":
            shop_piece.update(dt, run, shop_layout, window)
            shop_hand.update(dt, run, shop_layout, window)
        elif shop_piece.dragging or shop_piece.armed:
            shop_piece.clear()
        if visual_test.active and visual_test.game is not None:
            render_battle(screen, assets, visual_test.game, board_layout, relic_bar, run, army=deployment.army)
            _blit_text(
                screen,
                "Trait test",
                get_font(22, bold=True),
                (236, 220, 196),
                center=(board_layout.frame.centerx, board_layout.relics.y + 8),
            )
            draw_trait_tooltip(screen, visual_test.game, board_layout)
        else:
            present(screen, assets, run, deployment, relic_bar, scene, board_layout, shop_layout)
        trait_debug.draw(screen, run)
        if screen_menu.mode and not scene.motion.active:
            screen_menu.draw(screen)
        if not scene.motion.active:
            relics.draw(screen, assets, run, shop_layout)
            if run.phase in ("preview", "deployment", "battle") and not relics.open:
                relic_bar.draw_overlay(screen, assets, run, board_layout)
        gallery.draw(screen, assets, run)
        wood_swirl.draw_debug(screen)
        preview.draw(screen, assets)
        hand = (
            not preview.blocks
            and relic_bar.detail_id is None
            and (
                (run.phase in ("preview", "deployment", "battle") and relic_bar.hover_id is not None)
                or (run.phase == "shop" and (shop_hand.wants_hand(run, shop_layout, window) or shop_piece.wants(run, shop_layout, window)))
                or (
                    run.phase == "victory"
                    and scene.result_ready()
                    and continue_rect(window, run).collidepoint(pygame.mouse.get_pos())
                )
            )
        )
        wanted = pygame.SYSTEM_CURSOR_HAND if hand else pygame.SYSTEM_CURSOR_ARROW
        if cursor != wanted:
            pygame.mouse.set_cursor(wanted)
            cursor = wanted
        pygame.display.flip()
        dt = min(0.05, clock.tick(FPS) / 1000.0)
    pygame.quit()


def _advance_enemy(run, scene, enemy_turn: EnemyTurn, dt: float, visual_test) -> None:
    if visual_test.active or scene.motion.active or run.phase != "battle" or run.battle is None:
        return
    outcome = enemy_turn.update(run.battle, dt, run.rng)
    if outcome == "victory":
        settle_finished_board(run)
        run.finish_victory()
        scene.begin_banner("level_complete")
    elif outcome == "defeat":
        settle_finished_board(run)
        run.finish_defeat()
        scene.begin_banner("game_over")


def _pointer_blocked(scene: SceneManager, event: pygame.event.Event) -> bool:
    if not scene.blocks_pointer():
        return False
    return event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL)


def _continue_victory(scene: SceneManager, run: RunState, relic_bar: RelicBar) -> None:
    destination = "complete" if run.level >= MAX_LEVEL else "shop"
    kind, duration = slide_duration(run.phase, destination)
    relic_bar.close_detail()
    scene.begin(run, run.continue_from_victory, kind, duration)


def _leave_shop(scene: SceneManager, run: RunState, relic_bar: RelicBar) -> None:
    kind, duration = slide_duration("shop", "preview")
    relic_bar.close_detail()
    scene.begin(run, run.leave_shop, kind, duration)


if __name__ == "__main__":
    main()
