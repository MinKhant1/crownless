import pygame

from game.board import Board
from game.game import Game
from game.move import Move
from game.run_state import RunState
from rendering.army_panel import ArmyPanel
from rendering.asset_manager import AssetManager
from rendering.battle_columns import draw_left_sidebar
from rendering.board_renderer import draw_board
from rendering.hud_renderer import draw_background, draw_button, draw_crown, draw_labels
from rendering.layout import Layout, square_at
from rendering.overlay_renderer import draw_trait_tooltip
from rendering.piece_renderer import draw_pieces, draw_trait_sprite


class DeploymentScene:
    def __init__(self) -> None:
        self.press_id: int | None = None
        self.press_pos: tuple[int, int] | None = None
        self.dragging = False
        self.drag_pos: tuple[int, int] | None = None
        self.hover: tuple[int, int] | None = None
        self.army = ArmyPanel()

    def panels(self, window: tuple[int, int], layout: Layout) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
        return layout.left, layout.right, layout.deploy

    def command_buttons(self, layout: Layout) -> tuple[pygame.Rect, pygame.Rect]:
        return layout.reset, layout.start

    def icon_rects(self, run: RunState, layout: Layout) -> list[tuple[int, pygame.Rect]]:
        return self.army.icon_rects(run, layout)

    def display_game(self, run: RunState) -> Game:
        pieces = [enemy.copy() for enemy in run.enemies]
        for piece in run.army.pieces:
            position = run.deployment.placed.get(piece.id)
            if position is None:
                continue
            clone = piece.copy()
            clone.col, clone.row = position
            pieces.append(clone)
        game = Game(Board(pieces))
        game.current_level = run.level
        game.army_size = run.deployment.non_king_count(run.army)
        game.army_capacity = run.army.capacity
        game.turns.in_check = False
        game.turns.finished = False
        game.turns.battle_state = "ongoing"
        game.legal = []
        game.hover = self.hover
        empties, _swaps = self._destinations(run)
        if run.phase == "deployment" and run.selected_piece_id is not None:
            if run.selected_piece_id in run.deployment.placed:
                game.selected_id = run.selected_piece_id
            for col, row in empties:
                game.legal.append(Move(0, 1, col, row))
        return game

    def _destinations(self, run: RunState) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
        if run.phase != "deployment" or run.selected_piece_id is None:
            return [], []
        piece = run.army.piece_by_id(run.selected_piece_id)
        if piece is None:
            return [], []
        current = run.deployment.placed.get(piece.id)
        empties = [
            square
            for square in run.deployment.squares_for(piece, run.blocked_squares(), run.army.capacity, run.army)
            if square != current
        ]
        swaps: list[tuple[int, int]] = []
        for other_id, square in run.deployment.placed.items():
            if other_id == piece.id:
                continue
            other = run.army.piece_by_id(other_id)
            if other is None:
                continue
            if piece.id in run.deployment.placed or other.kind != "king":
                swaps.append(square)
        return empties, swaps

    def on_press(self, run: RunState, pos: tuple[int, int], layout: Layout, window: tuple[int, int]) -> None:
        self.press_pos = pos
        self.dragging = False
        self.drag_pos = pos
        self.press_id = None
        if run.phase != "deployment":
            return
        if layout.left.collidepoint(pos):
            return
        for piece_id, rect in self.icon_rects(run, layout):
            if rect.collidepoint(pos):
                self.press_id = piece_id
                return
        if layout.right.collidepoint(pos):
            return
        square = square_at(layout, pos)
        if square is None:
            return
        placed = run.deployment.piece_id_at(*square)
        if placed is not None:
            self.press_id = placed

    def on_motion(self, pos: tuple[int, int]) -> None:
        self.drag_pos = pos
        if self.press_id is None or self.press_pos is None:
            return
        if abs(pos[0] - self.press_pos[0]) + abs(pos[1] - self.press_pos[1]) > 12:
            self.dragging = True

    def on_release(self, run: RunState, pos: tuple[int, int], layout: Layout, window: tuple[int, int]) -> None:
        left, tray, button = self.panels(window, layout)
        if run.phase == "preview":
            if button.collidepoint(pos):
                run.begin_deployment()
            self._clear_press()
            return
        if run.phase != "deployment":
            self._clear_press()
            return
        reset, start = self.command_buttons(layout)
        if not self.dragging and reset.collidepoint(pos):
            run.reset_formation()
            self._clear_press()
            return
        if not self.dragging and start.collidepoint(pos):
            run.start_battle()
            self._clear_press()
            return
        if self.dragging and self.press_id is not None:
            self._drop(run, pos, layout, tray)
            self._clear_press()
            return
        if self.press_id is not None and not self.dragging:
            self._click_piece(run, self.press_id)
            self._clear_press()
            return
        square = square_at(layout, pos)
        if square is not None and run.selected_piece_id is not None:
            self._move_selected(run, square)
        elif not left.collidepoint(pos):
            run.selected_piece_id = None
        self._clear_press()

    def _move_selected(self, run: RunState, square: tuple[int, int]) -> None:
        selected_id = run.selected_piece_id
        piece = run.army.piece_by_id(selected_id or -1)
        if piece is None or selected_id is None:
            return
        occupant = run.deployment.piece_id_at(*square)
        if occupant is not None and occupant != selected_id:
            if selected_id in run.deployment.placed:
                if not run.swap_deployed_pieces(selected_id, occupant):
                    run.notice = "Square unavailable"
                else:
                    run.selected_piece_id = None
                return
            if run.replace_with_reserve(selected_id, occupant):
                run.selected_piece_id = None
            return
        if selected_id in run.deployment.placed:
            if run.reposition_piece(selected_id, square):
                run.selected_piece_id = None
            return
        if run.deployment.place(piece, square[0], square[1], run.blocked_squares(), run.army.capacity, run.army):
            run.selected_piece_id = None
            run.notice = ""
            return
        full = piece.kind != "king" and run.deployment.non_king_count(run.army) >= run.army.capacity
        run.notice = "Army is full" if full else "Square unavailable"

    def _drop(self, run: RunState, pos: tuple[int, int], layout: Layout, tray: pygame.Rect) -> None:
        piece = run.army.piece_by_id(self.press_id or -1)
        if piece is None:
            return
        square = square_at(layout, pos)
        if square is not None:
            run.selected_piece_id = piece.id
            self._move_selected(run, square)
            return
        if tray.collidepoint(pos):
            if piece.kind == "king":
                run.notice = "King stays"
                return
            if piece.id in run.deployment.placed:
                run.deployment.remove(piece.id)
                run.selected_piece_id = None
                run.notice = ""
                return
        run.notice = "Square unavailable"

    def _click_piece(self, run: RunState, piece_id: int) -> None:
        if run.selected_piece_id == piece_id:
            run.selected_piece_id = None
            run.notice = ""
            return
        selected_id = run.selected_piece_id
        if selected_id is not None:
            if selected_id in run.deployment.placed and piece_id in run.deployment.placed:
                if run.swap_deployed_pieces(selected_id, piece_id):
                    run.selected_piece_id = None
                return
            if selected_id not in run.deployment.placed and piece_id in run.deployment.placed:
                if run.replace_with_reserve(selected_id, piece_id):
                    run.selected_piece_id = None
                return
        run.selected_piece_id = piece_id
        run.notice = ""

    def _clear_press(self) -> None:
        self.press_id = None
        self.press_pos = None
        self.dragging = False
        self.drag_pos = None

    def draw(self, screen: pygame.Surface, assets: AssetManager, run: RunState, layout: Layout, relic_bar=None, backdrop: bool = True) -> None:
        game = self.display_game(run)
        if backdrop:
            draw_background(screen, assets)
        if relic_bar is not None:
            relic_bar.draw_cards(screen, assets, run, layout)
        draw_board(screen, assets, layout)
        draw_labels(screen, layout)
        if run.phase == "deployment":
            _empties, swaps = self._destinations(run)
            for col, row in swaps:
                mark = layout.square_rect(col, row).inflate(-10, -10)
                pygame.draw.rect(screen, (214, 170, 90), mark, width=3, border_radius=8)
        skip = self.press_id if self.dragging else None
        draw_pieces(screen, assets, game, layout, skip_id=skip)
        draw_crown(screen, assets, layout)
        draw_left_sidebar(screen, run, layout)
        self.army.draw(screen, assets, run, layout)
        if run.phase == "preview":
            draw_button(screen, layout.deploy, "Deploy")
        elif run.phase == "deployment":
            _reset, start = self.command_buttons(layout)
            draw_button(screen, start, "Start Battle", enabled=run.validate_deployment(), font_size=18)
        draw_trait_tooltip(screen, game, layout)
        if self.dragging and self.press_id is not None and self.drag_pos is not None:
            piece = run.army.piece_by_id(self.press_id)
            if piece is not None:
                held = pygame.Rect(0, 0, layout.square, layout.square)
                held.center = self.drag_pos
                draw_trait_sprite(
                    screen,
                    assets,
                    piece,
                    held,
                    int(layout.square * 0.84),
                    lift=max(8, layout.square * 0.14),
                )
